#!/usr/bin/env python3
"""记录运行时错误"""

def Error(error_type: str, error_message: str, hook_context) -> None:
    """记录错误到共享状态"""
    hook_context.append("errors", {
        "type": error_type,
        "message": error_message[:200]
    }, max_items=20)