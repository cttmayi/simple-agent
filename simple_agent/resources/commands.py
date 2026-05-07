from pathlib import Path
from typing import List, Optional
from simple_agent.resources.base import ResourceLoader


class CommandLoader(ResourceLoader):
    """Loader for command resources."""

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        return resource_dir / "COMMAND.md"

    def list_commands(self) -> List[dict]:
        """List all available commands."""
        return self.scan()

    def get_command_usage(self, name: str) -> Optional[str]:
        """Get usage string for a command."""
        resources = self.scan()
        for r in resources:
            if r["name"] == name:
                return r["metadata"].get("usage", f"/{r['name']}")
        return None