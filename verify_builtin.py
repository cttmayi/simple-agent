"""Verify builtin tools can be imported and registered."""

import sys

def test_imports():
    """Test that all builtin tools can be imported."""
    try:
        from simple_agent.tools.builtin import BASH, READ, WRITE, GREP, WebSearch
        print("✓ All builtin tools imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_registration():
    """Test that builtin tools are registered in the global registry."""
    try:
        from simple_agent.tools.registry import get_global_registry

        # Import builtin tools to trigger registration
        import simple_agent.tools.builtin

        registry = get_global_registry()
        expected_tools = ["bash", "read", "write", "grep", "web_search"]

        for tool_name in expected_tools:
            tool = registry.get_tool(tool_name)
            if tool is None:
                print(f"✗ Tool '{tool_name}' not registered")
                return False
            print(f"✓ Tool '{tool_name}' registered")

        return True
    except Exception as e:
        print(f"✗ Registration test failed: {e}")
        return False

def test_execute_methods():
    """Test that all tools have execute methods."""
    try:
        from simple_agent.tools.builtin import BASH, READ, WRITE, GREP, WebSearch

        for tool_class in [BASH, READ, WRITE, GREP, WebSearch]:
            if not hasattr(tool_class, 'execute'):
                print(f"✗ {tool_class.__name__} missing execute method")
                return False
            print(f"✓ {tool_class.__name__} has execute method")

        return True
    except Exception as e:
        print(f"✗ Execute method test failed: {e}")
        return False

def test_runtime_integration():
    """Test that runtime uses builtin tools."""
    try:
        from simple_agent.tools.registry import get_global_registry

        registry = get_global_registry()
        tools = registry.list_tools()
        builtin_names = {"bash", "read", "write", "grep", "web_search"}
        registered_names = {tool["name"] for tool in tools}

        missing = builtin_names - registered_names
        if missing:
            print(f"✗ Builtin tools not in registry: {missing}")
            return False

        print(f"✓ All builtin tools available in registry")
        print(f"  Registered tools: {len(registered_names)}")
        return True
    except Exception as e:
        print(f"✗ Runtime integration test failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("=" * 50)
    print("Builtin Tools Verification")
    print("=" * 50)

    tests = [
        test_imports,
        test_registration,
        test_execute_methods,
        test_runtime_integration,
    ]

    results = []
    for test in tests:
        print(f"\n{test.__name__}:")
        results.append(test())

    print("\n" + "=" * 50)
    if all(results):
        print("✓ All tests passed")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
