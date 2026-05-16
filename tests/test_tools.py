from simple_agent.tools.registry import ToolRegistry, tool

def test_tool_decorator():
    registry = ToolRegistry()

    @tool(name="test_tool", description="A test tool", registry=registry)
    def my_tool(value: str) -> str:
        return f"processed: {value}"

    tool_def = registry.get_tool("test_tool")
    assert tool_def is not None
    assert tool_def.name == "test_tool"
    assert tool_def.description == "A test tool"
    assert tool_def.fn("test") == "processed: test"

def test_tool_execution():
    registry = ToolRegistry()

    @tool(name="echo", description="Echo input", registry=registry)
    def echo(input: str) -> str:
        return input

    result = registry.execute_tool("echo", {"input": "hello"})
    assert result == "hello"

def test_tool_not_found():
    registry = ToolRegistry()
    result = registry.execute_tool("nonexistent", {})
    assert result is None

def test_tool_list_tools():
    registry = ToolRegistry()

    @tool(name="tool1", description="Tool 1", registry=registry)
    def tool1():
        pass

    @tool(name="tool2", description="Tool 2", registry=registry)
    def tool2():
        pass

    tools = registry.list_tools()
    assert len(tools) == 2
    assert any(t["name"] == "tool1" for t in tools)
    assert any(t["name"] == "tool2" for t in tools)

from simple_agent.tools.dispatcher import ToolDispatcher

def test_tool_dispatcher_execute():
    registry = ToolRegistry()

    @tool(name="test", description="Test tool", registry=registry)
    def test_fn(x: int) -> int:
        return x * 2

    dispatcher = ToolDispatcher(registry)
    result = dispatcher.execute({"name": "test", "arguments": {"x": 5}})
    assert result["success"] is True
    assert result["result"] == 10

def test_tool_dispatcher_invalid_tool():
    registry = ToolRegistry()
    dispatcher = ToolDispatcher(registry)
    result = dispatcher.execute({"name": "nonexistent", "arguments": {}})
    assert result["success"] is False
    assert "error" in result

def test_tool_dispatcher_invalid_arguments():
    registry = ToolRegistry()

    @tool(name="requires_int", description="Requires int", registry=registry)
    def requires_int(x: int) -> int:
        return x

    dispatcher = ToolDispatcher(registry)
    # With original spec, argument type validation is not performed
    # The function will accept the string and return it
    result = dispatcher.execute({"name": "requires_int", "arguments": {"x": "not an int"}})
    assert result["success"] is True
    assert result["result"] == "not an int"

def test_bash_output_limiting():
    """Test that bash output is limited to 5 lines."""
    from simple_agent.tools.builtin.bash import BASH

    # Generate output with more than 5 lines
    result = BASH._execute("for i in {1..10}; do echo \"line $i\"; done")

    assert result["success"] is True
    stdout = result["stdout"]
    # Should show only first 5 lines (no truncation message)
    assert "line 1" in stdout
    assert "line 2" in stdout
    assert "line 3" in stdout
    assert "line 4" in stdout
    assert "line 5" in stdout
    assert "line 6" not in stdout
    # Should have exactly 5 lines
    assert len(stdout.strip().split('\n')) == 5

def test_bash_stderr_limiting():
    """Test that bash stderr is limited to 5 lines."""
    from simple_agent.tools.builtin.bash import BASH

    # Generate stderr with more than 5 lines
    result = BASH._execute('for i in {1..10}; do echo "error $i" >&2; done')

    assert result["success"] is True
    stderr = result["stderr"]
    # Should show only first 5 errors (no truncation message)
    assert "error 1" in stderr
    assert "error 2" in stderr
    assert "error 3" in stderr
    assert "error 4" in stderr
    assert "error 5" in stderr
    assert "error 6" not in stderr
    # Should have exactly 5 lines
    assert len(stderr.strip().split('\n')) == 5

def test_tool_snapshot_isolation():
    """Test that snapshot is not modified after restore and subsequent registry changes."""
    registry = ToolRegistry()

    # Register first tool
    @tool(name="tool1", description="Tool 1", registry=registry)
    def tool1():
        return "tool1"

    # Take snapshot
    snapshot = registry.snapshot()
    assert len(snapshot) == 1
    assert "tool1" in snapshot

    # Add second tool
    @tool(name="tool2", description="Tool 2", registry=registry)
    def tool2():
        return "tool2"

    # Snapshot should not be affected
    assert len(snapshot) == 1
    assert "tool1" in snapshot
    assert "tool2" not in snapshot

    # Restore from snapshot
    registry.restore(snapshot)

    # Registry should have only tool1 now
    assert len(registry._tools) == 1
    assert "tool1" in registry._tools
    assert "tool2" not in registry._tools

    # Add a new tool to registry
    @tool(name="tool3", description="Tool 3", registry=registry)
    def tool3():
        return "tool3"

    # Snapshot should STILL not be affected
    assert len(snapshot) == 1
    assert "tool1" in snapshot
    assert "tool2" not in snapshot
    assert "tool3" not in snapshot

    # Registry should have tool1 and tool3
    assert len(registry._tools) == 2
    assert "tool1" in registry._tools
    assert "tool2" not in registry._tools
    assert "tool3" in registry._tools
