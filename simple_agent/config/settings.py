import os
import yaml
from pathlib import Path
from typing import Optional
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

    config_data = {}

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
