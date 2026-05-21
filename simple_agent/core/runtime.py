import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional
from shlex import split
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


def _is_hook_debug() -> bool:
    """Check if hook debug is enabled via environment variable."""
    return os.getenv("HOOK_DEBUG", "0") == "1"

# Import builtin tools to auto-register them
from simple_agent.tools import builtin  # noqa: F401
from simple_agent.tools.builtin.load_skill import LoadSkill
from simple_agent.tools.builtin.run_subagent import RunSubAgent


class Runtime:
    def __init__(
        self,
        config: Settings,
        log_file: Optional[str] = None,
        skip_api_init: bool = False,
        sink: Optional["OutputSink"] = None,
    ):
        self._config = config
        self._event_bus = EventBus()
        self._session = Session()
        self._renderer = UIRenderer()
        self._session_id: Optional[str] = None
        # Output sink: defaults to CliSink wrapping the renderer
        from simple_agent.core.sinks import CliSink, OutputSink
        self._sink: OutputSink = sink if sink is not None else CliSink(self._renderer)
        # Initialize HookContext singleton
        self._hook_context = HookContext()
        # Initialize prompt session with history for better input handling (especially for Chinese characters)
        self._prompt_session = PromptSession(
            history=InMemoryHistory(),
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

        # Agents loader supports multiple directories
        agents_dirs = config.paths.agents_dirs
        if isinstance(agents_dirs, str):
            agents_dirs = [agents_dirs]
        resolved_agents_dirs = [base_dir / d if not d.startswith("~") else d for d in agents_dirs]
        self._agent_loader = AgentLoader(resolved_agents_dirs)

        # Hooks loader - loads from hooks.json in plugin directory
        hooks_json_path = base_dir / config.paths.plugin_dir / "hooks/hooks.json"
        self._hook_loader = HookLoader(hooks_json_path)

        # Commands loader supports multiple directories
        commands_dirs = config.paths.commands_dirs
        if isinstance(commands_dirs, str):
            commands_dirs = [commands_dirs]
        # Also load skills as commands - skills can be invoked as /skill-name
        for skills_dir in skills_dirs:
            if skills_dir not in commands_dirs:
                commands_dirs.append(skills_dir)
        resolved_commands_dirs = [base_dir / d if not d.startswith("~") else d for d in commands_dirs]
        self._command_loader = CommandLoader(resolved_commands_dirs)

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

    def _get_allowed_tools(self) -> Optional[List[str]]:
        """Get list of allowed tools based on configuration.

        Returns:
            List of allowed tool names, or None if all tools are allowed.
        """
        all_tools = self._tool_registry.list_tools()
        enabled_tools = []

        for tool in all_tools:
            tool_name = tool['name']
            if self._config.tools.is_enabled(tool_name):
                enabled_tools.append(tool_name)

        # If all tools are enabled, return None to indicate no filtering
        if len(enabled_tools) == len(all_tools):
            return None

        return enabled_tools

    def _load_hooks(self):
        """Load and register all hooks from hooks.json configuration."""
        # Get unique event names from hooks.json
        all_hooks = self._hook_loader.list_hooks()
        event_names = set(hook["event_name"] for hook in all_hooks)

        if _is_hook_debug():
            sys.stderr.write(f"[DEBUG] Loading {len(all_hooks)} hooks for {len(event_names)} events...\n")

        # Register one handler per event name that processes all matching hooks
        for event_name in event_names:
            def make_handler(evt_name):
                def handler(event_obj):
                    # Get context string for matcher matching
                    # For SessionStart, use "startup" as default context
                    # This matches superpowers plugin's matcher pattern
                    context = None
                    if evt_name == "SessionStart":
                        context = event_obj.data.get("context", "startup")

                    # Get all hooks that should be triggered for this event
                    matching_hooks = self._hook_loader.get_hooks_for_event(evt_name, context)

                    if not matching_hooks:
                        return

                    # Execute all matching hooks in order
                    for hook_group in matching_hooks:
                        hook_definitions = hook_group.get("hooks", [])

                        for hook_def in hook_definitions:
                            try:
                                result = self._execute_hook_definition(hook_def, event_obj, evt_name)

                                if not result:
                                    continue

                                decision = result.get("decision", "allow")
                                message = result.get("message", "")
                                additional_context = result.get("additionalContext", "")
                                updated_input = result.get("updatedInput")

                                # Display message if provided
                                if message:
                                    self._renderer.render_message("system", message)

                                # Handle block decision
                                if decision == "block":
                                    if self._logger:
                                        self._logger.log_hook_block(
                                            event_name=event_obj.name,
                                            hook_name=hook_def.get("type", "unknown"),
                                            message=message
                                        )
                                    # Send block message to AI
                                    block_msg = f"[BLOCKED] {message}"
                                    self._session.add_message("system", block_msg)
                                    raise HookBlockedException(message)

                                # Handle additionalContext - send to AI
                                if additional_context:
                                    self._session.add_message("system", additional_context)

                                # Handle updatedInput - modify event data (for tool calls)
                                if updated_input and hasattr(event_obj, 'data'):
                                    event_obj.data.update(updated_input)

                            except Exception as e:
                                self._renderer.render_message("system", f"Hook failed: {str(e)}")
                                if _is_hook_debug():
                                    import traceback
                                    traceback.print_exc()

                return handler

            self._event_bus.subscribe(event_name, make_handler(event_name))

    def _execute_hook_definition(self, hook_def: Dict[str, Any], event: Event, event_name: str) -> Optional[dict]:
        """Execute a single hook definition from hooks.json configuration.

        Args:
            hook_def: Hook definition from hooks.json, e.g., {"type": "command", "command": "..."}
            event: Event object
            event_name: The event name (for logging)

        Returns:
            dict or None: Hook result with fields:
            - decision: "allow" | "block" (required)
            - message: CLI display content (optional)
            - updatedInput: Modified event data (optional)
            - additionalContext: Content to send to LLM (optional)
        """
        hook_type = hook_def.get("type", "command")

        # Build hook input in official format
        hook_input = self._build_hook_input(event)
        hook_input_json = json.dumps(hook_input, ensure_ascii=False)

        if _is_hook_debug():
            sys.stderr.write(f"[DEBUG] Hook triggered: {event_name} ({hook_type})\n")
            sys.stderr.write(f"[DEBUG] Hook input: {hook_input_json[:200]}..." if len(hook_input_json) > 200 else f"[DEBUG] Hook input: {hook_input_json}\n")

        if hook_type == "command":
            result = self._execute_command_hook(hook_def, hook_input_json)
        elif hook_type == "python":
            result = self._execute_python_hook(hook_def, hook_input_json)
        elif hook_type == "markdown":
            result = self._execute_markdown_hook(hook_def, event)
        else:
            self._renderer.render_message("system", f"Unknown hook type: {hook_type}")
            return None

        return result

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

        elif event_name == "BeforeBash":
            # BeforeBash: 执行 Bash 命令前置钩子
            command = event_data.get("command", "")
            cwd = event_data.get("cwd", "")
            timeout = event_data.get("timeout", 30)
            payload = {
                "command": command,
                "cwd": cwd,
                "timeout": timeout
            }

        elif event_name == "AfterBash":
            # AfterBash: Bash 命令执行完毕后置钩子
            command = event_data.get("command", "")
            stdout = event_data.get("stdout", "")
            stderr = event_data.get("stderr", "")
            exit_code = event_data.get("returncode", 0)
            success = exit_code == 0
            payload = {
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "exitCode": exit_code,
                "success": success
            }

        elif event_name == "BeforeEdit":
            # BeforeEdit: 文件编辑/写入操作执行前
            file_path = event_data.get("file_path", "")
            old_content = event_data.get("old_content", "")
            new_content = event_data.get("new_content", "")
            payload = {
                "filePath": file_path,
                "oldContent": old_content,
                "newContent": new_content
            }

        elif event_name == "AfterEdit":
            # AfterEdit: 文件编辑完成后
            file_path = event_data.get("file_path", "")
            final_content = event_data.get("final_content", "")
            success = event_data.get("success", True)
            payload = {
                "filePath": file_path,
                "finalContent": final_content,
                "success": success
            }

        elif event_name == "PreCompact":
            # PreCompact: 对话上下文压缩合并之前
            raw_context = event_data.get("raw_context", "")
            payload = {
                "rawContext": raw_context
            }

        elif event_name == "PostCompact":
            # PostCompact: 上下文压缩完成之后
            compressed_context = event_data.get("compressed_context", "")
            saved_tokens = event_data.get("saved_tokens", 0)
            payload = {
                "compressedContext": compressed_context,
                "savedTokens": saved_tokens
            }

        elif event_name == "SubagentStart":
            # SubagentStart: 子代理/子任务正式启动
            subagent_id = event_data.get("subagent_call_id", "")
            task_title = event_data.get("user_message", "")
            parent_session_id = event_data.get("parent_session_id", self._session_id)
            payload = {
                "subagentId": subagent_id,
                "taskTitle": task_title,
                "parentSessionId": parent_session_id
            }

        elif event_name == "SubagentStop":
            # SubagentStop: 子代理运行结束销毁
            subagent_id = event_data.get("subagent_call_id", "")
            finish_reason = event_data.get("finish_reason", "completed")
            duration = event_data.get("duration", 0)
            payload = {
                "subagentId": subagent_id,
                "finishReason": finish_reason,
                "duration": duration
            }

        elif event_name == "Notification":
            # Notification: 系统通知弹窗/权限提示触发
            notif_type = event_data.get("type", "")
            message = event_data.get("message", "")
            scope = event_data.get("scope", "global")
            payload = {
                "type": notif_type,
                "message": message,
                "scope": scope
            }

        elif event_name == "PluginLoad":
            # PluginLoad: 会话加载外部插件时
            plugin_name = event_data.get("plugin_name", "")
            plugin_version = event_data.get("plugin_version", "")
            plugin_root = event_data.get("plugin_root", "")
            payload = {
                "pluginName": plugin_name,
                "pluginVersion": plugin_version,
                "pluginRoot": plugin_root
            }

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

        if _is_hook_debug():
            sys.stderr.write(f"[DEBUG] Hook triggered: {event.name} @ {hook_dir.name}\n")
            sys.stderr.write(f"[DEBUG] Hook input: {hook_input_json[:200]}..." if len(hook_input_json) > 200 else f"[DEBUG] Hook input: {hook_input_json}\n")

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
                    # Show message immediately if provided
                    message = result.get("message", "")
                    if message:
                        self._renderer.render_message("system", message)

                    # If any hook returns block, immediately return the block result
                    if result.get("decision") == "block":
                        if _is_hook_debug():
                            sys.stderr.write(f"[DEBUG] Hook BLOCKED by {filename}: {result}\n")
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
                if _is_hook_debug():
                    import traceback
                    sys.stderr.write(f"[DEBUG] Hook exception traceback:\n")
                    traceback.print_exc()

        if _is_hook_debug() and combined_result:
            sys.stderr.write(f"[DEBUG] Combined hook result: {combined_result}\n")
        return combined_result

    def _execute_command_hook(self, hook_def: Dict[str, Any], hook_input_json: str) -> Optional[dict]:
        """Execute command hook from hooks.json.

        Args:
            hook_def: Hook definition with "command" field
            hook_input_json: JSON string to send to stdin

        Returns:
            dict: Hook result with official fields
        """
        import subprocess

        command = hook_def.get("command", "")
        is_async = hook_def.get("async", False)

        if not command:
            return None

        try:
            # Set CLAUDE_PLUGIN_ROOT environment variable for hooks
            plugin_root = Path.cwd() / self._config.paths.plugin_dir
            env = os.environ.copy()
            env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

            # Expand environment variables in command using the custom env dict
            def expand_vars(s: str, env_dict: dict) -> str:
                """Expand variables like ${VAR} using the provided environment dict."""
                import re
                pattern = r'\$\{([^}]+)\}'
                def replace_var(match):
                    var_name = match.group(1)
                    return env_dict.get(var_name, match.group(0))
                return re.sub(pattern, replace_var, s)

            expanded_command = expand_vars(command, env)

            # Parse command safely using shlex
            cmd_parts = split(expanded_command)

            # Handle .cmd files on Unix/macOS - need bash to execute them
            if cmd_parts and cmd_parts[0].endswith('.cmd'):
                import platform
                if platform.system() != 'Windows':
                    # On Unix/macOS, prepend bash to execute .cmd files
                    cmd_parts = ['bash'] + cmd_parts

            # Prepare hook input as JSON via stdin
            result = subprocess.run(
                cmd_parts,
                input=hook_input_json,
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,
                env=env,
            )

            if _is_hook_debug():
                sys.stderr.write(f"[DEBUG] Command hook executed: {' '.join(cmd_parts)}\n")
                sys.stderr.write(f"[DEBUG] Return code: {result.returncode}\n")
                if result.stdout.strip():
                    sys.stderr.write(f"[DEBUG] Hook output: {result.stdout.strip()[:200]}..." if len(result.stdout.strip()) > 200 else f"[DEBUG] Hook output: {result.stdout.strip()}\n")
                if result.stderr.strip():
                    sys.stderr.write(f"[DEBUG] Hook stderr: {result.stderr.strip()}\n")

            if result.returncode != 0:
                if result.stderr:
                    self._renderer.render_message("system", f"Command hook error: {result.stderr.strip()}")
                return None

            if result.stdout.strip():
                try:
                    hook_result = json.loads(result.stdout.strip())

                    # Handle superpowers hook format: {hookSpecificOutput: {additionalContext: "..."}}
                    if "hookSpecificOutput" in hook_result and "additionalContext" in hook_result["hookSpecificOutput"]:
                        return {
                            "decision": "allow",
                            "additionalContext": hook_result["hookSpecificOutput"]["additionalContext"]
                        }

                    # Handle Cursor format: {additional_context: "..."}
                    if "additional_context" in hook_result:
                        return {
                            "decision": "allow",
                            "additionalContext": hook_result["additional_context"]
                        }

                    # Default decision to allow if not specified
                    if "decision" not in hook_result:
                        hook_result["decision"] = "allow"

                    return hook_result
                except json.JSONDecodeError:
                    # If output is not valid JSON, default to allow
                    return {"decision": "allow"}

        except subprocess.TimeoutExpired:
            self._renderer.render_message("system", f"Command hook timed out: {command}")
            return None
        except Exception as e:
            self._renderer.render_message("system", f"Command hook failed: {str(e)}")
            return None

    def _execute_python_hook(self, hook_def: Dict[str, Any], hook_input_json: str) -> Optional[dict]:
        """Execute Python hook using official stdin/stdout JSON protocol.

        Args:
            hook_def: Hook definition with "file" field
            hook_input_json: JSON string to send to stdin

        Returns:
            dict: Hook result with official fields
        """
        import subprocess

        filepath_str = hook_def.get("file", "")
        if not filepath_str:
            return None

        # Expand environment variables in file path using the custom env dict
        plugin_root = Path.cwd() / self._config.paths.plugin_dir
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)

        # Custom expand function
        def expand_vars(s: str, env_dict: dict) -> str:
            """Expand variables like ${VAR} using the provided environment dict."""
            import re
            pattern = r'\$\{([^}]+)\}'
            def replace_var(match):
                var_name = match.group(1)
                return env_dict.get(var_name, match.group(0))
            return re.sub(pattern, replace_var, s)

        expanded_path = expand_vars(filepath_str, env)
        filepath = Path(expanded_path).expanduser()
        if not filepath.exists():
            return None

        try:
            # Execute Python script with JSON input via stdin, capture JSON output
            result = subprocess.run(
                [sys.executable, str(filepath)],
                input=hook_input_json,
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
            )

            if _is_hook_debug():
                sys.stderr.write(f"[DEBUG] Python hook {filepath.name} executed, returncode={result.returncode}\n")
                if result.stdout.strip():
                    sys.stderr.write(f"[DEBUG] Hook output: {result.stdout.strip()[:200]}..." if len(result.stdout.strip()) > 200 else f"[DEBUG] Hook output: {result.stdout.strip()}\n")
                if result.stderr.strip():
                    sys.stderr.write(f"[DEBUG] Hook stderr: {result.stderr.strip()}\n")

            if result.returncode != 0:
                if result.stderr:
                    self._renderer.render_message("system", f"Hook {filepath.name} error: {result.stderr.strip()}")
                return None

            # Parse JSON output from stdout
            if result.stdout.strip():
                try:
                    hook_result = json.loads(result.stdout.strip())
                    # Default decision to allow if not specified
                    if "decision" not in hook_result:
                        hook_result["decision"] = "allow"
                    # Validate decision value if specified
                    if hook_result["decision"] not in ["allow", "block"]:
                        self._renderer.render_message("system", f"Hook {filepath.name} invalid 'decision': {hook_result['decision']}, defaulting to allow")
                        hook_result["decision"] = "allow"
                    if _is_hook_debug():
                        sys.stderr.write(f"[DEBUG] Hook parsed result: {hook_result}\n")
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

            if _is_hook_debug():
                sys.stderr.write(f"[DEBUG] Shell hook {filepath.name} executed, returncode={result.returncode}\n")
                if result.stdout.strip():
                    sys.stderr.write(f"[DEBUG] Hook output: {result.stdout.strip()[:200]}..." if len(result.stdout.strip()) > 200 else f"[DEBUG] Hook output: {result.stdout.strip()}\n")
                if result.stderr.strip():
                    sys.stderr.write(f"[DEBUG] Hook stderr: {result.stderr.strip()}\n")

            if result.returncode != 0:
                if result.stderr:
                    self._renderer.render_message("system", f"Hook {filepath.name} error: {result.stderr.strip()}")
                return None

            # Parse JSON output from stdout
            if result.stdout.strip():
                try:
                    hook_result = json.loads(result.stdout.strip())
                    # Default decision to allow if not specified
                    if "decision" not in hook_result:
                        hook_result["decision"] = "allow"
                    # Validate decision value if specified
                    if hook_result["decision"] not in ["allow", "block"]:
                        self._renderer.render_message("system", f"Hook {filepath.name} invalid 'decision': {hook_result['decision']}, defaulting to allow")
                        hook_result["decision"] = "allow"
                    if _is_hook_debug():
                        sys.stderr.write(f"[DEBUG] Hook parsed result: {hook_result}\n")
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

    def _execute_markdown_hook(self, hook_def: Dict[str, Any], event: Event) -> Optional[dict]:
        """Execute Markdown hook (simple message append).

        Markdown hooks append content as additionalContext for the LLM.

        Args:
            hook_def: Hook definition with "file" or "content" field
            event: Event object

        Returns:
            dict with additionalContext field
        """
        try:
            # Support either file path or inline content
            if "file" in hook_def:
                filepath = Path(hook_def["file"]).expanduser()
                content = filepath.read_text()
            elif "content" in hook_def:
                content = hook_def["content"]
            else:
                return None

            # Simple template variable replacement
            variables = event.data or {}
            for key, value in variables.items():
                content = content.replace(f"{{{{{key}}}}}", str(value))

            return {
                "decision": "allow",
                "additionalContext": content
            }
        except Exception as e:
            self._renderer.render_message("system", f"Markdown hook failed: {str(e)}")
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
        agents_dirs = ", ".join(self._config.paths.agents_dirs)
        commands_dirs = ", ".join(self._config.paths.commands_dirs)

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
            '{agents_dirs}': agents_dirs,
            '{commands_dirs}': commands_dirs,

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
                if arg_data.strip():
                    try:
                        arguments = json.loads(arg_data)
                    except json.JSONDecodeError as e:
                        self._renderer.render_error(f"Invalid arguments for {tool_name}: {e}")
                        arguments = {}
                else:
                    arguments = {}
            else:
                arguments = arg_data or {}

            # Notify sink of tool start
            self._sink.on_tool_start(tool_name, arguments, tool_call["id"])

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

            # Notify sink of tool completion
            tool_result = result.get("result", result)
            success = tool_result.get("success", True)
            self._sink.on_tool_end(tool_name, arguments, tool_call["id"], result, success)

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
        allowed_tools = self._get_allowed_tools()
        tools = self._tool_registry.to_openai_format(allowed_tools)
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
                self._sink.on_message(next_msg["role"], content)

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
        # Notify sink: turn is starting
        self._sink.on_turn_start(input)

        # Check for slash commands
        command, args = self._parse_slash_command(input)
        if command:
            return self._handle_slash_command(command, args)

        # Regular message - add to session (don't render, it's shown in prompt)
        self._session.add_message("user", input)
        # Publish UserPromptSubmit event
        if _is_hook_debug():
            sys.stderr.write(f"[DEBUG] Publishing UserPromptSubmit event\n")
        self._event_bus.publish(Event("UserPromptSubmit", {
            "role": "user",
            "content": input
        }))
        return "message_processed"

    def init_session(self) -> None:
        """Initialize a session: restore loaded skills/agents, generate session_id,
        reset HookContext, log session start, publish SessionStart event.

        Shared by both CLI run() and the Web entrypoint.
        """
        import uuid

        # Restore loaded skills/agents from session (if resuming)
        loaded_skills = self._session.get_loaded_skills()
        loaded_agents = self._session.get_loaded_agents()
        if loaded_skills:
            self._loaded_skills.update(loaded_skills)
        if loaded_agents:
            self._loaded_agents.update(loaded_agents)

        # Generate session ID and log session start
        self._session_id = str(uuid.uuid4())
        self._hook_context.reset(self._session_id)
        if self._logger:
            self._logger.log_session_start(self._session_id)

        # Publish SessionStart event
        if _is_hook_debug():
            sys.stderr.write(f"[DEBUG] Publishing SessionStart event\n")
        self._event_bus.publish(Event("SessionStart", {
            "session_id": self._session_id,
            "context": "startup",
        }))

    def _run_one_turn(self) -> None:
        """Send current session messages to API and process the response.

        Handles tool_calls recursively (delegated to _handle_tool_calls_in_message).
        For a plain-text response, adds it to session and renders.

        Shared by both CLI run() loop and Web /api/turn handler.
        """
        messages = self._prepare_messages_with_context()
        allowed_tools = self._get_allowed_tools()
        tools = self._tool_registry.to_openai_format(allowed_tools)

        response = self._api_client.send_message(messages, tools)
        for msg in response:
            # Handle tool calls
            if "tool_calls" in msg and msg["tool_calls"]:
                self._handle_tool_calls_in_message(msg, response)
            else:
                content = msg.get("content", "")
                self._session.add_message(msg["role"], content)
                try:
                    self._renderer.render_message(msg["role"], content)
                except Exception as e:
                    self._renderer.render_error(f"Failed to render message: {str(e)}")
                    plain_content = content[:500] if content else ""
                    print(f"\n{msg['role']}: {plain_content}")

        # Turn finished
        self._sink.on_turn_end()

    def run(self):
        """Main run loop."""
        self.init_session()

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
                user_input = self._prompt_session.prompt(
                    "> ",
                )
                result = self.process_input(user_input)

                if result == "exit":
                    self._renderer.render_message("system", "Goodbye!")
                    # Publish Stop event
                    self._event_bus.publish(Event("Stop", {
                        "responseLength": 0,
                        "usedTools": []
                    }))
                    break
                elif result == "message_processed" or result == "command_processed":
                    self._run_one_turn()
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
                import traceback
                self._renderer.render_error(f"{type(e).__name__}: {e}")
                if _is_hook_debug():
                    self._renderer.console.print(f"[dim]{traceback.format_exc()}[/dim]")
