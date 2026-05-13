import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
from simple_agent.config.settings import Settings
from simple_agent.api.client import APIClient
from simple_agent.core.events import EventBus, Event, HookBlockedException, HookContext
from simple_agent.core.session import Session
from simple_agent.core.llm_logger import LLMLogger
from simple_agent.tools.registry import get_global_registry
from simple_agent.tools.dispatcher import ToolDispatcher
from simple_agent.resources.skills import SkillLoader
from simple_agent.resources.subagents import SubagentLoader
from simple_agent.resources.hooks import HookLoader
from simple_agent.resources.commands import CommandLoader
from simple_agent.ui.renderer import UIRenderer
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.history import InMemoryHistory

# Import builtin tools to auto-register them
from simple_agent.tools import builtin  # noqa: F401
from simple_agent.tools.builtin.load_skill import LoadSkill
from simple_agent.tools.builtin.load_subagent import LoadSubagent


class Runtime:
    def __init__(self, config: Settings, log_file: Optional[str] = None):
        self._config = config
        self._event_bus = EventBus()
        self._session = Session()
        self._renderer = UIRenderer()
        self._session_id: Optional[str] = None
        # Initialize HookContext singleton
        self._hook_context = HookContext()
        # Initialize prompt session with history for better input handling (especially for Chinese characters)
        self._prompt_session = PromptSession(
            history=InMemoryHistory()
        )

        # Initialize logger
        # Use configured log_dir or default to ./.simple-agent/logs
        log_dir = Path(config.logging.log_dir) if config.logging.log_dir else Path.cwd() / ".simple-agent" / "logs"
        self._logger = LLMLogger(log_dir, enabled=config.logging.enabled, log_file=log_file)

        # Initialize API client with logger
        self._api_client = APIClient(config.api, self._logger)

        # Use global registry (includes builtin tools)
        self._tool_registry = get_global_registry()
        self._tool_dispatcher = ToolDispatcher(self._tool_registry, self._event_bus)

        # Initialize resource loaders (resolve relative paths from current directory)
        base_dir = Path.cwd()
        self._skill_loader = SkillLoader(base_dir / config.paths.skills_dir)
        self._subagent_loader = SubagentLoader(base_dir / config.paths.subagents_dir)
        self._hook_loader = HookLoader(base_dir / config.paths.hooks_dir)
        self._command_loader = CommandLoader(base_dir / config.paths.commands_dir)

        # Load and register hooks
        self._load_hooks()

        # Load skills and build skills context (only metadata for lazy loading)
        self._skills_context = self._build_skills_context()
        self._loaded_skills = set()  # Track which skills have been fully loaded

        # Load subagents and build subagents context (only metadata for lazy loading)
        self._subagents_context = self._build_subagents_context()
        self._loaded_subagents = set()  # Track which subagents have been fully loaded

        # Set up load_skill and load_subagent tools
        LoadSkill.set_runtime(self._skill_loader, self._loaded_skills, self, self._event_bus)
        LoadSubagent.set_runtime(self._subagent_loader, self._loaded_subagents, self, self._event_bus)

        # Register the tool definitions
        from simple_agent.tools.builtin.load_skill import load_skill_tool_def
        from simple_agent.tools.builtin.load_subagent import load_subagent_tool_def
        self._tool_registry.register(load_skill_tool_def)
        self._tool_registry.register(load_subagent_tool_def)

    def _build_skills_context(self) -> str:
        """Build context string from all available skills (metadata only for lazy loading)."""
        skills = self._skill_loader.list_skills()
        if not skills:
            return ""

        context_parts = ["# Available Skills\n"]
        context_parts.append("The following skills are available. Ask to load them by name.\n\n")

        for skill in skills:
            context_parts.append(f"- **{skill['name']}**: {skill['description']}")

        return "\n".join(context_parts)

    def _build_subagents_context(self) -> str:
        """Build context string from all available subagents (metadata only for lazy loading)."""
        subagents = self._subagent_loader.list_subagents()
        if not subagents:
            return ""

        context_parts = ["# Available Subagents\n"]
        context_parts.append("The following subagents are available. Mention them in your request to auto-load.\n\n")

        for subagent in subagents:
            tools = subagent['metadata'].get('tools', [])
            tools_str = ', '.join(tools) if tools else 'all tools'
            context_parts.append(f"- **{subagent['name']}**: {subagent['description']}")
            context_parts.append(f"  Tools: {tools_str}\n")

        return "\n".join(context_parts)

    def _load_hooks(self):
        """Load and register all hooks."""
        hooks = self._hook_loader.list_hooks()

        for hook in hooks:
            event_name = hook["event_name"]

            # For each event, create a handler
            def make_handler(hook_data, evt_name):
                def handler(event_obj):
                    result = self._execute_hook(hook_data, event_obj)

                    # Handle block return value
                    if result and result.get("action") == "block":
                        message = result.get("message", "Hook blocked execution")

                        # 1. Terminal display (already shown in _execute_python_hook)
                        # 2. Log to logger
                        if self._logger:
                            self._logger.log_hook_block(
                                event_name=event_obj.name,
                                hook_name=hook_data["event_name"],
                                message=message
                            )
                        # 3. Send to AI (via session.add_message)
                        self._session.add_message("system", f"[BLOCKED] {message}")

                        # Throw exception to interrupt flow (only for tool_call_before)
                        raise HookBlockedException(message)
                return handler

            self._event_bus.subscribe(event_name, make_handler(hook, event_name))

            # Publish hook_loaded event
            self._event_bus.publish(Event("hook_loaded", {"hook_name": hook["event_name"]}))

    def _execute_hook(self, hook: Dict[str, Any], event: Event) -> Optional[dict]:
        """Execute hook.

        Args:
            hook: Hook data {"event_name", "path", "files"}
            event: Event object

        Returns:
            dict or None: {"action": "block", "message": "..."} indicates block
        """
        hook_dir = Path(hook["path"])

        for filename in hook["files"]:
            filepath = hook_dir / filename
            ext = filepath.suffix.lower()

            try:
                if ext == ".py":
                    result = self._execute_python_hook(filepath, event)
                    if result and result.get("action") == "block":
                        return result
                elif ext in [".sh", ".cmd"]:
                    self._execute_shell_hook(filepath, event)
                elif ext == ".md":
                    self._execute_prompt_hook(filepath, event)
            except Exception as e:
                self._renderer.render_message("system", f"Hook {filename} failed: {str(e)}")

        return None

    def _execute_python_hook(self, filepath: Path, event: Event) -> Optional[dict]:
        """Execute Python hook and return result.

        Args:
            filepath: Python hook file path
            event: Event object

        Returns:
            dict: Hook return value, possibly {"action": "block", "message": "..."}
        """
        import importlib.util
        import sys
        import re
        import inspect

        module_name = f"hook_{filepath.stem}"
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        event_name = event.name
        # Convert PascalCase to snake_case (e.g., "SessionStart" → "session_start")
        snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', event_name).lower()

        # Legacy name mapping for backward compatibility
        legacy_names = {
            "SessionStart": "session_start",
            "Stop": "session_end",
            "UserPromptSubmit": "message_sent",
            "PostMessage": "message_received",
            "PreToolUse": "tool_call_before",
            "PostToolUse": "tool_call_after",
            "ToolUseFailed": "tool_call_failed",
            "Error": "error_occurred",
        }
        legacy_name = legacy_names.get(event_name)

        # Try multiple function name patterns:
        func_names = [
            event_name,                           # "SessionStart"
            snake_name,                           # "session_start"
            legacy_name,                          # "session_end" (for Stop)
            f"on_{event_name}",                   # "on_SessionStart"
            f"on_{snake_name}",                   # "on_session_start"
            f"on_{legacy_name}",                  # "on_session_end" (if legacy_name exists)
        ]
        # Filter out None values
        func_names = [f for f in func_names if f is not None]

        for func_name in func_names:
            if hasattr(module, func_name):
                func = getattr(module, func_name)
                # Get function signature and filter arguments
                sig = inspect.signature(func)
                # Filter event.data to only include parameters the function accepts
                filtered_args = {k: v for k, v in event.data.items() if k in sig.parameters}
                result = func(**filtered_args)
                return result

        return None

    def _execute_shell_hook(self, filepath: Path, event: Event) -> None:
        """Execute Shell hook.

        Args:
            filepath: Shell script file path
            event: Event object
        """
        import subprocess

        try:
            result = subprocess.run(
                f"sh {filepath}" if filepath.suffix == ".sh" else filepath,
                shell=True,
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.stdout:
                self._renderer.render_message("system", result.stdout.strip())
            if result.stderr:
                self._renderer.render_message("system", f"Hook stderr: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            self._renderer.render_message("system", "Shell hook timed out")

    def _execute_prompt_hook(self, filepath: Path, event: Event) -> None:
        """Execute Prompt hook (simplified version, displays content).

        Args:
            filepath: Markdown file path
            event: Event object
        """
        prompt_content = filepath.read_text()

        variables = event.data or {}
        for key, value in variables.items():
            prompt_content = prompt_content.replace(f"{{{{{key}}}}}", str(value))

        # TODO: Full implementation should send to LLM
        self._renderer.render_message("system", f"[Prompt Hook] {prompt_content[:100]}...")

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
            skills = self._skill_loader.list_skills()
            subagents = self._subagent_loader.list_subagents()
            help_text = "# Available Commands\n\n- `/help` - Show this help message\n- `/exit` - Exit the agent\n\n"
            help_text += "AI can automatically load skills and subagents by mentioning them in your request.\n"

            if skills:
                help_text += "\n# Available Skills\n\n"
                for skill in skills:
                    help_text += f"- **{skill['name']}**: {skill['description']}\n"

            if subagents:
                help_text += "\n# Available Subagents\n\n"
                for subagent in subagents:
                    tools = subagent['metadata'].get('tools', [])
                    tools_str = ', '.join(tools) if tools else 'all tools'
                    help_text += f"- **{subagent['name']}**: {subagent['description']}\n"
                    help_text += f"  Tools: {tools_str}\n"

            return help_text
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

        # Add assistant message with tool_calls to session
        self._session.add_message(msg["role"], msg.get("content", ""), tool_calls=msg["tool_calls"])

        # Execute each tool call and show details
        for tool_call in msg["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])

            # Show which tool is being executed with details
            args_str = ""
            if arguments:
                args_parts = []
                for k, v in arguments.items():
                    if k not in ["cwd", "timeout", "case_sensitive"]:  # Skip internal params
                        v_str = str(v)
                        if len(v_str) > 50:
                            v_str = v_str[:50] + "..."
                        args_parts.append(f"{k}={v_str}")
                if args_parts:
                    args_str = " " + " ".join(args_parts)
            self._renderer.render_message("system", f"Running {tool_name}{args_str}")

            # Execute the tool
            result = self._tool_dispatcher.execute({
                "name": tool_name,
                "arguments": arguments,
            })

            # Log tool execution if logger is available (before any formatting)
            if self._logger and request_id:
                self._logger.log_tool_execution(
                    request_id=request_id,
                    tool_name=tool_name,
                    tool_call_id=tool_call["id"],
                    arguments=arguments,
                    result=result,
                )

            # Handle load_skill and load_subagent tools specially
            # These tools are handled separately - content is added to session
            # and we don't format/send their result to the API
            if tool_name not in ["load_skill", "load_subagent"]:
                # Regular tool - normal processing
                tool_result = result.get("result", result)

                # Format tool result for AI understanding
                # Builtin tools return structured dicts with 'success' field
                # Dispatcher may wrap results: {"success": True, "result": ...}
                # or return builtin result directly when it already has 'success' field

                # Build concise content for API (to avoid Extra data errors)
                if not tool_result.get("success", True):
                    # Tool failed - send error message
                    error_msg = tool_result.get("error", "Unknown error")
                    tool_content = f"[TOOL_ERROR] {error_msg}"
                elif "stdout" in tool_result:
                    # Shell command - show stdout/stderr
                    stdout = tool_result.get("stdout", "").strip()
                    stderr = tool_result.get("stderr", "").strip()
                    if stderr:
                        tool_content = f"Output:\n{stdout}\nErrors:\n{stderr}"
                    else:
                        tool_content = f"Output:\n{stdout}"
                elif "content" in tool_result:
                    # File read - show content
                    content = tool_result.get("content", "")
                    if len(content) > 500:
                        content = content[:500] + "..."
                    tool_content = f"Content:\n{content}"
                elif "matches" in tool_result:
                    # Grep - show match count and samples
                    matches = tool_result.get("matches", [])
                    if matches:
                        tool_content = f"Found {len(matches)} matches. First few:\n{matches[:3]}"
                    else:
                        tool_content = "No matches found"
                elif "results" in tool_result:
                    # Web search - show result count
                    results = tool_result.get("results", [])
                    tool_content = f"Found {len(results)} results"
                else:
                    tool_content = str(tool_result)

                # Add tool result to session with tool_call_id
                self._session.add_message("tool", tool_content, tool_call_id=tool_call["id"])
            else:
                # Send message to user for load_skill/load_subagent
                self._renderer.render_message("system", result.get("message", ""))

        # Send tool results back to API for next response
        messages = self._prepare_messages_with_context()
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

                # Publish PostMessage event
                if content:
                    self._event_bus.publish(Event("PostMessage", {
                        "role": next_msg["role"],
                        "content": content,
                        "hook_context": self._hook_context
                    }))

    def _prepare_messages_with_context(self) -> List[Dict[str, str]]:
        """Prepare messages with skills, subagents, and agent context."""
        messages = self._session.get_messages()

        # Build system context with skills, subagents, and AGENT.md
        system_parts = []

        # Add skills context
        if self._skills_context:
            system_parts.append(self._skills_context)

        # Add subagents context
        if self._subagents_context:
            system_parts.append(self._subagents_context)

        # Add AGENT.md context
        agent_context = self.get_agent_context()
        if agent_context:
            system_parts.append("# Agent Context\n")
            system_parts.append(agent_context)

        # Add manually loaded skills/subagents from session
        # These are added via /load-skill and /load-subagent commands
        manually_loaded_context = []
        for msg in messages:
            if msg.get("role") == "system" and msg.get("content"):
                content = msg.get("content", "")
                # Check if it's a manually loaded skill or subagent
                if content.startswith("# Skill:") or content.startswith("# Subagent:"):
                    manually_loaded_context.append(content)

        # Combine all system parts
        if manually_loaded_context:
            system_parts.extend(manually_loaded_context)

        # Prepare messages for API
        api_messages = []

        # Add combined system context if available
        if system_parts:
            api_messages.append({
                "role": "system",
                "content": "\n\n".join(system_parts)
            })

        # Add session messages (skip system messages since they're already in system_parts)
        for msg in messages:
            if msg.get("role") != "system":
                api_messages.append(msg)

        return api_messages

    def process_input(self, input: str) -> str:
        """Process user input."""
        # Check for slash commands
        command, args = self._parse_slash_command(input)
        if command:
            return self._handle_slash_command(command, args)

        # Regular message - add to session (don't render, it's shown in prompt)
        self._session.add_message("user", input)
        # Publish UserPromptSubmit event
        self._event_bus.publish(Event("UserPromptSubmit", {
            "role": "user",
            "content": input,
            "hook_context": self._hook_context
        }))
        return "message_processed"

    def run(self):
        """Main run loop."""
        # Restore loaded skills/subagents from session (if resuming)
        loaded_skills = self._session.get_loaded_skills()
        loaded_subagents = self._session.get_loaded_subagents()
        if loaded_skills:
            self._loaded_skills.update(loaded_skills)
        if loaded_subagents:
            self._loaded_subagents.update(loaded_subagents)

        # Generate session ID and log session start
        import uuid
        self._session_id = str(uuid.uuid4())
        # Reset HookContext for new session
        self._hook_context.reset(self._session_id)
        if self._logger:
            self._logger.log_session_start(self._session_id)

        # Publish SessionStart event with hook_context
        self._event_bus.publish(Event("SessionStart", {
            "session_id": self._session_id,
            "hook_context": self._hook_context
        }))

        self._renderer.render_message("system", "Simple Agent started. Type /help for commands.")

        # Debug: Show available skills (metadata only)
        skills = self._skill_loader.list_skills()
        if skills:
            self._renderer.render_message("system", f"Found {len(skills)} skill(s): {', '.join([s['name'] for s in skills])}")
            self._renderer.render_message("system", "Skills are loaded on-demand. Use /load-skill <name> to load a skill.")
        else:
            self._renderer.render_message("system", "No skills found in ./skills directory.")

        # Debug: Show available subagents (metadata only)
        subagents = self._subagent_loader.list_subagents()
        if subagents:
            self._renderer.render_message("system", f"Found {len(subagents)} subagent(s): {', '.join([s['name'] for s in subagents])}")
            self._renderer.render_message("system", "Subagents are loaded on-demand. Use /load-subagent <name> to load a subagent.")
        else:
            self._renderer.render_message("system", "No subagents found in ./subagents directory.")

        while True:
            try:
                # Flush output and print empty line to ensure terminal state is clean before prompt
                sys.stdout.flush()
                print()  # Add a newline before the prompt
                # Use prompt_toolkit for better multi-byte character handling (Chinese input)
                user_input = self._prompt_session.prompt("> ")
                result = self.process_input(user_input)

                if result == "exit":
                    self._renderer.render_message("system", "Goodbye!")
                    break
                elif result == "message_processed":
                    # Process message with API
                    messages = self._prepare_messages_with_context()
                    tools = self._tool_registry.to_openai_format()

                    response = self._api_client.send_message(messages, tools)
                    for msg in response:
                        # Handle tool calls
                        if "tool_calls" in msg and msg["tool_calls"]:
                            self._handle_tool_calls_in_message(msg, response)
                        else:
                            # Regular message (no tool calls)
                            content = msg.get("content", "")
                            self._session.add_message(msg["role"], content)
                            try:
                                self._renderer.render_message(msg["role"], content)
                            except Exception as e:
                                # Fallback to plain text if rendering fails
                                self._renderer.render_error(f"Failed to render message: {str(e)}")
                                # Try showing first 500 chars as plain text
                                plain_content = content[:500] if content else ""
                                print(f"\n{msg['role']}: {plain_content}")
                else:
                    # Unknown command result
                    self._renderer.render_message("system", result)

            except KeyboardInterrupt:
                self._renderer.render_message("system", "Goodbye!")

                # Publish Stop event
                self._event_bus.publish(Event("Stop", {
                    "session_id": self._session_id,
                    "hook_context": self._hook_context
                }))
                break
            except HookBlockedException:
                # Hook blocked, continue to next input
                continue
            except Exception as e:
                self._renderer.render_error(str(e))

                # Publish Error event
                self._event_bus.publish(Event("Error", {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "hook_context": self._hook_context
                }))
