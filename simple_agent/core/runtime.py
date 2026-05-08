import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from simple_agent.config.settings import Settings
from simple_agent.api.client import APIClient
from simple_agent.core.events import EventBus, Event
from simple_agent.core.session import Session
from simple_agent.core.llm_logger import LLMLogger
from simple_agent.tools.registry import get_global_registry
from simple_agent.tools.dispatcher import ToolDispatcher
from simple_agent.resources.skills import SkillLoader
from simple_agent.resources.subagents import SubagentLoader
from simple_agent.resources.hooks import HookLoader
from simple_agent.resources.commands import CommandLoader
from simple_agent.ui.renderer import UIRenderer

# Import builtin tools to auto-register them
from simple_agent.tools import builtin  # noqa: F401


class Runtime:
    def __init__(self, config: Settings):
        self._config = config
        self._event_bus = EventBus()
        self._session = Session()
        self._renderer = UIRenderer()

        # Initialize logger
        log_dir = Path(config.logging.log_dir) if config.logging.log_dir else None
        self._logger = LLMLogger(log_dir, enabled=config.logging.enabled)

        # Initialize API client with logger
        self._api_client = APIClient(config.api, self._logger)

        # Use global registry (includes builtin tools)
        self._tool_registry = get_global_registry()
        self._tool_dispatcher = ToolDispatcher(self._tool_registry)

        # Initialize resource loaders
        self._skill_loader = SkillLoader(Path(config.paths.skills_dir))
        self._subagent_loader = SubagentLoader(Path(config.paths.subagents_dir))
        self._hook_loader = HookLoader(Path(config.paths.hooks_dir))
        self._command_loader = CommandLoader(Path(config.paths.commands_dir))

        # Load and register hooks
        self._load_hooks()

    def _load_hooks(self):
        """Load and register all hooks."""
        hooks = self._hook_loader.list_hooks()
        for hook in hooks:
            # For now, just log hook discovery
            # Actual hook script execution will be added later
            pass

    def get_agent_context(self) -> Optional[str]:
        """Load AGENT.md from project root."""
        agent_md = Path.cwd() / "AGENT.md"
        if agent_md.exists():
            return agent_md.read_text()
        return None

    def _parse_slash_command(self, input: str) -> tuple[Optional[str], List[str]]:
        """Parse a slash command into command name and arguments."""
        if not input.startswith("/"):
            return None, []

        parts = input[1:].split()
        if not parts:
            return None, []

        command = parts[0]
        args = parts[1:]
        return command, args

    def _handle_slash_command(self, command: str, args: List[str]) -> str:
        """Handle a slash command."""
        if command == "help":
            return "Available commands: /help, /exit"
        elif command == "exit" or command == "quit":
            return "exit"
        return f"Unknown command: /{command}"

    def _handle_tool_calls_in_message(self, msg: Dict[str, Any], response: List[Dict[str, Any]]) -> None:
        """Handle tool calls in a message (recursive for multi-step tool use).

        Args:
            msg: The message containing tool_calls
            response: The full response list containing _request_id
        """
        # Get request_id for tool logging
        request_id = response[0].pop("_request_id", None) if response else None

        self._renderer.render_message("system", f"Executing {len(msg['tool_calls'])} tool(s)...")

        # Add assistant message with tool_calls to session
        self._session.add_message(msg["role"], msg.get("content", ""), tool_calls=msg["tool_calls"])

        # Execute each tool call
        for tool_call in msg["tool_calls"]:
            arguments = json.loads(tool_call["function"]["arguments"])
            result = self._tool_dispatcher.execute({
                "name": tool_call["function"]["name"],
                "arguments": arguments,
            })

            # Log tool execution if logger is available
            if self._logger and request_id:
                self._logger.log_tool_execution(
                    request_id=request_id,
                    tool_name=tool_call["function"]["name"],
                    tool_call_id=tool_call["id"],
                    arguments=arguments,
                    result=result,
                )

            # Format tool result for AI understanding
            # Builtin tools return structured dicts with 'success' field
            # When failed, add clear ERROR prefix for AI to understand
            tool_content = json.dumps(result, ensure_ascii=False, indent=2)

            if not result.get("success", True):
                error_msg = result.get("error", "Unknown error")
                # Add a prominent error indicator for AI
                tool_content = f"[TOOL_ERROR] {error_msg}\n\nDetails:\n{tool_content}"

            # Add tool result to session with tool_call_id
            self._session.add_message("tool", tool_content, tool_call_id=tool_call["id"])
            self._renderer.render_tool_result(tool_call["function"]["name"], result)

        # Send tool results back to API for next response
        messages = self._session.get_messages()
        tools = self._tool_registry.to_openai_format()
        next_response = self._api_client.send_message(messages, tools)

        for next_msg in next_response:
            # Get request_id for next iteration
            request_id = next_msg.pop("_request_id", None)

            if "tool_calls" in next_msg and next_msg["tool_calls"]:
                # More tool calls - recurse
                self._handle_tool_calls_in_message(next_msg, next_response)
            else:
                # Final response with content
                self._session.add_message(next_msg["role"], next_msg.get("content", ""))
                content = next_msg.get("content", "")
                if not content:
                    content = "(工具执行完成，AI 无额外响应)"
                self._renderer.render_message(next_msg["role"], content)

    def process_input(self, input: str) -> str:
        """Process user input."""
        # Check for slash commands
        command, args = self._parse_slash_command(input)
        if command:
            return self._handle_slash_command(command, args)

        # Regular message
        self._session.add_message("user", input)
        return "message_processed"

    def run(self):
        """Main run loop."""
        self._renderer.render_message("system", "Simple Agent started. Type /help for commands.")

        while True:
            try:
                user_input = input("\n> ")
                result = self.process_input(user_input)

                if result == "exit":
                    self._renderer.render_message("system", "Goodbye!")
                    break
                elif result == "message_processed":
                    # Process message with API
                    messages = self._session.get_messages()
                    tools = self._tool_registry.to_openai_format()

                    response = self._api_client.send_message(messages, tools)
                    for msg in response:
                        # Handle tool calls
                        if "tool_calls" in msg and msg["tool_calls"]:
                            self._handle_tool_calls_in_message(msg, response)
                        else:
                            # Regular message (no tool calls)
                            self._session.add_message(msg["role"], msg["content"])
                            self._renderer.render_message(msg["role"], msg["content"])
                else:
                    self._renderer.render_message("system", result)

            except KeyboardInterrupt:
                self._renderer.render_message("system", "\nGoodbye!")
                break
            except Exception as e:
                self._renderer.render_error(str(e))
