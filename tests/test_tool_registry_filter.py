import pytest
from simple_agent.tools.registry import ToolRegistry, ToolDefinition


def test_registry_filter_simple():
    registry = ToolRegistry()

    # Register multiple tools
    registry.register(ToolDefinition(name="bash", description="Bash", fn=lambda: None, parameters={}))
    registry.register(ToolDefinition(name="read", description="Read", fn=lambda: None, parameters={}))
    registry.register(ToolDefinition(name="write", description="Write", fn=lambda: None, parameters={}))

    # Save snapshot
    snapshot = registry.snapshot()

    # Filter to only bash and read
    registry.filter(["bash", "read"])

    # Should only have bash and read
    assert len(registry._tools) == 2
    assert "bash" in registry._tools
    assert "read" in registry._tools
    assert "write" not in registry._tools


def test_registry_filter_with_restore():
    registry = ToolRegistry()

    # Register multiple tools
    registry.register(ToolDefinition(name="bash", description="Bash", fn=lambda: None, parameters={}))
    registry.register(ToolDefinition(name="read", description="Read", fn=lambda: None, parameters={}))
    registry.register(ToolDefinition(name="write", description="Write", fn=lambda: None, parameters={}))

    # Save snapshot before filter
    snapshot = registry.snapshot()

    # Filter to only bash
    registry.filter(["bash"])
    assert len(registry._tools) == 1
    assert "bash" in registry._tools

    # Restore original state
    registry.restore(snapshot)
    assert len(registry._tools) == 3
    assert "bash" in registry._tools
    assert "read" in registry._tools
    assert "write" in registry._tools


def test_registry_filter_empty_list():
    registry = ToolRegistry()

    registry.register(ToolDefinition(name="bash", description="Bash", fn=lambda: None, parameters={}))
    registry.register(ToolDefinition(name="read", description="Read", fn=lambda: None, parameters={}))

    # Filter to empty list - should result in empty registry
    registry.filter([])
    assert len(registry._tools) == 0