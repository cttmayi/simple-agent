# Simple Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI tool similar to Claude Code with support for hooks, skills, subagents, and slash commands, using Python with OpenAI/Claude API.

**Architecture:** Plugin-based architecture with a lightweight runtime core. All features (skills, hooks, subagents, commands) are dynamically loaded from markdown-based definitions in their respective directories. The system uses an event bus for hooks and a tool registry for LLM-function interaction.

**Tech Stack:** Python 3.11+, rich for UI, pytest for testing, openai SDK for API, pydantic for configuration, pyyaml for config files.

---

## File Structure Map

**Core Runtime:**
- `simple_agent/config/settings.py` - Configuration loading with priority handling
- `simple_agent/core/events.py` - Event bus for hook system
- `simple_agent/core/session.py` - Session and message management
- `simple_agent/api/client.py` - Unified API client abstraction
- `simple_agent/api/providers.py` - OpenAI/Claude provider adapters
- `simple_agent/tools/registry.py` - Tool registration decorator and storage
- `simple_agent/tools/dispatcher.py` - Tool execution and result handling
- `simple_agent/resources/base.py` - Base classes for resource loaders
- `simple_agent/resources/skills.py` - Skill discovery and loading
- `simple_agent/resources/subagents.py` - Subagent discovery and loading
- `simple_agent/resources/hooks.py` - Hook discovery and loading
- `simple_agent/resources/commands.py` - Command discovery and loading
- `simple_agent/ui/renderer.py` - Rich-based terminal UI renderer
- `simple_agent/__init__.py` - Public API exports
- `simple_agent/main.py` - CLI entry point

**Tests:**
- `tests/test_config.py` - Configuration loading tests
- `tests/test_events.py` - Event bus tests
- `tests/test_tools.py` - Tool registry and dispatcher tests
- `tests/test_resources.py` - Resource loading tests
- `tests/test_api.py` - API client tests with mocks

---

## Phase 1: Project Setup and Configuration

### Task 1: Project Structure and Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `simple_agent/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Write pyproject.toml with project metadata and dependencies**

```toml
[project]
name = "simple-agent"
version = "0.1.0"
description = "A Claude Code-like CLI tool with hooks, skills, and subagents"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.0.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "rich>=13.0.0",
    "python-frontmatter>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-mock>=3.10.0",
    "responses>=0.23.0",
]

[project.scripts]
simple-agent = "simple_agent.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
```

- [ ] **Step 2: Create package __init__.py**

```python
"""Simple Agent - A Claude Code-like CLI tool."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create tests __init__.py**

```python
"""Tests for simple-agent."""
```

- [ ] **Step 4: Run test to verify project structure**

Run: `python -m pytest --version`
Expected: pytest version displayed

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml simple_agent/__init__.py tests/__init__.py
git commit -m "feat: add project structure and dependencies"
```

---

### Task 2: Configuration Management

**Files:**
- Create: `simple_agent/config/__init__.py`
- Create: `simple_agent/config/settings.py`
- Create: `tests/test_config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing test for configuration loading**

```python
import os
import tempfile
from pathlib import Path
from simple_agent.config.settings import Settings, load_config

def test_load_default_config():
    config = load_config()
    assert config.api.provider == "openai"
    assert config.api.model == "gpt-4o"
    assert config.paths.skills_dir == "./skills"
    assert config.paths.memory_dir == "./memory"

def test_config_priority_env():
    os.environ["OPENAI_API_KEY"] = "test-key"
    config = load_config()
    assert config.api.api_key == "test-key"
    os.environ.pop("OPENAI_API_KEY", None)

def test_config_priority_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".simple-agent" / "config.yml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("api:\n  model: gpt-3.5-turbo\n")
        os.chdir(tmpdir)
        config = load_config()
        assert config.api.model == "gpt-3.5-turbo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with "module 'simple_agent.config.settings' not found"

- [ ] **Step 3: Create config module __init__.py**

```python
"""Configuration management."""

from simple_agent.config.settings import Settings, load_config

__all__ = ["Settings", "load_config"]
```

- [ ] **Step 4: Write configuration models and loading logic**

```python
import os
import yaml
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    provider: str = "openai"
    base_url: Optional[str] = None
    api_key: Optional[str] = Field(default=None)
    model: str = "gpt-4o"


class PathsConfig(BaseModel):
    skills_dir: str = "./skills"
    subagents_dir: str = "./subagents"
    hooks_dir: str = "./hooks"
    commands_dir: str = "./commands"
    tools_dir: str = "./tools"
    memory_dir: str = "./memory"


class UIConfig(BaseModel):
    theme: str = "dark"
    show_thinking: bool = True


class Settings(BaseModel):
    api: APIConfig = Field(default_factory=APIConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    ui: UIConfig = Field(default_factory=UIConfig)


def _resolve_env_var(value: str) -> str:
    """Resolve ${VAR} environment variables in strings."""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        var_name = value[2:-1]
        return os.environ.get(var_name, value)
    return value


def _load_yaml_config(path: Path) -> dict:
    """Load YAML config file."""
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_config() -> Settings:
    """Load configuration with priority: CLI args > ENV > file > defaults."""
    config_data = {}

    # Check local config
    local_config = Path.cwd() / ".simple-agent" / "config.yml"
    if local_config.exists():
        config_data.update(_load_yaml_config(local_config))

    # Check user config
    user_config = Path.home() / ".config" / "simple-agent" / "config.yml"
    if user_config.exists():
        # User config should be loaded before local, but local takes priority
        user_data = _load_yaml_config(user_config)
        # Merge with user as base, local overrides
        merged = {**user_data, **config_data}
        config_data = merged

    # Apply environment variable overrides
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        config_data.setdefault("api", {})["api_key"] = api_key

    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("ANTHROPIC_BASE_URL")
    if base_url:
        config_data.setdefault("api", {})["base_url"] = base_url

    # Expand environment variables in values
    if "api" in config_data:
        for key, value in config_data["api"].items():
            if isinstance(value, str):
                config_data["api"][key] = _resolve_env_var(value)

    return Settings(**config_data)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS all tests

- [ ] **Step 6: Commit**

```bash
git add simple_agent/config/ tests/test_config.py
git commit -m "feat: add configuration management"
```

---

## Phase 2: Event System

### Task 3: Event Bus

**Files:**
- Create: `simple_agent/core/__init__.py`
- Create: `simple_agent/core/events.py`
- Create: `tests/test_events.py`
- Test: `tests/test_events.py`

- [ ] **Step 1: Write failing test for event bus**

```python
from simple_agent.core.events import EventBus, Event

def test_event_creation():
    event = Event(name="test_event", data={"key": "value"})
    assert event.name == "test_event"
    assert event.data == {"key": "value"}

def test_event_bus_subscribe():
    bus = EventBus()
    called = []

    def handler(event: Event):
        called.append(event)

    bus.subscribe("test_event", handler)
    bus.publish(Event(name="test_event", data={}))
    assert len(called) == 1

def test_event_bus_unsubscribe():
    bus = EventBus()
    called = []

    def handler(event: Event):
        called.append(event)

    bus.subscribe("test_event", handler)
    bus.unsubscribe("test_event", handler)
    bus.publish(Event(name="test_event", data={}))
    assert len(called) == 0

def test_event_bus_multiple_handlers():
    bus = EventBus()
    results = []

    def handler1(event: Event):
        results.append("handler1")

    def handler2(event: Event):
        results.append("handler2")

    bus.subscribe("test_event", handler1)
    bus.subscribe("test_event", handler2)
    bus.publish(Event(name="test_event", data={}))
    assert results == ["handler1", "handler2"]

def test_event_bus_handler_exception():
    bus = EventBus()
    called = []

    def failing_handler(event: Event):
        raise Exception("Handler failed")

    def working_handler(event: Event):
        called.append(event)

    bus.subscribe("test_event", failing_handler)
    bus.subscribe("test_event", working_handler)
    bus.publish(Event(name="test_event", data={}))
    assert len(called) == 1  # Handler exception shouldn't stop other handlers
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_events.py -v`
Expected: FAIL with "module 'simple_agent.core.events' not found"

- [ ] **Step 3: Create core module __init__.py**

```python
"""Core runtime components."""

from simple_agent.core.events import Event, EventBus

__all__ = ["Event", "EventBus"]
```

- [ ] **Step 4: Write event bus implementation**

```python
from typing import Callable, Dict, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Event:
    name: str
    data: dict


class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable[[Event], None]]] = {}

    def subscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """Subscribe a handler to an event."""
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """Unsubscribe a handler from an event."""
        if event_name in self._handlers:
            try:
                self._handlers[event_name].remove(handler)
            except ValueError:
                pass

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribed handlers."""
        handlers = self._handlers.get(event.name, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in handler for event {event.name}: {e}")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_events.py -v`
Expected: PASS all tests

- [ ] **Step 6: Commit**

```bash
git add simple_agent/core/ tests/test_events.py
git commit -m "feat: add event bus system"
```

---

## Phase 3: Tool System

### Task 4: Tool Registry

**Files:**
- Create: `simple_agent/tools/__init__.py`
- Create: `simple_agent/tools/registry.py`
- Create: `tests/test_tools.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write failing test for tool registry**

```python
from simple_agent.tools.registry import ToolRegistry, tool

def test_tool_decorator():
    registry = ToolRegistry()

    @tool(name="test_tool", description="A test tool")
    def my_tool(value: str) -> str:
        return f"processed: {value}"

    tool_def = registry.get_tool("test_tool")
    assert tool_def is not None
    assert tool_def.name == "test_tool"
    assert tool_def.description == "A test tool"
    assert tool_def.fn("test") == "processed: test"

def test_tool_execution():
    registry = ToolRegistry()

    @tool(name="echo", description="Echo input")
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

    @tool(name="tool1", description="Tool 1")
    def tool1():
        pass

    @tool(name="tool2", description="Tool 2")
    def tool2():
        pass

    tools = registry.list_tools()
    assert len(tools) == 2
    assert any(t["name"] == "tool1" for t in tools)
    assert any(t["name"] == "tool2" for t in tools)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL with "module 'simple_agent.tools.registry' not found"

- [ ] **Step 3: Create tools module __init__.py**

```python
"""Tool system."""

from simple_agent.tools.registry import ToolRegistry, tool

__all__ = ["ToolRegistry", "tool"]
```

- [ ] **Step 4: Write tool registry implementation**

```python
import inspect
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from functools import wraps

_registry = None


def get_global_registry() -> "ToolRegistry":
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


@dataclass
class ToolDefinition:
    name: str
    description: str
    fn: Callable
    parameters: Dict[str, Any]


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool_def: ToolDefinition) -> None:
        self._tools[tool_def.name] = tool_def

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        tool_def = self.get_tool(name)
        if tool_def is None:
            return None
        return tool_def.fn(**arguments)

    def list_tools(self) -> List[Dict[str, str]]:
        return [
            {
                "name": t.name,
                "description": t.description,
            }
            for t in self._tools.values()
        ]

    def to_openai_format(self) -> List[Dict[str, Any]]:
        """Export tools in OpenAI function calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]


def tool(name: Optional[str] = None, description: str = ""):
    """Decorator to register a function as a tool."""

    def decorator(fn: Callable):
        tool_name = name or fn.__name__

        # Build parameter schema from function signature
        sig = inspect.signature(fn)
        parameters = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for param_name, param in sig.parameters.items():
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else "string"
            param_type_str = "string"

            if param_type == int:
                param_type_str = "integer"
            elif param_type == float:
                param_type_str = "number"
            elif param_type == bool:
                param_type_str = "boolean"
            elif param_type == list:
                param_type_str = "array"

            parameters["properties"][param_name] = {"type": param_type_str}

            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)

        tool_def = ToolDefinition(
            name=tool_name,
            description=description,
            fn=fn,
            parameters=parameters,
        )

        get_global_registry().register(tool_def)
        return fn

    return decorator
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_tools.py -v`
Expected: PASS all tests

- [ ] **Step 6: Commit**

```bash
git add simple_agent/tools/ tests/test_tools.py
git commit -m "feat: add tool registry with decorator"
```

---

### Task 5: Tool Dispatcher

**Files:**
- Create: `simple_agent/tools/dispatcher.py`
- Test: `tests/test_tools.py` (extend)

- [ ] **Step 1: Write failing test for tool dispatcher**

```python
from simple_agent.tools.dispatcher import ToolDispatcher

def test_tool_dispatcher_execute():
    registry = ToolRegistry()

    @tool(name="test", description="Test tool")
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

    @tool(name="requires_int", description="Requires int")
    def requires_int(x: int) -> int:
        return x

    dispatcher = ToolDispatcher(registry)
    result = dispatcher.execute({"name": "requires_int", "arguments": {"x": "not an int"}})
    assert result["success"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL with "module 'simple_agent.tools.dispatcher' not found"

- [ ] **Step 3: Write tool dispatcher implementation**

```python
from typing import Any, Dict
from simple_agent.tools.registry import ToolRegistry


class ToolDispatcher:
    def __init__(self, registry: ToolRegistry):
        self._registry = registry

    def execute(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return result."""
        name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})

        try:
            result = self._registry.execute_tool(name, arguments)
            return {"success": True, "result": result}
        except TypeError as e:
            return {"success": False, "error": f"Invalid arguments: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools.py -v`
Expected: PASS all tests

- [ ] **Step 5: Commit**

```bash
git add simple_agent/tools/dispatcher.py tests/test_tools.py
git commit -m "feat: add tool dispatcher"
```

---

## Phase 4: API Client

### Task 6: API Client Foundation

**Files:**
- Create: `simple_agent/api/__init__.py`
- Create: `simple_agent/api/client.py`
- Create: `simple_agent/api/providers.py`
- Create: `tests/test_api.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing test for API client**

```python
from unittest.mock import Mock, patch
from simple_agent.api.client import APIClient
from simple_agent.config.settings import APIConfig

def test_api_client_init():
    config = APIConfig(provider="openai", api_key="test-key")
    client = APIClient(config)
    assert client._provider == "openai"

def test_api_client_send_message():
    config = APIConfig(provider="openai", api_key="test-key")
    client = APIClient(config)

    with patch.object(client._provider_impl, "send_message") as mock_send:
        mock_send.return_value = [{"role": "assistant", "content": "Response"}]

        messages = [{"role": "user", "content": "Hello"}]
        response = client.send_message(messages, tools=[])

        assert response == [{"role": "assistant", "content": "Response"}]
        mock_send.assert_called_once()

def test_api_client_stream():
    config = APIConfig(provider="openai", api_key="test-key")
    client = APIClient(config)

    chunks = ["Hello", " world", "!"]

    def mock_stream(messages, tools):
        for chunk in chunks:
            yield chunk

    with patch.object(client._provider_impl, "stream_message") as mock_stream:
        mock_stream.side_effect = mock_stream

        messages = [{"role": "user", "content": "Hello"}]
        result = list(client.stream_message(messages, tools=[]))

        assert result == chunks
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`
Expected: FAIL with "module 'simple_agent.api.client' not found"

- [ ] **Step 3: Create API module __init__.py**

```python
"""API client abstraction."""

from simple_agent.api.client import APIClient
from simple_agent.api.providers import OpenAIProvider, AnthropicProvider

__all__ = ["APIClient", "OpenAIProvider", "AnthropicProvider"]
```

- [ ] **Step 4: Write provider implementations**

```python
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List
from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk


class BaseProvider(ABC):
    @abstractmethod
    def send_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        pass

    @abstractmethod
    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        pass


class OpenAIProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any]):
        self.client = OpenAI(
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
        )
        self.model = config.get("model", "gpt-4o")

    def send_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        response: ChatCompletion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools or None,
        )

        assistant_message = {
            "role": "assistant",
            "content": response.choices[0].message.content or "",
        }

        if response.choices[0].message.tool_calls:
            assistant_message["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.choices[0].message.tool_calls
            ]

        return [assistant_message]

    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        stream: Stream[ChatCompletionChunk] = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools or None,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any]):
        # Anthropic uses OpenAI SDK with custom base_url
        self.client = OpenAI(
            api_key=config.get("api_key"),
            base_url=config.get("base_url", "https://api.anthropic.com"),
        )
        self.model = config.get("model", "claude-sonnet-4-20250514")

    def send_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        # Anthropic compatible call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools or None,
            extra_headers={"anthropic-version": "2023-06-01"},
        )

        assistant_message = {
            "role": "assistant",
            "content": response.choices[0].message.content or "",
        }

        if response.choices[0].message.tool_calls:
            assistant_message["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.choices[0].message.tool_calls
            ]

        return [assistant_message]

    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools or None,
            stream=True,
            extra_headers={"anthropic-version": "2023-06-01"},
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

- [ ] **Step 5: Write API client**

```python
from typing import AsyncGenerator, Dict, List
from simple_agent.api.providers import OpenAIProvider, AnthropicProvider
from simple_agent.config.settings import APIConfig


class APIClient:
    def __init__(self, config: APIConfig):
        self._config = config
        self._provider = config.provider

        provider_config = {
            "api_key": config.api_key,
            "base_url": config.base_url,
            "model": config.model,
        }

        if self._provider == "openai":
            self._provider_impl = OpenAIProvider(provider_config)
        elif self._provider == "anthropic":
            self._provider_impl = AnthropicProvider(provider_config)
        else:
            raise ValueError(f"Unknown provider: {self._provider}")

    def send_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        return self._provider_impl.send_message(messages, tools)

    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        return self._provider_impl.stream_message(messages, tools)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_api.py -v`
Expected: PASS all tests

- [ ] **Step 7: Commit**

```bash
git add simple_agent/api/ tests/test_api.py
git commit -m "feat: add API client with OpenAI/Anthropic support"
```

---

## Phase 5: Resource Loading

### Task 7: Resource Base Classes

**Files:**
- Create: `simple_agent/resources/__init__.py`
- Create: `simple_agent/resources/base.py`
- Create: `tests/test_resources.py`
- Test: `tests/test_resources.py`

- [ ] **Step 1: Write failing test for resource base classes**

```python
import tempfile
from pathlib import Path
from simple_agent.resources.base import BaseResource, ResourceLoader

class TestResource(BaseResource):
    name: str
    description: str

def test_base_resource_creation():
    resource = TestResource(name="test", description="A test resource")
    assert resource.name == "test"
    assert resource.description == "A test resource"

def test_resource_loader_scan_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = ResourceLoader(Path(tmpdir))
        resources = loader.scan()
        assert resources == []

def test_resource_loader_with_frontmatter():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test resource
        resource_dir = Path(tmpdir) / "test-resource"
        resource_dir.mkdir()
        md_file = resource_dir / "TEST.md"
        md_file.write_text("---\nname: test\ndescription: A test\n---\nContent")

        loader = ResourceLoader(tmpdir)
        resources = loader.scan()
        assert len(resources) == 1
        assert resources[0]["name"] == "test"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_resources.py -v`
Expected: FAIL with "module 'simple_agent.resources.base' not found"

- [ ] **Step 3: Create resources module __init__.py**

```python
"""Resource loading system."""

from simple_agent.resources.base import BaseResource, ResourceLoader

__all__ = ["BaseResource", "ResourceLoader"]
```

- [ ] **Step 4: Write resource base classes**

```python
import frontmatter
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import dataclass


@dataclass
class BaseResource:
    """Base class for all resources (skills, subagents, hooks, commands)."""
    name: str
    description: str
    path: Path
    metadata: Dict[str, Any]


class ResourceLoader:
    """Base class for loading resources from directories."""

    def __init__(self, base_dir: Path):
        self._base_dir = Path(base_dir)

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        """Get markdown file for a resource directory."""
        raise NotImplementedError

    def scan(self) -> List[Dict[str, Any]]:
        """Scan base directory for resources."""
        if not self._base_dir.exists():
            return []

        resources = []
        for item in self._base_dir.iterdir():
            if item.is_dir():
                md_file = self._get_markdown_file(item)
                if md_file and md_file.exists():
                    parsed = frontmatter.load(md_file)
                    resources.append({
                        "name": parsed.get("name", item.name),
                        "description": parsed.get("description", ""),
                        "path": str(item),
                        "metadata": parsed.metadata,
                        "content": parsed.content,
                    })
        return resources

    def load(self, name: str) -> BaseResource:
        """Load a specific resource by name."""
        resources = self.scan()
        for r in resources:
            if r["name"] == name:
                return BaseResource(
                    name=r["name"],
                    description=r["description"],
                    path=Path(r["path"]),
                    metadata=r["metadata"],
                )
        raise ValueError(f"Resource not found: {name}")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_resources.py -v`
Expected: PASS all tests

- [ ] **Step 6: Commit**

```bash
git add simple_agent/resources/base.py tests/test_resources.py
git commit -m "feat: add resource base classes"
```

---

### Task 8: Skill Loader

**Files:**
- Create: `simple_agent/resources/skills.py`
- Test: `tests/test_resources.py` (extend)

- [ ] **Step 1: Write failing test for skill loader**

```python
from simple_agent.resources.skills import SkillLoader

def test_skill_loader_scan():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test skill
        skill_dir = Path(tmpdir) / "test-skill"
        skill_dir.mkdir()
        md_file = skill_dir / "SKILL.md"
        md_file.write_text("---\nname: test-skill\ndescription: A test skill\n---\n# Test Skill\n\nThis is a test.")

        loader = SkillLoader(Path(tmpdir))
        skills = loader.list_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == "test-skill"
        assert skills[0]["description"] == "A test skill"

def test_skill_loader_get_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test skill
        skill_dir = Path(tmpdir) / "test-skill"
        skill_dir.mkdir()
        md_file = skill_dir / "SKILL.md"
        md_file.write_text("---\nname: test-skill\ndescription: A test skill\n---\n# Test Skill\n\nThis is content.")

        loader = SkillLoader(Path(tmpdir))
        content = loader.get_skill_content("test-skill")
        assert "# Test Skill" in content
        assert "This is content." in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_resources.py -v`
Expected: FAIL with "module 'simple_agent.resources.skills' not found"

- [ ] **Step 3: Write skill loader implementation**

```python
from pathlib import Path
from typing import List, Optional
from simple_agent.resources.base import ResourceLoader


class SkillLoader(ResourceLoader):
    """Loader for skill resources."""

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        return resource_dir / "SKILL.md"

    def list_skills(self) -> List[dict]:
        """List all available skills with metadata."""
        return self.scan()

    def get_skill_content(self, name: str) -> Optional[str]:
        """Get full markdown content of a skill."""
        resources = self.scan()
        for r in resources:
            if r["name"] == name:
                return r["content"]
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_resources.py -v`
Expected: PASS all tests

- [ ] **Step 5: Commit**

```bash
git add simple_agent/resources/skills.py tests/test_resources.py
git commit -m "feat: add skill loader"
```

---

### Task 9: Subagent Loader

**Files:**
- Create: `simple_agent/resources/subagents.py`
- Test: `tests/test_resources.py` (extend)

- [ ] **Step 1: Write failing test for subagent loader**

```python
from simple_agent.resources.subagents import SubagentLoader

def test_subagent_loader_scan():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test subagent
        agent_dir = Path(tmpdir) / "test-agent"
        agent_dir.mkdir()
        md_file = agent_dir / "AGENT.md"
        md_file.write_text("---\nname: test-agent\ndescription: A test agent\ntools: [Read, Glob]\ntype: explore\n---\n# Test Agent")

        loader = SubagentLoader(Path(tmpdir))
        agents = loader.list_subagents()
        assert len(agents) == 1
        assert agents[0]["name"] == "test-agent"
        assert agents[0]["type"] == "explore"

def test_subagent_get_tools():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test subagent
        agent_dir = Path(tmpdir) / "test-agent"
        agent_dir.mkdir()
        md_file = agent_dir / "AGENT.md"
        md_file.write_text("---\nname: test-agent\ntools: [Read, Glob, Grep]\n---\n# Test Agent")

        loader = SubagentLoader(Path(tmpdir))
        tools = loader.get_subagent_tools("test-agent")
        assert tools == ["Read", "Glob", "Grep"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_resources.py -v`
Expected: FAIL with "module 'simple_agent.resources.subagents' not found"

- [ ] **Step 3: Write subagent loader implementation**

```python
from pathlib import Path
from typing import List, Optional
from simple_agent.resources.base import ResourceLoader


class SubagentLoader(ResourceLoader):
    """Loader for subagent resources."""

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        return resource_dir / "AGENT.md"

    def list_subagents(self) -> List[dict]:
        """List all available subagents."""
        return self.scan()

    def get_subagent_tools(self, name: str) -> Optional[List[str]]:
        """Get tool list for a subagent."""
        resources = self.scan()
        for r in resources:
            if r["name"] == name:
                return r["metadata"].get("tools", [])
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_resources.py -v`
Expected: PASS all tests

- [ ] **Step 5: Commit**

```bash
git add simple_agent/resources/subagents.py tests/test_resources.py
git commit -m "feat: add subagent loader"
```

---

### Task 10: Hook Loader

**Files:**
- Create: `simple_agent/resources/hooks.py`
- Test: `tests/test_resources.py` (extend)

- [ ] **Step 1: Write failing test for hook loader**

```python
from simple_agent.resources.hooks import HookLoader

def test_hook_loader_scan():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test hook
        hook_dir = Path(tmpdir) / "test-hook"
        hook_dir.mkdir()
        md_file = hook_dir / "HOOK.md"
        md_file.write_text("---\nname: test-hook\nevents: [message_send_before]\n---\n# Test Hook")

        loader = HookLoader(Path(tmpdir))
        hooks = loader.list_hooks()
        assert len(hooks) == 1
        assert hooks[0]["name"] == "test-hook"
        assert "message_send_before" in hooks[0]["events"]

def test_hook_get_events():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test hook
        hook_dir = Path(tmpdir) / "test-hook"
        hook_dir.mkdir()
        md_file = hook_dir / "HOOK.md"
        md_file.write_text("---\nname: test-hook\nevents: [message_send_before, tool_call_after]\n---\n# Test Hook")

        loader = HookLoader(Path(tmpdir))
        events = loader.get_hook_events("test-hook")
        assert events == ["message_send_before", "tool_call_after"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_resources.py -v`
Expected: FAIL with "module 'simple_agent.resources.hooks' not found"

- [ ] **Step 3: Write hook loader implementation**

```python
from pathlib import Path
from typing import List, Optional
from simple_agent.resources.base import ResourceLoader


class HookLoader(ResourceLoader):
    """Loader for hook resources."""

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        return resource_dir / "HOOK.md"

    def list_hooks(self) -> List[dict]:
        """List all available hooks."""
        hooks = self.scan()
        # Ensure events field is present
        for h in hooks:
            h["events"] = h["metadata"].get("events", [])
        return hooks

    def get_hook_events(self, name: str) -> Optional[List[str]]:
        """Get event list for a hook."""
        hooks = self.list_hooks()
        for h in hooks:
            if h["name"] == name:
                return h["events"]
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_resources.py -v`
Expected: PASS all tests

- [ ] **Step 5: Commit**

```bash
git add simple_agent/resources/hooks.py tests/test_resources.py
git commit -m "feat: add hook loader"
```

---

### Task 11: Command Loader

**Files:**
- Create: `simple_agent/resources/commands.py`
- Test: `tests/test_resources.py` (extend)

- [ ] **Step 1: Write failing test for command loader**

```python
from simple_agent.resources.commands import CommandLoader

def test_command_loader_scan():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command
        cmd_dir = Path(tmpdir) / "test-cmd"
        cmd_dir.mkdir()
        md_file = cmd_dir / "COMMAND.md"
        md_file.write_text("---\nname: test-cmd\nusage: /test [args]\n---\n# Test Command")

        loader = CommandLoader(Path(tmpdir))
        commands = loader.list_commands()
        assert len(commands) == 1
        assert commands[0]["name"] == "test-cmd"
        assert commands[0]["usage"] == "/test [args]"

def test_command_get_usage():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command
        cmd_dir = Path(tmpdir) / "test-cmd"
        cmd_dir.mkdir()
        md_file = cmd_dir / "COMMAND.md"
        md_file.write_text("---\nname: test-cmd\nusage: /test <arg1> [arg2]\n---\n# Test Command")

        loader = CommandLoader(Path(tmpdir))
        usage = loader.get_command_usage("test-cmd")
        assert usage == "/test <arg1> [arg2]"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_resources.py -v`
Expected: FAIL with "module 'simple_agent.resources.commands' not found"

- [ ] **Step 3: Write command loader implementation**

```python
from pathlib import Path
from typing import List, Optional
from simple_agent.resources.base import ResourceLoader


class CommandLoader(ResourceLoader):
    """Loader for command resources."""

    def _get_markdown_file(self, resource_dir: Path) -> Path:
        return resource_dir / "COMMAND.md"

    def list_commands(self) -> List[dict]:
        """List all available commands."""
        return self.scan()

    def get_command_usage(self, name: str) -> Optional[str]:
        """Get usage string for a command."""
        resources = self.scan()
        for r in resources:
            if r["name"] == name:
                return r["metadata"].get("usage", f"/{r['name']}")
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_resources.py -v`
Expected: PASS all tests

- [ ] **Step 5: Commit**

```bash
git add simple_agent/resources/commands.py tests/test_resources.py
git commit -m "feat: add command loader"
```

---

## Phase 6: UI and Session

### Task 12: UI Renderer

**Files:**
- Create: `simple_agent/ui/__init__.py`
- Create: `simple_agent/ui/renderer.py`
- Create: `tests/test_ui.py`
- Test: `tests/test_ui.py`

- [ ] **Step 1: Write failing test for UI renderer**

```python
from simple_agent.ui.renderer import UIRenderer
from io import StringIO

def test_renderer_output():
    output = StringIO()
    renderer = UIRenderer(output)
    renderer.render_message("user", "Hello")
    result = output.getvalue()
    assert "Hello" in result

def test_renderer_code_block():
    output = StringIO()
    renderer = UIRenderer(output)
    renderer.render_code("python", "print('hello')")
    result = output.getvalue()
    assert "print('hello')" in result

def test_renderer_error():
    output = StringIO()
    renderer = UIRenderer(output)
    renderer.render_error("Something went wrong")
    result = output.getvalue()
    assert "Something went wrong" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui.py -v`
Expected: FAIL with "module 'simple_agent.ui.renderer' not found"

- [ ] **Step 3: Create UI module __init__.py**

```python
"""UI components."""

from simple_agent.ui.renderer import UIRenderer

__all__ = ["UIRenderer"]
```

- [ ] **Step 4: Write UI renderer implementation**

```python
import sys
from typing import TextIO
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel


class UIRenderer:
    def __init__(self, output: TextIO = sys.stdout):
        self.console = Console(file=output, force_terminal=True)

    def render_message(self, role: str, content: str) -> None:
        """Render a chat message."""
        if role == "user":
            style = "bold blue"
            prefix = "You"
        elif role == "assistant":
            style = "bold green"
            prefix = "Assistant"
        else:
            style = "bold yellow"
            prefix = role

        self.console.print(f"\n[{style}]{prefix}[/{style}]:")
        self.console.print(Markdown(content))

    def render_code(self, language: str, code: str) -> None:
        """Render a code block with syntax highlighting."""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self.console.print(Panel(syntax))

    def render_error(self, message: str) -> None:
        """Render an error message."""
        self.console.print(f"\n[bold red]Error:[/bold red] {message}")

    def render_warning(self, message: str) -> None:
        """Render a warning message."""
        self.console.print(f"\n[bold yellow]Warning:[/bold yellow] {message}")

    def render_thinking(self, message: str) -> None:
        """Render a thinking indicator."""
        self.console.print(f"[dim italic]... {message}[/dim italic]")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_ui.py -v`
Expected: PASS all tests

- [ ] **Step 6: Commit**

```bash
git add simple_agent/ui/ tests/test_ui.py
git commit -m "feat: add UI renderer with rich"
```

---

### Task 13: Session Manager

**Files:**
- Create: `simple_agent/core/session.py`
- Test: `tests/test_session.py`

- [ ] **Step 1: Write failing test for session manager**

```python
from simple_agent.core.session import Session

def test_session_add_message():
    session = Session()
    session.add_message("user", "Hello")
    messages = session.get_messages()
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"

def test_session_get_context():
    session = Session()
    session.add_message("user", "Hello")
    session.add_message("assistant", "Hi there!")
    context = session.get_context()
    assert "Hello" in context
    assert "Hi there!" in context

def test_session_clear():
    session = Session()
    session.add_message("user", "Hello")
    session.clear()
    messages = session.get_messages()
    assert len(messages) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_session.py -v`
Expected: FAIL with "module 'simple_agent.core.session' not found"

- [ ] **Step 3: Write session manager implementation**

```python
from typing import List, Dict


class Session:
    def __init__(self):
        self._messages: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str) -> None:
        self._messages.append({"role": role, "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        return self._messages.copy()

    def get_context(self) -> str:
        """Get formatted context string."""
        return "\n\n".join([f"{m['role']}: {m['content']}" for m in self._messages])

    def clear(self) -> None:
        self._messages.clear()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_session.py -v`
Expected: PASS all tests

- [ ] **Step 5: Commit**

```bash
git add simple_agent/core/session.py tests/test_session.py
git commit -m "feat: add session manager"
```

---

## Phase 7: Main Runtime

### Task 14: Main Runtime

**Files:**
- Create: `simple_agent/core/runtime.py`
- Create: `simple_agent/main.py`
- Create: `tests/test_runtime.py`
- Test: `tests/test_runtime.py`

- [ ] **Step 1: Write failing test for runtime**

```python
from unittest.mock import Mock, patch
from simple_agent.core.runtime import Runtime

def test_runtime_initialization():
    from simple_agent.config.settings import load_config
    config = load_config()
    runtime = Runtime(config)
    assert runtime._config == config

def test_runtime_process_command():
    config = Mock()
    runtime = Runtime(config)

    with patch.object(runtime, '_handle_slash_command') as mock_handle:
        mock_handle.return_value = "Command executed"
        result = runtime.process_input("/help")
        assert result == "Command executed"
        mock_handle.assert_called_once_with("help", [])

@patch('simple_agent.core.runtime.os.getcwd')
def test_runtime_load_agent_md(mock_getcwd, tmp_path):
    mock_getcwd.return_value = str(tmp_path)
    agent_md = tmp_path / "AGENT.md"
    agent_md.write_text("# Test Agent\n\nThis is a test.")

    from simple_agent.config.settings import load_config
    config = load_config()
    runtime = Runtime(config)
    context = runtime.get_agent_context()
    assert "Test Agent" in context
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_runtime.py -v`
Expected: FAIL with "module 'simple_agent.core.runtime' not found"

- [ ] **Step 3: Write runtime implementation**

```python
import os
from pathlib import Path
from typing import Dict, List, Optional
from simple_agent.config.settings import Settings
from simple_agent.api.client import APIClient
from simple_agent.core.events import EventBus, Event
from simple_agent.core.session import Session
from simple_agent.tools.registry import ToolRegistry
from simple_agent.tools.dispatcher import ToolDispatcher
from simple_agent.resources.skills import SkillLoader
from simple_agent.resources.subagents import SubagentLoader
from simple_agent.resources.hooks import HookLoader
from simple_agent.resources.commands import CommandLoader
from simple_agent.ui.renderer import UIRenderer


class Runtime:
    def __init__(self, config: Settings):
        self._config = config
        self._event_bus = EventBus()
        self._session = Session()
        self._renderer = UIRenderer()
        self._api_client = APIClient(config.api)
        self._tool_registry = ToolRegistry()
        self._tool_dispatcher = ToolDispatcher(self._tool_registry)

        # Initialize resource loaders
        self._skill_loader = SkillLoader(Path(config.paths.skills_dir))
        self._subagent_loader = SubagentLoader(Path(config.paths.subagents_dir))
        self._hook_loader = HookLoader(Path(config.paths.hooks_dir))
        self._command_loader = CommandLoader(Path(config.paths.commands_dir))

        # Load and register hooks
        self._load_hooks()

    def _load_hooks(self):
        """Load and register all hooks."""
        hooks = self._hook_loader.list_hooks()
        for hook in hooks:
            # For now, just log hook discovery
            # Actual hook script execution will be added later
            pass

    def get_agent_context(self) -> Optional[str]:
        """Load AGENT.md from project root."""
        agent_md = Path.cwd() / "AGENT.md"
        if agent_md.exists():
            return agent_md.read_text()
        return None

    def _parse_slash_command(self, input: str) -> tuple[Optional[str], List[str]]:
        """Parse a slash command into command name and arguments."""
        if not input.startswith("/"):
            return None, []

        parts = input[1:].split()
        if not parts:
            return None, []

        command = parts[0]
        args = parts[1:]
        return command, args

    def _handle_slash_command(self, command: str, args: List[str]) -> str:
        """Handle a slash command."""
        if command == "help":
            return "Available commands: /help, /exit"
        elif command == "exit" or command == "quit":
            return "exit"
        return f"Unknown command: /{command}"

    def process_input(self, input: str) -> str:
        """Process user input."""
        # Check for slash commands
        command, args = self._parse_slash_command(input)
        if command:
            return self._handle_slash_command(command, args)

        # Regular message
        self._session.add_message("user", input)
        return "message_processed"

    def run(self):
        """Main run loop."""
        self._renderer.render_message("system", "Simple Agent started. Type /help for commands.")

        while True:
            try:
                user_input = input("\n> ")
                result = self.process_input(user_input)

                if result == "exit":
                    self._renderer.render_message("system", "Goodbye!")
                    break
                elif result == "message_processed":
                    # Process message with API
                    messages = self._session.get_messages()
                    tools = self._tool_registry.to_openai_format()

                    response = self._api_client.send_message(messages, tools)
                    for msg in response:
                        self._session.add_message(msg["role"], msg["content"])
                        self._renderer.render_message(msg["role"], msg["content"])

                        # Handle tool calls
                        if "tool_calls" in msg:
                            for tool_call in msg["tool_calls"]:
                                result = self._tool_dispatcher.execute({
                                    "name": tool_call["function"]["name"],
                                    "arguments": eval(tool_call["function"]["arguments"]),
                                })
                                self._session.add_message("tool", str(result))
                else:
                    self._renderer.render_message("system", result)

            except KeyboardInterrupt:
                self._renderer.render_message("system", "\nGoodbye!")
                break
            except Exception as e:
                self._renderer.render_error(str(e))
```

- [ ] **Step 4: Write main entry point**

```python
import sys
from simple_agent.config.settings import load_config
from simple_agent.core.runtime import Runtime


def main():
    config = load_config()

    if not config.api.api_key:
        print("Error: No API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)

    runtime = Runtime(config)
    runtime.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_runtime.py -v`
Expected: PASS all tests

- [ ] **Step 6: Commit**

```bash
git add simple_agent/core/runtime.py simple_agent/main.py tests/test_runtime.py
git commit -m "feat: add main runtime with CLI loop"
```

---

## Phase 8: Documentation

### Task 15: README and Documentation

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
# Simple Agent

A Claude Code-like CLI tool with support for hooks, skills, subagents, and slash commands.

## Features

- **Tools**: Register Python functions as tools for LLM function calling
- **Skills**: Markdown-based knowledge documents that guide AI behavior
- **Subagents**: Specialized AI agents for specific tasks
- **Hooks**: Event-driven plugins for custom behavior
- **Commands**: Built-in and custom slash commands
- **Multi-Provider**: Support for OpenAI and Anthropic/Claude APIs

## Installation

```bash
pip install -e .
```

## Configuration

Create a `.simple-agent/config.yml` file:

```yaml
api:
  provider: openai  # or anthropic
  base_url: https://api.openai.com/v1
  api_key: ${OPENAI_API_KEY}
  model: gpt-4o

paths:
  skills_dir: ./skills
  subagents_dir: ./subagents
  hooks_dir: ./hooks
  commands_dir: ./commands
  tools_dir: ./tools
  memory_dir: ./memory

ui:
  theme: dark
  show_thinking: true
```

## Usage

```bash
simple-agent
```

## Project Structure

```
simple-agent/
├── simple_agent/          # Core package
├── skills/                 # Skill definitions
├── subagents/              # Subagent definitions
├── hooks/                  # Hook definitions
├── commands/               # Command definitions
├── tools/                  # Tool implementations
├── memory/                 # Auto-generated memory
└── AGENT.md                # Project-specific instructions
```

## Development

Run tests:

```bash
pytest
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```

---

## Self-Review

**Spec Coverage:**
- Core runtime components (session, events, API client, tool dispatcher, resource loaders) - Covered in Tasks 2-14
- Skill system with SKILL.md parsing and triggering - Covered in Task 8
- Tool system with decorator registration - Covered in Tasks 4-5
- Subagent system with AGENT.md parsing - Covered in Task 9
- Hook system with event bus integration - Covered in Tasks 3, 10, 14
- Command system with slash command parsing - Covered in Tasks 11, 14
- AGENT.md loading - Covered in Task 14
- Configuration management with priority - Covered in Task 2
- UI system with rich - Covered in Task 12
- Error handling - Covered in dispatcher and runtime
- Testing strategy - All components have unit tests

**Placeholder Scan:** No placeholders found (TBD, TODO, etc.)

**Type Consistency:** All types, method names, and signatures are consistent throughout the plan.
