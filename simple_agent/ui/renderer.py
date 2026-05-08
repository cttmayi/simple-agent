import sys
from typing import TextIO
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel


class UIRenderer:
    def __init__(self, output: TextIO = sys.stdout):
        self.console = Console(file=output)

    def render_message(self, role: str, content: str) -> None:
        """Render a chat message."""
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

        self.console.print(f"\n[{style}]{prefix}[/{style}]:")
        if content:
            self.console.print(Markdown(content))

    def render_tool_result(self, tool_name: str, result: dict) -> None:
        """Render a tool execution result."""
        # Handle both direct result and wrapped result formats
        tool_result = result.get("result", result)

        success = tool_result.get("success", False)
        status = "[bold green]✓[/bold green]" if success else "[bold red]✗[/bold red]"
        self.console.print(f"  {status} {tool_name}")

        if "error" in tool_result:
            self.console.print(f"    [red]Error:[/red] {tool_result['error']}")
        elif "content" in tool_result:
            # Truncate long content
            content = tool_result["content"]
            if len(content) > 200:
                content = content[:200] + "..."
            self.console.print(f"    {content}")
        elif "stdout" in tool_result:
            stdout = tool_result["stdout"].strip()
            if stdout:
                self.console.print(f"    [dim]{stdout}[/dim]")
            if tool_result.get("stderr"):
                self.console.print(f"    [red]{tool_result['stderr'].strip()}[/red]")
        elif "matches" in tool_result:
            matches = tool_result["matches"]
            if matches:
                self.console.print(f"    Found {len(matches)} match(es)")
                for m in matches[:3]:  # Show first 3 matches
                    self.console.print(f"      Line {m['line']}: {m['content'][:80]}")
                if len(matches) > 3:
                    self.console.print(f"      ... and {len(matches) - 3} more")
            else:
                self.console.print(f"    [dim]No matches found[/dim]")

    def render_code(self, language: str, code: str) -> None:
        """Render a code block with syntax highlighting."""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self.console.print(Panel(syntax))

    def render_error(self, message: str) -> None:
        """Render an error message."""
        self.console.print(f"\n[bold red]Error:[/bold red] {message}")

    def render_warning(self, message: str) -> None:
        """Render a warning message."""
        self.console.print(f"\n[bold yellow]Warning:[/bold yellow] {message}")

    def render_thinking(self, message: str) -> None:
        """Render a thinking indicator."""
        self.console.print(f"[dim italic]... {message}[/dim italic]")
