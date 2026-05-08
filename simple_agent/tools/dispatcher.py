import inspect
from typing import Any, Dict
from simple_agent.tools.registry import ToolRegistry


class ToolDispatcher:
    def __init__(self, registry: ToolRegistry):
        self._registry = registry

    def execute(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return result."""
        name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})

        try:
            result = self._registry.execute_tool(name, arguments)
            if result is None:
                return {"success": False, "error": f"Tool '{name}' not found"}
            # If result already has success field (from builtin tools), return as-is
            # Otherwise, wrap in success format
            if isinstance(result, dict) and "success" in result:
                return result
            return {"success": True, "result": result}
        except TypeError as e:
            return {"success": False, "error": f"Invalid arguments: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
