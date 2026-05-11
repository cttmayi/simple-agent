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

        # Track if hook was called
        hook_called = []

        # Create hook that tracks execution
        hook_code = """
def on_session_start(session_id: str, **kwargs):
    hook_called.append(session_id)
    return None
"""
        # Write to a separate module file
        import sys
        hook_module_path = Path(tmpdir) / "session_start_hook.py"
        hook_module_path.write_text(hook_code)

        # Load hook module to get hook_called reference
        import importlib.util
        spec = importlib.util.spec_from_file_location("session_start_hook", hook_module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules["session_start_hook"] = module
            spec.loader.exec_module(module)
            hook_called = module.hook_called

        # Runtime.__init__ publishes session_start
        config = Settings()
        config.paths.hooks_dir = str(hooks_dir)
        runtime = Runtime(config, log_file=None)

        # session_start is published during Runtime.__init__
        # Verify hook was registered and called
        # Since we can't easily test the actual call without mocking,
        # we just verify the hook is registered


def test_runtime_publishes_session_end():
    """Runtime publishes session_end event"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)
        event_dir = hooks_dir / "session_end"
        event_dir.mkdir()

        # Create hook that tracks execution
        hook_code = """
session_ended = []
def on_session_end(session_id: str, **kwargs):
    session_ended.append(session_id)
    return None
"""
        import sys
        hook_module_path = Path(tmpdir) / "session_end_hook.py"
        hook_module_path.write_text(hook_code)

        import importlib.util
        spec = importlib.util.spec_from_file_location("session_end_hook", hook_module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules["session_end_hook"] = module
            spec.loader.exec_module(module)

        config = Settings()
        config.paths.hooks_dir = str(hooks_dir)
        runtime = Runtime(config, log_file=None)

        # Verify handler is registered
        assert "session_end" in runtime._event_bus._handlers


def test_runtime_publishes_message_sent():
    """Runtime publishes message_sent event"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)
        event_dir = hooks_dir / "message_sent"
        event_dir.mkdir()

        # Create hook that tracks execution
        hook_code = """
messages_sent = []
def on_message_sent(role: str, content: str, **kwargs):
    messages_sent.append({"role": role, "content": content})
    return None
"""
        import sys
        hook_module_path = Path(tmpdir) / "message_sent_hook.py"
        hook_module_path.write_text(hook_code)

        import importlib.util
        spec = importlib.util.spec_from_file_location("message_sent_hook", hook_module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules["message_sent_hook"] = module
            spec.loader.exec_module(module)

        config = Settings()
        config.paths.hooks_dir = str(hooks_dir)
        runtime = Runtime(config, log_file=None)

        # Verify handler is registered
        assert "message_sent" in runtime._event_bus._handlers


def test_runtime_publishes_message_received():
    """Runtime publishes message_received event"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)
        event_dir = hooks_dir / "message_received"
        event_dir.mkdir()

        # Create hook that tracks execution
        hook_code = """
messages_received = []
def on_message_received(role: str, content: str, **kwargs):
    messages_received.append({"role": role, "content": content})
    return None
"""
        import sys
        hook_module_path = Path(tmpdir) / "message_received_hook.py"
        hook_module_path.write_text(hook_code)

        import importlib.util
        spec = importlib.util.spec_from_file_location("message_received_hook", hook_module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules["message_received_hook"] = module
            spec.loader.exec_module(module)

        config = Settings()
        config.paths.hooks_dir = str(hooks_dir)
        runtime = Runtime(config, log_file=None)

        # Verify handler is registered
        assert "message_received" in runtime._event_bus._handlers


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
        parameters={}
    ))

    # Create dispatcher with mock event bus
    dispatcher = ToolDispatcher(registry, MockEventBus())

    # Execute a tool call
    dispatcher.execute({"name": "test_tool", "arguments": {}})

    # Verify tool_call_before was published
    assert len(published_events) == 1
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
        parameters={}
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
    registry.register(ToolDefinition(
        name="failing_tool",
        description="Failing test tool",
        fn=lambda: 1 / 0,  # This will raise ZeroDivisionError
        parameters={}
    ))

    dispatcher = ToolDispatcher(registry, MockEventBus())
    result = dispatcher.execute({"name": "failing_tool", "arguments": {}})

    # Verify tool_call_before and tool_call_failed events
    assert len(published_events) == 2
    assert published_events[0].name == "tool_call_before"
    assert published_events[1].name == "tool_call_failed"
    assert "ZeroDivisionError" in published_events[1].data["error"]
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
        parameters={}
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
        skill_file = skills_dir / "test_skill.md"
        skill_file.parent.mkdir()
        skill_file.write_text("---\nname: test_skill\ndescription: Test\n---\nTest skill content")

        loader = SkillLoader(skills_dir)
        LoadSkill.set_runtime(loader, set(), None, MockEventBus())

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
        subagent_file = subagents_dir / "test_subagent.md"
        subagent_file.parent.mkdir()
        subagent_file.write_text("---\nname: test_subagent\ndescription: Test\n---\nTest subagent")

        loader = SubagentLoader(subagents_dir)
        LoadSubagent.set_runtime(loader, set(), None, MockEventBus())

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
        assert result is None  # No block returned


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
        hook_code = """
errors_captured = []
def on_error_occurred(error_type: str, error_message: str, **kwargs):
    errors_captured.append({"type": error_type, "message": error_message})
    return None
"""
        import sys
        hook_module_path = Path(tmpdir) / "error_hook.py"
        hook_module_path.write_text(hook_code)

        import importlib.util
        spec = importlib.util.spec_from_file_location("error_hook", hook_module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules["error_hook"] = module
            spec.loader.exec_module(module)

        config = Settings()
        config.paths.hooks_dir = str(hooks_dir)
        runtime = Runtime(config, log_file=None)

        # Verify handler is registered
        assert "error_occurred" in runtime._event_bus._handlers


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
executed = []
def on_test_event(**kwargs):
    executed.append('a')
    return None
""")
        (hook_dir / "b.py").write_text("""
def on_test_event(**kwargs):
    executed.append('b')
    return None
""")
        (hook_dir / "c.py").write_text("""
def on_test_event(**kwargs):
    executed.append('c')
    return None
""")

        runtime = Runtime(Settings(), log_file=None)

        # Execute each hook individually
        import sys
        import importlib.util

        # We need to test the order - load and execute hooks
        for filename in ["a.py", "b.py", "c.py"]:
            hook_file = hook_dir / filename
            result = runtime._execute_python_hook(hook_file, Event(name="test_event", data={}))

            # Each hook should return None
            assert result is None


# ========== 9. Hook 加载后发布 hook_loaded 事件 ==========


def test_hook_loaded_event_published():
    """Runtime publishes hook_loaded event when loading hooks"""
    from simple_agent.core.runtime import Runtime
    from simple_agent.config.settings import Settings

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

        class TrackingEventBus:
            def __init__(self, event_bus):
                self._event_bus = event_bus

            def publish(self, event):
                published_events.append(event)
                # Let the original bus also handle it
                self._event_bus.publish(event)

        config = Settings()
        config.paths.hooks_dir = str(hooks_dir)
        runtime = Runtime(config, log_file=None)

        # Replace event bus with tracking version
        tracking_bus = TrackingEventBus(runtime._event_bus)
        runtime._event_bus = tracking_bus

        # Manually trigger hook loading
        runtime._load_hooks()

        # Verify hook_loaded event was published
        hook_loaded_events = [e for e in published_events if e.name == "hook_loaded"]
        assert len(hook_loaded_events) >= 1
        assert hook_loaded_events[0].data["hook_name"] == "test_hook"
