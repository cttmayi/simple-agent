"""Load an agent dynamically."""

from typing import Dict, Any
from simple_agent.tools.registry import get_global_registry, ToolDefinition
from simple_agent.core.events import Event


class LoadAgent:
    """Load an agent's full instructions."""

    name = "load_agent"
    description = "Load an agent's full instructions by name"

    # This will be set by Runtime
    _agent_loader = None
    _loaded_agents = None
    _runtime = None  # Store runtime reference for logging
    _event_bus = None  # Event bus for publishing events

    @classmethod
    def set_runtime(cls, agent_loader, loaded_agents, runtime=None, event_bus=None):
        """Set runtime dependencies."""
        cls._agent_loader = agent_loader
        cls._loaded_agents = loaded_agents
        cls._runtime = runtime
        cls._event_bus = event_bus

    @staticmethod
    def execute(agent_name: str) -> Dict[str, Any]:
        """Load an agent's full content.

        Args:
            agent_name: Name of agent to load

        Returns:
            Dict with success, message, and optional error
        """
        if LoadAgent._agent_loader is None:
            return {
                "success": False,
                "message": "",
                "error": "Agent loader not initialized"
            }

        if agent_name in LoadAgent._loaded_agents:
            return {
                "success": True,
                "message": f"Agent '{agent_name}' is already loaded.",
            }

        agents = LoadAgent._agent_loader.list_agents()
        for agent in agents:
            if agent['name'] == agent_name:
                LoadAgent._loaded_agents.add(agent_name)
                # Log agent loaded
                if LoadAgent._runtime:
                    LoadAgent._runtime._logger.log_agent_loaded(agent_name)

                # Publish AgentLoaded event
                if LoadAgent._event_bus:
                    LoadAgent._event_bus.publish(Event("AgentLoaded", {
                        "agent_name": agent_name
                    }))

                return {
                    "success": True,
                    "message": f"Loaded agent: {agent_name}",
                    "content": agent['content']
                }

        return {
            "success": False,
            "message": "",
            "error": f"Agent '{agent_name}' not found"
        }


# Register with ToolRegistry
load_agent_tool_def = ToolDefinition(
    name=LoadAgent.name,
    description=LoadAgent.description,
    fn=LoadAgent.execute,
    parameters={
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": "Name of the agent to load"
            }
        },
        "required": ["agent_name"]
    }
)