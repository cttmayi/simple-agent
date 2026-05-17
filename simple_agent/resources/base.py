import frontmatter
from pathlib import Path
from typing import Any, Dict, List, Union
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

    def __init__(self, base_dirs: Union[str, Path, List[str], List[Path]]):
        """Initialize ResourceLoader with one or more base directories.

        Args:
            base_dirs: Single directory path as string/Path, or list of directory paths.
                       Paths can be absolute or relative. Supports ~ expansion.
        """
        if not isinstance(base_dirs, list):
            base_dirs = [base_dirs]

        self._base_dirs = []
        for d in base_dirs:
            if isinstance(d, Path):
                self._base_dirs.append(d.expanduser().resolve())
            else:
                self._base_dirs.append(Path(d).expanduser().resolve())

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        raise NotImplementedError()

    def scan(self) -> List[Dict[str, Any]]:
        """Scan all base directories for resources."""
        resources = []
        seen_names = set()  # Track resource names to avoid duplicates

        for base_dir in self._base_dirs:
            if not base_dir.exists():
                continue

            for item in base_dir.iterdir():
                if item.is_dir():
                    # Skip if we've already seen this resource name (first directory wins)
                    if item.name in seen_names:
                        continue

                    md_file = self._get_markdown_file(item)
                    if md_file and md_file.exists():
                        try:
                            parsed = frontmatter.load(md_file)
                            resources.append({
                                "name": parsed.get("name", item.name),
                                "description": parsed.get("description", ""),
                                "path": str(item),
                                "metadata": parsed.metadata,
                                "content": parsed.content,
                                "base_dir": str(base_dir),
                            })
                            seen_names.add(parsed.get("name", item.name))
                        except Exception:
                            # Skip resources that can't be parsed
                            continue

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
