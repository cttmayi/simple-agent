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
    skills_dir: str = "./.simple-agent/plugin/skills"
    agents_dir: str = "./.simple-agent/plugin/agents"
    hooks_dir: str = "./.simple-agent/plugin/hooks"
    commands_dir: str = "./.simple-agent/plugin/commands"
    tools_dir: str = "./.simple-agent/tools"
    memory_dir: str = "./.simple-agent/memory"
    logs_dir: str = "./.simple-agent/logs"


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


def load_config() -> Settings:
    """Load configuration with priority: CLI args > ENV > file > defaults."""
    config_data = {}

    # Check local config
    local_config = Path.cwd() / ".simple-agent" / "config.yml"
    if local_config.exists():
        config_data.update(_load_yaml_config(local_config))

    # Check user config
    user_config = Path.home() / ".config" / "simple-agent" / "config.yml"
    if user_config.exists():
        # User config should be loaded before local, but local takes priority
        user_data = _load_yaml_config(user_config)
        # Merge with user as base, local overrides
        merged = {**user_data, **config_data}
        config_data = merged

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
