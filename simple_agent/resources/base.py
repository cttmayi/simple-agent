import frontmatter
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import dataclass


@dataclass
class BaseResource:
    """Base class for all resources (skills, subagents, hooks, commands)."""
    name: str
    description: str
    path: Path
    metadata: Dict[str, Any]


class ResourceLoader:
    """Base class for loading resources from directories."""

    def __init__(self, base_dir: Path):
        self._base_dir = Path(base_dir)

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        raise NotImplementedError()

    def scan(self) -> List[Dict[str, Any]]:
        """Scan base directory for resources."""
        if not self._base_dir.exists():
            return []

        resources = []
        for item in self._base_dir.iterdir():
            if item.is_dir():
                md_file = self._get_markdown_file(item)
                if md_file and md_file.exists():
                    parsed = frontmatter.load(md_file)
                    resources.append({
                        "name": parsed.get("name", item.name),
                        "description": parsed.get("description", ""),
                        "path": str(item),
                        "metadata": parsed.metadata,
                        "content": parsed.content,
                    })
        return resources

    def load(self, name: str) -> BaseResource:
        """Load a specific resource by name."""
        resources = self.scan()
        for r in resources:
            if r["name"] == name:
                return BaseResource(
                    name=r["name"],
                    description=r["description"],
                    path=Path(r["path"]),
                    metadata=r["metadata"],
                )
        raise ValueError(f"Resource not found: {name}")
