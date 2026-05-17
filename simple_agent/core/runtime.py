import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
from rich.markup import escape
from simple_agent.config.settings import Settings
from simple_agent.api.client import APIClient
from simple_agent.core.events import EventBus, Event, HookBlockedException, HookContext
from simple_agent.core.session import Session
from simple_agent.core.llm_logger import LLMLogger
from simple_agent.core.todo_manager import TodoManager
from simple_agent.tools.registry import get_global_registry
from simple_agent.tools.dispatcher import ToolDispatcher
from simple_agent.resources.skills import SkillLoader
from simple_agent.resources.agents import AgentLoader
from simple_agent.resources.hooks import HookLoader
from simple_agent.resources.commands import CommandLoader
from simple_agent.resources.command_processor import CommandProcessor
from simple_agent.ui.renderer import UIRenderer
from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.history import InMemoryHistory

# Import builtin tools to auto-register them
from simple_agent.tools import builtin  # noqa: F401
from simple_agent.tools.builtin.load_skill import LoadSkill
from simple_agent.tools.builtin.run_subagent import RunSubAgent


class Runtime:
    def __init__(self, config: Settings, log_file: Optional[str] = None, skip_api_init: bool = False):
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

        # Initialize TodoManager for task tracking
        self._todo_manager = TodoManager()

        # Set up TODO tools
        from simple_agent.tools.builtin.todo import set_todo_manager
        set_todo_manager(self._todo_manager)

        # Initialize API client with logger (can be skipped for testing)
        if not skip_api_init:
            self._api_client = APIClient(config.api, self._logger)
        else:
            self._api_client = None

        # Use global registry (includes builtin tools)
        self._tool_registry = get_global_registry()
        self._tool_dispatcher = ToolDispatcher(self._tool_registry, self._event_bus)

        # Initialize resource loaders (resolve relative paths from current directory)
        base_dir = Path.cwd()
        # Skills loader supports multiple directories
        skills_dirs = config.paths.skills_dirs
        if isinstance(skills_dirs, str):
            skills_dirs = [skills_dirs]
        # Resolve relative paths to base_dir
        resolved_skills_dirs = [base_dir / d if not d.startswith("~") else d for d in skills_dirs]
        self._skill_loader = SkillLoader(resolved_skills_dirs)
        self._agent_loader = AgentLoader(base_dir / config.paths.agents_dir)
        self._hook_loader = HookLoader(base_dir / config.paths.hooks_dir)
        self._command_loader = CommandLoader(base_dir / config.paths.commands_dir)
        self._command_processor = CommandProcessor(config, self._logger)

        # Load and register hooks
        self._load_hooks()

        # Load skills and build skills context (only metadata for lazy loading)
        self._loaded_skills = set()  # Track which skills have been fully loaded
        self._skills_context = self._build_skills_context()

        # Load agents and build agents context (only metadata for lazy loading)
        self._loaded_agents = set()  # Track which agents have been fully loaded
        self._agents_context = self._build_agents_context()

        # Set up load_skill and run_subagent tools
        LoadSkill.set_runtime(self._skill_loader, self._loaded_skills, self, self._event_bus)
        RunSubAgent.set_runtime(self._agent_loader, self._loaded_agents, self._config.api, self._logger, self, self._event_bus, self._renderer)

        # Register the tool definitions
        from simple_agent.tools.builtin.load_skill import load_skill_tool_def
        from simple_agent.tools.builtin.run_subagent import run_subagent_tool_def
        self._tool_registry.register(load_skill_tool_def)
        self._tool_registry.register(run_subagent_tool_def)

    def _build_skills_context(self) -> str:
        """Build context string from all available skills (metadata only).

        First layer: Only show skill directory (summary), not full content.
        Full content is loaded via trigger layer (load_skill tool) only when needed.
        """
        skills = self._skill_loader.list_skills()
        if not skills:
            return ""

        context_parts = ["# Available Skills\n"]
        context_parts.append("The following skills are available. Ask to load them by name.\n\n")

        for skill in skills:
            context_parts.append(f"- **{skill['name']}**: {skill['description']}")

        return "\n".join(context_parts)

    def _build_agents_context(self) -> str:
        """Build context string from all available agents (metadata only).

        Agents run as isolated subagents with their own execution context.
        Use the run_subagent tool to invoke an agent with a specific task.
        """
        agents = self._agent_loader.list_agents()
        if not agents:
            return ""

        context_parts = ["# Available Agents\n"]
        context_parts.append("The following agents are available as subagents. Use run_subagent(agent_name, task) to invoke them.\n\n")

        for agent in agents:
            tools = agent['metadata'].get('tools', [])
            tools_str = ', '.join(tools) if tools else 'all tools'
            context_parts.append(f"- **{agent['name']}**: {agent['description']}")
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

                    if not result:
                        return

                    decision = result.get("decision")
                    message = result.get("message", "")
                    additional_context = result.get("additionalContext", "")
                    updated_input = result.get("updatedInput")

                    # Show message in CLI if provided
                    if message:
                        self._renderer.render_message("system", message)

                    # Handle block decision
                    if decision == "block":
                        if self._logger:
                            self._logger.log_hook_block(
                                event_name=event_obj.name,
                                hook_name=hook_data["event_name"],
                                message=message
                            )
                        # Send block message to AI
                        block_msg = f"[BLOCKED by {hook_data['event_name']}] {message}"
                        self._session.add_message("system", block_msg)
                        raise HookBlockedException(message)

                    # Handle additionalContext - send to AI
                    if additional_context:
                        self._session.add_message("system", f"[{hook_data['event_name']}] {additional_context}")

                    # Handle updatedInput - modify event data (for tool calls)
                    if updated_input and hasattr(event_obj, 'data'):
                        event_obj.data.update(updated_input)

                return handler

            self._event_bus.subscribe(event_name, make_handler(hook, event_name))

    def _execute_hook(self, hook: Dict[str, Any], event: Event) -> Optional[dict]:
        """Execute hook using official stdin/stdout JSON protocol.

        Args:
            hook: Hook data {"event_name", "path", "files"}
            event: Event object

        Returns:
            dict or None: Hook result with fields:
            - decision: "allow" | "block" (required)
            - message: CLI display content (optional)
            - updatedInput: Modified event data (optional)
            - additionalContext: Content to send to LLM (optional)
        """

    def _build_hook_input(self, event: Event) -> dict:
        """Build hook input JSON in official format.

        Official format varies by event type - see _OFFICIAL_HOOK_EVENTS docstring below.

        Args:
            event: Event object with name and data

        Returns:
            dict: Hook input JSON with structure: {event, session, project, payload}
        """
        event_name = event.name
        event_data = event.data if event.data else {}

        # Base session info
        session_info = {
            "id": self._session_id or "unknown"
        }

        # Base project info
        project_info = {
            "path": str(Path.cwd())
        }

        # Build payload based on event type
        payload = {}

        # Official Hook Events
        if event_name == "SessionStart":
            # SessionStart: 全新会话初始化启动, payload is empty
            payload = {}

        elif event_name == "UserPromptSubmit":
            # UserPromptSubmit: 用户输入内容提交，送入 LLM 前
            content = event_data.get("content", "")
            payload = {
                "userPrompt": content
            }

        elif event_name == "PreToolUse":
            # PreToolUse: LLM 生成工具调用指令，本地执行工具之前
            tool_name = event_data.get("tool_name", "")
            arguments = event_data.get("arguments", {})
            payload = {
                "tool": tool_name,
                "parameters": arguments
            }

        elif event_name == "PostToolUse":
            # PostToolUse: 工具执行完成，结果回传给 LLM 之前（成功 / 失败都走此事件）
            tool_name = event_data.get("tool_name", "")
            arguments = event_data.get("arguments", {})
            result = event_data.get("result", {})
            error = event_data.get("error")
            success = result.get("success", True) if isinstance(result, dict) else True

            payload = {
                "tool": tool_name,
                "parameters": arguments,
                "result": result,
                "error": error,
                "success": success
            }

        elif event_name == "Stop":
            # Stop: 主代理本轮回答结束、本轮会话轮次终止
            # Note: responseLength and usedTools would be tracked during the turn
            response_length = event_data.get("responseLength", 0)
            used_tools = event_data.get("usedTools", [])
            payload = {
                "responseLength": response_length,
                "usedTools": used_tools
            }

        elif event_name == "SkillLoad":
            # SkillLoad: 加载 .skill 技能文档时
            skill_name = event_data.get("skill_name", "")
            skill_path = event_data.get("skill_path", "")
            raw_content = event_data.get("raw_content", "")
            payload = {
                "skillName": skill_name,
                "skillPath": skill_path,
                "rawContent": raw_content
            }

        # Future/Not-Implemented Events (reserved for future development)
        # These events are in the official spec but not yet implemented
        elif event_name in ("BeforeBash", "AfterBash", "BeforeEdit", "AfterEdit",
                            "PreCompact", "PostCompact", "SubagentStart", "SubagentStop",
                            "Notification", "PluginLoad"):
            # Use raw event data as payload (will be refined when implemented)
            payload = event_data

        else:
            # Unknown event type, use raw event data as fallback
            payload = event_data

        return {
            "event": event_name,
            "session": session_info,
            "project": project_info,
            "payload": payload
        }

    def _execute_hook(self, hook: Dict[str, Any], event: Event) -> Optional[dict]:
        hook_dir = Path(hook["path"])
        combined_result = None

        # Prepare hook input in official format with session, project, and payload
        hook_input = self._build_hook_input(event)
        hook_input_json = json.dumps(hook_input, ensure_ascii=False)

        for filename in hook["files"]:
            filepath = hook_dir / filename
            ext = filepath.suffix.lower()

            try:
                result = None
                if ext == ".py":
                    result = self._execute_python_hook(filepath, hook_input_json)
                elif ext in [".sh", ".cmd"]:
                    result = self._execute_shell_hook(filepath, hook_input_json)
                elif ext == ".md":
                    result = self._execute_markdown_hook(filepath, event)

                if result:
                    # If any hook returns block, immediately return the block result
                    if result.get("decision") == "block":
                        return result
                    # Combine results: allow merges additionalContext and updatedInput
                    if combined_result is None:
                        combined_result = result
                    else:
                        # Merge results
                        if result.get("additionalContext"):
                            combined_result["additionalContext"] = result.get("additionalContext")
                        if result.get("updatedInput"):
                            if combined_result.get("updatedInput") is None:
                                combined_result["updatedInput"] = result["updatedInput"]
                            else:
                                combined_result["updatedInput"].update(result["updatedInput"])

            except Exception as e:
                self._renderer.render_message("system", f"Hook {filename} failed: {str(e)}")

        return combined_result

    def _execute_python_hook(self, filepath: Path, hook_input_json: str) -> Optional[dict]:
        """Execute Python hook using official stdin/stdout JSON protocol.

        Args:
            filepath: Python hook file path
            hook_input_json: JSON string to send to stdin

        Returns:
            dict: Hook result with official fields:
            - decision: "allow" | "block"
            - message: CLI display (optional)
            - updatedInput: Modified event data (optional)
            - additionalContext: Content for LLM (optional)
        """
        import subprocess

        try:
            # Execute Python script with JSON input via stdin, capture JSON output
            result = subprocess.run(
                [sys.executable, str(filepath)],
                input=hook_input_json,
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                if result.stderr:
                    self._renderer.render_message("system", f"Hook {filepath.name} error: {result.stderr.strip()}")
                return None

            # Parse JSON output from stdout
            if result.stdout.strip():
                try:
                    hook_result = json.loads(result.stdout.strip())
                    # Validate required fields
                    if "decision" not in hook_result:
                        self._renderer.render_message("system", f"Hook {filepath.name} missing 'decision' field")
                        return None
                    if hook_result["decision"] not in ["allow", "block"]:
                        self._renderer.render_message("system", f"Hook {filepath.name} invalid 'decision': {hook_result['decision']}")
                        return None
                    return hook_result
                except json.JSONDecodeError as e:
                    self._renderer.render_message("system", f"Hook {filepath.name} invalid JSON: {e}")
                    return None

            # No output means allow
            return {"decision": "allow"}

        except subprocess.TimeoutExpired:
            self._renderer.render_message("system", f"Hook {filepath.name} timed out")
            return None
        except Exception as e:
            self._renderer.render_message("system", f"Hook {filepath.name} failed: {str(e)}")
            return None

    def _execute_shell_hook(self, filepath: Path, hook_input_json: str) -> Optional[dict]:
        """Execute Shell hook using official stdin/stdout JSON protocol.

        Args:
            filepath: Shell script file path
            hook_input_json: JSON string to send to stdin

        Returns:
            dict: Hook result with official fields
        """
        import subprocess

        try:
            shell_cmd = f"sh {filepath}" if filepath.suffix == ".sh" else str(filepath)
            result = subprocess.run(
                shell_cmd,
                input=hook_input_json,
                shell=True,
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                if result.stderr:
                    self._renderer.render_message("system", f"Hook {filepath.name} error: {result.stderr.strip()}")
                return None

            # Parse JSON output from stdout
            if result.stdout.strip():
                try:
                    hook_result = json.loads(result.stdout.strip())
                    if "decision" not in hook_result:
                        self._renderer.render_message("system", f"Hook {filepath.name} missing 'decision' field")
                        return None
                    if hook_result["decision"] not in ["allow", "block"]:
                        self._renderer.render_message("system", f"Hook {filepath.name} invalid 'decision': {hook_result['decision']}")
                        return None
                    return hook_result
                except json.JSONDecodeError as e:
                    self._renderer.render_message("system", f"Hook {filepath.name} invalid JSON: {e}")
                    return None

            return {"decision": "allow"}

        except subprocess.TimeoutExpired:
            self._renderer.render_message("system", f"Hook {filepath.name} timed out")
            return None
        except Exception as e:
            self._renderer.render_message("system", f"Hook {filepath.name} failed: {str(e)}")
            return None

    def _execute_markdown_hook(self, filepath: Path, event: Event) -> Optional[dict]:
        """Execute Markdown hook (simple message append).

        Markdown hooks append content as additionalContext for the LLM.

        Args:
            filepath: Markdown file path
            event: Event object

        Returns:
            dict with additionalContext field
        """
        try:
            content = filepath.read_text()

            # Simple template variable replacement
            variables = event.data or {}
            for key, value in variables.items():
                content = content.replace(f"{{{{{key}}}}}", str(value))

            return {
                "decision": "allow",
                "additionalContext": content
            }
        except Exception as e:
            self._renderer.render_message("system", f"Hook {filepath.name} failed: {str(e)}")
            return None

    def get_agent_context(self) -> Optional[str]:
        """Load AGENT.md from plugin directory."""
        agent_md = Path.cwd() / "plugin" / "AGENT.md"
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
        # Handle builtin commands first
        if command == "help":
            return self._cmd_help()
        elif command == "exit" or command == "quit":
            return "exit"

        # Handle special commands with actions
        if command == "clear":
            self._session.clear()
            self._loaded_skills.clear()
            self._loaded_agents.clear()
            return self._load_command("clear", args)
        elif command == "reset":
            self._session.clear()
            self._loaded_skills.clear()
            self._loaded_agents.clear()
            return self._load_command("reset", args)

        # Load command
        cmd_data = self._command_loader.get_command(command)
        if not cmd_data:
            return f"Unknown command: /{command}"

        # Use CommandProcessor to process
        processed = self._command_processor.process(cmd_data, args)

        # Apply allowed tools restriction
        if processed.allowed_tools:
            saved_tools = self._tool_registry.snapshot()
            allowed = [t.strip() for t in processed.allowed_tools.split(",")]
            self._tool_registry.filter(allowed)
        else:
            saved_tools = None

        # Add command content as user message (no prefix)
        self._session.add_message("user", processed.content)

        # Restore tools
        if saved_tools:
            self._tool_registry.restore(saved_tools)

        # Return special marker to indicate API call needed
        return "command_processed"

    def _cmd_help(self) -> str:
        """Generate help text."""
        skills = self._skill_loader.list_skills()
        agents = self._agent_loader.list_agents()
        commands = self._command_loader.list_commands()

        help_text = "# Available Commands\n\n"
        help_text += "## Builtin Commands\n"
        help_text += "- `/help` - Show this help message\n"
        help_text += "- `/exit` - Exit the agent\n"
        help_text += "- `/clear` - Clear conversation history\n"
        help_text += "- `/reset` - Reset session (clear history and unload skills/agents)\n\n"

        if commands:
            help_text += "## Custom Commands\n"
            for cmd in commands:
                usage = cmd["metadata"].get("usage", f"/{cmd['name']}")
                desc = cmd["metadata"].get("description", "")
                help_text += f"- `{usage}` - {desc}\n"
            help_text += "\n"

        help_text += "AI can automatically load skills and agents by mentioning them in your request.\n"

        if skills:
            help_text += "\n# Available Skills\n\n"
            for skill in skills:
                help_text += f"- **{skill['name']}**: {skill['description']}\n"

        if agents:
            help_text += "\n# Available Agents\n\n"
            for agent in agents:
                tools = agent['metadata'].get('tools', [])
                tools_str = ', '.join(tools) if tools else 'all tools'
                help_text += f"- **{agent['name']}**: {agent['description']}\n"
                help_text += f"  Tools: {tools_str}\n"

        return help_text

    def _load_command(self, command_name: str, args: List[str]) -> Optional[str]:
        """Load and execute a custom command.

        Args:
            command_name: Name of the command
            args: Command arguments

        Returns:
            Command result or None if command not found
        """
        try:
            commands = self._command_loader.list_commands()
            for cmd in commands:
                if cmd["name"] == command_name:
                    # Get the content (markdown without frontmatter)
                    content = cmd.get("content", "")

                    # Replace template variables
                    content = self._replace_command_variables(content)

                    return content
            return None
        except Exception as e:
            return f"Error loading command: {str(e)}"

    def _replace_command_variables(self, content: str) -> str:
        """Replace template variables in command content.

        Args:
            content: Content with template variables

        Returns:
            Content with variables replaced
        """
        import re

        # Session info
        session_id = self._session_id or "N/A"
        message_count = len(self._session.get_messages())

        # Configuration
        api_provider = self._config.api.provider
        model = self._config.api.model
        base_url = self._config.api.base_url or "default"

        # Paths
        skills_dirs = ", ".join(self._config.paths.skills_dirs)
        agents_dir = self._config.paths.agents_dir
        hooks_dir = self._config.paths.hooks_dir
        commands_dir = self._config.paths.commands_dir

        # UI
        theme = self._config.ui.theme
        show_thinking = self._config.ui.show_thinking

        # Logging
        logging_enabled = self._config.logging.enabled
        log_dir = self._config.logging.log_dir or "default"

        # Resources
        skills = self._skill_loader.list_skills()
        agents = self._agent_loader.list_agents()
        total_skills = len(skills)
        total_agents = len(agents)
        loaded_skills = self._loaded_skills
        loaded_agents = self._loaded_agents

        # Skills list
        skills_list = "\n".join([f"- **{s['name']}**: {s['description']}" for s in skills])
        loaded_skills_list = "\n".join([f"- **{s}**" for s in sorted(loaded_skills)]) if loaded_skills else "None"

        # Agents list
        agents_list = "\n".join([f"- **{a['name']}**: {a['description']}" for a in agents])
        loaded_agents_list = "\n".join([f"- **{a}**" for a in sorted(loaded_agents)]) if loaded_agents else "None"

        # Replace variables
        replacements = {
            # Session
            '{session_id}': session_id,
            '{message_count}': str(message_count),

            # Configuration
            '{api_provider}': api_provider,
            '{model}': model,
            '{base_url}': base_url,

            # Paths
            '{skills_dirs}': skills_dirs,
            '{agents_dir}': agents_dir,
            '{hooks_dir}': hooks_dir,
            '{commands_dir}': commands_dir,

            # UI
            '{theme}': theme,
            '{show_thinking}': str(show_thinking),

            # Logging
            '{logging_enabled}': str(logging_enabled),
            '{log_dir}': log_dir,

            # Resources
            '{skills_count}': str(len(loaded_skills)),
            '{agents_count}': str(len(loaded_agents)),
            '{total_skills}': str(total_skills),
            '{total_agents}': str(total_agents),

            # Lists
            '{skills_list}': skills_list,
            '{loaded_skills}': loaded_skills_list,
            '{agents_list}': agents_list,
            '{loaded_agents}': loaded_agents_list,
        }

        for var, value in replacements.items():
            content = content.replace(var, value)

        return content

    def _handle_tool_calls_in_message(
        self, msg: Dict[str, Any], response: List[Dict[str, Any]], request_id: Optional[str] = None
    ) -> None:
        """Handle tool calls in a message (recursive for multi-step tool use).

        Args:
            msg: The message containing tool_calls
            response: The full response list containing _request_id
            request_id: Optional request_id from caller (to avoid double-pop)
        """
        # Get request_id for tool logging (only if not provided by caller)
        if request_id is None:
            request_id = response[0].pop("_request_id", None) if response else None

        # Extract subagent context from response if available
        subagent_call_id = response[0].pop("_subagent_call_id", None) if response else None
        subagent_agent_name = response[0].pop("_subagent_agent_name", None) if response else None

        # Add assistant message with tool_calls to session
        self._session.add_message(msg["role"], msg.get("content", ""), tool_calls=msg["tool_calls"])

        # Execute each tool call and show details
        for tool_call in msg["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            # Handle both JSON string and already-parsed dict
            arg_data = tool_call["function"]["arguments"]
            if isinstance(arg_data, str):
                arguments = json.loads(arg_data)
            else:
                arguments = arg_data

            # Build args string for display
            args_str = ""
            if arguments and isinstance(arguments, dict):
                args_parts = []
                for k, v in arguments.items():
                    # Skip internal params
                    if k not in ["cwd", "timeout", "case_sensitive"]:
                        v_str = str(v)
                        if len(v_str) > 20:
                            v_str = v_str[:20] + "..."
                        args_parts.append(f"{k}={v_str}")
                if args_parts:
                    args_str = '[' + ', '.join(args_parts) + ']'

            # Print tool name and args before execution (no newline)
            if args_str:
                self._renderer.console.print(f"{tool_name} {escape(args_str)}", end="")
            else:
                self._renderer.console.print(f"{tool_name}", end="")

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
                    subagent_call_id=subagent_call_id,
                    subagent_agent_name=subagent_agent_name,
                )

            # Show completion status with checkmark (on same line, then newline)
            tool_result = result.get("result", result)
            success = tool_result.get("success", True)
            status = "[bold green]✓[/bold green]" if success else "[bold red]✗[/bold red]"
            self._renderer.console.print(f" {status}")  # Add space and status, then newline

            # Render tool result to user in CLI
            self._renderer.render_tool_result(tool_name, result, arguments)

            # Handle load_skill and load_agent tools specially
            # These tools are handled separately - content is added to session
            # and we don't format/send their result to the API
            if tool_name not in ["load_skill", "load_agent"]:
                # Regular tool - normal processing
                tool_result = result.get("result", result)

                # Format tool result for AI understanding (using unified stdout/stderr format)
                # Build tool header for context
                args_parts = []
                for k, v in arguments.items():
                    if k not in ["cwd", "timeout", "case_sensitive"]:
                        v_str = repr(v)
                        if len(v_str) > 30:
                            v_str = v_str[:30] + "..."
                        args_parts.append(f"{k}={v_str}")
                tool_header = f"{tool_name}({', '.join(args_parts)})"

                # All tools now return stdout/stderr format
                stdout = tool_result.get("stdout", "").strip()
                stderr = tool_result.get("stderr", "").strip()

                if not tool_result.get("success", True):
                    # Tool failed - combine header and error
                    tool_content = f"{tool_header}\nError: {stderr or stdout}"
                else:
                    # Tool succeeded - combine header and output
                    parts = [tool_header]
                    if stdout:
                        parts.append(f"Output:\n{stdout}")
                    if stderr:
                        parts.append(f"Warnings:\n{stderr}")
                    tool_content = "\n".join(parts)

                # Add tool result to session with tool_call_id
                self._session.add_message("tool", tool_content, tool_call_id=tool_call["id"])
            else:
                # Send message to user for load_skill/load_agent
                self._renderer.render_message("system", result.get("message", ""))

                # Add skill/agent content to session as system message
                # This ensures AI knows the skill/agent is loaded
                if tool_name == "load_skill" and result.get("success"):
                    skill_name = arguments.get("skill_name")
                    skill_content = result.get("content", "")

                    if skill_content:
                        # Add as tool message so LLM receives full content
                        tool_msg = f"# Loaded Skill: {skill_name}\n{skill_content}"
                        self._session.add_message("tool", tool_msg, tool_call_id=tool_call["id"])
                elif tool_name == "load_agent" and result.get("success"):
                    agent_name = arguments.get("agent_name")
                    agent_content = result.get("content", "")
                    if agent_content:
                        # Add as tool message so LLM receives full content
                        tool_msg = f"# Loaded Agent: {agent_name}\n{agent_content}"
                        self._session.add_message("tool", tool_msg, tool_call_id=tool_call["id"])

        # Send tool results back to API for next response
        messages = self._prepare_messages_with_context()
        tools = self._tool_registry.to_openai_format()
        next_response = self._api_client.send_message(messages, tools)

        for next_msg in next_response:
            # Get request_id for next iteration
            request_id = next_msg.pop("_request_id", None)

            if "tool_calls" in next_msg and next_msg["tool_calls"]:
                # More tool calls - recurse, passing request_id
                self._handle_tool_calls_in_message(next_msg, next_response, request_id)
            else:
                # Final response with content
                self._session.add_message(next_msg["role"], next_msg.get("content", ""))
                content = next_msg.get("content", "")
                if not content:
                    content = "(工具执行完成，AI 无额外响应)"
                self._renderer.render_message(next_msg["role"], content)

    def _prepare_messages_with_context(self) -> List[Dict[str, str]]:
        """Prepare messages with agent context, skills, and agents."""
        messages = self._session.get_messages()

        # Build system context with AGENT.md, skills, and agents
        system_parts = []

        # Add AGENT.md context first (base agent instructions)
        agent_context = self.get_agent_context()
        if agent_context:
            system_parts.append("# Agent Context\n")
            system_parts.append(agent_context)

        # Add skills context (includes loaded skills with full content)
        if self._skills_context:
            system_parts.append(self._skills_context)

        # Add agents context
        if self._agents_context:
            system_parts.append(self._agents_context)

        # Add command system messages (from slash commands)
        for msg in messages:
            if msg.get("role") == "system" and msg.get("content"):
                system_parts.append(msg["content"])

        # Prepare messages for API
        api_messages = []

        # Add combined system context if available
        if system_parts:
            api_messages.append({
                "role": "system",
                "content": "\n\n".join(system_parts)
            })

        # Add non-system session messages (user, assistant, tool)
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
            "content": input
        }))
        return "message_processed"

    def run(self):
        """Main run loop."""
        # Restore loaded skills/agents from session (if resuming)
        loaded_skills = self._session.get_loaded_skills()
        loaded_agents = self._session.get_loaded_agents()
        if loaded_skills:
            self._loaded_skills.update(loaded_skills)
        if loaded_agents:
            self._loaded_agents.update(loaded_agents)

        # Generate session ID and log session start
        import uuid
        self._session_id = str(uuid.uuid4())
        # Reset HookContext for new session
        self._hook_context.reset(self._session_id)
        if self._logger:
            self._logger.log_session_start(self._session_id)

        # Publish SessionStart event
        self._event_bus.publish(Event("SessionStart", {
            "session_id": self._session_id
        }))

        self._renderer.render_message("system", "Simple Agent started. Type /help for commands.")

        # Debug: Show available skills (metadata only)
        skills = self._skill_loader.list_skills()
        if skills:
            self._renderer.render_message("system", f"Found {len(skills)} skill(s): {', '.join([s['name'] for s in skills])}")
            self._renderer.render_message("system", "Skills are loaded on-demand. Use /load-skill <name> to load a skill.")
        else:
            self._renderer.render_message("system", "No skills found in ./plugin/skills directory.")

        # Debug: Show available agents (metadata only)
        agents = self._agent_loader.list_agents()
        if agents:
            self._renderer.render_message("system", f"Found {len(agents)} agent(s): {', '.join([s['name'] for s in agents])}")
            self._renderer.render_message("system", "Agents are loaded on-demand. Use /load-agent <name> to load an agent.")
        else:
            self._renderer.render_message("system", "No agents found in ./plugin/agents directory.")

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
                elif result == "message_processed" or result == "command_processed":
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
                    "responseLength": 0,  # TODO: Track actual response length
                    "usedTools": []  # TODO: Track used tools in current turn
                }))
                break
            except HookBlockedException:
                # Hook blocked, continue to next input
                continue
            except Exception as e:
                self._renderer.render_error(str(e))
