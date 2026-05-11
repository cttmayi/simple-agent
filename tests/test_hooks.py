from pathlib import Path
import tempfile
import pytest
from simple_agent.resources.hooks import HookLoader
from simple_agent.core.events import Event


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


def test_execute_python_hook_returns_none():
    """Python hook without block returns None"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple Python hook that doesn't block
        hook_file = Path(tmpdir) / "test_hook.py"
        hook_file.write_text("""
def on_test_event(**data):
    print("Hook executed")
    return None
""")

        runtime = Runtime(Settings(), log_file=None)
        event = Event(name="test_event", data={"key": "value"})

        result = runtime._execute_python_hook(hook_file, event)
        assert result is None


def test_execute_python_hook_returns_block():
    """Python hook can return block to prevent execution"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a Python hook that blocks execution
        hook_file = Path(tmpdir) / "block_hook.py"
        hook_file.write_text("""
def on_test_event(**data):
    if data.get("block"):
        return {"action": "block", "message": "Blocked by hook"}
    return None
""")

        runtime = Runtime(Settings(), log_file=None)
        event = Event(name="test_event", data={"block": True})

        result = runtime._execute_python_hook(hook_file, event)
        assert result is not None
        assert result["action"] == "block"
        assert "Blocked by hook" in result["message"]


def test_execute_python_hook_missing_function():
    """Python hook with no matching function returns None"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a Python hook without the expected function
        hook_file = Path(tmpdir) / "no_func_hook.py"
        hook_file.write_text("""
def on_other_event(data):
    return None
""")

        runtime = Runtime(Settings(), log_file=None)
        event = Event(name="test_event", data={})

        result = runtime._execute_python_hook(hook_file, event)
        assert result is None


def test_execute_hook_returns_block():
    """_execute_hook stops early when Python hook returns block"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hook_dir = Path(tmpdir) / "test_event"
        hook_dir.mkdir()

        # Create Python hook that blocks
        (hook_dir / "block.py").write_text("""
def on_test_event(**data):
    return {"action": "block", "message": "Stopped early"}
""")

        # Create shell hook that should NOT execute
        (hook_dir / "script.sh").write_text("echo 'This should not run'")

        runtime = Runtime(Settings(), log_file=None)
        hook = {"event_name": "test_event", "path": str(hook_dir), "files": ["block.py", "script.sh"]}
        event = Event(name="test_event", data={})

        result = runtime._execute_hook(hook, event)
        assert result is not None
        assert result["action"] == "block"
        assert "Stopped early" in result["message"]


def test_execute_hook_runs_all_types():
    """_execute_hook runs all hook types in order"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hook_dir = Path(tmpdir) / "test_event"
        hook_dir.mkdir()

        # Create all hook types
        (hook_dir / "hook.py").write_text("""
def on_test_event(data):
    return None
""")
        (hook_dir / "hook.sh").write_text("echo 'Shell hook executed'")
        (hook_dir / "hook.md").write_text("{{key}} value is {{key}}")

        runtime = Runtime(Settings(), log_file=None)
        hook = {"event_name": "test_event", "path": str(hook_dir), "files": ["hook.py", "hook.sh", "hook.md"]}
        event = Event(name="test_event", data={"key": "test"})

        result = runtime._execute_hook(hook, event)
        assert result is None  # No block returned
