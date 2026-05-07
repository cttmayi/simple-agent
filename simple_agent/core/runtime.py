import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from simple_agent.config.settings import Settings
from simple_agent.api.client import APIClient
from simple_agent.core.events import EventBus, Event
from simple_agent.core.session import Session
from simple_agent.tools.registry import ToolRegistry
from simple_agent.tools.dispatcher import ToolDispatcher
from simple_agent.resources.skills import SkillLoader
from simple_agent.resources.subagents import SubagentLoader
from simple_agent.resources.hooks import HookLoader
from simple_agent.resources.commands import CommandLoader
from simple_agent.ui.renderer import UIRenderer


class Runtime:
    def __init__(self, config: Settings):
        self._config = config
        self._event_bus = EventBus()
        self._session = Session()
        self._renderer = UIRenderer()
        self._api_client = APIClient(config.api)
        self._tool_registry = ToolRegistry()
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
                        self._session.add_message(msg["role"], msg["content"])
                        self._renderer.render_message(msg["role"], msg["content"])

                        # Handle tool calls
                        if "tool_calls" in msg:
                            for tool_call in msg["tool_calls"]:
                                result = self._tool_dispatcher.execute({
                                    "name": tool_call["function"]["name"],
                                    "arguments": json.loads(tool_call["function"]["arguments"]),
                                })
                                self._session.add_message("tool", str(result))
                else:
                    self._renderer.render_message("system", result)

            except KeyboardInterrupt:
                self._renderer.render_message("system", "\nGoodbye!")
                break
            except Exception as e:
                self._renderer.render_error(str(e))
