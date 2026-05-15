from pathlib import Path
from typing import List, Optional
import frontmatter


class CommandLoader:
    """Loader for command resources (flat .md files)."""

    def __init__(self, base_dir: Path):
        self._base_dir = Path(base_dir)

    def list_commands(self) -> List[dict]:
        """List all available commands."""
        if not self._base_dir.exists():
            return []

        commands = []
        for item in self._base_dir.iterdir():
            if item.is_file() and item.suffix == ".md" and item.name != "README.md":
                parsed = frontmatter.load(item)
                # Use filename without .md as name if not in frontmatter
                name = parsed.get("name", item.stem)
                commands.append({
                    "name": name,
                    "description": parsed.get("description", ""),
                    "path": str(item),
                    "metadata": parsed.metadata,
                    "content": parsed.content,
                })
        return commands

    def get_command(self, name: str) -> Optional[dict]:
        """Get a specific command by name."""
        commands = self.list_commands()
        for cmd in commands:
            if cmd["name"] == name:
                return cmd
        return None

    def get_command_usage(self, name: str) -> Optional[str]:
        """Get usage string for a command."""
        cmd = self.get_command(name)
        if cmd:
            return cmd["metadata"].get("usage", f"/{cmd['name']}")
        return None