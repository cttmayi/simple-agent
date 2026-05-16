#!/usr/bin/env python3
"""记录工具调用"""

def PostToolUse(tool_name: str, arguments: dict, result: dict, hook_context) -> None:
    """记录工具调用结果"""
    hook_context.tools_called += 1
    if result.get("success", False):
        hook_context.tools_succeeded += 1
    else:
        hook_context.tools_failed += 1
    hook_context.append("tools_used", {
        "name": tool_name,
        "success": result.get("success", False)
    }, max_items=20)