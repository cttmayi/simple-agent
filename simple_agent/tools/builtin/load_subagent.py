
"""Load a subagent dynamically."""

from typing import Dict, Any
from simple_agent.tools.registry import get_global_registry, ToolDefinition
from simple_agent.core.events import Event


class LoadSubagent:
    """Load a subagent's full instructions."""

    name = "load_subagent"
    description = "Load a subagent's full instructions by name"

    # This will be set by Runtime
    _subagent_loader = None
    _loaded_subagents = None
    _runtime = None  # Store runtime reference for logging
    _event_bus = None  # Event bus for publishing events

    @classmethod
    def set_runtime(cls, subagent_loader, loaded_subagents, runtime=None, event_bus=None):
        """Set runtime dependencies."""
        cls._subagent_loader = subagent_loader
        cls._loaded_subagents = loaded_subagents
        cls._runtime = runtime
        cls._event_bus = event_bus

    @staticmethod
    def execute(subagent_name: str) -> Dict[str, Any]:
        """Load a subagent's full content.

        Args:
            subagent_name: Name of subagent to load

        Returns:
            Dict with success, message, and optional error
        """
        if LoadSubagent._subagent_loader is None:
            return {
                "success": False,
                "message": "",
                "error": "Subagent loader not initialized"
            }

        if subagent_name in LoadSubagent._loaded_subagents:
            return {
                "success": True,
                "message": f"Subagent '{subagent_name}' is already loaded."
            }

        subagents = LoadSubagent._subagent_loader.list_subagents()
        for subagent in subagents:
            if subagent['name'] == subagent_name:
                LoadSubagent._loaded_subagents.add(subagent_name)
                # Log subagent loaded
                if LoadSubagent._runtime:
                    LoadSubagent._runtime._logger.log_subagent_loaded(subagent_name)

                # Publish subagent_loaded event
                if LoadSubagent._event_bus:
                    LoadSubagent._event_bus.publish(Event("subagent_loaded", {
                        "subagent_name": subagent_name
                    }))

                return {
                    "success": True,
                    "message": f"Loaded subagent: {subagent_name}",
                    "content": subagent['content']
                }

        return {
            "success": False,
            "message": "",
            "error": f"Subagent '{subagent_name}' not found"
        }


# Register with ToolRegistry
load_subagent_tool_def = ToolDefinition(
    name=LoadSubagent.name,
    description=LoadSubagent.description,
    fn=LoadSubagent.execute,
    parameters={
        "type": "object",
        "properties": {
            "subagent_name": {
                "type": "string",
                "description": "Name of the subagent to load"
            }
        },
        "required": ["subagent_name"]
    }
)
