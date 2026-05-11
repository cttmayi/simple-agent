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
        self._current_role = None  # Track current role for merging consecutive system messages

    def render_message(self, role: str, content: str) -> None:
        """Render a chat message."""
        # Skip empty content
        if not content:
            return

        # For system role, we want to merge consecutive system messages
        if role == "system":
            if self._current_role != "system":
                # Starting a new block of system messages, show the prefix
                self._current_role = "system"
                self.console.print(f"\n[bold yellow]system:[/bold yellow]")
            # Just print content without additional prefix for system
            self.console.print(Markdown(content))
            return

        # For non-system roles, reset current role and handle normally
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
            # For system role, just print content
            if role == "system":
                if content:
                    self.console.print(escape(content))
                return

            self.console.print(f"\n[{style}]{prefix}[/{style}]:")
            if content:
                self.console.print(escape(content))

    def render_tool_result(self, tool_name: str, result: dict, arguments: dict = None) -> None:
        """Render a tool execution result with detailed output.

        Args:
            tool_name: Name of the tool
            result: Result dict from tool execution
            arguments: Optional arguments dict for display
        """
        try:
            # Handle both direct result and wrapped result formats
            tool_result = result.get("result", result)

            success = tool_result.get("success", False)
            status = "[bold green]✓[/bold green]" if success else "[bold red]✗[/bold red]"

            # Show full command/parameters on same line with status
            if arguments:
                args_display = []
                for key, value in arguments.items():
                    # Only show user-relevant args
                    if key not in ["cwd", "timeout", "case_sensitive"]:
                        # Truncate long values for display
                        value_str = str(value)
                        if len(value_str) > 20:
                            value_str = value_str[:20] + "..."
                        args_display.append(f"{key}={value_str}")
                if args_display:
                    # Build args string and escape it
                    args_str = '[' + ', '.join(args_display) + ']'
                    # Print status with markup, tool name, and escaped args
                    self.console.print(f"  {status} {tool_name} {escape(args_str)}")
                else:
                    self.console.print(f"  {status} {tool_name}")
            else:
                self.console.print(f"  {status} {tool_name}")

            # Show detailed output (not truncated for user feedback)
            if "error" in tool_result:
                # Show full error message
                self.console.print(f"  [red]Error:[/red] {escape(tool_result['error'])}")
            elif "content" in tool_result:
                # Show full file content (no truncation for user feedback)
                content = tool_result["content"]
                if content:
                    # Escape rich markup to prevent MarkupError
                    self.console.print(f"  {escape(content)}")
            elif "stdout" in tool_result:
                # Show stdout (no truncation)
                stdout = tool_result.get("stdout", "").strip()
                if stdout:
                    self.console.print(f"  {stdout}")
                # Show stderr if present
                stderr = tool_result.get("stderr", "").strip()
                if stderr:
                    self.console.print(f"  [red]{escape(stderr)}[/red]")
                # Show return code if non-zero
                returncode = tool_result.get("returncode")
                if returncode and returncode != 0:
                    self.console.print(f"  [dim]Exit code: {returncode}[/dim]")
            elif "matches" in tool_result:
                # Show match details
                matches = tool_result["matches"]
                if matches:
                    self.console.print(f"  [dim]Found {len(matches)} matches:[/dim]")
                    for m in matches:
                        self.console.print(f"      [cyan]Line {m['line']}:[/cyan] {escape(m['content'])}")
                else:
                    self.console.print(f"  [dim]No matches found[/dim]")
            elif "results" in tool_result:
                # Show web search results
                results = tool_result.get("results", [])
                if results:
                    self.console.print(f"  [dim]Found {len(results)} results:[/dim]")
                    for i, r in enumerate(results[:5], start=1):
                        title = r.get("title", "")
                        url = r.get("url", "")
                        snippet = r.get("snippet", "")
                        self.console.print(f"  [{i}] [link]{escape(title)}[/link]")
                        if url:
                            self.console.print(f"        URL: {url}")
                        if snippet and len(snippet) < 150:
                            self.console.print(f"        {escape(snippet)}")
                    if len(results) > 5:
                        self.console.print(f"  ... and {len(results) - 5} more results")
                else:
                    self.console.print(f"  [dim]No results found[/dim]")
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

    def render_warning(self, message: str) -> None:
        """Render a warning message."""
        self.console.print(f"\n[bold yellow]Warning:[/bold yellow] {escape(message)}")

    def render_thinking(self, message: str) -> None:
        """Render a thinking indicator."""
        self.console.print(Text.assemble(
            Text("... ", style="dim italic"),
            Text(escape(message), style="dim italic")
        ))