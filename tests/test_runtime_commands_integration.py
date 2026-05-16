"""Integration tests for Runtime CommandProcessor integration."""
import tempfile
from pathlib import Path
from simple_agent.config.settings import load_config
from simple_agent.core.runtime import Runtime
from simple_agent.core.session import Session


def test_command_processor_integration():
    """Test CommandProcessor integration with Runtime."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command
        cmd_dir = Path(tmpdir) / "commands"
        cmd_dir.mkdir()
        cmd_file = cmd_dir / "test.md"
        cmd_file.write_text("---\nname: test\ndescription: Test\n---\nHello $1")

        # Create runtime with custom command dir
        config = load_config()
        config.paths.commands_dir = str(cmd_dir)
        runtime = Runtime(config, skip_api_init=True)

        # Reload command loader with new path
        from simple_agent.resources.commands import CommandLoader
        runtime._command_loader = CommandLoader(cmd_dir)

        # Process command
        result = runtime._handle_slash_command("test", ["World"])

        assert result == "command_processed"

        # Check session has system message
        messages = runtime._session.get_messages()
        system_msgs = [m for m in messages if m.get("role") == "system"]
        assert len(system_msgs) > 0
        assert "Hello World" in system_msgs[-1].get("content", "")


def test_command_processor_with_allowed_tools():
    """Test CommandProcessor with allowed-tools restriction."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command with allowed-tools
        cmd_dir = Path(tmpdir) / "commands"
        cmd_dir.mkdir()
        cmd_file = cmd_dir / "restricted.md"
        cmd_file.write_text(
            "---\nname: restricted\ndescription: Restricted command\nallowed-tools: Bash,Grep\n---\nUse only Bash and Grep"
        )

        # Create runtime with custom command dir
        config = load_config()
        config.paths.commands_dir = str(cmd_dir)
        runtime = Runtime(config, skip_api_init=True)

        # Reload command loader with new path
        from simple_agent.resources.commands import CommandLoader
        runtime._command_loader = CommandLoader(cmd_dir)

        # Snapshot current tools (before command processing)
        tools_before = runtime._tool_registry.to_openai_format()
        tools_count_before = len(tools_before)
        assert tools_count_before > 0  # Should have builtin tools

        # Process command
        result = runtime._handle_slash_command("restricted", [])

        assert result == "command_processed"

        # Check session has system message
        messages = runtime._session.get_messages()
        system_msgs = [m for m in messages if m.get("role") == "system"]
        assert len(system_msgs) > 0
        content = system_msgs[-1].get("content", "")
        assert "Use only Bash and Grep" in content

        # Check tools are restored after command processing
        tools_after = runtime._tool_registry.to_openai_format()
        tools_count_after = len(tools_after)
        assert tools_count_after == tools_count_before


def test_command_processor_unknown_command():
    """Test CommandProcessor with unknown command."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create empty command dir
        cmd_dir = Path(tmpdir) / "commands"
        cmd_dir.mkdir()

        # Create runtime with custom command dir
        config = load_config()
        config.paths.commands_dir = str(cmd_dir)
        runtime = Runtime(config, skip_api_init=True)

        # Reload command loader with new path
        from simple_agent.resources.commands import CommandLoader
        runtime._command_loader = CommandLoader(cmd_dir)

        # Process unknown command
        result = runtime._handle_slash_command("unknown", [])

        assert result == "Unknown command: /unknown"

        # Check session does NOT have system message
        messages = runtime._session.get_messages()
        system_msgs = [m for m in messages if m.get("role") == "system"]
        assert len(system_msgs) == 0


def test_command_processor_builtin_commands():
    """Test builtin commands still work."""
    config = load_config()
    runtime = Runtime(config, skip_api_init=True)

    # Test help command
    result = runtime._handle_slash_command("help", [])
    assert result != "command_processed"  # Returns help text directly
    assert "# Available Commands" in result

    # Test exit command
    result = runtime._handle_slash_command("exit", [])
    assert result == "exit"

    # Test quit command (alias for exit)
    result = runtime._handle_slash_command("quit", [])
    assert result == "exit"


def test_command_processor_template_variables():
    """Test CommandProcessor with template variables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command with template variables
        cmd_dir = Path(tmpdir) / "commands"
        cmd_dir.mkdir()
        cmd_file = cmd_dir / "vars.md"
        cmd_file.write_text(
            "---\nname: vars\ndescription: Test variables\n---\n"
            "Model: {model}, Provider: {api_provider}"
        )

        # Create runtime with custom command dir
        config = load_config()
        config.paths.commands_dir = str(cmd_dir)
        runtime = Runtime(config, skip_api_init=True)

        # Reload command loader with new path
        from simple_agent.resources.commands import CommandLoader
        runtime._command_loader = CommandLoader(cmd_dir)

        # Process command
        result = runtime._handle_slash_command("vars", [])

        assert result == "command_processed"

        # Check session has system message with replaced variables
        messages = runtime._session.get_messages()
        system_msgs = [m for m in messages if m.get("role") == "system"]
        assert len(system_msgs) > 0
        content = system_msgs[-1].get("content", "")
        assert "Model:" in content
        assert "Provider:" in content
        assert config.api.model in content
        assert config.api.provider in content


def test_help_command_shows_namespaces():
    """Test help command shows namespaced commands correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create commands with namespaces
        cmd_dir = Path(tmpdir) / "commands"
        cmd_dir.mkdir()
        git_dir = cmd_dir / "git"
        git_dir.mkdir()

        (cmd_dir / "flat.md").write_text("---\nname: flat\ndescription: Flat command\n---\nContent")
        (git_dir / "commit.md").write_text("---\nname: git/commit\ndescription: Git commit\n---\nContent")

        config = load_config()
        config.paths.commands_dir = str(cmd_dir)
        runtime = Runtime(config, skip_api_init=True)

        from simple_agent.resources.commands import CommandLoader
        runtime._command_loader = CommandLoader(cmd_dir)

        help_output = runtime._cmd_help()

        assert "/flat" in help_output
        assert "/git/commit" in help_output