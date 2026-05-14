#!/usr/bin/env python3
"""会话开始时显示欢迎消息"""

def SessionStart(session_id: str, hook_context) -> None:
    """会话开始时显示欢迎消息"""
    short_id = session_id[:8] if len(session_id) > 8 else session_id
    print(f"🚀 会话已启动! ID: {short_id}")