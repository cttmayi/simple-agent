from pathlib import Path
from typing import List, Optional, Union
import frontmatter


class CommandLoader:
    """Loader for command resources (supports .md files with namespace) from multiple directories."""

    def __init__(self, base_dirs: Union[str, Path, List[str], List[Path]]):
        """Initialize CommandLoader with one or more base directories.

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

    def list_commands(self) -> List[dict]:
        """List all available commands."""
        commands = []
        seen_commands = set()  # Track command names to avoid duplicates

        for base_dir in self._base_dirs:
            if not base_dir.exists():
                continue

            # Skills directories: only load SKILL.md files from first level subdirectories
            # Commands directories: scan recursively for all .md files
            if "skill" in base_dir.name.lower() or any("skill" in d.lower() for d in base_dir.parts):
                # Skills: only look for SKILL.md files in immediate subdirectories
                md_files = base_dir.glob("*/SKILL.md")
            else:
                # Commands: recursive scan
                md_files = base_dir.rglob("*.md")

            for md_file in md_files:
                # Skip README.md files (only in recursive command scanning)
                if md_file.name == "README.md":
                    continue

                # Calculate relative path as command name with namespace
                rel_path = md_file.relative_to(base_dir)
                command_name = str(rel_path.with_suffix('')).replace('\\', '/')

                parsed = frontmatter.load(md_file)

                # Use frontmatter name if available, otherwise fall back to filename-based name
                name = parsed.get("name", command_name)

                # Skip if we've already seen this command name (first directory wins)
                if name in seen_commands:
                    continue

                commands.append({
                    "name": name,
                    "description": parsed.get("description", ""),
                    "path": str(md_file),
                    "metadata": parsed.metadata,
                    "content": parsed.content,
                    "base_dir": str(base_dir),
                })
                seen_commands.add(name)

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