from pathlib import Path
from typing import List, Optional
from simple_agent.resources.base import ResourceLoader


class SkillLoader(ResourceLoader):
    """Loader for skill resources."""

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        return resource_dir / "SKILL.md"

    def list_skills(self) -> List[dict]:
        """List all available skills with metadata."""
        return self.scan()

    def get_skill_content(self, name: str) -> Optional[str]:
        """Get full markdown content of a skill."""
        resources = self.scan()
        for r in resources:
            if r["name"] == name:
                return r["content"]
        return None