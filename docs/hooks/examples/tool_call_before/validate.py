#!/usr/bin/env python
"""Example tool_call_before hook - logs and validates tool calls."""

def on_tool_call_before(tool_name: str, arguments: dict) -> dict:
    """Called before a tool is executed.

    Args:
        tool_name: Name of the tool being called
        arguments: Arguments passed to the tool

    Returns:
        dict: Action to take ("continue" or "block")
    """
    # Log the tool call
    print(f"[Hook] Tool call: {tool_name}")

    # Example: Block dangerous commands
    if tool_name == "bash" and "command" in arguments:
        cmd = arguments["command"]
        if "rm -rf /" in cmd:
            return {"action": "block", "message": "禁止删除根目录命令"}

    # Continue with tool execution
    return {"action": "continue"}