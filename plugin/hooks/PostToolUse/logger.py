#!/usr/bin/env python3
"""记录工具调用"""

def PostToolUse(tool_name: str, arguments: dict, result: dict, hook_context) -> None:
    """记录工具调用结果"""
    hook_context.append("tools_used", {
        "name": tool_name,
        "success": result.get("success", False)
    }, max_items=20)