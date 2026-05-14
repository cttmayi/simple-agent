from pathlib import Path
from typing import List, Optional
from simple_agent.resources.base import ResourceLoader


class AgentLoader(ResourceLoader):
    """Loader for agent resources."""

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        return resource_dir / "AGENT.md"

    def list_agents(self) -> List[dict]:
        """List all available agents."""
        return self.scan()

    def get_agent_tools(self, name: str) -> Optional[List[str]]:
        """Get tool list for an agent."""
        resources = self.scan()
        for r in resources:
            if r["name"] == name:
                return r["metadata"].get("tools")
        return None