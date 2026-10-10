# -*- coding: utf-8 -*-
"""
LangGraph ReAct Agent 核心逻辑
- 加载 .env
- 用 DeepSeek（OpenAI 兼容协议）作为 LLM
- 定义工具（调用 Java 后端 /api/agent/tools/*）
- 用 LangGraph 的 create_react_agent 构造 ReAct 循环
- 支持多轮上下文（_history 模块级维护，后续接 FastAPI 会改成按 session 存）
"""
import os
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from retriever import build_bm25_index, hybrid_search

# 全局懒加载 BM25，避免每次调用都重建索引
_bm25 = None
_manuals = None

def get_bm25_resources():
    global _bm25, _manuals
    if _bm25 is None:
        _bm25, _manuals = build_bm25_index()
    return _bm25, _manuals


# ============ 加载配置 ============
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
JAVA_BASE = os.getenv("JAVA_BACKEND_URL", "http://localhost:8080")

if not DEEPSEEK_API_KEY:
    raise RuntimeError("未找到 DEEPSEEK_API_KEY，请检查 .env 文件")

# ============ 定义 LLM ============
llm = ChatOpenAI(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    temperature=0.3,
    timeout=60,
)


# ============ 定义工具 ============
@tool
def list_devices(status: str = "", device_type: str = "", keyword: str = "", limit: int = 500) -> str:
    """查询设备列表。可按状态（NORMAL/WARNING/FAULT）、设备类型（如'空调'、'电机'）、关键字过滤。
    默认返回全部设备（最多 500 条），一般不需要修改 limit 参数。
    返回体含 total（符合条件的真实总数）、returned（本次返回数）、truncated（是否截断）、devices（设备列表）。"""
    params = {"limit": limit}
    if status:
        params["status"] = status
    if device_type:
        params["deviceType"] = device_type
    if keyword:
        params["keyword"] = keyword
    r = requests.get(f"{JAVA_BASE}/api/agent/tools/devices", params=params, timeout=15)
    r.raise_for_status()
    return r.text


@tool
def get_device_status(device_id: int) -> str:
    """查询某台设备的实时状态、最新遥测数据。参数 device_id 是设备数字 ID。"""
    r = requests.get(f"{JAVA_BASE}/api/agent/tools/device-status",
                     params={"deviceId": device_id}, timeout=15)
    if r.status_code == 404:
        return f"设备不存在：device_id={device_id}"
    r.raise_for_status()
    return r.text


@tool
def search_manual(query: str) -> str:
    """
    当用户询问设备故障原因、故障现象、排查步骤、维修方法时，调用此工具检索本地知识库。
    """
    bm25, manuals = get_bm25_resources()
    results = hybrid_search(query, bm25, manuals, top_k=3)

    if not results:
        return (
            "【知识库未命中】本地知识库中没有找到与该问题高度匹配的故障手册。\n"
            "请告知用户：当前知识库暂无直接匹配的案例，建议生成维修工单，安排维修人员现场排查。"
            "严禁凭空编造故障原因。"
        )

    output_lines = ["检索到以下知识库手册（已按相关度精排）：\n"]
    for i, r in enumerate(results, 1):
        output_lines.append(f"【手册{i}】{r['device_type']} - {r['fault_type']} (相关度: {r.get('rerank_score', 0):.2f})")
        output_lines.append(f"故障现象：{r['fault_phenomenon']}")
        output_lines.append(f"处理方法：{r['repair_method']}\n")

    return "\n".join(output_lines)


@tool
def get_device_telemetry(device_id: int, limit: int = 100) -> str:
    """查询某台设备最近的遥测趋势数据（温度、湿度、电流、电压、振动）。
    limit 默认 100 条，一般不需要调小。
    返回体含 total（该设备遥测总数）、returned、truncated、telemetryList。"""
    r = requests.get(
        f"{JAVA_BASE}/api/agent/tools/telemetry",
        params={"deviceId": device_id, "limit": limit},
        timeout=15,
    )
    r.raise_for_status()
    return r.text


@tool
def list_orders(status: str = "", device_id: int = 0, limit: int = 200) -> str:
    """查询工单列表。可按状态（PENDING_REVIEW/ASSIGNED/REPAIRING/VERIFYING/COMPLETED/REJECTED）和设备 ID 过滤。
    默认返回最多 200 条。
    返回体含 total、returned、truncated、orders。"""
    params = {"limit": limit}
    if status:
        params["status"] = status
    if device_id:
        params["deviceId"] = device_id
    r = requests.get(f"{JAVA_BASE}/api/agent/tools/orders", params=params, timeout=15)
    r.raise_for_status()
    return r.text


@tool
def get_device_summary() -> str:
    """获取设备总览统计。包含 4 个字段：
    - total：设备总数
    - byStatus：按状态分组的台数（NORMAL/WARNING/FAULT）
    - byType：按类型分组的台数
    - byStatusAndType：按"状态×类型"交叉分组的台数（例如 byStatusAndType["FAULT"]["空调"] = 5）

    【必须调用本工具的场景】任何涉及"数量/几台/多少台/分布"的问题，包括：
    - "有多少设备"、"多少台故障"、"多少台告警"
    - "故障设备里各类型分别几台"、"哪些类型故障最多"
    - "异常设备的类型分布"

    【禁止】不要从 list_devices 返回的列表里数数，一律用本工具的字段直接引用。"""
    r = requests.get(f"{JAVA_BASE}/api/agent/tools/device-summary", timeout=15)
    r.raise_for_status()
    return r.text


tools = [list_devices, get_device_status, get_device_telemetry, get_device_summary, search_manual]


# ============ 系统 Prompt ============
SYSTEM_PROMPT = """你是一个设备智能运维助手，服务于实验室设备运维平台。

你的职责：
1. 帮用户查询设备状态、遥测数据、工单信息。
2. 当用户问设备相关问题时，优先调用工具获取**真实数据**再回答，绝不要编造数据。
3. 回答简洁清晰，用中文。
4. 如果工具返回的数据里出现异常数值（如温度>35、湿度>70、电流>20、电压>250、振动>6），主动提醒用户。

【工具返回值说明】返回体含三个关键字段：
- `total`：符合条件的所有记录数（真实总数，以它为准）
- `returned`：本次返回的记录数
- `truncated`：数据是否被截断（returned < total 时为 true）

【关于诊断的严格要求】
1. 当用户询问设备故障的原因、排查方法、维修方案时，你必须调用 search_manual 工具查询知识库。
2. 在给出最终诊断结论前，务必先获取该设备的最新遥测数据（get_device_telemetry）以确认现状。
3. 最终回答必须结合【知识库手册证据】和【实际遥测数据】。不能脱离手册凭空编造原因。
4. 如果知识库检索结果的相关度很低，你必须诚实告知用户“知识库中暂无完全匹配的手册”，并建议生成维修工单（create_repair_order），绝不能强行编造。

【硬性规则】（违反将导致回答不准确，必须严格遵守）
1. 回答里提及"总数/共多少"时，**必须以 total 字段为准**，禁止把 returned 当总数。
2. 工具默认 limit 已经足够大（设备 500、遥测 100、工单 200），**一般情况下不要主动传更小的 limit**。
3. 若 truncated=true，必须告诉用户"以下是前 X 条，共 Y 条"，并建议用筛选条件缩小范围。
4. **不允许反问用户"是否需要我调用工具"或"是否要我查看"**，直接调用工具给出答案。
5. 当用户说"全部""所有""都要看"时，理解为**延续上一轮的话题**，直接调用对应工具（用默认大 limit）拉取数据。
6. 【数据必须现场拉取，禁止引用记忆】
   任何涉及设备/工单**具体数据**的回答——无论用户是否说了"实时/当前"——都必须**重新调用工具**，
   不允许引用你上文记忆里的数字或清单。设备状态是实时变化的，上文记忆可能已过时。

7. 【严格区分"清单"和"统计"两类回答，禁止混淆】
   
   A) 用户问"有哪些 / 列出 / 清单 / 详情"→
      - 只调 list_devices
      - 回答里**只输出设备名称、ID、状态、类型等明细**
      - **绝对不允许输出"按类型 X 台""按状态 Y 台"之类的任何汇总数字**
      - 如果用户想要汇总，让他明确说"统计一下"
   
   B) 用户问"多少台 / 几台 / 统计 / 分布 / 占比"→
      - 只调 get_device_summary
      - 回答里**只输出数字**（total、byStatus、byType、byStatusAndType）
      - **不要列出具体设备清单**
   
   C) 用户同时要清单和统计（例如"有哪些异常设备"）→
      - 先调 get_device_summary 拿数字，再调 list_devices 拿清单
      - 回答里的**数字全部从 summary 引用**，**清单从 list 引用**
   
8. 【绝对红线】任何数字统计（总数、某状态几台、某类型几台、某状态下某类型几台）
   **必须来自 get_device_summary 的字段**，
   **绝对禁止从 list_devices 返回的设备列表里数**——LLM 数数必然出错，
   而且长列表会数错、漏数、顺序错乱。
"""


# ============ 创建 Agent ============
agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT,
)


# ============ 会话历史（命令行测试用；接 FastAPI 后按 session_id 存）============
_history = []


def _build_context_for_llm(history):
    """
    把历史消息压缩成"干净的对话摘要"：
    - 保留 user 消息原文
    - 保留 AI 最终回答的前 120 字（截断，避免 LLM 从摘要里提取数字）
    - 丢弃所有 tool_calls 和 ToolMessage 结构
    """
    from langchain_core.messages import AIMessage, HumanMessage

    clean = []
    for m in history:
        if isinstance(m, HumanMessage):
            clean.append(m)
        elif isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
            truncated = m.content[:120] + "..." if len(m.content) > 120 else m.content
            clean.append(AIMessage(content=truncated))
        # 其他消息（带 tool_calls 的 AI、ToolMessage）一律丢弃
    return clean


def chat(user_input: str, reset: bool = False) -> dict:
    """
    单轮对话。内部维护多轮上下文，但传给 LLM 的历史会被压缩为"摘要"，
    只保留 user 原文 + AI 回答前 120 字，防止 LLM 复用旧数据、反复调工具。
    """
    global _history
    if reset:
        _history = []

    # 1. 构建干净的上下文（不含工具调用结构）
    context = _build_context_for_llm(_history)
    # 2. 加上本轮用户问题
    context = context + [{"role": "user", "content": user_input}]

    # 3. 调用 Agent
    result = agent.invoke({"messages": context})
    messages = result["messages"]

    # 4. 提取本轮新产生的 tool_calls（因为 context 里没有历史的 tool_calls）
    tool_calls = []
    for m in messages:
        calls = getattr(m, "tool_calls", None)
        if calls:
            for c in calls:
                tool_calls.append({"name": c.get("name"), "args": c.get("args")})

    # 5. 找最终回答
    final_answer = ""
    for m in reversed(messages):
        if m.__class__.__name__ == "AIMessage" \
                and m.content \
                and not getattr(m, "tool_calls", None):
            final_answer = m.content
            break

    # 6. 更新历史：只追加本轮 user + 最终 AI 回答（其他丢弃）
    from langchain_core.messages import AIMessage
    _history = _history + [
        {"role": "user", "content": user_input},
        AIMessage(content=final_answer),
    ]

    return {
        "answer": final_answer,
        "tool_calls": tool_calls,
        "messages": messages,
    }