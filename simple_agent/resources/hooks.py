from pathlib import Path
from typing import Any, Dict, List, Optional
from simple_agent.resources.base import ResourceLoader


class HookLoader(ResourceLoader):
    """Loader for hook resources."""

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        return resource_dir / "HOOK.md"

    def scan(self) -> List[Dict[str, Any]]:
        """Scan hooks/ directory subdirectories, each subdirectory is an event."""
        if not self._base_dir.exists():
            return []

        hooks = []

        for event_dir in sorted(self._base_dir.iterdir()):
            if not event_dir.is_dir():
                continue

            # Scan all hook files within the event directory
            hook_files = []
            for item in sorted(event_dir.iterdir()):
                if item.is_file():
                    ext = item.suffix.lower()
                    if ext in [".py", ".sh", ".cmd", ".md"]:
                        hook_files.append(item.name)

            if hook_files:
                hooks.append({
                    "event_name": event_dir.name,
                    "path": str(event_dir),
                    "files": hook_files,
                })

        return hooks

    def list_hooks(self) -> List[dict]:
        """List all available hooks."""
        return self.scan()
