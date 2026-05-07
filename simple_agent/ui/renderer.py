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
        else:
            style = "bold yellow"
            prefix = role

        self.console.print(f"\n[{style}]{prefix}[/{style}]:")
        self.console.print(Markdown(content))

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
