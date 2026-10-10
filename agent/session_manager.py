# -*- coding: utf-8 -*-
"""
多会话管理：每个 session_id 独立维护一份对话历史。
命令行版本用模块级 _history 只支持单用户，Web 版必须按 session 隔离。
内存版实现，生产可换 Redis。
"""
from typing import Dict, List
from langchain_core.messages import AIMessage

# 每个 session_id 对应一条消息历史（只保留 user + AI 摘要）
_sessions: Dict[str, List] = {}

# 单会话最多保留多少轮（防止 context 无限长）
MAX_TURNS = 20


def get_history(session_id: str) -> List:
    """获取某个会话的历史"""
    return _sessions.get(session_id, [])


def append_turn(session_id: str, user_input: str, ai_answer: str):
    """追加一轮对话到历史（只存 user + AI 回答摘要）"""
    if session_id not in _sessions:
        _sessions[session_id] = []

    _sessions[session_id].append({"role": "user", "content": user_input})
    _sessions[session_id].append(AIMessage(content=ai_answer))

    # 超长时丢弃最早的消息（保留最近的 MAX_TURNS 轮）
    if len(_sessions[session_id]) > MAX_TURNS * 2:
        _sessions[session_id] = _sessions[session_id][-MAX_TURNS * 2:]


def build_context(session_id: str, user_input: str) -> List:
    """
    构造本轮发给 LLM 的消息列表。
    只保留 user 原文 + AI 回答前 120 字，杜绝 LLM 复用旧数据。
    """
    history = get_history(session_id)
    clean = []
    for m in history:
        if isinstance(m, dict) and m.get("role") == "user":
            clean.append(m)
        elif isinstance(m, AIMessage):
            content = m.content or ""
            truncated = content[:120] + "..." if len(content) > 120 else content
            clean.append(AIMessage(content=truncated))
    clean.append({"role": "user", "content": user_input})
    return clean


def clear_session(session_id: str):
    """清空某个会话"""
    _sessions.pop(session_id, None)


def list_sessions():
    """列出所有活跃会话（调试用）"""
    return list(_sessions.keys())