import os
import tempfile
from pathlib import Path
from simple_agent.config.settings import Settings, load_config
from simple_agent.core.runtime import Runtime
from simple_agent.core.session import Session
from simple_agent.resources.commands import CommandLoader

def test_parse_slash_command():
    """Test slash command parsing."""
    config = load_config()
    runtime = Runtime(config, skip_api_init=True)

    # Test parsing valid commands
    command, args = runtime._parse_slash_command("/help")
    assert command == "help"
    assert args == []

    command, args = runtime._parse_slash_command("/exit")
    assert command == "exit"
    assert args == []

    command, args = runtime._parse_slash_command("/config get model")
    assert command == "config"
    assert args == ["get", "model"]

    command, args = runtime._parse_slash_command("/skills load test")
    assert command == "skills"
    assert args == ["load", "test"]

    # Test non-slash input
    command, args = runtime._parse_slash_command("hello world")
    assert command is None
    assert args == []

def test_parse_slash_command_empty():
    """Test parsing empty slash command."""
    config = load_config()
    runtime = Runtime(config, skip_api_init=True)

    command, args = runtime._parse_slash_command("/")
    assert command is None
    assert args == []

    command, args = runtime._parse_slash_command("/  ")
    assert command is None
    assert args == []

def test_handle_builtin_commands():
    """Test builtin command handling."""
    config = load_config()
    runtime = Runtime(config, skip_api_init=True)

    # Test /help
    result = runtime._handle_slash_command("help", [])
    assert result.startswith("# Available Commands")
    assert "/help" in result
    assert "/exit" in result

    # Test /exit
    result = runtime._handle_slash_command("exit", [])
    assert result == "exit"

    result = runtime._handle_slash_command("quit", [])
    assert result == "exit"

    # Test unknown command
    result = runtime._handle_slash_command("unknown", [])
    assert result == "Unknown command: /unknown"

def test_replace_command_variables():
    """Test template variable replacement in commands."""
    config = load_config()
    runtime = Runtime(config, skip_api_init=True)

    # Test session variables
    content = "Session: {session_id}, Messages: {message_count}"
    result = runtime._replace_command_variables(content)
    assert "Session:" in result
    assert "Messages:" in result

    # Test config variables
    content = "API: {api_provider}, Model: {model}"
    result = runtime._replace_command_variables(content)
    assert "API:" in result
    assert "Model:" in result

    # Test resource variables
    runtime._loaded_skills.add('test-skill')
    content = "Loaded skills: {loaded_skills}"
    result = runtime._replace_command_variables(content)
    assert "test-skill" in result

def test_load_command_from_directory():
    """Test loading command from custom directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command
        cmd_file = Path(tmpdir) / "test.md"
        cmd_file.write_text("---\nname: test\ndescription: Test command\nusage: /test\n---\n# Test\nContent here.")

        config = load_config()
        runtime = Runtime(config, skip_api_init=True)
        runtime._command_loader = CommandLoader(tmpdir)

        result = runtime._load_command("test", [])
        assert "Content here." in result

def test_load_command_nonexistent():
    """Test loading non-existent command."""
    config = load_config()
    runtime = Runtime(config, skip_api_init=True)

    result = runtime._load_command("nonexistent", [])
    assert result is None

def test_template_variables_in_command_files():
    """Test that template variables in command files work."""
    loader = CommandLoader('plugin/commands')

    # Get status command which uses template variables
    status_cmd = loader.get_command('status')
    assert status_cmd is not None

    # Check that template variables are present in content
    content = status_cmd['content']
    assert '{session_id}' in content or 'Session ID' in content
    assert '{message_count}' in content or 'Message Count' in content

def test_cmd_help_includes_custom_commands():
    """Test that help command includes custom commands."""
    config = load_config()
    runtime = Runtime(config, skip_api_init=True)

    result = runtime._cmd_help()
    assert "# Available Commands" in result
    assert "## Builtin Commands" in result

    # Check that some known commands are listed
    assert "/help" in result
    assert "/exit" in result
    assert "/clear" in result
    assert "/reset" in result

def test_custom_command_execution():
    """Test execution of custom commands."""
    config = load_config()
    runtime = Runtime(config, skip_api_init=True)

    # Test version command
    result = runtime._handle_slash_command("version", [])
    assert result == "command_processed"
    # Check system message was added to session
    messages = runtime._session.get_messages()
    system_msgs = [m for m in messages if m.get("role") == "system"]
    assert len(system_msgs) > 0
    assert "Simple Agent CLI" in system_msgs[-1].get("content", "")

    # Clear session and test status command
    runtime._session.clear()
    result = runtime._handle_slash_command("status", [])
    assert result == "command_processed"
    # Check system message was added to session
    messages = runtime._session.get_messages()
    system_msgs = [m for m in messages if m.get("role") == "system"]
    assert len(system_msgs) > 0
    assert "# Session Status" in system_msgs[-1].get("content", "")