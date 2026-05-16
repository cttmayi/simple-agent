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

        # Check session has user message with command content
        messages = runtime._session.get_messages()
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assert len(user_msgs) > 0
        assert "Hello World" in user_msgs[-1].get("content", "")


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

        # Check session has user message with command content
        messages = runtime._session.get_messages()
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assert len(user_msgs) > 0
        content = user_msgs[-1].get("content", "")
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

        # Check session does NOT have user message (unknown command returns error)
        messages = runtime._session.get_messages()
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assert len(user_msgs) == 0


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
    """Test CommandProcessor with parameters and features."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command with parameters
        cmd_dir = Path(tmpdir) / "commands"
        cmd_dir.mkdir()
        cmd_file = cmd_dir / "vars.md"
        cmd_file.write_text(
            "---\nname: vars\ndescription: Test variables\n---\n"
            "Parameter: $1\nHas args: $#"
        )

        # Create runtime with custom command dir
        config = load_config()
        config.paths.commands_dir = str(cmd_dir)
        runtime = Runtime(config, skip_api_init=True)

        # Reload command loader with new path
        from simple_agent.resources.commands import CommandLoader
        runtime._command_loader = CommandLoader(cmd_dir)

        # Process command
        result = runtime._handle_slash_command("vars", ["test"])

        assert result == "command_processed"

        # Check session has user message with replaced parameters
        messages = runtime._session.get_messages()
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assert len(user_msgs) > 0
        content = user_msgs[-1].get("content", "")
        assert "Parameter: test" in content
        assert "Has args: 1" in content


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


def test_full_command_with_all_features():
    """Test command with all features: parameters, bash, file inclusion, allowed-tools."""
    # Save original working directory
    original_cwd = Path.cwd()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        cmd_dir = Path(tmpdir) / "commands"
        cmd_dir.mkdir()

        # Create a test file to include (in tmpdir)
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("This is the test file content.\nSecond line.")

        # Change to tmpdir so bash commands and file inclusion work from there
        import os
        os.chdir(tmpdir)

        try:
            # Create command with all features
            cmd_file = cmd_dir / "full-featured.md"
            cmd_file.write_text(
                """---
name: full-featured
description: Command with all features
allowed-tools: Bash,Grep
---
# Full Featured Command

## Parameters
You entered: $1
Has args: $#

## Bash Execution
Current dir: !`pwd`
User: !`whoami`

## File Inclusion
@test.txt

You can only use Bash and Grep tools.
"""
            )

            # Create runtime with custom command dir
            config = load_config()
            config.paths.commands_dir = str(cmd_dir)
            runtime = Runtime(config, skip_api_init=True)

            # Reload command loader with new path
            from simple_agent.resources.commands import CommandLoader
            runtime._command_loader = CommandLoader(cmd_dir)

            # Snapshot tools before command
            tools_before_count = len(runtime._tool_registry.to_openai_format())

            # Process command with argument
            result = runtime._handle_slash_command("full-featured", ["Hello World"])

            assert result == "command_processed"

            # Check session has user message with command content
            messages = runtime._session.get_messages()
            user_msgs = [m for m in messages if m.get("role") == "user"]
            assert len(user_msgs) > 0

            content = user_msgs[-1].get("content", "")

            # Check parameters were replaced
            assert "Hello World" in content

            # Check bash commands were executed
            # Current dir should be tmpdir
            assert tmpdir in content or str(cmd_dir) in content
            assert "User:" in content  # whoami should have executed

            # Check file was included
            assert "This is the test file content" in content
            assert "Second line" in content

            # Check allowed-tools message is present
            assert "Bash and Grep tools" in content or "Bash,Grep" in content

            # Check tools are restored after command
            tools_after_count = len(runtime._tool_registry.to_openai_format())
            assert tools_after_count == tools_before_count
        finally:
            # Restore original working directory
            os.chdir(original_cwd)