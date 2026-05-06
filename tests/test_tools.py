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
