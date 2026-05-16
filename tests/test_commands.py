import os
import tempfile
from pathlib import Path
from simple_agent.resources.commands import CommandLoader

def test_command_loader_scans_directory():
    """Test that CommandLoader can scan for commands."""
    loader = CommandLoader('plugin/commands')
    commands = loader.list_commands()

    assert len(commands) > 0

    # Check that expected commands exist
    command_names = [cmd['name'] for cmd in commands]
    assert 'version' in command_names
    assert 'clear' in command_names
    assert 'status' in command_names
    assert 'config' in command_names
    assert 'skills' in command_names
    assert 'agents' in command_names
    assert 'reset' in command_names

def test_command_loader_has_metadata():
    """Test that commands have proper metadata."""
    loader = CommandLoader('plugin/commands')
    commands = loader.list_commands()

    for cmd in commands:
        assert 'name' in cmd
        assert 'description' in cmd
        assert 'metadata' in cmd
        assert 'content' in cmd
        assert cmd['name']  # name should not be empty
        assert cmd['description']  # description should not be empty

def test_command_usage():
    """Test that commands have usage information (default is /name)."""
    loader = CommandLoader('plugin/commands')
    commands = loader.list_commands()

    for cmd in commands:
        # usage is now optional, default is /name
        usage = cmd['metadata'].get('usage')
        if usage is None:
            usage = f"/{cmd['name']}"
        assert usage.startswith('/')  # usage should start with /

def test_get_command():
    """Test that we can get a specific command."""
    loader = CommandLoader('plugin/commands')
    version_cmd = loader.get_command('version')

    assert version_cmd is not None
    assert version_cmd['name'] == 'version'
    assert 'content' in version_cmd

def test_command_usage_method():
    """Test that get_command_usage works."""
    loader = CommandLoader('plugin/commands')
    usage = loader.get_command_usage('status')

    assert usage is not None
    assert usage.startswith('/')
    assert 'status' in usage

def test_command_loader_empty_directory():
    """Test CommandLoader with empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = CommandLoader(tmpdir)
        commands = loader.list_commands()
        assert len(commands) == 0

def test_command_loader_nonexistent_directory():
    """Test CommandLoader with non-existent directory."""
    loader = CommandLoader('/nonexistent/path')
    commands = loader.list_commands()
    assert len(commands) == 0

def test_command_ignores_non_md_files():
    """Test that non-.md files are ignored."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create .txt file (should be ignored)
        txt_file = Path(tmpdir) / "test.txt"
        txt_file.write_text("---\nname: test\n---\nTest")

        # Create .md file (should be loaded)
        md_file = Path(tmpdir) / "test.md"
        md_file.write_text("---\nname: test\n---\nTest")

        loader = CommandLoader(tmpdir)
        commands = loader.list_commands()
        assert len(commands) == 1
        assert commands[0]['name'] == 'test'

def test_command_ignores_readme():
    """Test that README.md is ignored."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create README.md (should be ignored)
        readme_file = Path(tmpdir) / "README.md"
        readme_file.write_text("---\nname: readme\n---\nReadme")

        # Create another .md file (should be loaded)
        cmd_file = Path(tmpdir) / "test.md"
        cmd_file.write_text("---\nname: test\n---\nTest")

        loader = CommandLoader(tmpdir)
        commands = loader.list_commands()
        assert len(commands) == 1
        assert commands[0]['name'] == 'test'
        assert 'readme' not in [cmd['name'] for cmd in commands]

def test_command_falls_back_to_filename():
    """Test that command name falls back to filename when not in frontmatter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create command without name in frontmatter
        md_file = Path(tmpdir) / "my-command.md"
        md_file.write_text("---\ndescription: Test description\n---\nContent")

        loader = CommandLoader(tmpdir)
        commands = loader.list_commands()
        assert len(commands) == 1
        assert commands[0]['name'] == 'my-command'

def test_command_with_template_variables():
    """Test that command content with template variables is preserved."""
    with tempfile.TemporaryDirectory() as tmpdir:
        md_file = Path(tmpdir) / "test.md"
        md_file.write_text("---\nname: test\n---\nHello {session_id}!")

        loader = CommandLoader(tmpdir)
        cmd = loader.get_command('test')
        assert cmd is not None
        assert '{session_id}' in cmd['content']

def test_command_get_nonexistent():
    """Test getting a non-existent command."""
    loader = CommandLoader('plugin/commands')
    cmd = loader.get_command('nonexistent')
    assert cmd is None

def test_command_get_usage_nonexistent():
    """Test get_command_usage for non-existent command."""
    loader = CommandLoader('plugin/commands')
    usage = loader.get_command_usage('nonexistent')
    assert usage is None

def test_command_path_attribute():
    """Test that command has path attribute."""
    loader = CommandLoader('plugin/commands')
    commands = loader.list_commands()

    for cmd in commands:
        assert 'path' in cmd
        assert cmd['path'].endswith('.md')
        assert Path(cmd['path']).exists()

def test_command_without_usage_in_metadata():
    """Test command without usage metadata returns default."""
    with tempfile.TemporaryDirectory() as tmpdir:
        md_file = Path(tmpdir) / "test.md"
        md_file.write_text("---\nname: test\ndescription: Test\n---\nContent")

        loader = CommandLoader(tmpdir)
        usage = loader.get_command_usage('test')
        assert usage == '/test'  # default is /{name}

def test_command_duplicate_names():
    """Test behavior when multiple files have the same name in frontmatter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two files with same name in metadata but different filenames
        md_file1 = Path(tmpdir) / "first.md"
        md_file1.write_text("---\ndescription: First command\n---\nFirst")

        md_file2 = Path(tmpdir) / "second.md"
        md_file2.write_text("---\ndescription: Second command\n---\nSecond")

        loader = CommandLoader(tmpdir)
        commands = loader.list_commands()
        # Both should be loaded with their filename as command name
        assert len(commands) == 2
        assert all(cmd['name'] in ['first', 'second'] for cmd in commands)

def test_command_frontmatter_parsing():
    """Test that frontmatter is correctly parsed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        md_file = Path(tmpdir) / "test-cmd.md"
        md_file.write_text("""---
description: A test command
usage: /test <arg> [optional]
extra_field: extra_value
---

# Test Command

This is the content.
""")

        loader = CommandLoader(tmpdir)
        cmd = loader.get_command('test-cmd')

        assert cmd is not None
        assert cmd['name'] == 'test-cmd'
        assert cmd['description'] == 'A test command'
        assert cmd['metadata']['usage'] == '/test <arg> [optional]'
        assert cmd['metadata']['extra_field'] == 'extra_value'
        assert '# Test Command' in cmd['content']
        assert 'This is the content.' in cmd['content']