from pathlib import Path
from typing import List, Optional
from simple_agent.resources.base import ResourceLoader


class HookLoader(ResourceLoader):
    """Loader for hook resources."""

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        return resource_dir / "HOOK.md"

    def list_hooks(self) -> List[dict]:
        """List all available hooks."""
        hooks = self.scan()
        # Ensure events field is present
        for h in hooks:
            h["events"] = h["metadata"].get("events", [])
        return hooks

    def get_hook_events(self, name: str) -> Optional[List[str]]:
        """Get event list for a hook."""
        hooks = self.list_hooks()
        for h in hooks:
            if h["name"] == name:
                return h["events"]
        return None
