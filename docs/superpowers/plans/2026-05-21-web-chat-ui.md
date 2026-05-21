# Web 聊天 UI 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 simple-agent 增加浏览器内的交互式聊天界面，复用现有 Runtime/Session/工具系统，通过 OutputSink 接口解耦 UI 与核心逻辑。

**Architecture:** 引入 `OutputSink` 协议，把 Runtime 中对 `UIRenderer` 和 `console.print` 的调用收敛到 sink。`CliSink` 包装现有 UIRenderer 保持 CLI 行为不变；`WebTurnSink` 把事件序列化到 list。Web 后端用 Flask 暴露 `/api/turn` 接口，同步执行一轮对话后一次性返回事件列表；前端是无构建步骤的原生 JS 单页应用。

**Tech Stack:** Python 3.11+、Flask（新增依赖）、原生 JS、marked.js（CDN）、highlight.js（CDN）、pytest。

**Spec:** `docs/superpowers/specs/2026-05-21-web-chat-ui-design.md`

---

## 文件清单

### 新增

| 文件 | 责任 |
|------|------|
| `simple_agent/core/sinks.py` | 定义 `OutputSink` 协议、`CliSink`、`WebTurnSink`，~150 行 |
| `simple_agent/web/chat_server.py` | Flask 应用 + 7 个路由 + 单例 Runtime/Sink 状态 + init 函数，~200 行 |
| `simple_agent/web/static/chat.html` | 单页应用骨架 + CDN 引用 |
| `simple_agent/web/static/chat.css` | 暗色主题、布局、气泡、工具卡片 |
| `simple_agent/web/static/chat.js` | 前端逻辑：初始化、发送、事件渲染、侧边栏、resume |
| `tests/test_sinks.py` | 测试 CliSink / WebTurnSink |
| `tests/test_web_chat.py` | 测试 chat_server 路由 |
| `tests/test_runtime_turn.py` | 测试 Runtime 抽出的 `init_session` 和 `_run_one_turn` |

### 修改

| 文件 | 修改点 |
|------|--------|
| `pyproject.toml` | dependencies 列表加 `flask>=3.0.0`、`flask-cors>=4.0.0` |
| `simple_agent/core/runtime.py` | (1) 构造函数加 `sink` 参数；(2) 工具调用/最终响应处的 `_renderer` 调用替换为 sink 调用；(3) 抽出 `init_session()` 和 `_run_one_turn()` 方法 |
| `simple_agent/main.py` | 加 `--web-chat` 命令行参数与 `run_chat_server()` 函数 |
| `README.md` | 增加 "Web 聊天 UI" 章节 |
| `CLAUDE.md` | 开发命令章节加 `simple-agent --web-chat` |

### 不修改

- `simple_agent/web/server.py` 和 `analyzer.html`（现有只读日志分析器，与本项目无关，保持不动）
- `simple_agent/ui/renderer.py`（CliSink 包装它即可，不改它本身）
- `simple_agent/core/session.py` / `events.py` / `llm_logger.py`（无需改动）

---

## Task 1: 加 Flask 依赖

**Files:**
- Modify: `pyproject.toml:11-18`

- [ ] **Step 1: 修改 pyproject.toml 加依赖**

把 dependencies 列表改为：

```toml
dependencies = [
    "openai>=1.0.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "rich>=13.0.0",
    "python-frontmatter>=1.0.0",
    "prompt-toolkit>=3.0.0",
    "flask>=3.0.0",
    "flask-cors>=4.0.0",
]
```

- [ ] **Step 2: 安装依赖**

Run: `pip install -e .`
Expected: 安装成功，Flask 和 flask-cors 被装上

- [ ] **Step 3: 验证现有 pytest 通过**

Run: `pytest`
Expected: 所有现有测试通过（基线确认）

- [ ] **Step 4: 提交**

```bash
git add pyproject.toml
git commit -m "feat: 添加 Flask 依赖以支持 Web 聊天 UI"
```

---

## Task 2: 定义 OutputSink 协议与 CliSink

**Files:**
- Create: `simple_agent/core/sinks.py`
- Create: `tests/test_sinks.py`

- [ ] **Step 1: 写失败测试 - CliSink 调用 UIRenderer**

创建 `tests/test_sinks.py`：

```python
from unittest.mock import MagicMock
from simple_agent.core.sinks import CliSink, WebTurnSink


def test_cli_sink_on_message_calls_renderer():
    renderer = MagicMock()
    sink = CliSink(renderer)

    sink.on_message("assistant", "hello")

    renderer.render_message.assert_called_once_with("assistant", "hello")


def test_cli_sink_on_error_calls_renderer():
    renderer = MagicMock()
    sink = CliSink(renderer)

    sink.on_error("boom")

    renderer.render_error.assert_called_once_with("boom")


def test_cli_sink_on_tool_start_prints_inline():
    renderer = MagicMock()
    sink = CliSink(renderer)

    sink.on_tool_start("READ", {"path": "/tmp/x"}, "call_1")

    # 应该用 end="" 调用 console.print 显示工具名+参数
    args, kwargs = renderer.console.print.call_args
    assert "READ" in args[0]
    assert "path" in args[0]
    assert kwargs.get("end") == ""


def test_cli_sink_on_tool_end_prints_status_and_result():
    renderer = MagicMock()
    sink = CliSink(renderer)
    result = {"success": True, "stdout": "ok"}

    sink.on_tool_end("READ", {"path": "/tmp/x"}, "call_1", result, True)

    # 应该先 print 一个绿色 ✓，再 render_tool_result
    assert renderer.console.print.called
    renderer.render_tool_result.assert_called_once_with("READ", result, {"path": "/tmp/x"})


def test_cli_sink_on_tool_end_failure_prints_red_x():
    renderer = MagicMock()
    sink = CliSink(renderer)
    result = {"success": False, "error": "oops"}

    sink.on_tool_end("READ", {}, "call_1", result, False)

    # 找到那次 print 调用，验证含红 ✗
    printed = [str(c) for c in renderer.console.print.call_args_list]
    assert any("✗" in s for s in printed)


def test_cli_sink_turn_and_status_are_noops():
    renderer = MagicMock()
    sink = CliSink(renderer)

    sink.on_turn_start("hi")
    sink.on_turn_end()
    sink.on_status("skill_loaded", {"name": "x"})

    # 这些是 no-op，不应触发 renderer
    renderer.render_message.assert_not_called()
    renderer.render_error.assert_not_called()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_sinks.py -v`
Expected: FAIL，提示 `simple_agent.core.sinks` 模块不存在

- [ ] **Step 3: 实现 OutputSink 协议和 CliSink**

创建 `simple_agent/core/sinks.py`：

```python
"""OutputSink protocol and implementations for decoupling Runtime from UI."""
from typing import Protocol, runtime_checkable
from simple_agent.ui.renderer import UIRenderer


@runtime_checkable
class OutputSink(Protocol):
    """Abstract output channel for Runtime - implemented by CLI and Web."""

    def on_message(self, role: str, content: str) -> None: ...
    def on_error(self, message: str) -> None: ...
    def on_tool_start(self, tool_name: str, arguments: dict, call_id: str) -> None: ...
    def on_tool_end(
        self, tool_name: str, arguments: dict, call_id: str,
        result: dict, success: bool,
    ) -> None: ...
    def on_turn_start(self, user_input: str) -> None: ...
    def on_turn_end(self) -> None: ...
    def on_status(self, kind: str, data: dict) -> None: ...


def _format_tool_args(arguments: dict) -> str:
    """Format arguments dict as compact bracket string for inline display."""
    if not arguments or not isinstance(arguments, dict):
        return ""
    no_truncate_keys = {"command"}
    skip_keys = {"cwd", "timeout", "case_sensitive", "description", "metadata"}
    priority_keys = ["subject", "command", "path", "task_id", "query", "skill_name", "agent_name"]
    parts = []
    shown = set()
    for k in priority_keys:
        if k in arguments and k not in skip_keys:
            v = str(arguments[k])
            if k not in no_truncate_keys and len(v) > 30:
                v = v[:29] + "…"
            parts.append(f"{k}={v}")
            shown.add(k)
    for k, v in arguments.items():
        if k in shown or k in skip_keys:
            continue
        if len(parts) >= 4:
            parts.append("…")
            break
        v = str(v)
        if len(v) > 20:
            v = v[:19] + "…"
        parts.append(f"{k}={v}")
    return f"[{', '.join(parts)}]" if parts else ""


class CliSink:
    """OutputSink implementation that wraps the existing UIRenderer for CLI mode."""

    def __init__(self, renderer: UIRenderer):
        self._renderer = renderer

    def on_message(self, role: str, content: str) -> None:
        self._renderer.render_message(role, content)

    def on_error(self, message: str) -> None:
        self._renderer.render_error(message)

    def on_tool_start(self, tool_name: str, arguments: dict, call_id: str) -> None:
        from rich.markup import escape
        args_str = _format_tool_args(arguments)
        if args_str:
            self._renderer.console.print(f"{tool_name} {escape(args_str)}", end="")
        else:
            self._renderer.console.print(f"{tool_name}", end="")

    def on_tool_end(
        self, tool_name: str, arguments: dict, call_id: str,
        result: dict, success: bool,
    ) -> None:
        status = "[bold green]✓[/bold green]" if success else "[bold red]✗[/bold red]"
        self._renderer.console.print(f" {status}")
        self._renderer.render_tool_result(tool_name, result, arguments)

    def on_turn_start(self, user_input: str) -> None:
        pass  # CLI 不需要这个事件

    def on_turn_end(self) -> None:
        pass

    def on_status(self, kind: str, data: dict) -> None:
        pass


class WebTurnSink:
    """OutputSink implementation that accumulates events into a list for HTTP return."""

    def __init__(self):
        self.events: list[dict] = []

    def on_message(self, role: str, content: str) -> None:
        self.events.append({"type": "message", "role": role, "content": content})

    def on_error(self, message: str) -> None:
        self.events.append({"type": "error", "message": message})

    def on_tool_start(self, tool_name: str, arguments: dict, call_id: str) -> None:
        self.events.append({
            "type": "tool_start",
            "tool_name": tool_name,
            "arguments": arguments,
            "call_id": call_id,
        })

    def on_tool_end(
        self, tool_name: str, arguments: dict, call_id: str,
        result: dict, success: bool,
    ) -> None:
        self.events.append({
            "type": "tool_end",
            "tool_name": tool_name,
            "arguments": arguments,
            "call_id": call_id,
            "result": result,
            "success": success,
        })

    def on_turn_start(self, user_input: str) -> None:
        self.events.append({"type": "turn_start", "user_input": user_input})

    def on_turn_end(self) -> None:
        self.events.append({"type": "turn_end"})

    def on_status(self, kind: str, data: dict) -> None:
        self.events.append({"type": "status", "kind": kind, "data": data})
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_sinks.py -v`
Expected: 6 个 CliSink 测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add simple_agent/core/sinks.py tests/test_sinks.py
git commit -m "feat: 新增 OutputSink 协议与 CliSink 实现

CliSink 包装 UIRenderer 保持 CLI 输出行为不变，为后续 Web 端解耦做准备。"
```

---

## Task 3: 测试 WebTurnSink

**Files:**
- Modify: `tests/test_sinks.py`（追加）

- [ ] **Step 1: 追加 WebTurnSink 测试**

在 `tests/test_sinks.py` 末尾追加：

```python
def test_web_sink_on_message_appends_event():
    sink = WebTurnSink()

    sink.on_message("assistant", "hello")

    assert sink.events == [
        {"type": "message", "role": "assistant", "content": "hello"}
    ]


def test_web_sink_on_error_appends_event():
    sink = WebTurnSink()

    sink.on_error("boom")

    assert sink.events == [{"type": "error", "message": "boom"}]


def test_web_sink_tool_start_and_end():
    sink = WebTurnSink()

    sink.on_tool_start("READ", {"path": "/x"}, "c1")
    sink.on_tool_end("READ", {"path": "/x"}, "c1", {"success": True, "stdout": "ok"}, True)

    assert len(sink.events) == 2
    assert sink.events[0] == {
        "type": "tool_start",
        "tool_name": "READ",
        "arguments": {"path": "/x"},
        "call_id": "c1",
    }
    assert sink.events[1] == {
        "type": "tool_end",
        "tool_name": "READ",
        "arguments": {"path": "/x"},
        "call_id": "c1",
        "result": {"success": True, "stdout": "ok"},
        "success": True,
    }


def test_web_sink_turn_start_end():
    sink = WebTurnSink()

    sink.on_turn_start("hi")
    sink.on_turn_end()

    assert sink.events == [
        {"type": "turn_start", "user_input": "hi"},
        {"type": "turn_end"},
    ]


def test_web_sink_status_event():
    sink = WebTurnSink()

    sink.on_status("skill_loaded", {"name": "brainstorming"})

    assert sink.events == [
        {"type": "status", "kind": "skill_loaded", "data": {"name": "brainstorming"}}
    ]


def test_web_sink_events_can_be_cleared():
    sink = WebTurnSink()
    sink.on_message("assistant", "first")
    sink.events.clear()
    sink.on_message("assistant", "second")

    assert sink.events == [
        {"type": "message", "role": "assistant", "content": "second"}
    ]
```

- [ ] **Step 2: 运行测试验证通过**

Run: `pytest tests/test_sinks.py -v`
Expected: 全部 12 个测试 PASS（CliSink 6 个 + WebTurnSink 6 个）

- [ ] **Step 3: 提交**

```bash
git add tests/test_sinks.py
git commit -m "test: 补充 WebTurnSink 单元测试"
```

---

## Task 4: 抽出 Runtime.init_session()

**Files:**
- Modify: `simple_agent/core/runtime.py:1334-1376`
- Create: `tests/test_runtime_turn.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_runtime_turn.py`：

```python
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from simple_agent.core.runtime import Runtime
from simple_agent.config.settings import Settings


def test_init_session_sets_session_id():
    """init_session() 应该生成 session_id 并发布 SessionStart 事件。"""
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            config = Settings()
            runtime = Runtime(config, skip_api_init=True)

            assert runtime._session_id is None
            runtime.init_session()
            assert runtime._session_id is not None
            assert len(runtime._session_id) > 0
    finally:
        os.chdir(old_cwd)


def test_init_session_publishes_session_start_event():
    """init_session() 应该发布 SessionStart 事件。"""
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            config = Settings()
            runtime = Runtime(config, skip_api_init=True)

            received_events = []
            runtime._event_bus.subscribe(
                "SessionStart",
                lambda e: received_events.append(e),
            )

            runtime.init_session()

            assert len(received_events) == 1
            assert received_events[0].data.get("context") == "startup"
            assert received_events[0].data.get("session_id") == runtime._session_id
    finally:
        os.chdir(old_cwd)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_runtime_turn.py -v`
Expected: FAIL，提示 `Runtime` 没有 `init_session` 方法

- [ ] **Step 3: 在 Runtime 上实现 init_session()**

在 `simple_agent/core/runtime.py` 的 `run()` 方法**之前**插入新方法（约在第 1334 行前）：

```python
    def init_session(self) -> None:
        """Initialize a session: restore loaded skills/agents, generate session_id,
        reset HookContext, log session start, publish SessionStart event.

        Shared by both CLI run() and the Web entrypoint.
        """
        import uuid

        # Restore loaded skills/agents from session (if resuming)
        loaded_skills = self._session.get_loaded_skills()
        loaded_agents = self._session.get_loaded_agents()
        if loaded_skills:
            self._loaded_skills.update(loaded_skills)
        if loaded_agents:
            self._loaded_agents.update(loaded_agents)

        # Generate session ID and log session start
        self._session_id = str(uuid.uuid4())
        self._hook_context.reset(self._session_id)
        if self._logger:
            self._logger.log_session_start(self._session_id)

        # Publish SessionStart event
        if _is_hook_debug():
            sys.stderr.write(f"[DEBUG] Publishing SessionStart event\n")
        self._event_bus.publish(Event("SessionStart", {
            "session_id": self._session_id,
            "context": "startup",
        }))
```

然后修改 `run()` 方法开头（约 1336-1358 行），删除被搬走的代码，改为调用 `self.init_session()`：

```python
    def run(self):
        """Main run loop."""
        self.init_session()

        self._renderer.render_message("system", "Simple Agent started. Type /help for commands.")
        # ... 后面保留：show available skills/agents/banner、while True 循环
```

注意：原来 1336-1358 行的内容（restore loaded skills、生成 uuid、reset HookContext、log_session_start、publish SessionStart 事件）全部移到 `init_session()`。`run()` 中保留从 "self._renderer.render_message('system', 'Simple Agent started...')" 开始的代码。

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_runtime_turn.py -v`
Expected: 2 个测试 PASS

- [ ] **Step 5: 跑全量测试确认 CLI 行为没变**

Run: `pytest`
Expected: 全部通过

- [ ] **Step 6: 提交**

```bash
git add simple_agent/core/runtime.py tests/test_runtime_turn.py
git commit -m "refactor: 抽出 Runtime.init_session() 方法

将会话初始化逻辑（生成 session_id、发布 SessionStart 事件、加载已加载的 skills/agents）从 run() 中提取出来，为 Web 入口复用做准备。"
```

---

## Task 5: 抽出 Runtime._run_one_turn()

**Files:**
- Modify: `simple_agent/core/runtime.py:1397-1419` (while 循环内 "调 API + 处理响应" 部分)
- Modify: `tests/test_runtime_turn.py`（追加）

- [ ] **Step 1: 追加失败测试**

在 `tests/test_runtime_turn.py` 末尾追加：

```python
def test_run_one_turn_calls_api_and_renders_response():
    """_run_one_turn() 应该调 API，处理纯文本响应并 render。"""
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            config = Settings()
            runtime = Runtime(config, skip_api_init=True)
            runtime.init_session()

            # Mock api_client - 返回一条无 tool_calls 的简单响应
            runtime._api_client = MagicMock()
            runtime._api_client.send_message.return_value = [
                {"role": "assistant", "content": "Hello, world!"}
            ]

            # Mock renderer 以验证调用
            runtime._renderer = MagicMock()
            runtime._renderer.console = MagicMock()

            # 用户输入已通过 process_input 加入 session
            runtime._session.add_message("user", "hi")
            runtime._run_one_turn()

            # 验证 send_message 被调用
            runtime._api_client.send_message.assert_called_once()
            # 验证响应被加入 session
            messages = runtime._session.get_messages()
            assert messages[-1]["role"] == "assistant"
            assert messages[-1]["content"] == "Hello, world!"
            # 验证 renderer 收到了响应
            runtime._renderer.render_message.assert_any_call("assistant", "Hello, world!")
    finally:
        os.chdir(old_cwd)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_runtime_turn.py::test_run_one_turn_calls_api_and_renders_response -v`
Expected: FAIL，提示 `_run_one_turn` 方法不存在

- [ ] **Step 3: 实现 _run_one_turn()**

在 `simple_agent/core/runtime.py` 中，紧跟 `init_session()` 之后插入：

```python
    def _run_one_turn(self) -> None:
        """Send current session messages to API and process the response.

        Handles tool_calls recursively (delegated to _handle_tool_calls_in_message).
        For a plain-text response, adds it to session and renders.

        Shared by both CLI run() loop and Web /api/turn handler.
        """
        messages = self._prepare_messages_with_context()
        allowed_tools = self._get_allowed_tools()
        tools = self._tool_registry.to_openai_format(allowed_tools)

        response = self._api_client.send_message(messages, tools)
        for msg in response:
            # Handle tool calls
            if "tool_calls" in msg and msg["tool_calls"]:
                self._handle_tool_calls_in_message(msg, response)
            else:
                content = msg.get("content", "")
                self._session.add_message(msg["role"], content)
                try:
                    self._renderer.render_message(msg["role"], content)
                except Exception as e:
                    self._renderer.render_error(f"Failed to render message: {str(e)}")
                    plain_content = content[:500] if content else ""
                    print(f"\n{msg['role']}: {plain_content}")
```

然后修改 `run()` 中 while 循环里 `elif result == "message_processed" or result == "command_processed":` 分支（原 1397-1419 行），替换整段为：

```python
                elif result == "message_processed" or result == "command_processed":
                    self._run_one_turn()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_runtime_turn.py -v`
Expected: 3 个测试全部 PASS

- [ ] **Step 5: 跑全量测试**

Run: `pytest`
Expected: 全部通过

- [ ] **Step 6: 提交**

```bash
git add simple_agent/core/runtime.py tests/test_runtime_turn.py
git commit -m "refactor: 抽出 Runtime._run_one_turn() 方法

将单轮对话的执行逻辑（API 调用、tool_calls 处理、响应 render）从 run() 循环中提取出来，为 Web 入口复用做准备。"
```

---

## Task 6: Runtime 构造函数注入 sink

**Files:**
- Modify: `simple_agent/core/runtime.py:37-48` (构造函数)
- Modify: `tests/test_runtime_turn.py`（追加）

- [ ] **Step 1: 追加测试 - 默认 sink 是 CliSink**

在 `tests/test_runtime_turn.py` 末尾追加：

```python
def test_runtime_has_default_cli_sink():
    """Runtime 默认应当持有 CliSink 实例。"""
    from simple_agent.core.sinks import CliSink

    config = Settings()
    runtime = Runtime(config, skip_api_init=True)

    assert isinstance(runtime._sink, CliSink)


def test_runtime_accepts_custom_sink():
    """Runtime 应该接受注入的 sink。"""
    from simple_agent.core.sinks import WebTurnSink

    config = Settings()
    custom_sink = WebTurnSink()
    runtime = Runtime(config, skip_api_init=True, sink=custom_sink)

    assert runtime._sink is custom_sink
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_runtime_turn.py::test_runtime_has_default_cli_sink tests/test_runtime_turn.py::test_runtime_accepts_custom_sink -v`
Expected: FAIL，`Runtime` 没有 `_sink` 属性，也不接受 `sink` 参数

- [ ] **Step 3: 修改 Runtime 构造函数**

修改 `simple_agent/core/runtime.py:37` 行的 `__init__` 签名和前几行：

```python
    def __init__(
        self,
        config: Settings,
        log_file: Optional[str] = None,
        skip_api_init: bool = False,
        sink: Optional["OutputSink"] = None,
    ):
        self._config = config
        self._event_bus = EventBus()
        self._session = Session()
        self._renderer = UIRenderer()
        self._session_id: Optional[str] = None

        # Output sink: defaults to CliSink wrapping the renderer
        from simple_agent.core.sinks import CliSink, OutputSink
        self._sink: OutputSink = sink if sink is not None else CliSink(self._renderer)

        # ... 余下保持不变
```

在文件顶部 imports 区域可以选择性加 `from typing import TYPE_CHECKING` 并在 TYPE_CHECKING 内 import OutputSink，但延迟 import（如上）也可以避免循环依赖问题。

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_runtime_turn.py -v`
Expected: 5 个测试全部 PASS

- [ ] **Step 5: 跑全量测试**

Run: `pytest`
Expected: 全部通过

- [ ] **Step 6: 提交**

```bash
git add simple_agent/core/runtime.py tests/test_runtime_turn.py
git commit -m "feat: Runtime 构造函数支持注入 OutputSink

默认创建 CliSink 包装现有 UIRenderer，保持 CLI 行为不变。"
```

---

## Task 7: Runtime 工具调用走 sink

**Files:**
- Modify: `simple_agent/core/runtime.py:1161-1192` (工具开始/完成的打印)

- [ ] **Step 1: 写测试验证工具调用通过 sink**

在 `tests/test_runtime_turn.py` 末尾追加：

```python
def test_run_one_turn_routes_tool_calls_through_sink():
    """_run_one_turn() 在执行 tool_calls 时应触发 sink.on_tool_start / on_tool_end。"""
    from simple_agent.core.sinks import WebTurnSink

    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            config = Settings()
            sink = WebTurnSink()
            runtime = Runtime(config, skip_api_init=True, sink=sink)
            runtime.init_session()

            # Mock api_client：第一次返回 tool_calls，第二次返回最终消息
            runtime._api_client = MagicMock()
            runtime._api_client.send_message.side_effect = [
                [{
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {
                            "name": "Bash",
                            "arguments": '{"command": "echo hi"}',
                        },
                    }],
                }],
                [{"role": "assistant", "content": "Done"}],
            ]

            # Mock tool dispatcher
            runtime._tool_dispatcher = MagicMock()
            runtime._tool_dispatcher.execute.return_value = {
                "success": True,
                "stdout": "hi",
            }

            runtime._session.add_message("user", "run echo")
            runtime._run_one_turn()

            # 验证 sink 收到了 tool_start 和 tool_end 事件
            types = [e["type"] for e in sink.events]
            assert "tool_start" in types
            assert "tool_end" in types
            tool_start_event = next(e for e in sink.events if e["type"] == "tool_start")
            assert tool_start_event["tool_name"] == "Bash"
            assert tool_start_event["call_id"] == "call_1"
            tool_end_event = next(e for e in sink.events if e["type"] == "tool_end")
            assert tool_end_event["success"] is True
    finally:
        os.chdir(old_cwd)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_runtime_turn.py::test_run_one_turn_routes_tool_calls_through_sink -v`
Expected: FAIL，sink 收不到事件

- [ ] **Step 3: 修改 _handle_tool_calls_in_message 走 sink**

在 `simple_agent/core/runtime.py` 找到 `_handle_tool_calls_in_message` 方法，做三处替换：

**替换 1**（约 1161-1165 行 "Print tool name and args before execution"）：

```python
            # Notify sink of tool start
            self._sink.on_tool_start(tool_name, arguments, tool_call["id"])
```

删掉原来 `if args_str: console.print(...) else: console.print(...)` 那几行（CliSink 内部已经做了同样的事），同时 `args_str` 变量构造可以保留（_handle 后面还可能用到 args_parts），但不再用于这里的打印。

实际上 args_parts 在后面工具结果格式化时还有用（约 1204 行 "args_parts = []"），那一处保留。只删除第 1161-1165 行的"打印工具名行"。

**替换 2**（约 1186-1192 行 "Show completion status with checkmark"）：

```python
            # Notify sink of tool completion
            tool_result = result.get("result", result)
            success = tool_result.get("success", True)
            self._sink.on_tool_end(tool_name, arguments, tool_call["id"], result, success)
```

删除原来：
- `tool_result = result.get("result", result)`（保留在新代码里）
- `success = tool_result.get("success", True)`（保留）
- `status = "[bold green]✓[/bold green]"...`（CliSink 内部处理）
- `self._renderer.console.print(f" {status}")`（CliSink 内部处理）
- `self._renderer.render_tool_result(tool_name, result, arguments)`（CliSink 内部处理）

**替换 3**（约 1267-1271 行 "Final response with content"）：

```python
            else:
                # Final response with content
                self._session.add_message(next_msg["role"], next_msg.get("content", ""))
                content = next_msg.get("content", "")
                if not content:
                    content = "(工具执行完成，AI 无额外响应)"
                self._sink.on_message(next_msg["role"], content)
```

把最后一行的 `self._renderer.render_message(...)` 换成 `self._sink.on_message(...)`。

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_runtime_turn.py -v`
Expected: 6 个测试全部 PASS

- [ ] **Step 5: 跑全量测试**

Run: `pytest`
Expected: 全部通过

- [ ] **Step 6: 手动验证 CLI 输出不变**

Run: `simple-agent`（如果有 API key），输入 "请用 Bash 工具执行 ls"，确认终端仍然看到 `Bash [command=ls] ✓` 和工具结果。

如果没有 API key，跳过这步，依赖 pytest 即可。

- [ ] **Step 7: 提交**

```bash
git add simple_agent/core/runtime.py tests/test_runtime_turn.py
git commit -m "refactor: Runtime 工具调用与最终响应改为通过 OutputSink

CliSink 内部仍调用 UIRenderer，CLI 输出行为保持一致；为 Web 端注入 WebTurnSink 提供了接入点。"
```

---

## Task 8: Runtime turn 边界走 sink

**Files:**
- Modify: `simple_agent/core/runtime.py` `process_input` 方法 + `_run_one_turn` 方法

- [ ] **Step 1: 写测试验证 turn_start/turn_end**

追加到 `tests/test_runtime_turn.py`：

```python
def test_turn_start_and_end_events_are_emitted():
    """完整一轮对话应当发出 turn_start 和 turn_end 事件。"""
    from simple_agent.core.sinks import WebTurnSink

    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            config = Settings()
            sink = WebTurnSink()
            runtime = Runtime(config, skip_api_init=True, sink=sink)
            runtime.init_session()

            runtime._api_client = MagicMock()
            runtime._api_client.send_message.return_value = [
                {"role": "assistant", "content": "OK"}
            ]

            runtime.process_input("hello")
            runtime._run_one_turn()

            types = [e["type"] for e in sink.events]
            assert types[0] == "turn_start"
            assert types[-1] == "turn_end"
            assert sink.events[0]["user_input"] == "hello"
    finally:
        os.chdir(old_cwd)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_runtime_turn.py::test_turn_start_and_end_events_are_emitted -v`
Expected: FAIL

- [ ] **Step 3: 在 process_input 加 on_turn_start**

修改 `process_input` 方法（`simple_agent/core/runtime.py:1316` 附近）：

```python
    def process_input(self, input: str) -> str:
        """Process user input."""
        # Notify sink: turn is starting
        self._sink.on_turn_start(input)

        # Check for slash commands
        command, args = self._parse_slash_command(input)
        if command:
            return self._handle_slash_command(command, args)

        # ... 余下保持不变
```

- [ ] **Step 4: 在 _run_one_turn 末尾加 on_turn_end**

修改 `_run_one_turn` 方法末尾，加一行：

```python
            else:
                # ... 现有渲染逻辑

        # Turn finished
        self._sink.on_turn_end()
```

加在 for 循环之外、方法 return 之前。

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/test_runtime_turn.py -v`
Expected: 7 个测试全部 PASS

- [ ] **Step 6: 跑全量测试**

Run: `pytest`
Expected: 全部通过

- [ ] **Step 7: 提交**

```bash
git add simple_agent/core/runtime.py tests/test_runtime_turn.py
git commit -m "feat: Runtime 在 turn 边界发出 turn_start/turn_end 事件

CLI 中 CliSink 实现为 no-op 故行为不变；Web 端可以用这些事件作为流标记。"
```

---

## Task 9: chat_server 单例与 init_runtime

**Files:**
- Create: `simple_agent/web/chat_server.py`
- Create: `tests/test_web_chat.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_web_chat.py`：

```python
import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import MagicMock
from simple_agent.config.settings import Settings


@pytest.fixture
def tmpcwd():
    old = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        yield Path(tmp)
        os.chdir(old)


def test_init_runtime_creates_singleton(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    assert chat_server._runtime is not None
    assert chat_server._sink is not None
    assert chat_server._runtime._session_id is not None  # init_session 已被调用


def test_init_runtime_injects_web_sink(tmpcwd):
    from simple_agent.web import chat_server
    from simple_agent.core.sinks import WebTurnSink

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    assert isinstance(chat_server._sink, WebTurnSink)
    assert chat_server._runtime._sink is chat_server._sink
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_web_chat.py -v`
Expected: FAIL，`simple_agent.web.chat_server` 不存在

- [ ] **Step 3: 创建 chat_server.py（init 部分）**

创建 `simple_agent/web/chat_server.py`：

```python
"""Web chat server for simple-agent.

Single-session model: one Runtime instance shared by all browser tabs.
"""
import threading
from pathlib import Path
from typing import Optional
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from simple_agent.config.settings import Settings
from simple_agent.core.runtime import Runtime
from simple_agent.core.sinks import WebTurnSink
from simple_agent.core.events import HookBlockedException


# Module-level singletons (single-session model)
_runtime: Optional[Runtime] = None
_sink: Optional[WebTurnSink] = None
_runtime_lock = threading.Lock()

# Flask app
app = Flask(__name__)
CORS(app)


def init_runtime(
    config: Settings,
    resume_log: Optional[str] = None,
    skip_api_init: bool = False,
) -> None:
    """Initialize (or replace) the singleton Runtime with a WebTurnSink injected.

    Args:
        config: Settings object.
        resume_log: Optional path to a log file to resume from.
        skip_api_init: For testing - skip APIClient construction.
    """
    global _runtime, _sink

    _sink = WebTurnSink()
    _runtime = Runtime(
        config,
        log_file=resume_log,
        skip_api_init=skip_api_init,
        sink=_sink,
    )

    if resume_log:
        log_path = Path(resume_log)
        if log_path.exists():
            _runtime._session.load_from_log(log_path)

    _runtime.init_session()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_web_chat.py -v`
Expected: 2 个测试 PASS

- [ ] **Step 5: 提交**

```bash
git add simple_agent/web/chat_server.py tests/test_web_chat.py
git commit -m "feat: 新增 chat_server 单例与 init_runtime 函数

为 Web 聊天后端建立基础：一个 server 进程对应一个 Runtime 单例，注入 WebTurnSink。"
```

---

## Task 10: /api/session 路由

**Files:**
- Modify: `simple_agent/web/chat_server.py`
- Modify: `tests/test_web_chat.py`

- [ ] **Step 1: 追加测试**

在 `tests/test_web_chat.py` 末尾追加：

```python
def test_api_session_returns_metadata(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    config.api.model = "gpt-4o-test"
    config.api.provider = "openai"
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.get("/api/session")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["session_id"] == chat_server._runtime._session_id
    assert data["model"] == "gpt-4o-test"
    assert data["provider"] == "openai"
    assert "messages" in data
    assert isinstance(data["messages"], list)


def test_api_session_includes_existing_messages(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._session.add_message("user", "hi")
    chat_server._runtime._session.add_message("assistant", "hello")

    client = chat_server.app.test_client()
    data = client.get("/api/session").get_json()

    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_web_chat.py -v`
Expected: 新的 2 个测试 FAIL（404）

- [ ] **Step 3: 实现 /api/session 路由**

在 `chat_server.py` 末尾追加：

```python
@app.route("/api/session", methods=["GET"])
def api_session():
    """Return session metadata for frontend initialization."""
    if _runtime is None:
        return jsonify({"error": "Runtime not initialized"}), 500

    return jsonify({
        "session_id": _runtime._session_id,
        "model": _runtime._config.api.model,
        "provider": _runtime._config.api.provider,
        "messages": _runtime._session.get_messages(),
    })
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_web_chat.py -v`
Expected: 4 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add simple_agent/web/chat_server.py tests/test_web_chat.py
git commit -m "feat: 新增 /api/session 路由返回会话元数据"
```

---

## Task 11: /api/turn 路由

**Files:**
- Modify: `simple_agent/web/chat_server.py`
- Modify: `tests/test_web_chat.py`

- [ ] **Step 1: 追加测试**

```python
def test_api_turn_returns_events_for_plain_message(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.return_value = [
        {"role": "assistant", "content": "Hi there!"}
    ]

    client = chat_server.app.test_client()
    resp = client.post("/api/turn", json={"input": "hello"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert "events" in data
    types = [e["type"] for e in data["events"]]
    assert "turn_start" in types
    assert "message" in types
    assert "turn_end" in types
    # 验证 assistant 消息内容正确
    msg = next(e for e in data["events"] if e["type"] == "message")
    assert msg["content"] == "Hi there!"
    assert data["session_id"] == chat_server._runtime._session_id


def test_api_turn_clears_events_between_turns(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.return_value = [
        {"role": "assistant", "content": "ok"}
    ]

    client = chat_server.app.test_client()
    data1 = client.post("/api/turn", json={"input": "first"}).get_json()
    data2 = client.post("/api/turn", json={"input": "second"}).get_json()

    # 第二轮的 events 不应含有第一轮的内容
    first_inputs = [e for e in data2["events"] if e.get("user_input") == "first"]
    assert len(first_inputs) == 0
    second_inputs = [e for e in data2["events"] if e.get("user_input") == "second"]
    assert len(second_inputs) == 1


def test_api_turn_handles_slash_command(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.post("/api/turn", json={"input": "/help"})

    assert resp.status_code == 200
    data = resp.get_json()
    # /help 返回 help text，作为 system message
    assert any(
        e["type"] == "message" and "Available Commands" in e.get("content", "")
        for e in data["events"]
    )


def test_api_turn_handles_exception_via_sink_error(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.side_effect = RuntimeError("boom")

    client = chat_server.app.test_client()
    resp = client.post("/api/turn", json={"input": "hi"})

    assert resp.status_code == 200
    data = resp.get_json()
    error_events = [e for e in data["events"] if e["type"] == "error"]
    assert len(error_events) == 1
    assert "boom" in error_events[0]["message"]
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_web_chat.py -v`
Expected: 新 4 个测试 FAIL

- [ ] **Step 3: 实现 /api/turn 路由**

在 `chat_server.py` 末尾追加：

```python
@app.route("/api/turn", methods=["POST"])
def api_turn():
    """Execute one conversation turn synchronously.

    Body: {"input": "user message text"}
    Returns: {"events": [...], "session_id": "..."}
    """
    if _runtime is None or _sink is None:
        return jsonify({"error": "Runtime not initialized"}), 500

    payload = request.get_json(silent=True) or {}
    user_input = payload.get("input", "")

    with _runtime_lock:
        _sink.events.clear()
        try:
            result = _runtime.process_input(user_input)
            if result in ("message_processed", "command_processed"):
                _runtime._run_one_turn()
            elif result == "exit":
                _sink.on_message("system", "Session ended.")
            else:
                # 比如 /help 返回的文本
                _sink.on_message("system", result)
        except HookBlockedException as e:
            _sink.on_message("system", f"[BLOCKED] {e}")
        except Exception as e:
            _sink.on_error(f"{type(e).__name__}: {e}")

        events = list(_sink.events)

    return jsonify({
        "events": events,
        "session_id": _runtime._session_id,
    })
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_web_chat.py -v`
Expected: 8 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add simple_agent/web/chat_server.py tests/test_web_chat.py
git commit -m "feat: 新增 /api/turn 路由执行单轮对话

通过 _runtime_lock 串行化并发请求，捕获异常并通过 sink.on_error 反馈到前端。"
```

---

## Task 12: /api/sidebar 路由

**Files:**
- Modify: `simple_agent/web/chat_server.py`
- Modify: `tests/test_web_chat.py`

- [ ] **Step 1: 追加测试**

```python
def test_api_sidebar_returns_structured_data(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.get("/api/sidebar")

    assert resp.status_code == 200
    data = resp.get_json()
    assert "todos" in data
    assert "loaded_skills" in data
    assert "available_skills" in data
    assert "available_agents" in data
    assert isinstance(data["todos"], list)
    assert isinstance(data["loaded_skills"], list)
    assert isinstance(data["available_skills"], list)
    assert isinstance(data["available_agents"], list)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_web_chat.py::test_api_sidebar_returns_structured_data -v`
Expected: FAIL (404)

- [ ] **Step 3: 实现 /api/sidebar 路由**

在 `chat_server.py` 末尾追加：

```python
@app.route("/api/sidebar", methods=["GET"])
def api_sidebar():
    """Return sidebar data: todos, loaded skills, available skills/agents."""
    if _runtime is None:
        return jsonify({"error": "Runtime not initialized"}), 500

    todos = _runtime._todo_manager.get_all_tasks() if _runtime._todo_manager else []

    return jsonify({
        "todos": todos,
        "loaded_skills": sorted(_runtime._loaded_skills),
        "available_skills": _runtime._skill_loader.list_skills(),
        "available_agents": _runtime._agent_loader.list_agents(),
    })
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_web_chat.py::test_api_sidebar_returns_structured_data -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add simple_agent/web/chat_server.py tests/test_web_chat.py
git commit -m "feat: 新增 /api/sidebar 路由提供 TODOs/skills/agents 数据"
```

---

## Task 13: /api/logs 与 /api/resume 路由

**Files:**
- Modify: `simple_agent/web/chat_server.py`
- Modify: `tests/test_web_chat.py`

- [ ] **Step 1: 追加测试**

```python
def test_api_logs_returns_list(tmpcwd):
    from simple_agent.web import chat_server

    log_dir = tmpcwd / ".simple-agent" / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "llm-20260520-101010.jsonl").write_text("")
    (log_dir / "llm-20260519-101010.jsonl").write_text("")

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.get("/api/logs")

    assert resp.status_code == 200
    data = resp.get_json()
    assert "logs" in data
    # 应按 mtime 倒序
    assert len(data["logs"]) == 2
    assert all("path" in entry and "name" in entry for entry in data["logs"])


def test_api_resume_replaces_runtime(tmpcwd):
    from simple_agent.web import chat_server

    log_dir = tmpcwd / ".simple-agent" / "logs"
    log_dir.mkdir(parents=True)
    log_file = log_dir / "llm-20260520-101010.jsonl"
    # 写一条 session_start 和一条 user message
    log_file.write_text(
        '{"type": "session_start", "session_id": "old-sess"}\n'
        '{"type": "message", "role": "user", "content": "resumed hi"}\n'
    )

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    old_runtime_id = id(chat_server._runtime)

    client = chat_server.app.test_client()
    resp = client.post("/api/resume", json={"log_file": str(log_file)})

    assert resp.status_code == 200
    # Runtime 实例被替换
    assert id(chat_server._runtime) != old_runtime_id
    # session messages 应包含 resumed message
    messages = chat_server._runtime._session.get_messages()
    assert any(m.get("content") == "resumed hi" for m in messages)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_web_chat.py -v -k "logs or resume"`
Expected: FAIL (404)

- [ ] **Step 3: 实现两个路由**

在 `chat_server.py` 末尾追加：

```python
@app.route("/api/logs", methods=["GET"])
def api_logs():
    """List available log files for resume, sorted by mtime descending."""
    if _runtime is None:
        return jsonify({"error": "Runtime not initialized"}), 500

    log_dir_str = _runtime._config.logging.log_dir
    log_dir = Path(log_dir_str) if log_dir_str else Path.cwd() / ".simple-agent" / "logs"

    logs = []
    if log_dir.exists():
        files = sorted(
            log_dir.glob("*.jsonl"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        logs = [{"path": str(f), "name": f.name} for f in files]

    return jsonify({"logs": logs})


@app.route("/api/resume", methods=["POST"])
def api_resume():
    """Replace the singleton Runtime with a new one resumed from the given log file."""
    if _runtime is None:
        return jsonify({"error": "Runtime not initialized"}), 500

    payload = request.get_json(silent=True) or {}
    log_file = payload.get("log_file")
    if not log_file:
        return jsonify({"error": "Missing log_file"}), 400

    log_path = Path(log_file)
    if not log_path.exists():
        return jsonify({"error": "Log file not found"}), 404

    with _runtime_lock:
        # Preserve the same config so api key etc. remain valid
        config = _runtime._config
        # skip_api_init must match the original runtime's mode
        skip = _runtime._api_client is None
        init_runtime(config, resume_log=str(log_path), skip_api_init=skip)

    return jsonify({"session_id": _runtime._session_id})
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/test_web_chat.py -v`
Expected: 11 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add simple_agent/web/chat_server.py tests/test_web_chat.py
git commit -m "feat: 新增 /api/logs 和 /api/resume 路由支持从历史日志恢复"
```

---

## Task 14: 静态文件路由 + 前端 HTML 骨架

**Files:**
- Modify: `simple_agent/web/chat_server.py`
- Create: `simple_agent/web/static/chat.html`

- [ ] **Step 1: 创建 chat.html**

创建 `simple_agent/web/static/chat.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Simple Agent - Chat</title>
  <link rel="stylesheet" href="/static/chat.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/atom-one-dark.min.css">
</head>
<body>
  <header id="app-header">
    <div class="header-left">
      <span class="brand">Simple Agent</span>
      <span class="meta">session: <span id="session-id">—</span></span>
      <span class="meta">model: <span id="model-name">—</span></span>
    </div>
    <div class="header-right">
      <button id="resume-btn" title="从日志恢复">⟳ 恢复</button>
    </div>
  </header>

  <div id="app-body">
    <aside id="sidebar">
      <section>
        <h3>TODOs</h3>
        <ul id="todo-list"><li class="empty">无</li></ul>
      </section>
      <section>
        <h3>已加载 Skills</h3>
        <ul id="loaded-skills-list"><li class="empty">无</li></ul>
      </section>
      <section>
        <h3>可用 Skills</h3>
        <ul id="available-skills-list"><li class="empty">无</li></ul>
      </section>
      <section>
        <h3>可用 Agents</h3>
        <ul id="available-agents-list"><li class="empty">无</li></ul>
      </section>
    </aside>

    <main id="chat-area">
      <div id="messages"></div>
      <form id="input-form">
        <textarea id="input-box" placeholder="输入消息或 /help 查看命令... (Ctrl/Cmd+Enter 发送)" rows="3"></textarea>
        <button type="submit" id="send-btn">发送</button>
      </form>
    </main>
  </div>

  <div id="resume-dialog" class="dialog hidden">
    <div class="dialog-content">
      <h3>选择日志恢复</h3>
      <ul id="log-file-list"></ul>
      <button id="resume-cancel">取消</button>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/highlight.min.js"></script>
  <script src="/static/chat.js"></script>
</body>
</html>
```

- [ ] **Step 2: 加静态文件路由到 chat_server.py**

在 `chat_server.py` 末尾追加：

```python
_STATIC_DIR = Path(__file__).parent / "static"


@app.route("/")
def index():
    return send_from_directory(str(_STATIC_DIR), "chat.html")


@app.route("/static/<path:filename>")
def static_file(filename: str):
    return send_from_directory(str(_STATIC_DIR), filename)
```

- [ ] **Step 3: 写测试验证静态资源能被服务**

追加到 `tests/test_web_chat.py`：

```python
def test_index_serves_chat_html(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.get("/")

    assert resp.status_code == 200
    assert b"Simple Agent" in resp.data
    assert b"chat.js" in resp.data
```

- [ ] **Step 4: 运行测试**

Run: `pytest tests/test_web_chat.py -v`
Expected: 12 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add simple_agent/web/chat_server.py simple_agent/web/static/chat.html tests/test_web_chat.py
git commit -m "feat: 新增 Web 聊天 UI 静态文件路由与 HTML 骨架"
```

---

## Task 15: 前端 CSS

**Files:**
- Create: `simple_agent/web/static/chat.css`

- [ ] **Step 1: 创建 chat.css**

创建 `simple_agent/web/static/chat.css`：

```css
:root {
  --bg: #1e1e1e;
  --bg-alt: #252526;
  --bg-card: #2d2d30;
  --fg: #d4d4d4;
  --fg-dim: #999;
  --accent: #569cd6;
  --user: #4ec9b0;
  --assistant: #c586c0;
  --system: #dcdcaa;
  --error: #f48771;
  --success: #6a9955;
  --border: #3e3e42;
}

* { box-sizing: border-box; }

html, body {
  margin: 0; padding: 0; height: 100%;
  background: var(--bg);
  color: var(--fg);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 14px;
}

#app-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 16px;
  background: var(--bg-alt);
  border-bottom: 1px solid var(--border);
}
.brand { font-weight: bold; color: var(--accent); margin-right: 24px; }
.meta { color: var(--fg-dim); margin-right: 16px; font-size: 12px; }
.header-right button {
  background: var(--bg-card); color: var(--fg);
  border: 1px solid var(--border); padding: 4px 10px;
  border-radius: 4px; cursor: pointer;
}
.header-right button:hover { background: var(--border); }

#app-body {
  display: flex; height: calc(100vh - 41px);
}

#sidebar {
  width: 240px; padding: 12px;
  background: var(--bg-alt);
  border-right: 1px solid var(--border);
  overflow-y: auto;
}
#sidebar section { margin-bottom: 20px; }
#sidebar h3 {
  margin: 0 0 8px 0; font-size: 11px; text-transform: uppercase;
  color: var(--fg-dim); letter-spacing: 0.5px;
}
#sidebar ul {
  list-style: none; padding: 0; margin: 0;
}
#sidebar li {
  padding: 4px 0; font-size: 12px; color: var(--fg);
}
#sidebar li.empty { color: var(--fg-dim); font-style: italic; }
.todo-status { display: inline-block; width: 14px; }
.todo-completed { color: var(--success); }
.todo-pending { color: var(--fg-dim); }
.todo-in_progress { color: var(--system); }

#chat-area {
  flex: 1; display: flex; flex-direction: column;
}

#messages {
  flex: 1; overflow-y: auto; padding: 16px;
}

.bubble {
  margin-bottom: 12px; padding: 10px 14px;
  border-radius: 8px;
  background: var(--bg-card);
  border-left: 3px solid var(--fg-dim);
  max-width: 90%;
}
.bubble.user {
  border-left-color: var(--user);
  margin-left: auto; background: #2a3d3a;
}
.bubble.assistant { border-left-color: var(--assistant); }
.bubble.system {
  border-left-color: var(--system);
  background: #2d2c1f; font-size: 13px;
}
.bubble.error {
  border-left-color: var(--error);
  background: #3d2c2a; color: #f48771;
}
.bubble .role {
  font-size: 11px; text-transform: uppercase;
  color: var(--fg-dim); margin-bottom: 4px; letter-spacing: 0.5px;
}
.bubble .content {
  word-wrap: break-word;
}
.bubble pre {
  background: #1a1a1a; padding: 10px;
  border-radius: 4px; overflow-x: auto;
}
.bubble code {
  background: #1a1a1a; padding: 2px 5px;
  border-radius: 3px; font-family: "SF Mono", Consolas, monospace;
  font-size: 12px;
}
.bubble pre code { padding: 0; background: none; }

.tool-card {
  margin-bottom: 12px; border: 1px solid var(--border);
  border-radius: 6px; overflow: hidden;
}
.tool-header {
  padding: 8px 12px; cursor: pointer;
  background: var(--bg-card); display: flex; justify-content: space-between;
  font-family: "SF Mono", Consolas, monospace; font-size: 12px;
}
.tool-header .status.ok { color: var(--success); }
.tool-header .status.fail { color: var(--error); }
.tool-body {
  display: none; padding: 8px 12px;
  background: #1a1a1a; font-family: "SF Mono", Consolas, monospace;
  font-size: 12px; max-height: 400px; overflow-y: auto;
}
.tool-card.expanded .tool-body { display: block; }
.tool-body pre {
  white-space: pre-wrap; word-wrap: break-word; margin: 0;
}

#input-form {
  display: flex; padding: 12px;
  border-top: 1px solid var(--border);
  background: var(--bg-alt);
}
#input-box {
  flex: 1; background: var(--bg-card); color: var(--fg);
  border: 1px solid var(--border); border-radius: 4px;
  padding: 8px; resize: vertical; font-family: inherit; font-size: 14px;
}
#send-btn {
  margin-left: 8px; padding: 0 20px;
  background: var(--accent); color: white; border: none;
  border-radius: 4px; cursor: pointer; font-size: 14px;
}
#send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.dialog.hidden { display: none; }
.dialog {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}
.dialog-content {
  background: var(--bg-card); padding: 20px;
  border-radius: 8px; min-width: 400px; max-width: 600px;
  max-height: 80vh; overflow-y: auto;
}
.dialog-content h3 { margin-top: 0; }
.dialog-content ul { list-style: none; padding: 0; }
.dialog-content li {
  padding: 8px; cursor: pointer; border-radius: 4px;
  font-family: monospace; font-size: 12px;
}
.dialog-content li:hover { background: var(--border); }

.loading {
  display: inline-block; width: 12px; height: 12px;
  border: 2px solid var(--fg-dim);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-left: 8px;
}
@keyframes spin { to { transform: rotate(360deg); } }
```

- [ ] **Step 2: 提交**

```bash
git add simple_agent/web/static/chat.css
git commit -m "feat: 新增 Web 聊天 UI 样式表"
```

---

## Task 16: 前端 JS - 初始化与发送

**Files:**
- Create: `simple_agent/web/static/chat.js`

- [ ] **Step 1: 创建 chat.js（初始化 + 发送）**

创建 `simple_agent/web/static/chat.js`：

```javascript
// Simple Agent Web Chat - frontend logic

const $ = (id) => document.getElementById(id);
const messagesEl = $('messages');
const inputBox = $('input-box');
const sendBtn = $('send-btn');
const inputForm = $('input-form');

// Configure marked + highlight.js
marked.setOptions({
  breaks: true,
  gfm: true,
  highlight: (code, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value;
    }
    return hljs.highlightAuto(code).value;
  },
});

function renderMarkdown(content) {
  return marked.parse(content || '');
}

function appendBubble(role, content, klass) {
  const div = document.createElement('div');
  div.className = `bubble ${klass || role}`;
  div.innerHTML = `
    <div class="role">${role}</div>
    <div class="content">${renderMarkdown(content)}</div>
  `;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  // Highlight any rendered code
  div.querySelectorAll('pre code').forEach((b) => hljs.highlightElement(b));
  return div;
}

function appendError(message) {
  const div = document.createElement('div');
  div.className = 'bubble error';
  div.innerHTML = `<div class="role">error</div><div class="content">${escapeHtml(message)}</div>`;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendToolCard(event) {
  // event is tool_end (we ignore tool_start; tool_end carries everything)
  const card = document.createElement('div');
  card.className = 'tool-card';
  const statusClass = event.success ? 'ok' : 'fail';
  const statusIcon = event.success ? '✓' : '✗';
  const argsStr = formatArgs(event.arguments);
  card.innerHTML = `
    <div class="tool-header">
      <span>${escapeHtml(event.tool_name)} ${escapeHtml(argsStr)}</span>
      <span class="status ${statusClass}">${statusIcon}</span>
    </div>
    <div class="tool-body">
      <pre>${escapeHtml(JSON.stringify(event.result, null, 2))}</pre>
    </div>
  `;
  card.querySelector('.tool-header').addEventListener('click', () => {
    card.classList.toggle('expanded');
  });
  messagesEl.appendChild(card);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function formatArgs(args) {
  if (!args || typeof args !== 'object') return '';
  const parts = [];
  for (const [k, v] of Object.entries(args)) {
    if (parts.length >= 3) { parts.push('…'); break; }
    let s = typeof v === 'string' ? v : JSON.stringify(v);
    if (s.length > 30) s = s.slice(0, 29) + '…';
    parts.push(`${k}=${s}`);
  }
  return parts.length ? `[${parts.join(', ')}]` : '';
}

function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderEvent(ev) {
  switch (ev.type) {
    case 'message':
      appendBubble(ev.role, ev.content);
      break;
    case 'error':
      appendError(ev.message);
      break;
    case 'tool_end':
      appendToolCard(ev);
      break;
    case 'tool_start':
    case 'turn_start':
    case 'turn_end':
    case 'status':
      // tool_start info already included in tool_end; turn_*/status currently unused
      break;
    default:
      console.warn('Unknown event type', ev);
  }
}

async function loadSession() {
  const resp = await fetch('/api/session');
  const data = await resp.json();
  $('session-id').textContent = (data.session_id || '—').slice(0, 8) + '…';
  $('model-name').textContent = data.model || '—';
  messagesEl.innerHTML = '';
  for (const msg of data.messages || []) {
    if (msg.role === 'tool') continue; // tool messages 重绘成卡片需要 result 信息，恢复时简化处理
    appendBubble(msg.role, msg.content || '');
  }
}

async function sendTurn(input) {
  appendBubble('user', input);
  inputBox.value = '';
  sendBtn.disabled = true;
  sendBtn.innerHTML = '发送 <span class="loading"></span>';

  try {
    const resp = await fetch('/api/turn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input }),
    });
    const data = await resp.json();
    for (const ev of (data.events || [])) renderEvent(ev);
    refreshSidebar();
  } catch (e) {
    appendError(`Request failed: ${e.message || e}`);
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = '发送';
  }
}

inputForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = inputBox.value.trim();
  if (!text) return;
  sendTurn(text);
});

inputBox.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    inputForm.requestSubmit();
  }
});

// Sidebar + resume implemented in next task; provide stubs for now
function refreshSidebar() {}

// Boot
loadSession();
```

- [ ] **Step 2: 手动验证（如果有 API key）**

如果有 API key：
- Run: `simple-agent --web-chat`（这个标志在 Task 18 才加；本步可跳过到 Task 18 后再回来手动验证）

如果没有 API key：跳过手动验证，依赖后端单元测试。

- [ ] **Step 3: 提交**

```bash
git add simple_agent/web/static/chat.js
git commit -m "feat: 实现 Web 聊天 UI 前端初始化与发送逻辑

支持 Markdown/代码高亮、工具卡片折叠展开、Ctrl/Cmd+Enter 快捷发送。"
```

---

## Task 17: 前端 JS - 侧边栏与 resume

**Files:**
- Modify: `simple_agent/web/static/chat.js`

- [ ] **Step 1: 把 `refreshSidebar` stub 和 resume 逻辑实现**

把 `chat.js` 末尾 `function refreshSidebar() {}` 这行替换为：

```javascript
async function refreshSidebar() {
  try {
    const resp = await fetch('/api/sidebar');
    const data = await resp.json();
    renderTodoList(data.todos || []);
    renderSimpleList('loaded-skills-list', data.loaded_skills || [], (s) => s);
    renderSimpleList(
      'available-skills-list',
      data.available_skills || [],
      (s) => `<strong>${escapeHtml(s.name)}</strong>: ${escapeHtml(s.description || '')}`,
      true,
    );
    renderSimpleList(
      'available-agents-list',
      data.available_agents || [],
      (a) => `<strong>${escapeHtml(a.name)}</strong>: ${escapeHtml(a.description || '')}`,
      true,
    );
  } catch (e) {
    console.warn('refreshSidebar failed', e);
  }
}

function renderTodoList(todos) {
  const ul = $('todo-list');
  if (!todos.length) {
    ul.innerHTML = '<li class="empty">无</li>';
    return;
  }
  ul.innerHTML = '';
  for (const t of todos) {
    const li = document.createElement('li');
    const status = t.status || 'pending';
    const icon = { completed: '✓', in_progress: '⚙', pending: '◯', blocked: '🚫' }[status] || '◯';
    li.innerHTML = `<span class="todo-status todo-${status}">${icon}</span> ${escapeHtml(t.subject || '')}`;
    ul.appendChild(li);
  }
}

function renderSimpleList(elId, items, render, isHtml = false) {
  const ul = $(elId);
  if (!items.length) {
    ul.innerHTML = '<li class="empty">无</li>';
    return;
  }
  ul.innerHTML = '';
  for (const item of items) {
    const li = document.createElement('li');
    const content = render(item);
    if (isHtml) li.innerHTML = content;
    else li.textContent = content;
    ul.appendChild(li);
  }
}

// Resume dialog
const resumeBtn = $('resume-btn');
const resumeDialog = $('resume-dialog');
const logFileList = $('log-file-list');
const resumeCancel = $('resume-cancel');

resumeBtn.addEventListener('click', async () => {
  try {
    const resp = await fetch('/api/logs');
    const data = await resp.json();
    logFileList.innerHTML = '';
    if (!data.logs || !data.logs.length) {
      logFileList.innerHTML = '<li class="empty">无可用日志</li>';
    } else {
      for (const log of data.logs) {
        const li = document.createElement('li');
        li.textContent = log.name;
        li.addEventListener('click', () => doResume(log.path));
        logFileList.appendChild(li);
      }
    }
    resumeDialog.classList.remove('hidden');
  } catch (e) {
    appendError(`Load logs failed: ${e.message || e}`);
  }
});

resumeCancel.addEventListener('click', () => {
  resumeDialog.classList.add('hidden');
});

async function doResume(logPath) {
  resumeDialog.classList.add('hidden');
  try {
    const resp = await fetch('/api/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ log_file: logPath }),
    });
    if (!resp.ok) {
      const err = await resp.json();
      appendError(`Resume failed: ${err.error}`);
      return;
    }
    await loadSession();
    await refreshSidebar();
  } catch (e) {
    appendError(`Resume failed: ${e.message || e}`);
  }
}

// Initial sidebar load
refreshSidebar();
```

- [ ] **Step 2: 提交**

```bash
git add simple_agent/web/static/chat.js
git commit -m "feat: Web 聊天 UI 实现侧边栏与日志恢复对话框"
```

---

## Task 18: main.py 入口加 --web-chat

**Files:**
- Modify: `simple_agent/main.py:91-94` (现有 `--web` flag 区域)
- Modify: `simple_agent/main.py:141-158` (run_web_server 附近)

- [ ] **Step 1: 在 argparse 之前加 --web-chat 分支**

修改 `simple_agent/main.py:91-94`，把当前的 `--web` 检查保持，再加一段 `--web-chat`：

```python
    # Check for --web flag (legacy analyzer)
    if "--web" in sys.argv:
        run_web_server()
        return

    # Check for --web-chat flag (interactive chat UI)
    if "--web-chat" in sys.argv:
        sys.argv.remove("--web-chat")
        run_chat_server()
        return
```

- [ ] **Step 2: 加 run_chat_server 函数**

在 `main.py` 末尾（`run_web_server` 之后）追加：

```python
def run_chat_server():
    """Run the interactive web chat server."""
    parser = argparse.ArgumentParser(description="Simple Agent Web Chat")
    parser.add_argument("-p", "--plugin", type=str,
                        help="Plugin directory (default: ./plugins/default)")
    parser.add_argument("--resume", nargs="?", const="auto",
                        help="Resume from latest log file or specified log file")
    parser.add_argument("--port", type=int, default=5002,
                        help="Port to listen on (default: 5002)")
    args = parser.parse_args()

    resume_log = None
    if args.resume == "auto":
        latest = get_latest_log_file()
        if latest:
            resume_log = str(latest)
    elif args.resume:
        resume_log = args.resume

    config = load_config(plugin_dir=args.plugin)
    if not config.api.api_key:
        print("Error: No API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.")
        sys.exit(1)

    try:
        from simple_agent.web.chat_server import init_runtime, app
    except ImportError:
        print("Error: Flask is not installed. Run: pip install -e .")
        sys.exit(1)

    init_runtime(config, resume_log=resume_log)
    print(f"Simple Agent Web Chat: http://localhost:{args.port}")
    if resume_log:
        print(f"Resumed from: {resume_log}")
    print("Press Ctrl+C to stop the server")
    app.run(host="127.0.0.1", port=args.port, debug=False)
```

- [ ] **Step 3: 跑全量测试**

Run: `pytest`
Expected: 全部通过（main.py 的改动不破坏现有测试）

- [ ] **Step 4: 手动启动验证**

如果环境有 API key：

```bash
simple-agent --web-chat
```

在浏览器打开 http://localhost:5002，验证：
- 页面正常加载
- 输入 "hi" 发送，能看到 user 气泡和 assistant 回复
- 输入 `/help`，看到命令帮助
- 让 AI 调一个工具（例如 "用 Bash 列出当前目录"），看到工具卡片，可点击展开
- 侧边栏显示 skills/agents
- 点 "⟳ 恢复" 按钮，列出日志文件，能选择并切换

如果没有 API key：跳过这步。

- [ ] **Step 5: 提交**

```bash
git add simple_agent/main.py
git commit -m "feat: main.py 新增 --web-chat 命令启动 Web 聊天服务

支持 --resume 和 --port 参数，缺少 Flask 时给出友好提示。"
```

---

## Task 19: 文档更新

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: 在 README.md 增加 Web 聊天章节**

打开 `README.md`，在适当位置（如 "使用方法" 之后）追加一节：

```markdown
## Web 聊天 UI

simple-agent 提供浏览器内的交互式聊天界面：

```bash
# 启动 Web 聊天服务
simple-agent --web-chat

# 指定端口
simple-agent --web-chat --port 8080

# 从最近的日志恢复会话
simple-agent --web-chat --resume

# 从指定日志恢复
simple-agent --web-chat --resume .simple-agent/logs/llm-20260520-101010.jsonl
```

浏览器打开 http://localhost:5002（默认端口）即可使用。

特性：
- 实时对话，工具调用过程以可折叠卡片显示
- 侧边栏显示 TODOs / 已加载 Skills / 可用 Skills 与 Agents
- 支持斜杠命令（`/help`、`/clear` 等，与 CLI 一致）
- Markdown 渲染 + 代码语法高亮
- 一键从历史日志恢复会话
```

- [ ] **Step 2: 在 CLAUDE.md 开发命令部分增加 web-chat**

在 `CLAUDE.md` 的 "开发命令" 章节里 `simple-agent --logs` 那一段附近追加：

```bash
# 启动 Web 聊天 UI
simple-agent --web-chat                # 默认端口 5002
simple-agent --web-chat --port 8080    # 指定端口
simple-agent --web-chat --resume       # 从最近日志恢复
```

- [ ] **Step 3: 跑全量测试**

Run: `pytest`
Expected: 全部通过

- [ ] **Step 4: 提交**

```bash
git add README.md CLAUDE.md
git commit -m "docs: 更新 README 和 CLAUDE.md，说明 --web-chat 用法"
```

---

## 自检结果

**1. Spec coverage（每个 spec 章节是否有对应 task）**

| Spec 章节 | 实现 Task |
|-----------|-----------|
| 关键决定：单会话、独立服务、一次性返回、resume、方案 B | Task 6-13、18 |
| 架构总览（OutputSink + chat_server 单例） | Task 2-3、9 |
| OutputSink 协议（7 个事件方法） | Task 2-3 |
| CliSink/WebTurnSink 行为 | Task 2-3 |
| Runtime 改动：init_session、_run_one_turn、构造函数加 sink | Task 4-6 |
| Runtime 改动：5-10 处调用点改走 sink | Task 7-8 |
| chat_server 模块级状态与 init_runtime | Task 9 |
| 6 个 HTTP 路由 | Task 10-14 |
| 错误与边界（lock、HookBlockedException、Exception） | Task 11 |
| main.py --web-chat 入口 | Task 18 |
| 前端文件结构与 CDN 库 | Task 14-17 |
| 前端事件 → DOM 映射 | Task 16 |
| 工具卡片折叠 | Task 16 |
| 斜杠命令支持 | Task 11、16（直接走 /api/turn） |
| Resume UI | Task 17 |
| 测试章节 | Task 2-13 各 task 内的测试 |
| 文档更新 | Task 19 |

✓ 全部覆盖。

**2. Placeholder scan**：无 TBD、TODO、"implement later"、"similar to Task N"、"add appropriate error handling" 类占位符。每段代码改动都给了完整代码。✓

**3. Type consistency**：
- `OutputSink` 协议 7 个方法签名在 Task 2 定义，Task 7、8 中 Runtime 调用 `self._sink.on_tool_start(tool_name, arguments, tool_call["id"])` 与签名 `on_tool_start(tool_name, arguments, call_id)` 匹配。✓
- `WebTurnSink.events` 在 Task 2 定义为 list[dict]，Task 11 `_sink.events.clear()` 和 `list(_sink.events)` 用法一致。✓
- chat_server 模块级 `_runtime`、`_sink`、`_runtime_lock` 名称在 Task 9-13 全程一致。✓
- 前端事件字段（`type`、`role`、`content`、`tool_name`、`arguments`、`call_id`、`result`、`success`）与后端 WebTurnSink 输出 dict 字段名一致。✓
- `init_runtime(config, resume_log=None, skip_api_init=False)` 签名在 Task 9 定义，Task 13、18 调用方式与之一致。✓

---

## 执行说明

实施过程中请严格按 task 顺序进行。每个 task 自成一个 commit，保证可二分回滚。Runtime 重构（Task 4-8）改动最敏感，要求每步之后 `pytest` 全绿才能进下一步——这是验证"CLI 行为不变"的核心保障。

前端无自动化测试，依靠后端测试 + 手动验证（Task 18 第 4 步）覆盖。
