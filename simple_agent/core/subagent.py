"""Subagent execution system for running agents in isolated contexts."""

from typing import Dict, Any, Optional, List, Callable
from simple_agent.core.session import Session
from simple_agent.api.client import APIClient
from simple_agent.tools.dispatcher import ToolDispatcher
from simple_agent.tools.registry import get_global_registry
from simple_agent.config.settings import APIConfig
from simple_agent.core.llm_logger import LLMLogger
from simple_agent.core.events import Event
import uuid


class SubAgentRunner:
    """Run an agent in an isolated execution context."""

    def __init__(
        self,
        agent_name: str,
        agent_content: str,
        agent_tools: Optional[List[str]] = None,
        config: Optional[APIConfig] = None,
        logger: Optional[LLMLogger] = None,
        event_bus=None,
        tool_callback: Optional[Callable[[str, Dict[str, Any], Dict[str, Any]], None]] = None
    ):
        """Initialize subagent runner.

        Args:
            agent_name: Name of the agent
            agent_content: Full agent content (instructions)
            agent_tools: List of tools the agent can use
            config: API configuration
            logger: LLM logger
            event_bus: Event bus for publishing events
            tool_callback: Optional callback for tool execution (tool_name, result, arguments)
        """
        self._agent_name = agent_name
        self._agent_content = agent_content
        self._agent_tools = agent_tools or []
        self._config = config
        self._logger = logger
        self._event_bus = event_bus
        self._tool_callback = tool_callback

        # Generate a unique call ID for tracking this subagent execution
        self._subagent_call_id = str(uuid.uuid4())

        # Create isolated session
        self._session = Session()

        # Create API client
        if config:
            self._api_client = APIClient(config, logger)
        else:
            self._api_client = None

        # Create tool dispatcher with event bus
        self._tool_registry = get_global_registry()
        self._tool_dispatcher = ToolDispatcher(self._tool_registry, event_bus)

    @property
    def subagent_call_id(self) -> str:
        """Get the subagent call ID for this execution."""
        return self._subagent_call_id

    def run(self, user_message: str, max_turns: int = 10) -> Dict[str, Any]:
        """Run the subagent with a task.

        Args:
            user_message: The task/question for the agent
            max_turns: Maximum number of conversation turns

        Returns:
            Dict with success, response, and metadata
        """
        if not self._api_client:
            return {
                "success": False,
                "error": "API client not configured for subagent"
            }

        # Log subagent invocation
        if self._logger:
            self._logger.log_subagent_invoked(self._agent_name, user_message)

        # Publish SubAgentStart event
        if self._event_bus:
            self._event_bus.publish(Event("SubAgentStart", {
                "agent_name": self._agent_name,
                "user_message": user_message,
                "subagent_call_id": self._subagent_call_id
            }))

        try:
            # Prepare messages with agent instructions as system prompt
            messages = [
                {
                    "role": "system",
                    "content": self._agent_content
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]

            # Filter tools if agent_tools is specified
            tools = self._tool_registry.to_openai_format()
            if self._agent_tools:
                tools = [t for t in tools if t.get("function", {}).get("name") in self._agent_tools]

            # Execute conversation
            final_response = ""
            tool_calls_count = 0

            for turn in range(max_turns):
                # Send message with subagent context for logging
                response = self._api_client.send_message(
                    messages,
                    tools,
                    subagent_call_id=self._subagent_call_id,
                    subagent_agent_name=self._agent_name,
                )

                # Process response messages
                for msg in response:
                    if "tool_calls" in msg and msg["tool_calls"]:
                        # Handle tool calls
                        tool_calls_count += len(msg["tool_calls"])
                        messages.append(msg)

                        # Execute each tool call
                        for tool_call in msg["tool_calls"]:
                            tool_result = self._execute_tool_call(tool_call, msg.get("_request_id"))

                            # Add tool result to messages
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": tool_result.get("content", str(tool_result.get("error", "Failed")))
                            })
                    else:
                        # Regular message
                        content = msg.get("content", "")
                        if content:
                            messages.append(msg)
                            final_response = content
                            # If no tool calls, we're done
                            if not msg.get("tool_calls"):
                                break

                # If we got a response without tool calls, we're done
                if not any(msg.get("tool_calls") for msg in response):
                    break

            # Publish SubAgentComplete event
            if self._event_bus:
                self._event_bus.publish(Event("SubAgentComplete", {
                    "agent_name": self._agent_name,
                    "user_message": user_message,
                    "tool_calls_count": tool_calls_count,
                    "turns_used": turn + 1
                }))

            # Log subagent completion
            if self._logger:
                self._logger.log_subagent_complete(
                    self._subagent_call_id,
                    self._agent_name,
                    tool_calls_count,
                    turn + 1,
                    True  # success
                )

            return {
                "success": True,
                "response": final_response,
                "metadata": {
                    "agent_name": self._agent_name,
                    "tool_calls_count": tool_calls_count,
                    "turns_used": turn + 1,
                    "subagent_call_id": self._subagent_call_id
                }
            }

        except Exception as e:
            # Publish SubAgentError event
            if self._event_bus:
                self._event_bus.publish(Event("SubAgentError", {
                    "agent_name": self._agent_name,
                    "error": str(e)
                }))

            # Log subagent completion with failure
            if self._logger:
                self._logger.log_subagent_complete(
                    self._subagent_call_id,
                    self._agent_name,
                    tool_calls_count,
                    0,
                    False  # success = False
                )

            return {
                "success": False,
                "error": str(e)
            }

    def _execute_tool_call(self, tool_call: Dict[str, Any], request_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a single tool call.

        Args:
            tool_call: Tool call from the API
            request_id: Optional request ID for logging

        Returns:
            Tool execution result
        """
        tool_name = tool_call["function"]["name"]
        tool_call_id = tool_call.get("id", "")

        try:
            arguments = tool_call["function"]["arguments"]
            if isinstance(arguments, str):
                import json
                arguments = json.loads(arguments)

            # Execute tool using dispatcher format
            result = self._tool_dispatcher.execute({"name": tool_name, "arguments": arguments})

            # Log tool execution with subagent context
            if self._logger and request_id:
                self._logger.log_tool_execution(
                    request_id=request_id,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    arguments=arguments,
                    result=result,
                    subagent_call_id=self._subagent_call_id,
                    subagent_agent_name=self._agent_name,
                )

            # Call the tool callback if provided
            if self._tool_callback:
                self._tool_callback(tool_name, result, arguments)

            return result

        except Exception as e:
            error_result = {
                "success": False,
                "error": f"Error executing tool {tool_name}: {str(e)}"
            }

            # Log tool execution with subagent context even on error
            if self._logger and request_id:
                self._logger.log_tool_execution(
                    request_id=request_id,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    arguments=arguments,
                    result=error_result,
                    subagent_call_id=self._subagent_call_id,
                    subagent_agent_name=self._agent_name,
                )

            # Call the tool callback even on error
            if self._tool_callback:
                self._tool_callback(tool_name, error_result, arguments)
            return error_result