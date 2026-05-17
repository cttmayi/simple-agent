"""Run an agent as a subagent in an isolated context."""

from typing import Dict, Any, Optional
from simple_agent.tools.registry import get_global_registry, ToolDefinition
from simple_agent.core.events import Event
from simple_agent.core.subagent import SubAgentRunner
from simple_agent.config.settings import APIConfig
from rich.markup import escape


class RunSubAgent:
    """Run an agent as a subagent with isolated execution context."""

    name = "run_subagent"
    description = "Run a specialized agent as a subagent for a specific task. The agent will have its own execution context and tools."

    # Dependencies set by Runtime
    _agent_loader = None
    _loaded_agents = None
    _api_config: Optional[APIConfig] = None
    _logger = None
    _runtime = None  # Store runtime reference
    _event_bus = None  # Event bus for publishing events
    _renderer = None  # UIRenderer for displaying subagent tool calls

    @classmethod
    def set_runtime(cls, agent_loader, loaded_agents, api_config=None, logger=None, runtime=None, event_bus=None, renderer=None):
        """Set runtime dependencies.

        Args:
            agent_loader: Agent loader instance
            loaded_agents: Set of loaded agent names
            api_config: APIConfig object (not full Settings)
            logger: LLM logger instance
            runtime: Runtime instance
            event_bus: Event bus instance
            renderer: UIRenderer instance for displaying tool calls
        """
        cls._agent_loader = agent_loader
        cls._loaded_agents = loaded_agents
        cls._api_config = api_config
        cls._logger = logger
        cls._runtime = runtime
        cls._event_bus = event_bus
        cls._renderer = renderer

    @staticmethod
    def execute(agent_name: str, task: str, max_turns: int = 10) -> Dict[str, Any]:
        """Run an agent as a subagent for a specific task.

        Args:
            agent_name: Name of the agent to run
            task: The task/question for the agent
            max_turns: Maximum number of conversation turns (default: 10)

        Returns:
            Dict with success, response, and metadata
        """
        if RunSubAgent._agent_loader is None:
            return {
                "success": False,
                "error": "Agent loader not initialized"
            }

        # Find the agent
        agents = RunSubAgent._agent_loader.list_agents()
        agent = None
        for a in agents:
            if a['name'] == agent_name:
                agent = a
                break

        if not agent:
            return {
                "success": False,
                "error": f"Agent '{agent_name}' not found"
            }

        # Get agent's tools from metadata
        agent_tools = agent.get('metadata', {}).get('tools', [])

        # Track first tool call for proper newline
        first_tool_call = [True]

        # Create tool callback for displaying subagent tool calls with indentation
        def tool_callback(tool_name: str, result: Dict[str, Any], arguments: Dict[str, Any]) -> None:
            """Callback to render subagent tool calls with indentation."""
            if not RunSubAgent._renderer:
                return

            # Print newline before first tool call (to separate from run_subagent status line)
            if first_tool_call[0]:
                RunSubAgent._renderer.console.print()  # Add newline
                first_tool_call[0] = False

            # Build args string for display
            args_str = ""
            if arguments and isinstance(arguments, dict):
                args_parts = []
                for k, v in arguments.items():
                    if k not in ["cwd", "timeout", "case_sensitive"]:
                        v_str = str(v)
                        if len(v_str) > 20:
                            v_str = v_str[:20] + "..."
                        args_parts.append(f"{k}={v_str}")
                if args_parts:
                    args_str = '[' + ', '.join(args_parts) + ']'

            # Print indented tool name and args before execution
            if args_str:
                RunSubAgent._renderer.console.print(f"  {tool_name} {escape(args_str)}", end="")
            else:
                RunSubAgent._renderer.console.print(f"  {tool_name}", end="")

            # Show completion status
            tool_result = result.get("result", result)
            success = tool_result.get("success", True)
            status = "[bold green]✓[/bold green]" if success else "[bold red]✗[/bold red]"
            RunSubAgent._renderer.console.print(f" {status}")

            # Render tool result with indentation
            RunSubAgent._renderer.render_tool_result_indented(tool_name, result, arguments)

        # Create subagent runner with tool callback
        runner = SubAgentRunner(
            agent_name=agent_name,
            agent_content=agent['content'],
            agent_tools=agent_tools,
            config=RunSubAgent._api_config,
            logger=RunSubAgent._logger,
            event_bus=RunSubAgent._event_bus,
            tool_callback=tool_callback,
            parent_session_id=RunSubAgent._runtime._session_id if RunSubAgent._runtime else None
        )

        # Track loaded agent
        if RunSubAgent._loaded_agents is not None:
            RunSubAgent._loaded_agents.add(agent_name)

        # Publish AgentLoaded event (for backward compatibility with hooks)
        if RunSubAgent._event_bus:
            RunSubAgent._event_bus.publish(Event("AgentLoaded", {
                "agent_name": agent_name
            }))

        # Run the subagent
        result = runner.run(task, max_turns=max_turns)

        # Return only the response content to the main agent
        # Include subagent_call_id for linking to subagent conversations in web UI
        if result.get("success"):
            return {
                "success": True,
                "content": result.get("response", ""),
                "metadata": result.get("metadata", {}),
            }
        else:
            # On error, include the error message
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "content": result.get("error", "Unknown error"),
            }


# Register with ToolRegistry
run_subagent_tool_def = ToolDefinition(
    name=RunSubAgent.name,
    description=RunSubAgent.description,
    fn=RunSubAgent.execute,
    parameters={
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": "Name of the agent to run"
            },
            "task": {
                "type": "string",
                "description": "The task or question for the agent"
            },
            "max_turns": {
                "type": "integer",
                "description": "Maximum number of conversation turns (default: 10)",
                "default": 10
            }
        },
        "required": ["agent_name", "task"]
    }
)