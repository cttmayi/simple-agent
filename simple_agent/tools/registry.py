import inspect
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from functools import wraps

_registry = None


def get_global_registry() -> "ToolRegistry":
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


@dataclass
class ToolDefinition:
    name: str
    description: str
    fn: Callable
    parameters: Dict[str, Any]


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool_def: ToolDefinition) -> None:
        self._tools[tool_def.name] = tool_def

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        tool_def = self.get_tool(name)
        if tool_def is None:
            return None
        return tool_def.fn(**arguments)

    def list_tools(self) -> List[Dict[str, str]]:
        return [
            {
                "name": t.name,
                "description": t.description,
            }
            for t in self._tools.values()
        ]

    def to_openai_format(self, allowed: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Export tools in OpenAI function calling format.

        Args:
            allowed: Optional list of allowed tool names. If provided, only
                    tools in this list will be exported. If None, all tools
                    are exported.

        Returns:
            List of tools in OpenAI function calling format.
        """
        if allowed is not None:
            allowed_set = set(allowed)
            tools = [t for t in self._tools.values() if t.name in allowed_set]
        else:
            tools = self._tools.values()

        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    def snapshot(self) -> Dict[str, ToolDefinition]:
        """Save current tool state as a copy."""
        return self._tools.copy()

    def restore(self, snapshot: Dict[str, ToolDefinition]) -> None:
        """Restore tool state from snapshot."""
        self._tools = snapshot.copy()

    def filter(self, allowed: List[str]) -> None:
        """Filter tools to only include those in the allowed list.

        Args:
            allowed: List of tool names to allow
        """
        allowed_set = set(allowed)
        self._tools = {
            name: tool for name, tool in self._tools.items()
            if name in allowed_set
        }


def tool(name: Optional[str] = None, description: str = "", registry: Optional["ToolRegistry"] = None):
    """Decorator to register a function as a tool."""

    def decorator(fn: Callable):
        tool_name = name or fn.__name__

        # Build parameter schema from function signature
        sig = inspect.signature(fn)
        parameters = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for param_name, param in sig.parameters.items():
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else "string"
            param_type_str = "string"

            if param_type == int:
                param_type_str = "integer"
            elif param_type == float:
                param_type_str = "number"
            elif param_type == bool:
                param_type_str = "boolean"
            elif param_type == list:
                param_type_str = "array"

            parameters["properties"][param_name] = {"type": param_type_str}

            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)

        tool_def = ToolDefinition(
            name=tool_name,
            description=description,
            fn=fn,
            parameters=parameters,
        )

        # Use provided registry or global registry
        target_registry = registry or get_global_registry()
        target_registry.register(tool_def)
        return fn

    return decorator
