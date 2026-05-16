import tempfile
from pathlib import Path
from simple_agent.resources.commands import CommandLoader


def test_namespace_from_subdirectory():
    """Test that frontmatter name overrides namespace-based name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create subdirectory with command
        subdir = Path(tmpdir) / "git"
        subdir.mkdir()
        cmd_file = subdir / "commit.md"
        cmd_file.write_text("---\nname: commit\ndescription: Commit\n---\nContent")

        loader = CommandLoader(tmpdir)
        commands = loader.list_commands()

        # Should use frontmatter name, not namespace
        assert len(commands) == 1
        assert commands[0]["name"] == "commit"


def test_namespace_flat_commands():
    """Test that flat commands (no subdirectory) work without namespace prefix."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create flat command
        cmd_file = Path(tmpdir) / "help.md"
        cmd_file.write_text("---\nname: help\ndescription: Help\n---\nContent")

        loader = CommandLoader(tmpdir)
        commands = loader.list_commands()

        # Should have command without namespace prefix
        assert len(commands) == 1
        assert commands[0]["name"] == "help"


def test_nested_namespace():
    """Test that frontmatter name overrides multi-level namespace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create nested subdirectory
        subdir = Path(tmpdir) / "frontend" / "test"
        subdir.mkdir(parents=True)
        cmd_file = subdir / "run.md"
        cmd_file.write_text("---\nname: run\ndescription: Run tests\n---\nContent")

        loader = CommandLoader(tmpdir)
        commands = loader.list_commands()

        # Should use frontmatter name, not namespace
        assert len(commands) == 1
        assert commands[0]["name"] == "run"