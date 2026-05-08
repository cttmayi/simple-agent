# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Run the agent
simple-agent

# Run tests
pytest

# Run specific test file
pytest tests/test_tools.py

# Run specific test
pytest tests/test_tools.py::test_register_tool
```

## Architecture Overview

The codebase uses a plugin-based architecture with these key patterns:

### Core Components

- **simple_agent/core/runtime.py**: Main application loop, orchestrates API calls, tool execution, and UI
- **simple_agent/core/session.py**: Maintains conversation history with support for tool_calls and tool_call_id
- **simple_agent/tools/registry.py**: Global singleton registry for tools. Uses `get_global_registry()` to access
- **simple_agent/tools/dispatcher.py**: Executes tools through the registry with error handling
- **simple_agent/api/client.py** & **providers.py**: Unified API client for OpenAI and Anthropic

### Tool System

Tools are registered in a global registry. Builtin tools auto-register on import:
- Import `simple_agent.tools.builtin` to load all builtin tools
- Use `@tool` decorator to register custom functions
- Tools must return dicts with at least a `success` boolean field
- The `ToolDispatcher.execute()` wrapper adds error handling, but builtin tools include their own

Tool result format expected by AI:
```python
{
    "success": True/False,
    "stdout": "...",      # for BASH
    "content": "...",     # for READ
    "matches": [...],     # for GREP
    "results": [...],     # for WebSearch
    "error": "...",       # optional, when success=False
}
```

When tool execution fails, the error is sent to AI with a `[TOOL_ERROR]` prefix so it can understand and retry.

### Multi-Step Tool Calling

The runtime handles recursive tool calling automatically:
1. AI returns tool_calls → Execute all tools → Send results back to API
2. AI may return more tool_calls → Execute → Send results back → Repeat
3. AI returns final content without tool_calls → Display to user

This flow is handled in `Runtime._handle_tool_calls_in_message()`.

### Configuration System

Config is loaded with priority: `~/.config/simple-agent/config.yml` → `./.simple-agent/config.yml` → Environment variables

Use environment variables to override:
```bash
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1
simple-agent
```

### Logging System

- LLM requests/responses logged to `logs/llm/llm-YYYY-MM-DD.jsonl` (JSONL format)
- Use `simple-agent --logs` to view in human-readable format
- Log entries include: request_id, timestamp, model, messages, tool_calls, usage, tool executions

**Tool Execution Logging**: All tool executions are logged to the log file (not just to the session).
- The log captures: tool_name, tool_call_id, arguments, and the full result dict
- Check `simple-agent --logs` to review tool execution results

### Resource Loading

Skills, subagents, hooks, and commands are loaded from frontmatter markdown files using `python-frontmatter`. The loader classes (`SkillLoader`, `SubagentLoader`, etc.) provide `list_*()` and `get_*()` methods.

### Session and Message Format

The Session maintains message history with support for tool calling:
```python
session.add_message(
    role="user",                    # user, assistant, tool, system
    content="...",                   # message content
    tool_call_id="...",                # optional, for tool role
    tool_calls=[...]                  # optional, for assistant role with tool_calls
)
```

Messages are passed directly to the OpenAI API which expects `tool_calls` and `tool_call_id` fields for function calling.

### UI Rendering

`UIRenderer` uses the `rich` library for terminal output. It has methods for:
- `render_message(role, content)`: Regular chat messages
- `render_tool_result(tool_name, result)`: Formatted tool execution output
- `render_error(message)`: Error messages

### Testing

Tests use pytest and are organized by module:
- `test_config.py`: Configuration loading
- `test_tools.py`: Tool registry and dispatching
- `test_runtime.py`: Runtime behavior
- `test_api.py`: API client and providers
- `test_ui.py`: UI rendering
- `test_session.py`: Session management

When adding new features, add corresponding tests in the appropriate file.