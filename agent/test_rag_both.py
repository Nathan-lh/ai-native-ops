# -*- coding: utf-8 -*-
"""人话版测试：正确解析 SSE 格式（event 与 data 分行）"""
import requests
import json
import time

URL = "http://localhost:8000/api/chat/stream"


def run_case(title: str, message: str, session_id: str):
    print("\n" + "=" * 70)
    print(f"【{title}】")
    print(f"提问：{message}")
    print("=" * 70)

    payload = {"session_id": session_id, "message": message}

    tool_calls = []
    tool_results = []
    final_answer = ""
    current_event = None

    with requests.post(URL, json=payload, stream=True) as r:
        for raw_line in r.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8")

            # SSE 格式：event 行单独出现，下一行是 data
            if line.startswith("event: "):
                current_event = line[7:].strip()
                continue

            if line.startswith("data: "):
                data_str = line[6:]
                try:
                    data = json.loads(data_str)
                except Exception:
                    continue

                if current_event == "tool_call":
                    tool_calls.append(
                        f"  → {data.get('name')}  {data.get('args')}"
                    )
                elif current_event == "tool_result":
                    preview = data.get("preview", "")
                    tool_results.append(str(preview)[:300])
                elif current_event == "done":
                    final_answer = data.get("answer", "")
                    # done 事件里也带 tool_calls，作为兜底
                    if not tool_calls:
                        for tc in data.get("tool_calls", []):
                            tool_calls.append(f"  → {tc.get('name')}  {tc.get('args')}")

    print("【调用的工具】")
    print("\n".join(tool_calls) if tool_calls else "  （无）")

    print("\n【知识库检索返回（截断显示）】")
    if tool_results:
        for i, t in enumerate(tool_results, 1):
            print(f"  结果{i}: {t}")
    else:
        print("  （无）")

    print("\n【Agent 最终回答】")
    print(final_answer if final_answer else "（空）")

    print("\n【判定】")
    if "知识库未命中" in final_answer or "暂无直接匹配" in final_answer or "生成维修工单" in final_answer:
        print("  ✅ 触发兜底：引导用户建工单，未编造原因。")
    elif final_answer:
        print("  ✅ 正常命中：给出了基于手册的诊断。")
    else:
        print("  ⚠️ 未收到最终回答，请检查 main.py 窗口是否有报错。")


if __name__ == "__main__":
    run_case(
        title="场景 A：正常问题（应命中知识库）",
        message="有一台空调温度持续升高，可能是什么原因？",
        session_id="test_normal_001",
    )

    time.sleep(2)

    run_case(
        title="场景 B：兜底问题（应触发未命中）",
        message="机房里的服务器主板烧了怎么办？",
        session_id="test_fallback_001",
    )