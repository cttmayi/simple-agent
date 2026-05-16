import sys
from typing import TextIO
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from rich.markup import escape


class UIRenderer:
    def __init__(self, output: TextIO = sys.stdout):
        self.console = Console(file=output)
        self._current_role = None  # Track current role
        self._has_shown_system_prefix = False  # Track if system: prefix has been shown

    def render_message(self, role: str, content: str) -> None:
        """Render a chat message."""
        # Handle empty content for assistant role - show a placeholder
        if not content and role == "assistant":
            content = "(AI returned empty response)"
            self.console.print(f"\n[dim yellow]⚠ {content}[/dim yellow]")
            return

        # Skip empty content for other roles (but not for system to allow empty lines if needed)
        if not content and role != "system":
            return

        # For system role, show prefix only on first message
        if role == "system":
            if not self._has_shown_system_prefix:
                # First system message: show the prefix
                self._has_shown_system_prefix = True
                self.console.print(f"\n[bold yellow]system:[/bold yellow]")
            # Print content directly (no additional prefix)
            self.console.print(Markdown(content))
            return

        # For non-system roles, reset the prefix flag and handle normally
        self._has_shown_system_prefix = False
        self._current_role = role

        if role == "user":
            style = "bold blue"
            prefix = "You"
        elif role == "assistant":
            style = "bold green"
            prefix = "Assistant"
        elif role == "tool":
            style = "bold cyan"
            prefix = "Tool"
        else:
            style = "bold yellow"
            prefix = role

        try:
            self.console.print(f"\n[{style}]{prefix}[/{style}]:")
            if content:
                self.console.print(Markdown(content))
        except Exception as e:
            # Fallback to plain text if Markdown rendering fails
            self.console.print(f"\n[{style}]{prefix}[/{style}]:")
            if content:
                self.console.print(escape(content))

    def render_tool_result(self, tool_name: str, result: dict, arguments: dict = None) -> None:
        """Render a tool execution result with detailed output.

        Args:
            tool_name: Name of the tool
            result: Result dict from tool execution
            arguments: Optional arguments dict for display (not used - status shown by caller)
        """
        try:
            # Handle both direct result and wrapped result formats
            tool_result = result.get("result", result)

            # Skip status line - it's now shown by caller (runtime.py)

            # Show detailed output (not truncated for user feedback)
            if "error" in tool_result:
                # Show full error message
                error_msg = tool_result['error']
                self.console.print(f"  │  [red]Error:[/red] {escape(error_msg)}")
            elif "content" in tool_result:
                # Show file content with indentation and line limiting
                content = tool_result["content"]
                if content:
                    # Limit to first 5 lines, but always show truncation message if present
                    lines = content.split('\n')
                    has_truncation_msg = any('[文件已被截断' in line for line in lines)
                    if has_truncation_msg:
                        # Find and keep truncation message
                        truncation_start = next(i for i, line in enumerate(lines) if '[文件已被截断' in line)
                        content_lines = lines[:5] + lines[truncation_start:]
                        content = '\n'.join(content_lines)
                    elif len(lines) > 5:
                        content = '\n'.join(lines[:5])
                    # Escape rich markup and print with visual separator
                    escaped = escape(content)
                    for line in escaped.split('\n'):
                        if line.strip():  # Skip empty lines
                            self.console.print(f"  │  {line}", overflow="ignore")
            elif "stdout" in tool_result:
                # Show stdout with visual separator
                stdout = tool_result.get("stdout", "").strip()
                if stdout:
                    for line in stdout.split('\n'):
                        if line.strip():  # Skip empty lines
                            self.console.print(f"  │  {line}", overflow="ignore")
                # Show stderr if present
                stderr = tool_result.get("stderr", "").strip()
                if stderr:
                    for line in stderr.split('\n'):
                        self.console.print(f"  │  [red]{escape(line)}[/red]", overflow="ignore")
                # Show return code if non-zero
                returncode = tool_result.get("returncode")
                if returncode and returncode != 0:
                    self.console.print(f"  │  [dim]Exit code: {returncode}[/dim]")
            elif "matches" in tool_result:
                # Show match details
                matches = tool_result["matches"]
                if matches:
                    self.console.print(f"  │  [dim]Found {len(matches)} matches:[/dim]")
                    for m in matches:
                        self.console.print(f"  │      [cyan]Line {m['line']}:[/cyan] {escape(m['content'])}")
                else:
                    self.console.print(f"  │  [dim]No matches found[/dim]")
            elif "results" in tool_result:
                # Show web search results
                results = tool_result.get("results", [])
                if results:
                    self.console.print(f"  │  [dim]Found {len(results)} results:[/dim]")
                    for i, r in enumerate(results[:5], start=1):
                        title = r.get("title", "")
                        url = r.get("url", "")
                        snippet = r.get("snippet", "")
                        self.console.print(f"  │  [{i}] [link]{escape(title)}[/link]")
                        if url:
                            self.console.print(f"  │      URL: {url}")
                        if snippet and len(snippet) < 150:
                            self.console.print(f"  │      {escape(snippet)}")
                    if len(results) > 5:
                        self.console.print(f"  │  ... and {len(results) - 5} more results")
                else:
                    self.console.print(f"  │  [dim]No results found[/dim]")
        except Exception as e:
            # Fallback to simple output if rendering fails
            self.console.print(f"  Error rendering tool result: {escape(str(e))}")

    def render_code(self, language: str, code: str) -> None:
        """Render a code block with syntax highlighting."""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self.console.print(Panel(syntax))

    def render_error(self, message: str) -> None:
        """Render an error message."""
        self.console.print(f"\n[bold red]Error:[/bold red] {escape(message)}")

    def render_task_status(self, task: dict) -> None:
        """渲染任务状态内联显示。

        Args:
            task: 任务字典
        """
        status = task.get("status", "pending")
        task_id = task.get("id", "unknown")
        subject = task.get("subject", "")

        # 状态图标和样式
        status_config = {
            "pending": ("⏳", "dim"),
            "in_progress": ("⚙️", "yellow"),
            "completed": ("✓", "green"),
            "blocked": ("🚫", "red"),
            "deleted": ("🗑️", "dim")
        }

        icon, style = status_config.get(status, ("⏳", "dim"))

        # 进度
        progress = task.get("progress", 0)

        # 构建显示文本
        if status == "in_progress":
            text = f"[{style}]{icon} 任务 #{task_id} 进行中: {subject} ({progress}%)[/{style}]"
        elif status == "completed":
            text = f"[{style}]{icon} 任务 #{task_id} 完成: {subject}[/{style}]"
        elif status == "pending":
            text = f"[{style}]{icon} 任务 #{task_id}: {subject}[/{style}]"
        elif status == "blocked":
            text = f"[{style}]{icon} 任务 #{task_id} 阻塞: {subject}[/{style}]"
        else:
            text = f"[{style}]{icon} 任务 #{task_id}: {subject}[/{style}]"

        self.console.print(text)

    def render_task_list(self, tasks: list) -> None:
        """渲染任务列表（带层级缩进）。

        Args:
            tasks: 任务列表
        """
        self.console.print("\n[bold]任务列表[/bold]\n")

        def render_task_recursive(task: dict, indent: int = 0) -> None:
            """递归渲染任务。"""
            status = task.get("status", "pending")
            task_id = task.get("id", "?")
            subject = task.get("subject", "")
            progress = task.get("progress", 0)

            status_config = {
                "pending": ("⏳", "dim"),
                "in_progress": ("⚙️", "yellow"),
                "completed": ("✓", "green"),
                "blocked": ("🚫", "red"),
            }

            icon, style = status_config.get(status, ("⏳", "dim"))
            prefix = "  " * indent

            self.console.print(f"{prefix}[{style}]{icon} #{task_id}[/{style}] {subject} ({progress}%)")

            # 递归渲染子任务
            children = task.get("children", [])
            for child in children:
                render_task_recursive(child, indent + 1)

        for task in tasks:
            render_task_recursive(task)

        self.console.print()

    def render_warning(self, message: str) -> None:
        """Render a warning message."""
        self.console.print(f"\n[bold yellow]Warning:[/bold yellow] {escape(message)}")

    def render_thinking(self, message: str) -> None:
        """Render a thinking indicator."""
        self.console.print(Text.assemble(
            Text("... ", style="dim italic"),
            Text(escape(message), style="dim italic")
        ))

    def render_tool_result_indented(self, tool_name: str, result: dict, arguments: dict = None) -> None:
        """Render a tool execution result with indentation (for subagent tools).

        Args:
            tool_name: Name of the tool
            result: Result dict from tool execution
            arguments: Optional arguments dict for display
        """
        try:
            # Handle both direct result and wrapped result formats
            tool_result = result.get("result", result)

            # Show detailed output (not truncated for user feedback)
            if "error" in tool_result:
                # Show full error message
                error_msg = tool_result['error']
                self.console.print(f"  │    [red]Error:[/red] {escape(error_msg)}")
            elif "content" in tool_result:
                # Show file content with indentation and line limiting
                content = tool_result["content"]
                if content:
                    # Limit to first 5 lines, but always show truncation message if present
                    lines = content.split('\n')
                    has_truncation_msg = any('[文件已被截断' in line for line in lines)
                    if has_truncation_msg:
                        # Find and keep truncation message
                        truncation_start = next(i for i, line in enumerate(lines) if '[文件已被截断' in line)
                        content_lines = lines[:5] + lines[truncation_start:]
                        content = '\n'.join(content_lines)
                    elif len(lines) > 5:
                        content = '\n'.join(lines[:5])
                    # Escape rich markup and print with visual separator (extra indent for subagent)
                    escaped = escape(content)
                    for line in escaped.split('\n'):
                        if line.strip():  # Skip empty lines
                            self.console.print(f"  │    {line}", overflow="ignore")
            elif "stdout" in tool_result:
                # Show stdout with visual separator
                stdout = tool_result.get("stdout", "").strip()
                if stdout:
                    for line in stdout.split('\n'):
                        if line.strip():  # Skip empty lines
                            self.console.print(f"  │    {line}", overflow="ignore")
                # Show stderr if present
                stderr = tool_result.get("stderr", "").strip()
                if stderr:
                    for line in stderr.split('\n'):
                        self.console.print(f"  │    [red]{escape(line)}[/red]", overflow="ignore")
                # Show return code if non-zero
                returncode = tool_result.get("returncode")
                if returncode and returncode != 0:
                    self.console.print(f"  │    [dim]Exit code: {returncode}[/dim]")
            elif "matches" in tool_result:
                # Show match details
                matches = tool_result["matches"]
                if matches:
                    self.console.print(f"  │    [dim]Found {len(matches)} matches:[/dim]")
                    for m in matches:
                        self.console.print(f"  │        [cyan]Line {m['line']}:[/cyan] {escape(m['content'])}")
                else:
                    self.console.print(f"  │    [dim]No matches found[/dim]")
            elif "results" in tool_result:
                # Show web search results
                results = tool_result.get("results", [])
                if results:
                    self.console.print(f"  │    [dim]Found {len(results)} results:[/dim]")
                    for i, r in enumerate(results[:5], start=1):
                        title = r.get("title", "")
                        url = r.get("url", "")
                        snippet = r.get("snippet", "")
                        self.console.print(f"  │    [{i}] [link]{escape(title)}[/link]")
                        if url:
                            self.console.print(f"  │        URL: {url}")
                        if snippet and len(snippet) < 150:
                            self.console.print(f"  │        {escape(snippet)}")
                    if len(results) > 5:
                        self.console.print(f"  │    ... and {len(results) - 5} more results")
                else:
                    self.console.print(f"  │    [dim]No results found[/dim]")
        except Exception as e:
            # Fallback to simple output if rendering fails
            self.console.print(f"  Error rendering tool result: {escape(str(e))}")