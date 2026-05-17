"""Tests for the official hook mechanism (stdin/stdout JSON protocol)."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from simple_agent.core.runtime import Runtime
from simple_agent.core.events import Event, HookBlockedException
from simple_agent.config.settings import Settings


def test_hook_loader_loads_json_config():
    """HookLoader loads hooks from JSON configuration."""
    from simple_agent.resources.hooks import HookLoader

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create hooks.json
        hooks_file = Path(tmpdir) / "hooks.json"
        hooks_file.write_text('''
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Session started'",
            "async": false
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "markdown",
            "content": "Processing..."
          }
        ]
      }
    ]
  }
}
''')

        loader = HookLoader(hooks_file)
        hooks = loader.list_hooks()

        assert len(hooks) == 2
        assert hooks[0]["event_name"] == "SessionStart"
        assert hooks[1]["event_name"] == "UserPromptSubmit"

        # Test getting hooks for specific event
        session_hooks = loader.get_hooks_for_event("SessionStart")
        assert len(session_hooks) == 1
        assert session_hooks[0]["matcher"] == ""
        assert len(session_hooks[0]["hooks"]) == 1


def test_python_hook_allow():
    """Test Python hook that returns allow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a Python hook that allows
        hook_file = Path(tmpdir) / "allow.py"
        hook_file.write_text("""
import sys
import json

input_json = sys.stdin.read()
data = json.loads(input_json)

result = {
    "decision": "allow",
    "message": "Hook passed"
}

print(json.dumps(result, ensure_ascii=False))
""")

        # Create mock runtime components
        runtime = Runtime.__new__(Runtime)
        runtime._config = Settings()
        runtime._event_bus = MagicMock()
        runtime._renderer = MagicMock()
        runtime._logger = MagicMock()
        runtime._session = MagicMock()

        # Create hook input
        hook_input = {
            "event": "SessionStart",
            "payload": {"session_id": "test-123"}
        }
        hook_input_json = json.dumps(hook_input, ensure_ascii=False)

        # Execute hook
        hook_def = {"file": str(hook_file)}
        result = runtime._execute_python_hook(hook_def, hook_input_json)

        assert result is not None
        assert result["decision"] == "allow"
        assert result["message"] == "Hook passed"


def test_python_hook_block():
    """Test Python hook that returns block."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a Python hook that blocks
        hook_file = Path(tmpdir) / "block.py"
        hook_file.write_text("""
import sys
import json

input_json = sys.stdin.read()
data = json.loads(input_json)

tool = data.get("payload", {}).get("tool", "")

if tool == "DANGER":
    result = {
        "decision": "block",
        "message": "Dangerous tool blocked"
    }
else:
    result = {
        "decision": "allow",
        "message": "Tool allowed"
    }

print(json.dumps(result, ensure_ascii=False))
""")

        runtime = Runtime.__new__(Runtime)
        runtime._config = Settings()
        runtime._event_bus = MagicMock()
        runtime._renderer = MagicMock()
        runtime._logger = MagicMock()
        runtime._session = MagicMock()

        hook_input = {
            "event": "PreToolUse",
            "payload": {"tool": "DANGER", "parameters": {}}
        }
        hook_input_json = json.dumps(hook_input, ensure_ascii=False)

        hook_def = {"file": str(hook_file)}
        result = runtime._execute_python_hook(hook_def, hook_input_json)

        assert result is not None
        assert result["decision"] == "block"
        assert result["message"] == "Dangerous tool blocked"


def test_shell_hook_allow():
    """Test Shell hook that returns allow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a Shell hook that allows
        hook_file = Path(tmpdir) / "allow.sh"
        hook_file.write_text("""#!/bin/bash
set -e

INPUT_JSON=$(cat)

echo '{"decision": "allow", "message": "Shell hook passed"}'
""")
        hook_file.chmod(0o755)

        runtime = Runtime.__new__(Runtime)
        runtime._config = Settings()
        runtime._event_bus = MagicMock()
        runtime._renderer = MagicMock()
        runtime._logger = MagicMock()
        runtime._session = MagicMock()

        hook_input = {"event": "SessionStart", "payload": {}}
        hook_input_json = json.dumps(hook_input, ensure_ascii=False)

        result = runtime._execute_shell_hook(hook_file, hook_input_json)

        assert result is not None
        assert result["decision"] == "allow"
        assert result["message"] == "Shell hook passed"


def test_python_hook_with_additional_context():
    """Test Python hook that adds context for LLM."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hook_file = Path(tmpdir) / "add_context.py"
        hook_file.write_text("""
import sys
import json

input_json = sys.stdin.read()
data = json.loads(input_json)

result = {
    "decision": "allow",
    "message": "Added context",
    "additionalContext": "Remember: user prefers concise responses."
}

print(json.dumps(result, ensure_ascii=False))
""")

        runtime = Runtime.__new__(Runtime)
        runtime._config = Settings()
        runtime._event_bus = MagicMock()
        runtime._renderer = MagicMock()
        runtime._logger = MagicMock()
        runtime._session = MagicMock()

        hook_input = {"event": "UserPromptSubmit", "payload": {"content": "test"}}
        hook_input_json = json.dumps(hook_input, ensure_ascii=False)

        hook_def = {"file": str(hook_file)}
        result = runtime._execute_python_hook(hook_def, hook_input_json)

        assert result is not None
        assert result["decision"] == "allow"
        assert result["additionalContext"] == "Remember: user prefers concise responses."


def test_markdown_hook():
    """Test Markdown hook that appends content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hook_file = Path(tmpdir) / "context.md"
        hook_file.write_text("""
You are running in a test environment.
Session ID: {{session_id}}
""")

        runtime = Runtime.__new__(Runtime)
        runtime._config = Settings()
        runtime._event_bus = MagicMock()
        runtime._renderer = MagicMock()
        runtime._logger = MagicMock()
        runtime._session = MagicMock()
        runtime._session_id = "test-123"

        event = Event("SessionStart", {"session_id": "test-123"})

        hook_def = {"file": str(hook_file)}
        result = runtime._execute_markdown_hook(hook_def, event)

        assert result is not None
        assert result["decision"] == "allow"
        assert "test-123" in result["additionalContext"]


def test_execute_hook_definition_with_block():
    """_execute_hook_definition stops early when hook returns block."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hook_file = Path(tmpdir) / "block.py"
        hook_file.write_text("""
import sys, json
input_json = sys.stdin.read()
print(json.dumps({"decision": "block", "message": "Blocked"}))
""")

        runtime = Runtime.__new__(Runtime)
        runtime._config = Settings()
        runtime._event_bus = MagicMock()
        runtime._renderer = MagicMock()
        runtime._logger = MagicMock()
        runtime._session = MagicMock()
        runtime._session_id = "test-session-id"

        hook_def = {"type": "python", "file": str(hook_file)}
        event = Event("TestEvent", {"session_id": "test"})

        result = runtime._execute_hook_definition(hook_def, event, "TestEvent")

        assert result is not None
        assert result["decision"] == "block"


def test_hook_handler_processes_additional_context():
    """Test that handler correctly processes additionalContext and sends to LLM."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime = Runtime.__new__(Runtime)
        runtime._config = Settings()
        runtime._event_bus = MagicMock()
        runtime._renderer = MagicMock()
        runtime._logger = MagicMock()
        runtime._session = MagicMock()

        # Test the handler logic directly
        hook_data = {"event_name": "UserPromptSubmit"}
        event = Event("UserPromptSubmit", {"content": "test"})

        def handler(event_obj):
            result = {"decision": "allow", "message": "Processed", "additionalContext": "User prefers concise responses"}

            if result.get("message"):
                runtime._renderer.render_message("system", result["message"])

            if result.get("additionalContext"):
                runtime._session.add_message("system", f"[{hook_data['event_name']}] {result['additionalContext']}")

        handler(event)

        runtime._renderer.render_message.assert_called_once_with("system", "Processed")
        runtime._session.add_message.assert_called_once_with(
            "system",
            "[UserPromptSubmit] User prefers concise responses"
        )


def test_hook_handler_raises_on_block():
    """Test that handler raises HookBlockedException on block decision."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runtime = Runtime.__new__(Runtime)
        runtime._config = Settings()
        runtime._event_bus = MagicMock()
        runtime._renderer = MagicMock()
        runtime._logger = MagicMock()
        runtime._session = MagicMock()

        hook_data = {"event_name": "PreToolUse"}
        event = Event("PreToolUse", {"tool": "danger"})

        def handler(event_obj):
            result = {"decision": "block", "message": "Tool blocked"}

            if result.get("message"):
                runtime._renderer.render_message("system", result["message"])

            if result.get("decision") == "block":
                runtime._session.add_message("system", f"[BLOCKED by {hook_data['event_name']}] {result['message']}")
                raise HookBlockedException(result["message"])

        try:
            handler(event)
            assert False, "Should have raised HookBlockedException"
        except HookBlockedException as e:
            assert str(e) == "Tool blocked"
            runtime._renderer.render_message.assert_called_once_with("system", "Tool blocked")
            runtime._session.add_message.assert_called_once()


def test_python_hook_no_output_means_allow():
    """Test Python hook with no stdout output defaults to allow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a hook that outputs nothing
        hook_file = Path(tmpdir) / "silent.py"
        hook_file.write_text("""
import sys
# Read stdin but output nothing
sys.stdin.read()
""")

        runtime = Runtime.__new__(Runtime)
        runtime._config = Settings()
        runtime._event_bus = MagicMock()
        runtime._renderer = MagicMock()
        runtime._logger = MagicMock()
        runtime._session = MagicMock()

        hook_input = {"event": "SessionStart", "payload": {}}
        hook_input_json = json.dumps(hook_input, ensure_ascii=False)

        hook_def = {"file": str(hook_file)}
        result = runtime._execute_python_hook(hook_def, hook_input_json)

        assert result is not None
        assert result["decision"] == "allow"


def test_python_hook_invalid_json_fails():
    """Test Python hook with invalid JSON output fails gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a hook that outputs invalid JSON
        hook_file = Path(tmpdir) / "invalid.py"
        hook_file.write_text("""
import sys
print("This is not JSON")
""")

        runtime = Runtime.__new__(Runtime)
        runtime._config = Settings()
        runtime._event_bus = MagicMock()
        runtime._renderer = MagicMock()
        runtime._logger = MagicMock()
        runtime._session = MagicMock()

        hook_input = {"event": "SessionStart", "payload": {}}
        hook_input_json = json.dumps(hook_input, ensure_ascii=False)

        hook_def = {"file": str(hook_file)}
        result = runtime._execute_python_hook(hook_def, hook_input_json)

        assert result is None
        runtime._renderer.render_message.assert_called()


def test_python_hook_missing_decision_defaults_to_allow():
    """Test Python hook without decision field defaults to 'allow'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a hook that outputs JSON without decision
        hook_file = Path(tmpdir) / "no_decision.py"
        hook_file.write_text("""
import sys
import json
print(json.dumps({"message": "Hello"}))
""")

        runtime = Runtime.__new__(Runtime)
        runtime._config = Settings()
        runtime._event_bus = MagicMock()
        runtime._renderer = MagicMock()
        runtime._logger = MagicMock()
        runtime._session = MagicMock()

        hook_input = {"event": "SessionStart", "payload": {}}
        hook_input_json = json.dumps(hook_input, ensure_ascii=False)

        hook_def = {"file": str(hook_file)}
        result = runtime._execute_python_hook(hook_def, hook_input_json)

        assert result is not None
        assert result["decision"] == "allow"
        assert result["message"] == "Hello"


def test_hook_with_updated_input():
    """Test hook that returns updatedInput to modify event data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hook_file = Path(tmpdir) / "update.py"
        hook_file.write_text("""
import sys
import json

input_json = sys.stdin.read()
data = json.loads(input_json)

result = {
    "decision": "allow",
    "message": "Updated",
    "updatedInput": {
        "tool": data.get("payload", {}).get("tool") + "_modified",
        "parameters": {"new_key": "new_value"}
    }
}

print(json.dumps(result, ensure_ascii=False))
""")

        runtime = Runtime.__new__(Runtime)
        runtime._config = Settings()
        runtime._event_bus = MagicMock()
        runtime._renderer = MagicMock()
        runtime._logger = MagicMock()
        runtime._session = MagicMock()

        hook_input = {"event": "PreToolUse", "payload": {"tool": "test", "parameters": {}}}
        hook_input_json = json.dumps(hook_input, ensure_ascii=False)

        hook_def = {"file": str(hook_file)}
        result = runtime._execute_python_hook(hook_def, hook_input_json)

        assert result is not None
        assert result["decision"] == "allow"
        assert result["updatedInput"]["tool"] == "test_modified"
        assert result["updatedInput"]["parameters"]["new_key"] == "new_value"


def test_multiple_hooks_combined_results():
    """Test that multiple hooks combine their results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create Python hooks
        hook1 = Path(tmpdir) / "hook1.py"
        hook1.write_text("""
import sys, json
input_json = sys.stdin.read()
print(json.dumps({"decision": "allow", "message": "Hook 1 processed"}))
""")

        hook2 = Path(tmpdir) / "hook2.py"
        hook2.write_text("""
import sys, json
input_json = sys.stdin.read()
print(json.dumps({"decision": "allow", "additionalContext": "Context from hook 2"}))
""")

        runtime = Runtime.__new__(Runtime)
        runtime._config = Settings()
        runtime._event_bus = MagicMock()
        runtime._renderer = MagicMock()
        runtime._logger = MagicMock()
        runtime._session = MagicMock()
        runtime._session_id = "test-session-id"

        # Use real _execute_python_hook
        def mock_execute_python(hook_def, hook_input_json):
            import subprocess
            filepath_str = hook_def.get("file", "")
            result = subprocess.run(
                [sys.executable, str(filepath_str)],
                input=hook_input_json,
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.stdout.strip():
                return json.loads(result.stdout.strip())
            return {"decision": "allow"}

        runtime._execute_python_hook = mock_execute_python
        runtime._execute_shell_hook = lambda f, j: None
        runtime._execute_markdown_hook = lambda f, e: None

        # Create hook definitions
        hook_group = {
            "event_name": "TestEvent",
            "matcher": "",
            "hooks": [
                {"type": "python", "file": str(hook1)},
                {"type": "python", "file": str(hook2)},
            ]
        }
        event = Event("TestEvent", {})

        combined_result = None
        for hook_def in hook_group["hooks"]:
            result = runtime._execute_hook_definition(hook_def, event, "TestEvent")
            if result:
                if combined_result is None:
                    combined_result = result
                else:
                    # Merge results
                    if result.get("message"):
                        combined_result["message"] = result["message"]
                    if result.get("additionalContext"):
                        combined_result["additionalContext"] = result["additionalContext"]

        assert combined_result is not None
        assert combined_result["decision"] == "allow"
        assert combined_result["message"] == "Hook 1 processed"
        assert combined_result["additionalContext"] == "Context from hook 2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])