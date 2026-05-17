import inspect
import time
from typing import Any, Dict
from simple_agent.tools.registry import ToolRegistry
from simple_agent.core.events import Event, HookBlockedException


class ToolDispatcher:
    def __init__(self, registry: ToolRegistry, event_bus=None):
        self._registry = registry
        self._event_bus = event_bus

    def execute(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return result."""
        name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})

        # Publish PreToolUse event
        if self._event_bus:
            try:
                self._event_bus.publish(Event("PreToolUse", {
                    "tool_name": name,
                    "arguments": arguments
                }))
            except HookBlockedException:
                # Hook blocked the tool call, return error result
                return {
                    "success": False,
                    "error": "Tool call blocked by hook"
                }

        # Tool-specific pre-hooks
        if name == "bash" and self._event_bus:
            self._event_bus.publish(Event("BeforeBash", {
                "command": arguments.get("command", ""),
                "cwd": arguments.get("cwd", ""),
                "timeout": arguments.get("timeout", 30)
            }))
        elif name in ("read", "write") and self._event_bus:
            file_path = arguments.get("file_path", "")
            if name == "read":
                # Read doesn't have oldContent/newContent, just file path
                old_content = ""
                new_content = ""
            else:  # write
                old_content = arguments.get("old_content", "")
                new_content = arguments.get("content", "")

            self._event_bus.publish(Event("BeforeEdit", {
                "file_path": file_path,
                "old_content": old_content,
                "new_content": new_content
            }))

        # Track start time for SubagentStop duration calculation
        start_time = time.time()

        try:
            result = self._registry.execute_tool(name, arguments)
            if result is None:
                return {"success": False, "error": f"Tool '{name}' not found"}
            # Builtin tools return structured dicts with 'success' field
            # Custom tools might return other formats - check for success field
            if isinstance(result, dict) and "success" in result:
                # Already has correct format
                pass
            else:
                # Custom tool without success field - wrap it
                result = {"success": True, "result": result}

            # Tool-specific post-hooks
            if name == "bash" and self._event_bus:
                self._event_bus.publish(Event("AfterBash", {
                    "command": arguments.get("command", ""),
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "returncode": result.get("returncode", 0),
                    "success": result.get("success", True)
                }))
            elif name in ("read", "write") and self._event_bus:
                file_path = arguments.get("file_path", "")
                final_content = result.get("content", "") if name == "read" else arguments.get("content", "")
                self._event_bus.publish(Event("AfterEdit", {
                    "file_path": file_path,
                    "final_content": final_content,
                    "success": result.get("success", True)
                }))

            # Publish PostToolUse event
            if self._event_bus:
                self._event_bus.publish(Event("PostToolUse", {
                    "tool_name": name,
                    "arguments": arguments,
                    "result": result
                }))

            return result
        except TypeError as e:
            return {"success": False, "error": f"Invalid arguments: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
