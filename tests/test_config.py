import os
import tempfile
from pathlib import Path
from simple_agent.config.settings import Settings, load_config

def test_load_default_config():
    import os
    import tempfile
    # Run in temp dir to avoid local config file
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        try:
            config = load_config()
            assert config.api.provider == "openai"
            assert config.api.model == "gpt-4o"
            assert config.paths.skills_dirs == ["./plugins/default/skills"]
            assert config.paths.memory_dir == "./.simple-agent/memory"
        finally:
            os.chdir(old_cwd)

def test_config_priority_env():
    os.environ["OPENAI_API_KEY"] = "test-key"
    config = load_config()
    assert config.api.api_key == "test-key"
    os.environ.pop("OPENAI_API_KEY", None)

def test_config_priority_file():
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".simple-agent" / "config.yml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text("api:\n  model: gpt-3.5-turbo\n")
            os.chdir(tmpdir)
            config = load_config()
            assert config.api.model == "gpt-3.5-turbo"
    finally:
        os.chdir(old_cwd)


def test_config_priority_levels():
    """Test configuration priority: local > user > plugin-specific > shared plugin > defaults."""
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Create plugin metadata (plugin.json controls resource paths)
            plugin_dir = Path(tmpdir) / "plugins/default"
            plugin_dir.mkdir(parents=True)
            plugin_metadata = plugin_dir / ".claude-plugin" / "plugin.json"
            plugin_metadata.parent.mkdir(parents=True)
            plugin_metadata.write_text('{"name": "test", "skills": ["./skills"], "agents": ["./agents"], "commands": ["./commands"]}')

            # Create shared plugin config (base settings)
            plugins_config = Path(tmpdir) / "plugins/config.yml"
            plugins_config.parent.mkdir(parents=True, exist_ok=True)
            plugins_config.write_text("api:\n  model: gpt-3.5\npaths:\n  tools_dir: ./.simple-agent/tools\n")

            # Create plugin-specific config (overrides shared)
            plugin_config = plugin_dir / "config.yml"
            plugin_config.write_text("api:\n  model: gpt-3.5-turbo\n")

            # Create local config (overrides plugin-specific)
            local_config = Path(tmpdir) / ".simple-agent" / "config.yml"
            local_config.parent.mkdir(parents=True)
            local_config.write_text("api:\n  model: gpt-4o-mini\n")

            config = load_config()

            # Local config should have highest priority for api.model
            assert config.api.model == "gpt-4o-mini"
            # skills_dirs from plugin.json (no automatic ~/.agents/skills)
            assert config.paths.skills_dirs == ["plugins/default/skills"]
            # agents_dirs from plugin.json (array format)
            assert config.paths.agents_dirs == ["plugins/default/agents"]
            # commands_dirs from plugin.json (array format)
            assert config.paths.commands_dirs == ["plugins/default/commands"]
            # tools_dir from shared plugin config
            assert config.paths.tools_dir == "./.simple-agent/tools"
    finally:
        os.chdir(old_cwd)


def test_plugin_json_array_paths():
    """Test plugin.json array format for resource paths."""
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Create plugin metadata with array paths
            plugin_dir = Path(tmpdir) / "plugins/default"
            plugin_dir.mkdir(parents=True)
            plugin_metadata = plugin_dir / ".claude-plugin" / "plugin.json"
            plugin_metadata.parent.mkdir(parents=True)
            plugin_metadata.write_text('{"name": "test", "skills": ["skills", "~/.agents/skills", "~/custom/skills"], "agents": ["agents", "~/custom/agents"], "commands": ["commands"]}')

            config = load_config()

            # All paths should be loaded as arrays
            # skills: from plugin.json (including ~/.agents/skills if explicitly configured)
            assert config.paths.skills_dirs == ["plugins/default/skills", "~/.agents/skills", "~/custom/skills"]
            assert config.paths.agents_dirs == ["plugins/default/agents", "~/custom/agents"]
            assert config.paths.commands_dirs == ["plugins/default/commands"]

            # Backwards compatibility: singular properties should still work
            assert config.paths.agents_dir == "plugins/default/agents"
            assert config.paths.commands_dir == "plugins/default/commands"
    finally:
        os.chdir(old_cwd)


def test_config_merge_additional_paths():
    """Test that YAML config can add additional resource paths to plugin.json paths."""
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Create plugin metadata with basic paths
            plugin_dir = Path(tmpdir) / "plugins/default"
            plugin_dir.mkdir(parents=True)
            plugin_metadata = plugin_dir / ".claude-plugin" / "plugin.json"
            plugin_metadata.parent.mkdir(parents=True)
            plugin_metadata.write_text('{"name": "test", "skills": ["./skills"], "agents": ["./agents"], "commands": ["./commands"]}')

            # Create shared plugin config with additional paths
            plugins_config = Path(tmpdir) / "plugins/config.yml"
            plugins_config.parent.mkdir(parents=True, exist_ok=True)
            plugins_config.write_text("""
paths:
  skills_dir: ["~/.agents/skills", "~/custom/skills"]
  agents_dir: "~/custom/agents"
""")

            config = load_config()

            # Skills: plugin.json + config.yml
            assert config.paths.skills_dirs == ["plugins/default/skills", "~/.agents/skills", "~/custom/skills"]
            # Agents: plugin.json + config.yml
            assert config.paths.agents_dirs == ["plugins/default/agents", "~/custom/agents"]
            # Commands: only from plugin.json
            assert config.paths.commands_dirs == ["plugins/default/commands"]

            # Backwards compatibility: singular properties return first path
            assert config.paths.agents_dir == "plugins/default/agents"
            assert config.paths.commands_dir == "plugins/default/commands"
    finally:
        os.chdir(old_cwd)
