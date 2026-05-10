from pathlib import Path
import tempfile
import pytest
from simple_agent.resources.hooks import HookLoader


def test_hook_loader_scans_directories():
    """HookLoader scans hooks/ directory subdirectories"""
    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)

        # Create event directory and files
        event_dir = hooks_dir / "test_event"
        event_dir.mkdir()

        # Create different types of hook files
        (event_dir / "hook.py").write_text("def on_test_event(): pass")
        (event_dir / "hook.sh").write_text("echo test")
        (event_dir / "hook.md").write_text("test prompt")

        loader = HookLoader(hooks_dir)
        hooks = loader.list_hooks()

        assert len(hooks) == 1
        assert hooks[0]["event_name"] == "test_event"
        assert hooks[0]["files"] == ["hook.md", "hook.py", "hook.sh"]


def test_hook_loader_ignores_non_hook_files():
    """HookLoader ignores files without hook extensions"""
    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)

        event_dir = hooks_dir / "test_event"
        event_dir.mkdir()

        # Create hook files and non-hook files
        (event_dir / "hook.py").write_text("def on_test_event(): pass")
        (event_dir / "readme.txt").write_text("This should be ignored")
        (event_dir / "log.log").write_text("This should be ignored")

        loader = HookLoader(hooks_dir)
        hooks = loader.list_hooks()

        assert len(hooks) == 1
        assert hooks[0]["files"] == ["hook.py"]


def test_hook_loader_ignores_empty_directories():
    """HookLoader ignores directories without hook files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)

        # Create empty event directory
        event_dir = hooks_dir / "empty_event"
        event_dir.mkdir()

        loader = HookLoader(hooks_dir)
        hooks = loader.list_hooks()

        assert len(hooks) == 0


def test_hook_loader_ignores_non_directory_items():
    """HookLoader ignores files in the hooks directory root"""
    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)

        # Create a file directly in hooks dir
        (hooks_dir / "readme.txt").write_text("This should be ignored")

        loader = HookLoader(hooks_dir)
        hooks = loader.list_hooks()

        assert len(hooks) == 0


def test_hook_loader_handles_non_existent_directory():
    """HookLoader returns empty list when directory doesn't exist"""
    hooks_dir = Path("/non/existent/path")

    loader = HookLoader(hooks_dir)
    hooks = loader.list_hooks()

    assert len(hooks) == 0


def test_hook_loader_recognizes_all_hook_extensions():
    """HookLoader recognizes all valid hook file extensions"""
    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)

        event_dir = hooks_dir / "test_event"
        event_dir.mkdir()

        # Create all valid hook file types
        (event_dir / "script.py").write_text("# python hook")
        (event_dir / "script.sh").write_text("# bash hook")
        (event_dir / "script.cmd").write_text("# windows hook")
        (event_dir / "script.md").write_text("# markdown hook")

        loader = HookLoader(hooks_dir)
        hooks = loader.list_hooks()

        assert len(hooks) == 1
        assert set(hooks[0]["files"]) == {"script.py", "script.sh", "script.cmd", "script.md"}
