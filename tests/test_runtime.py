from unittest.mock import Mock, patch
from simple_agent.core.runtime import Runtime
from simple_agent.config.settings import load_config

def test_runtime_initialization():
    config = load_config()
    runtime = Runtime(config)
    assert runtime._config == config

def test_runtime_process_command():
    config = Mock()
    runtime = Runtime(config)

    with patch.object(runtime, '_handle_slash_command') as mock_handle:
        mock_handle.return_value = "Command executed"
        result = runtime.process_input("/help")
        assert result == "Command executed"
        mock_handle.assert_called_once_with("help", [])

@patch('simple_agent.core.runtime.os.getcwd')
def test_runtime_load_agent_md(tmp_path, mock_getcwd):
    mock_getcwd.return_value = str(tmp_path)
    agent_md = tmp_path / "AGENT.md"
    agent_md.write_text("# Test Agent\n\nThis is a test.")

    config = Mock()
    runtime = Runtime(config)
    context = runtime.get_agent_context()
    assert "Test Agent" in context
