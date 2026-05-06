from pathlib import Path
from typing import List, Optional
from simple_agent.resources.base import ResourceLoader


class SubagentLoader(ResourceLoader):
    """Loader for subagent resources."""

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        return resource_dir / "AGENT.md"

    def list_subagents(self) -> List[dict]:
        """List all available subagents."""
        return self.scan()

    def get_subagent_tools(self, name: str) -> Optional[List[str]]:
        """Get tool list for a subagent."""
        resources = self.scan()
        for r in resources:
            if r["name"] == name:
                return r["metadata"].get("tools")
        return None
