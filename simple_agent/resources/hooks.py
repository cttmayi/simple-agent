import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from shlex import split


class HookLoader:
    """Loader for hook resources from JSON configuration file."""

    def __init__(self, hook_config_path: Optional[Union[str, Path]] = None):
        """Initialize HookLoader with hooks.json configuration path.

        Args:
            hook_config_path: Path to hooks.json file. If None, uses default path.
        """
        if hook_config_path is None:
            # Default to plugins/default/hooks/hooks.json
            self._config_path = Path.cwd() / "plugins/default/hooks/hooks.json"
        else:
            self._config_path = Path(hook_config_path).expanduser().resolve()

        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """Load hooks.json configuration file."""
        if self._config_path.exists():
            try:
                with open(self._config_path) as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                # If config file exists but is invalid, log warning but don't fail
                print(f"Warning: Failed to load hooks.json: {e}")
                self._config = {}
        else:
            self._config = {}

    def scan(self) -> List[Dict[str, Any]]:
        """Scan hooks.json for hook definitions."""
        hooks = []
        hooks_config = self._config.get("hooks", {})

        for event_name, hook_groups in hooks_config.items():
            if isinstance(hook_groups, list):
                for hook_group in hook_groups:
                    if isinstance(hook_group, dict):
                        hooks.append({
                            "event_name": event_name,
                            "matcher": hook_group.get("matcher", ""),
                            "hooks": hook_group.get("hooks", []),
                        })

        return hooks

    def list_hooks(self) -> List[dict]:
        """List all available hooks."""
        return self.scan()

    def get_hooks_for_event(self, event_name: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all hooks that should be triggered for a specific event.

        Args:
            event_name: The event name to filter by
            context: Optional context string to match against the matcher regex

        Returns:
            List of hook configurations that match the event and context
        """
        hooks = self.scan()
        matching_hooks = []

        for hook in hooks:
            if hook["event_name"] == event_name:
                matcher = hook.get("matcher", "")
                # If matcher is empty, always include
                # If context is provided and matcher matches, include
                if not matcher:
                    matching_hooks.append(hook)
                elif context and re.search(matcher, context):
                    matching_hooks.append(hook)

        return matching_hooks

    def reload(self):
        """Reload hooks.json configuration."""
        self._load_config()
