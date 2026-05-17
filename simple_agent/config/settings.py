import os
import yaml
import json
from pathlib import Path
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field, model_validator, ConfigDict


class APIConfig(BaseModel):
    provider: str = "openai"
    base_url: Optional[str] = None
    api_key: Optional[str] = Field(default=None)
    model: str = "gpt-4o"


class PathsConfig(BaseModel):
    skills_dirs: list[str] = ["./plugins/default/skills"]
    additional_skills_dir: Optional[Union[str, list[str]]] = Field(default=None, alias="skills_dir")
    agents_dirs: list[str] = ["./plugins/default/agents"]
    additional_agents_dir: Optional[Union[str, list[str]]] = Field(default=None, alias="agents_dir")
    commands_dirs: list[str] = ["./plugins/default/commands"]
    additional_commands_dir: Optional[Union[str, list[str]]] = Field(default=None, alias="commands_dir")
    tools_dir: str = "./.simple-agent/tools"
    memory_dir: str = "./.simple-agent/memory"
    logs_dir: str = "./.simple-agent/logs"
    plugin_dir: str = "./plugins/default"

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode='after')
    def merge_additional_paths(self):
        """Merge additional paths from config into the main path lists."""
        # Merge skills
        if self.additional_skills_dir is not None:
            if isinstance(self.additional_skills_dir, str):
                self.skills_dirs.append(self.additional_skills_dir)
            else:
                self.skills_dirs.extend(self.additional_skills_dir)

        # Merge agents
        if self.additional_agents_dir is not None:
            if isinstance(self.additional_agents_dir, str):
                self.agents_dirs.append(self.additional_agents_dir)
            else:
                self.agents_dirs.extend(self.additional_agents_dir)

        # Merge commands
        if self.additional_commands_dir is not None:
            if isinstance(self.additional_commands_dir, str):
                self.commands_dirs.append(self.additional_commands_dir)
            else:
                self.commands_dirs.extend(self.additional_commands_dir)

        return self

    # Backwards compatibility - allow accessing as singular names (returns first path)
    @property
    def agents_dir(self) -> str:
        return self.agents_dirs[0] if self.agents_dirs else "./plugins/default/agents"

    @property
    def commands_dir(self) -> str:
        return self.commands_dirs[0] if self.commands_dirs else "./plugins/default/commands"


class UIConfig(BaseModel):
    theme: str = "dark"
    show_thinking: bool = True


class LoggingConfig(BaseModel):
    enabled: bool = True
    log_dir: Optional[str] = None  # Defaults to ./.simple-agent/logs


class ToolsConfig(BaseModel):
    """配置哪些工具对 LLM 可用。

    工具名称为键，布尔值为值。true 表示可用，false 表示禁用。
    如果工具名未在配置中指定，默认为可用（true）。
    """
    # 内置工具默认全部可用
    Bash: bool = True
    Read: bool = True
    Write: bool = True
    Edit: bool = True
    Grep: bool = True
    Glob: bool = True
    Skill: bool = True
    # TODO 工具
    TaskCreate: bool = True
    TaskGet: bool = True
    TaskUpdate: bool = True
    TaskList: bool = True
    # Agent 工具
    Agent: bool = True
    # 其他自定义工具可以在这里添加

    def is_enabled(self, tool_name: str) -> bool:
        """检查工具是否启用。

        Args:
            tool_name: 工具名称

        Returns:
            bool: 如果工具启用返回 True，否则返回 False
        """
        # 尝试匹配工具名（处理大小写变化）
        # 例如工具注册表中的名称可能是 'bash'，但配置中的字段名是 'Bash'
        # 首先尝试直接匹配
        if hasattr(self, tool_name):
            return getattr(self, tool_name)

        # 尝试首字母大写的形式
        capitalized = tool_name.capitalize()
        if hasattr(self, capitalized):
            return getattr(self, capitalized)

        # 尝试全大写的形式
        upper = tool_name.upper()
        if hasattr(self, upper):
            return getattr(self, upper)

        # 默认启用
        return True


class Settings(BaseModel):
    api: APIConfig = Field(default_factory=APIConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    plugin_info: Optional[Dict[str, Any]] = None  # 插件元数据信息


def _resolve_env_var(value: str) -> str:
    """Resolve ${VAR} environment variables in strings."""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        var_name = value[2:-1]
        return os.environ.get(var_name, value)
    return value


def _deep_merge(base: dict, update: dict) -> dict:
    """Deep merge two dictionaries.

    Args:
        base: Base dictionary to merge into
        update: Dictionary to merge from (takes precedence)

    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


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
    """Load configuration with priority: CLI args > ENV > local > user > plugin_config.yml > defaults.

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
            agents_dirs = []
            if isinstance(agents_path, list):
                for ap in agents_path:
                    if ap.startswith("~") or ap.startswith("/"):
                        agents_dirs.append(ap)
                    elif ap.startswith("./") or ap.startswith("../"):
                        # Already relative - strip leading ./ and make relative to plugin
                        agents_dirs.append(str(plugin_relative / ap.lstrip("./")))
                    else:
                        # Directory name only, under plugin
                        agents_dirs.append(str(plugin_relative / ap))
            else:
                if agents_path.startswith("~") or agents_path.startswith("/"):
                    agents_dirs.append(agents_path)
                elif agents_path.startswith("./") or agents_path.startswith("../"):
                    # Already relative - strip leading ./ and make relative to plugin
                    agents_dirs.append(str(plugin_relative / agents_path.lstrip("./")))
                else:
                    # Directory name only, under plugin
                    agents_dirs.append(str(plugin_relative / agents_path))
            paths_data["agents_dirs"] = agents_dirs

        if "skills" in plugin_metadata:
            skills_path = plugin_metadata["skills"]
            skills_dirs = []
            if isinstance(skills_path, list):
                for sp in skills_path:
                    if sp.startswith("~") or sp.startswith("/"):
                        skills_dirs.append(sp)
                    elif sp.startswith("./") or sp.startswith("../"):
                        # Already relative - strip leading ./ and make relative to plugin
                        skills_dirs.append(str(plugin_relative / sp.lstrip("./")))
                    else:
                        # Directory name only, under plugin
                        skills_dirs.append(str(plugin_relative / sp))
            else:
                if skills_path.startswith("~") or skills_path.startswith("/"):
                    skills_dirs.append(skills_path)
                elif skills_path.startswith("./") or skills_path.startswith("../"):
                    # Already relative - strip leading ./ and make relative to plugin
                    skills_dirs.append(str(plugin_relative / skills_path.lstrip("./")))
                else:
                    # Directory name only, under plugin
                    skills_dirs.append(str(plugin_relative / skills_path))
            paths_data["skills_dirs"] = skills_dirs

        if "commands" in plugin_metadata:
            commands_path = plugin_metadata["commands"]
            commands_dirs = []
            if isinstance(commands_path, list):
                for cp in commands_path:
                    if cp.startswith("~") or cp.startswith("/"):
                        commands_dirs.append(cp)
                    elif cp.startswith("./") or cp.startswith("../"):
                        # Already relative - strip leading ./ and make relative to plugin
                        commands_dirs.append(str(plugin_relative / cp.lstrip("./")))
                    else:
                        # Directory name only, under plugin
                        commands_dirs.append(str(plugin_relative / cp))
            else:
                if commands_path.startswith("~") or commands_path.startswith("/"):
                    commands_dirs.append(commands_path)
                elif commands_path.startswith("./") or commands_path.startswith("../"):
                    # Already relative - strip leading ./ and make relative to plugin
                    commands_dirs.append(str(plugin_relative / commands_path.lstrip("./")))
                else:
                    # Directory name only, under plugin
                    commands_dirs.append(str(plugin_relative / commands_path))
            paths_data["commands_dirs"] = commands_dirs

        # Auto-discover default resource directories if not specified in plugin.json
        # This allows plugins like superpowers to work without explicit path configuration
        if "skills_dirs" not in paths_data:
            skills_dir = plugin_path / "skills"
            if skills_dir.exists() and skills_dir.is_dir():
                paths_data["skills_dirs"] = [str(plugin_relative / "skills")]

        if "agents_dirs" not in paths_data:
            agents_dir = plugin_path / "agents"
            if agents_dir.exists() and agents_dir.is_dir():
                paths_data["agents_dirs"] = [str(plugin_relative / "agents")]

        if "commands_dirs" not in paths_data:
            commands_dir = plugin_path / "commands"
            if commands_dir.exists() and commands_dir.is_dir():
                paths_data["commands_dirs"] = [str(plugin_relative / "commands")]

    # Start with plugins/config.yml as base (shared config for all plugins)
    plugins_config = Path.cwd() / "plugins" / "config.yml"
    if plugins_config.exists():
        config_data = _deep_merge(config_data, _load_yaml_config(plugins_config))

    # Then plugin-specific config (overrides plugins/config.yml)
    plugin_config = plugin_path / "config.yml"
    if plugin_config.exists():
        config_data = _deep_merge(config_data, _load_yaml_config(plugin_config))

    # Then user config (overrides plugin config)
    user_config = Path.home() / ".config" / "simple-agent" / "config.yml"
    if user_config.exists():
        config_data = _deep_merge(config_data, _load_yaml_config(user_config))

    # Then local config (highest priority)
    local_config = Path.cwd() / ".simple-agent" / "config.yml"
    if local_config.exists():
        config_data = _deep_merge(config_data, _load_yaml_config(local_config))

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
