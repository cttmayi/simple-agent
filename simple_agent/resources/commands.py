from pathlib import Path
from typing import List, Optional
import frontmatter


class CommandLoader:
    """Loader for command resources (supports .md files with namespace)."""

    def __init__(self, base_dir: Path):
        self._base_dir = Path(base_dir)

    def list_commands(self) -> List[dict]:
        """List all available commands."""
        if not self._base_dir.exists():
            return []

        commands = []
        for md_file in self._base_dir.rglob("*.md"):
            if md_file.name == "README.md":
                continue

            # Calculate relative path as command name with namespace
            rel_path = md_file.relative_to(self._base_dir)
            command_name = str(rel_path.with_suffix('')).replace('\\', '/')

            parsed = frontmatter.load(md_file)

            # Use frontmatter name if available, otherwise fall back to filename-based name
            name = parsed.get("name", command_name)

            commands.append({
                "name": name,
                "description": parsed.get("description", ""),
                "path": str(md_file),
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