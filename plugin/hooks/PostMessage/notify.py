#!/usr/bin/env python3
"""收到AI响应时记录到共享状态"""

def PostMessage(role: str, content: str, hook_context) -> None:
    """记录助手消息"""
    hook_context.append("assistant_messages", {
        "content": content[:100] + "..." if len(content) > 100 else content
    }, max_items=10)