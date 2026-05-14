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
            assert config.paths.skills_dir == "./.simple-agent/plugin/skills"
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
