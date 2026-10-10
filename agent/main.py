# -*- coding: utf-8 -*-
"""
FastAPI 入口：暴露 /api/health 和 /api/chat/stream (SSE)
"""
import json
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agent_core import agent, tools
from session_manager import build_context, append_turn, clear_session, list_sessions

app = FastAPI(title="AI-Native 设备运维 Agent")

# 允许前端跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 请求模型 ====================
class ChatRequest(BaseModel):
    session_id: str = ""
    message: str


# ==================== 健康检查 ====================
@app.get("/api/health")
def health():
    return {"service": "ai-ops-agent", "status": "UP"}


# ==================== 会话管理 ====================
@app.post("/api/chat/session")
def new_session():
    """创建一个新会话，返回 session_id"""
    return {"session_id": str(uuid.uuid4())}


@app.delete("/api/chat/session/{session_id}")
def del_session(session_id: str):
    clear_session(session_id)
    return {"message": "会话已清空"}


@app.get("/api/chat/sessions")
def get_sessions():
    """调试用：列出所有会话"""
    return {"sessions": list_sessions()}


# ==================== 核心：SSE 流式对话 ====================
@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    """
    SSE 流式接口。事件类型：
    - event: start     / 开始
    - event: thinking  / LLM 思考中（每轮 ReAct 循环开始）
    - event: tool_call / 正在调用工具
    - event: tool_result / 工具返回
    - event: token     / LLM 生成的 token 片段
    - event: done      / 完成，含完整回答
    - event: error     / 出错
    """
    session_id = req.session_id or str(uuid.uuid4())

    async def event_generator():
        try:
            # 0) 通知前端 session_id（首次会话时）
            yield {
                "event": "start",
                "data": json.dumps({"session_id": session_id}),
            }

            # 1) 构造上下文
            context = build_context(session_id, req.message)

            # 2) 用 astream_events 拿到 LangGraph 的所有事件
            final_answer = ""
            tool_calls_record = []

            async for event in agent.astream_events(
                {"messages": context}, version="v2"
            ):
                if await request.is_disconnected():
                    return

                kind = event.get("event")

                # LLM 开始新一轮
                if kind == "on_chat_model_start":
                    yield {
                        "event": "thinking",
                        "data": json.dumps({"msg": "模型开始思考"}),
                    }

                # LLM 逐 token 输出
                elif kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and getattr(chunk, "content", None):
                        content = chunk.content
                        if isinstance(content, str) and content:
                            yield {
                                "event": "token",
                                "data": json.dumps({"text": content}),
                            }

                # 工具开始调用
                elif kind == "on_tool_start":
                    name = event.get("name", "")
                    inputs = event["data"].get("input", {})
                    tool_calls_record.append({"name": name, "args": inputs})
                    yield {
                        "event": "tool_call",
                        "data": json.dumps({"name": name, "args": inputs}),
                    }

                # 工具返回结果
                elif kind == "on_tool_end":
                    output = event["data"].get("output", "")
                    # 输出太长就截断，避免 SSE payload 过大
                    if isinstance(output, str):
                        preview = output[:300] + ("..." if len(output) > 300 else "")
                    else:
                        preview = str(output)[:300]
                    yield {
                        "event": "tool_result",
                        "data": json.dumps({"preview": preview}),
                    }

                # Agent 结束（拿到最终回答）
                elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                    output = event["data"].get("output", {})
                    if isinstance(output, dict) and "messages" in output:
                        msgs = output["messages"]
                        for m in reversed(msgs):
                            if m.__class__.__name__ == "AIMessage" \
                                    and m.content \
                                    and not getattr(m, "tool_calls", None):
                                final_answer = m.content
                                break

            # 3) 保存到会话历史
            append_turn(session_id, req.message, final_answer)

            # 4) 发送完成事件
            yield {
                "event": "done",
                "data": json.dumps({
                    "session_id": session_id,
                    "answer": final_answer,
                    "tool_calls": tool_calls_record,
                }),
            }

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}),
            }

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)