import inspect
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
