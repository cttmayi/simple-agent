#!/usr/bin/env python3
"""工具调用失败时记录错误"""

def ToolUseFailed(tool_name: str, arguments: dict, error: str, hook_context) -> None:
    """记录失败的工具调用"""
    hook_context.append("errors", {
        "tool": tool_name,
        "error": error[:200]
    }, max_items=10)