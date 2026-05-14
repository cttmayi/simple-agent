#!/usr/bin/env python3
"""记录用户发送的消息"""

def UserPromptSubmit(role: str, content: str, hook_context) -> None:
    """记录用户消息到共享状态"""
    hook_context.append("user_messages", {
        "role": role,
        "content": content[:100] + "..." if len(content) > 100 else content
    }, max_items=10)