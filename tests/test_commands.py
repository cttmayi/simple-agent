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
    """Test that commands have usage information."""
    loader = CommandLoader('plugin/commands')
    commands = loader.list_commands()

    for cmd in commands:
        usage = cmd['metadata'].get('usage')
        assert usage is not None
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