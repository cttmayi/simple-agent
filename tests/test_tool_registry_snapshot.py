import pytest
from simple_agent.tools.registry import ToolRegistry, ToolDefinition, get_global_registry
from simple_agent.tools import builtin  # noqa: F401

def test_registry_snapshot():
    registry = get_global_registry()

    # Get initial tool count
    initial_count = len(registry._tools)

    # Save snapshot
    snapshot = registry.snapshot()

    # Snapshot should be a copy
    assert snapshot == registry._tools
    assert snapshot is not registry._tools

def test_registry_restore():
    registry = ToolRegistry()

    # Register a tool
    tool1 = ToolDefinition(name="test1", description="Test 1", fn=lambda: None, parameters={})
    registry.register(tool1)

    # Save snapshot
    snapshot = registry.snapshot()

    # Register another tool
    tool2 = ToolDefinition(name="test2", description="Test 2", fn=lambda: None, parameters={})
    registry.register(tool2)

    # Should have 2 tools
    assert len(registry._tools) == 2

    # Restore snapshot
    registry.restore(snapshot)

    # Should have 1 tool again
    assert len(registry._tools) == 1
    assert "test1" in registry._tools
    assert "test2" not in registry._tools