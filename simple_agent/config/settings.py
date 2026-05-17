import os
import yaml
import json
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    provider: str = "openai"
    base_url: Optional[str] = None
    api_key: Optional[str] = Field(default=None)
    model: str = "gpt-4o"


class PathsConfig(BaseModel):
    skills_dirs: list[str] = ["./plugins/default/skills"]
    agents_dir: str = "./plugins/default/agents"
    hooks_dir: str = "./plugins/default/hooks"
    commands_dir: str = "./plugins/default/commands"
    tools_dir: str = "./.simple-agent/tools"
    memory_dir: str = "./.simple-agent/memory"
    logs_dir: str = "./.simple-agent/logs"
    plugin_dir: str = "./plugins/default"  # 新增插件目录配置


class UIConfig(BaseModel):
    theme: str = "dark"
    show_thinking: bool = True


class LoggingConfig(BaseModel):
    enabled: bool = True
    log_dir: Optional[str] = None  # Defaults to ./.simple-agent/logs


class Settings(BaseModel):
    api: APIConfig = Field(default_factory=APIConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    plugin_info: Optional[Dict[str, Any]] = None  # 插件元数据信息


def _resolve_env_var(value: str) -> str:
    """Resolve ${VAR} environment variables in strings."""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        var_name = value[2:-1]
        return os.environ.get(var_name, value)
    return value


def _load_yaml_config(path: Path) -> dict:
    """Load YAML config file."""
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _load_plugin_metadata(plugin_path: Path) -> Optional[Dict[str, Any]]:
    """Load plugin metadata from .claude-plugin/plugin.json.

    Args:
        plugin_path: Path to the plugin directory

    Returns:
        Plugin metadata dict or None if not found
    """
    plugin_json = plugin_path / ".claude-plugin" / "plugin.json"
    if plugin_json.exists():
        with open(plugin_json) as f:
            return json.load(f)
    return None


def load_config(plugin_dir: Optional[str] = None) -> Settings:
    """Load configuration with priority: CLI args > ENV > local > plugin > user > defaults.

    Args:
        plugin_dir: Path to the plugin directory (default: ./plugins/default)
    """
    # Set default plugin directory
    if plugin_dir is None:
        plugin_dir = "./plugins/default"

    # Resolve plugin directory relative to current directory
    plugin_path = Path.cwd() / plugin_dir
    # Get relative path from cwd to plugin (e.g., "plugins/default")
    try:
        plugin_relative = plugin_path.relative_to(Path.cwd())
    except ValueError:
        # plugin_path is not under cwd, use full path
        plugin_relative = str(plugin_path)

    config_data = {}

    # Load plugin metadata if available
    plugin_metadata = _load_plugin_metadata(plugin_path)
    if plugin_metadata:
        config_data["plugin_info"] = plugin_metadata

        # Apply resource paths from plugin.json if specified
        # These paths are relative to the plugin directory
        paths_data = config_data.setdefault("paths", {})

        if "agents" in plugin_metadata:
            agents_path = plugin_metadata["agents"]
            # Support both string and list for agents
            if isinstance(agents_path, list):
                agents_path = agents_path[0] if agents_path else "./agents"
            # Convert to path relative to cwd
            if agents_path.startswith("./") or agents_path.startswith("../"):
                # Already relative
                paths_data["agents_dir"] = str(plugin_relative / agents_path.lstrip("./"))
            else:
                # Directory name only, under plugin
                paths_data["agents_dir"] = str(plugin_relative / agents_path)

        if "skills" in plugin_metadata:
            skills_path = plugin_metadata["skills"]
            skills_dirs = []
            if isinstance(skills_path, list):
                for sp in skills_path:
                    if sp.startswith("./") or sp.startswith("../"):
                        skills_dirs.append(str(plugin_relative / sp.lstrip("./")))
                    else:
                        skills_dirs.append(str(plugin_relative / sp))
            else:
                if skills_path.startswith("./") or skills_path.startswith("../"):
                    skills_dirs.append(str(plugin_relative / skills_path.lstrip("./")))
                else:
                    skills_dirs.append(str(plugin_relative / skills_path))
            # Also include user's global skills directory
            skills_dirs.append("~/.agents/skills")
            paths_data["skills_dirs"] = skills_dirs

        if "hooks" in plugin_metadata:
            hooks_path = plugin_metadata["hooks"]
            # Support both string and list for hooks
            if isinstance(hooks_path, list):
                hooks_path = hooks_path[0] if hooks_path else "./hooks"
            if hooks_path.startswith("./") or hooks_path.startswith("../"):
                paths_data["hooks_dir"] = str(plugin_relative / hooks_path.lstrip("./"))
            else:
                paths_data["hooks_dir"] = str(plugin_relative / hooks_path)

        if "commands" in plugin_metadata:
            commands_path = plugin_metadata["commands"]
            # Support both string and list for commands
            if isinstance(commands_path, list):
                commands_path = commands_path[0] if commands_path else "./commands"
            if commands_path.startswith("./") or commands_path.startswith("../"):
                paths_data["commands_dir"] = str(plugin_relative / commands_path.lstrip("./"))
            else:
                paths_data["commands_dir"] = str(plugin_relative / commands_path)

    # Start with user config as base
    user_config = Path.home() / ".config" / "simple-agent" / "config.yml"
    if user_config.exists():
        config_data.update(_load_yaml_config(user_config))

    # Then plugin config (overrides user)
    plugin_config = plugin_path / "config.yml"
    if plugin_config.exists():
        # Merge with plugin as base
        merged = {**config_data, **_load_yaml_config(plugin_config)}
        config_data = merged

    # Then local config (highest priority, overrides everything)
    local_config = Path.cwd() / ".simple-agent" / "config.yml"
    if local_config.exists():
        # Merge with local as base
        merged = {**config_data, **_load_yaml_config(local_config)}
        config_data = merged

    # Set plugin_dir in config
    config_data.setdefault("paths", {})["plugin_dir"] = plugin_dir

    # Apply environment variable overrides
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        config_data.setdefault("api", {})["api_key"] = api_key

    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("ANTHROPIC_BASE_URL")
    if base_url:
        config_data.setdefault("api", {})["base_url"] = base_url

    # Expand environment variables in values
    if "api" in config_data:
        for key, value in config_data["api"].items():
            if isinstance(value, str):
                config_data["api"][key] = _resolve_env_var(value)

    return Settings(**config_data)
