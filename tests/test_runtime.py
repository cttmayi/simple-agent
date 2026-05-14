import os
import tempfile
from pathlib import Path
from simple_agent.core.runtime import Runtime
from simple_agent.config.settings import load_config, Settings


def test_runtime_initialization():
    config = load_config()
    runtime = Runtime(config)
    assert runtime._config == config


def test_runtime_process_command():
    # Use Settings() instead of Mock to avoid Path conversion issues
    config = Settings()
    runtime = Runtime(config)

    from unittest.mock import patch
    with patch.object(runtime, '_handle_slash_command') as mock_handle:
        mock_handle.return_value = "Command executed"
        result = runtime.process_input("/help")
        assert result == "Command executed"
        mock_handle.assert_called_once_with("help", [])


def test_runtime_load_agent_md():
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            agent_dir = Path(tmpdir) / "plugin"
            agent_dir.mkdir(parents=True)
            agent_md = agent_dir / "AGENT.md"
            agent_md.write_text("# Test Agent\n\nThis is a test.")

            config = Settings()
            runtime = Runtime(config, skip_api_init=True)
            context = runtime.get_agent_context()
            assert "Test Agent" in context
    finally:
        os.chdir(old_cwd)