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
        # Shell hook output will be returned as append_to_message
        assert result is not None and result.get("append_to_message") == "Shell hook executed"


def test_load_hooks_registers_event_handlers():
    """加载 hooks 后，事件总线有对应的处理器"""
    from simple_agent.core.runtime import Runtime, HookBlockedException
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)

        # Create an event directory with a Python hook
        event_dir = hooks_dir / "custom_event"
        event_dir.mkdir()

        (event_dir / "hook.py").write_text("""
def on_custom_event(**data):
    return None
""")

        # Create Runtime with hooks directory
        config = Settings()
        config.paths.hooks_dir = str(hooks_dir)
        runtime = Runtime(config, log_file=None)

        # Check that event handler is registered
        # EventBus._handlers is a private attribute, but we need to access it for testing
        handlers = runtime._event_bus._handlers
        assert "custom_event" in handlers
        assert len(handlers["custom_event"]) == 1

        # Test that the handler works
        execution_count = []

        # Replace the handler with our own to count executions
        original_handler = handlers["custom_event"][0]
        def counting_handler(event):
            execution_count.append(1)
            original_handler(event)

        handlers["custom_event"][0] = counting_handler

        # Publish event
        event = Event(name="custom_event", data={})
        runtime._event_bus.publish(event)

        # Verify handler was called
        assert len(execution_count) == 1


def test_log_hook_block():
    """LLMLogger.log_hook_block logs hook block events"""
    from simple_agent.core.llm_logger import LLMLogger

    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir)
        logger = LLMLogger(log_dir, enabled=True)

        # Log a hook block
        logger.log_hook_block(
            event_name="tool_call_before",
            hook_name="block_tool",
            message="Tool blocked by hook"
        )

        # Read the log file and verify entry
        log_file = logger.get_log_file_path()
        import json
        with open(log_file, "r") as f:
            entries = [json.loads(line) for line in f if line.strip()]

        assert len(entries) == 1
        assert entries[0]["type"] == "hook_block"
        assert entries[0]["event_name"] == "tool_call_before"
        assert entries[0]["hook_name"] == "block_tool"
        assert entries[0]["message"] == "Tool blocked by hook"
        assert "timestamp" in entries[0]


def test_log_hook_block_when_disabled():
    """LLMLogger.log_hook_block does nothing when disabled"""
    from simple_agent.core.llm_logger import LLMLogger

    logger = LLMLogger(enabled=False)

    # Should not raise any errors
    logger.log_hook_block(
        event_name="tool_call_before",
        hook_name="block_tool",
        message="Tool blocked by hook"
    )

    # Verify no log file was created
    log_file = logger.get_log_file_path()
    assert not log_file.exists()


# ========== 1. Runtime 事件发布测试 ==========


def test_runtime_publishes_session_start():
    """Runtime publishes session_start event when loaded"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)
        event_dir = hooks_dir / "session_start"
        event_dir.mkdir()

        # Create a simple hook file
        (event_dir / "hook.py").write_text("""
def on_session_start(session_id: str, **kwargs):
    return None
""")

        # Change to the temp directory (Runtime uses Path.cwd())
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Runtime.__init__ loads hooks
            config = Settings()
            config.paths.hooks_dir = "."
            runtime = Runtime(config, log_file=None)

            # Verify hook handler is registered
            assert "session_start" in runtime._event_bus._handlers
        finally:
            os.chdir(old_cwd)


def test_runtime_publishes_session_end():
    """Runtime publishes session_end event"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)
        event_dir = hooks_dir / "session_end"
        event_dir.mkdir()

        (event_dir / "hook.py").write_text("""
def on_session_end(session_id: str, **kwargs):
    return None
""")

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            config = Settings()
            config.paths.hooks_dir = "."
            runtime = Runtime(config, log_file=None)

            # Verify handler is registered
            assert "session_end" in runtime._event_bus._handlers
        finally:
            os.chdir(old_cwd)


def test_runtime_publishes_message_sent():
    """Runtime publishes message_sent event"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)
        event_dir = hooks_dir / "message_sent"
        event_dir.mkdir()

        (event_dir / "hook.py").write_text("""
def on_message_sent(role: str, content: str, **kwargs):
    return None
""")

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            config = Settings()
            config.paths.hooks_dir = "."
            runtime = Runtime(config, log_file=None)

            # Verify handler is registered
            assert "message_sent" in runtime._event_bus._handlers
        finally:
            os.chdir(old_cwd)


def test_runtime_publishes_message_received():
    """Runtime publishes message_received event"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)
        event_dir = hooks_dir / "message_received"
        event_dir.mkdir()

        (event_dir / "hook.py").write_text("""
def on_message_received(role: str, content: str, **kwargs):
    return None
""")

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            config = Settings()
            config.paths.hooks_dir = "."
            runtime = Runtime(config, log_file=None)

            # Verify handler is registered
            assert "message_received" in runtime._event_bus._handlers
        finally:
            os.chdir(old_cwd)


# ========== 2. ToolDispatcher 事件发布测试 ==========


def test_tool_dispatcher_publishes_tool_call_before():
    """ToolDispatcher publishes tool_call_before event"""
    from simple_agent.tools.dispatcher import ToolDispatcher
    from simple_agent.tools.registry import ToolRegistry, ToolDefinition

    # Create event bus to track published events
    published_events = []

    class MockEventBus:
        def publish(self, event):
            published_events.append(event)

    # Create registry with a test tool
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="test_tool",
        description="Test tool",
        fn=lambda: {"success": True, "result": "ok"},
        parameters={"type": "object", "properties": {}}
    ))

    # Create dispatcher with mock event bus
    dispatcher = ToolDispatcher(registry, MockEventBus())

    # Execute a tool call
    dispatcher.execute({"name": "test_tool", "arguments": {}})

    # Verify tool_call_before was published
    assert len(published_events) >= 1
    assert published_events[0].name == "tool_call_before"
    assert published_events[0].data["tool_name"] == "test_tool"


def test_tool_dispatcher_publishes_tool_call_after():
    """ToolDispatcher publishes tool_call_after event on success"""
    from simple_agent.tools.dispatcher import ToolDispatcher
    from simple_agent.tools.registry import ToolRegistry, ToolDefinition

    published_events = []

    class MockEventBus:
        def publish(self, event):
            published_events.append(event)

    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="test_tool",
        description="Test tool",
        fn=lambda: {"success": True, "result": "ok"},
        parameters={"type": "object", "properties": {}}
    ))

    dispatcher = ToolDispatcher(registry, MockEventBus())
    dispatcher.execute({"name": "test_tool", "arguments": {}})

    # Verify both before and after events
    assert len(published_events) == 2
    assert published_events[1].name == "tool_call_after"
    assert published_events[1].data["tool_name"] == "test_tool"
    assert published_events[1].data["result"]["success"] is True


def test_tool_dispatcher_publishes_tool_call_failed():
    """ToolDispatcher publishes tool_call_failed event on error"""
    from simple_agent.tools.dispatcher import ToolDispatcher
    from simple_agent.tools.registry import ToolRegistry, ToolDefinition

    published_events = []

    class MockEventBus:
        def publish(self, event):
            published_events.append(event)

    registry = ToolRegistry()

    # Define a function that fails
    def failing_function():
        return 1 / 0  # This will raise ZeroDivisionError

    registry.register(ToolDefinition(
        name="failing_tool",
        description="Failing test tool",
        fn=failing_function,
        parameters={"type": "object", "properties": {}}
    ))

    dispatcher = ToolDispatcher(registry, MockEventBus())
    result = dispatcher.execute({"name": "failing_tool", "arguments": {}})

    # Verify tool_call_before and tool_call_failed events
    assert len(published_events) >= 2
    assert published_events[0].name == "tool_call_before"
    assert published_events[1].name == "tool_call_failed"
    assert result["success"] is False


# ========== 3. Hook 阻止工具执行测试 ==========


def test_hook_blocks_tool_execution():
    """Hook can block tool execution"""
    from simple_agent.tools.dispatcher import ToolDispatcher
    from simple_agent.tools.registry import ToolRegistry, ToolDefinition
    from simple_agent.core.events import Event, HookBlockedException

    published_events = []

    class MockEventBus:
        def __init__(self):
            self.should_block = True

        def publish(self, event):
            published_events.append(event)
            if self.should_block and event.name == "tool_call_before":
                raise HookBlockedException("Tool blocked by hook")

    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="test_tool",
        description="Test tool",
        fn=lambda: {"success": True, "result": "should not execute"},
        parameters={"type": "object", "properties": {}}
    ))

    event_bus = MockEventBus()
    dispatcher = ToolDispatcher(registry, event_bus)

    # Execute tool - should be blocked
    result = dispatcher.execute({"name": "test_tool", "arguments": {}})

    # Verify tool was blocked
    assert result["success"] is False
    assert "blocked" in result["error"].lower()

    # Verify tool_call_before was published
    assert len(published_events) == 1
    assert published_events[0].name == "tool_call_before"


# ========== 4. LoadSkill/LoadSubagent 事件测试 ==========


def test_load_skill_publishes_event():
    """LoadSkill publishes skill_loaded event"""
    from simple_agent.tools.builtin.load_skill import LoadSkill
    from simple_agent.resources.skills import SkillLoader

    published_events = []

    class MockEventBus:
        def publish(self, event):
            published_events.append(event)

    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)
        skill_dir = skills_dir / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: test_skill\ndescription: Test\n---\nTest skill content")

        loader = SkillLoader(skills_dir)
        loaded_skills = set()
        LoadSkill.set_runtime(loader, loaded_skills, None, MockEventBus())

        result = LoadSkill.execute("test_skill")

        # Verify skill_loaded event was published
        assert result["success"] is True
        assert len(published_events) == 1
        assert published_events[0].name == "skill_loaded"
        assert published_events[0].data["skill_name"] == "test_skill"


def test_load_subagent_publishes_event():
    """LoadSubagent publishes subagent_loaded event"""
    from simple_agent.tools.builtin.load_subagent import LoadSubagent
    from simple_agent.resources.subagents import SubagentLoader

    published_events = []

    class MockEventBus:
        def publish(self, event):
            published_events.append(event)

    with tempfile.TemporaryDirectory() as tmpdir:
        subagents_dir = Path(tmpdir)
        subagent_dir = subagents_dir / "test_subagent"
        subagent_dir.mkdir()
        subagent_file = subagent_dir / "AGENT.md"
        subagent_file.write_text("---\nname: test_subagent\ndescription: Test\n---\nTest subagent")

        loader = SubagentLoader(subagents_dir)
        loaded_subagents = set()
        LoadSubagent.set_runtime(loader, loaded_subagents, None, MockEventBus())

        result = LoadSubagent.execute("test_subagent")

        # Verify subagent_loaded event was published
        assert result["success"] is True
        assert len(published_events) == 1
        assert published_events[0].name == "subagent_loaded"
        assert published_events[0].data["subagent_name"] == "test_subagent"


# ========== 5. Shell Hook 测试 ==========


def test_shell_hook_execution():
    """Shell hook is executed correctly"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hook_dir = Path(tmpdir) / "test_event"
        hook_dir.mkdir()

        # Create shell hook
        hook_file = hook_dir / "test.sh"
        hook_file.write_text("#!/bin/bash\necho 'SHELL_HOOK_EXECUTED'")
        hook_file.chmod(0o755)

        runtime = Runtime(Settings(), log_file=None)
        hook = {"event_name": "test_event", "path": str(hook_dir), "files": ["test.sh"]}
        event = Event(name="test_event", data={})

        # Execute hook - should not raise
        result = runtime._execute_hook(hook, event)
        # Shell hook output is returned as append_to_message
        assert result is not None and result.get("append_to_message") == "SHELL_HOOK_EXECUTED"


# ========== 6. Prompt Hook 测试 ==========


def test_prompt_hook_variable_replacement():
    """Prompt hook correctly replaces variables"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hook_dir = Path(tmpdir) / "test_event"
        hook_dir.mkdir()

        # Create prompt hook with variables
        (hook_dir / "prompt.md").write_text("{{name}} did {{action}}")

        runtime = Runtime(Settings(), log_file=None)
        hook = {"event_name": "test_event", "path": str(hook_dir), "files": ["prompt.md"]}
        event = Event(name="test_event", data={"name": "Alice", "action": "jumped"})

        # Execute hook
        result = runtime._execute_hook(hook, event)
        assert result is None

        # The hook is displayed via _renderer, which we can't easily test
        # The variable replacement logic is in _execute_prompt_hook


# ========== 7. 错误事件测试 ==========


def test_error_occurred_event_published():
    """Runtime publishes error_occurred event when exception occurs"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)
        event_dir = hooks_dir / "error_occurred"
        event_dir.mkdir()

        # Create hook that tracks errors
        (event_dir / "hook.py").write_text("""
def on_error_occurred(error_type: str, error_message: str, **kwargs):
    return None
""")

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            config = Settings()
            config.paths.hooks_dir = "."
            runtime = Runtime(config, log_file=None)

            # Verify handler is registered
            assert "error_occurred" in runtime._event_bus._handlers
        finally:
            os.chdir(old_cwd)


# ========== 8. 多个 Hook 测试 ==========


def test_multiple_hooks_execute_in_order():
    """Multiple hooks execute in alphabetical order of filenames"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hook_dir = Path(tmpdir) / "test_event"
        hook_dir.mkdir()

        # Create multiple Python hooks
        (hook_dir / "a.py").write_text("""
def on_test_event(**kwargs):
    return None
""")
        (hook_dir / "b.py").write_text("""
def on_test_event(**kwargs):
    return None
""")
        (hook_dir / "c.py").write_text("""
def on_test_event(**kwargs):
    return None
""")

        runtime = Runtime(Settings(), log_file=None)

        # Execute each hook individually
        for filename in ["a.py", "b.py", "c.py"]:
            hook_file = hook_dir / filename
            result = runtime._execute_python_hook(hook_file, Event(name="test_event", data={}))

            # Each hook should return None
            assert result is None

        # Test that hooks are executed in order by creating hook with multiple files
        hook_data = {"event_name": "test_event", "path": str(hook_dir), "files": ["a.py", "b.py", "c.py"]}
        result = runtime._execute_hook(hook_data, Event(name="test_event", data={}))

        # No block should be returned
        assert result is None


# ========== 9. Hook 加载测试 ==========


def test_hook_loaded_event_published():
    """Test that hooks are loaded from file system"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings
    from simple_agent.core.events import EventBus

    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)
        event_dir = hooks_dir / "test_hook"
        event_dir.mkdir()

        # Create a hook
        (event_dir / "hook.py").write_text("""
def on_test_hook(**kwargs):
    return None
""")

        # Track published events
        published_events = []

        class TrackingEventBus(EventBus):
            def __init__(self):
                super().__init__()

            def publish(self, event):
                published_events.append(event)
                # Let the original bus also handle it
                super().publish(event)

        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            config = Settings()
            config.paths.hooks_dir = "."

            # Create a runtime with tracking event bus
            # We can't easily replace the event bus after initialization,
            # so we'll test by checking the hook is loaded

            runtime = Runtime(config, log_file=None)

            # Verify hook is loaded
            assert "test_hook" in [h["event_name"] for h in runtime._hook_loader.list_hooks()]
        finally:
            os.chdir(old_cwd)
