import frontmatter
from pathlib import Path
from typing import List, Optional, Union
from simple_agent.resources.base import BaseResource


class SkillLoader:
    """Loader for skill resources from multiple directories."""

    def __init__(self, base_dirs: Union[str, Path, List[str], List[Path]]):
        """Initialize SkillLoader with one or more base directories.

        Args:
            base_dirs: Single directory path as string/Path, or list of directory paths.
                        Paths can be absolute or relative. Supports ~ expansion.
        """
        if not isinstance(base_dirs, list):
            base_dirs = [base_dirs]

        self._base_dirs = []
        for d in base_dirs:
            if isinstance(d, Path):
                # Expanduser only if Path object, resolve() will handle relative paths
                self._base_dirs.append(d.expanduser().resolve())
            else:
                # String path - expanduser and resolve
                self._base_dirs.append(Path(d).expanduser().resolve())

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        return resource_dir / "SKILL.md"

    def scan(self) -> List[Dict[str, Any]]:
        """Scan all base directories for resources."""
        from typing import Any

        resources = []
        seen_names = set()  # Track skill names to avoid duplicates

        for base_dir in self._base_dirs:
            if not base_dir.exists():
                continue

            for item in base_dir.iterdir():
                if item.is_dir():
                    # Skip if we've already seen this skill name (first directory wins)
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
                                "base_dir": str(base_dir),  # Track which directory this came from
                            })
                            seen_names.add(parsed.get("name", item.name))
                        except Exception:
                            # Skip skills that can't be parsed
                            continue

        return resources

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

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Get skill information by name.

        Args:
            name: Skill name

        Returns:
            Dict with keys: name, description, path, metadata, content
        """
        resources = self.scan()
        for r in resources:
            if r["name"] == name:
                return r
        return None