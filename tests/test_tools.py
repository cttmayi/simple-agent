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
