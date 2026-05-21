# Web Chat SSE 流式推送 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `/api/turn` 从一次性 JSON 返回改为 SSE 流式推送，每个事件产生即推送到前端。

**Architecture:** WebTurnSink 新增 `event_callback` 参数，每产出一个事件同时 append 到 list 并调 callback。`/api/turn` 在后台线程执行 Runtime，通过 `queue.Queue` 把事件桥接到 SSE 生成器。前端 `sendTurn` 改为 `fetch` + `ReadableStream` 逐条消费 SSE。

**Tech Stack:** Python queue/threading、Flask Response SSE、JS ReadableStream

**Spec:** `docs/superpowers/specs/2026-05-22-web-chat-sse-design.md`

---

## 文件清单

### 修改

| 文件 | 修改点 |
|------|--------|
| `simple_agent/core/sinks.py` | WebTurnSink 加 `event_callback` 参数 + `_emit` 方法，7 个 `on_*` 方法改用 `_emit` |
| `simple_agent/web/chat_server.py` | `/api/turn` 改为 SSE Response（后台线程 + queue + generate） |
| `simple_agent/web/static/chat.js` | `sendTurn` 从 `resp.json()` 改为 SSE ReadableStream 消费 |
| `tests/test_sinks.py` | 新增 WebTurnSink callback 测试 |
| `tests/test_web_chat.py` | 重写 `/api/turn` 相关测试，从 JSON 断言改为 SSE 解析断言 |

### 不修改

- `simple_agent/core/runtime.py` — 不动
- `simple_agent/core/sinks.py` 的 `CliSink` — 不动
- 前端 `chat.css` / `chat.html` — 不动
- `/api/session`、`/api/sidebar`、`/api/logs`、`/api/resume` 路由 — 不动

---

## Task 1: WebTurnSink 加 event_callback + _emit

**Files:**
- Modify: `simple_agent/core/sinks.py:89-129`
- Modify: `tests/test_sinks.py`

- [ ] **Step 1: 写失败测试 — callback 被调用**

追加到 `tests/test_sinks.py`：

```python
def test_web_sink_callback_is_called_on_each_event():
    callback = MagicMock()
    sink = WebTurnSink(event_callback=callback)

    sink.on_message("assistant", "hi")
    sink.on_tool_start("READ", {"path": "/x"}, "c1")
    sink.on_tool_end("READ", {"path": "/x"}, "c1", {"success": True}, True)
    sink.on_error("boom")
    sink.on_turn_start("hello")
    sink.on_turn_end()
    sink.on_status("skill_loaded", {"name": "x"})

    assert callback.call_count == 7
    # Verify callback receives same dict as in events list
    for i, call in enumerate(callback.call_args_list):
        assert call[0][0] == sink.events[i]
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/test_sinks.py::test_web_sink_callback_is_called_on_each_event -v`
Expected: FAIL — `WebTurnSink.__init__()` 不接受 `event_callback` 参数

- [ ] **Step 3: 修改 WebTurnSink**

修改 `simple_agent/core/sinks.py` 中 `WebTurnSink` 类：

```python
class WebTurnSink:
    """OutputSink implementation that accumulates events into a list for HTTP return.

    When event_callback is provided, each event is also passed to the callback
    immediately (used by SSE streaming). Without callback, behavior is unchanged.
    """

    def __init__(self, event_callback=None):
        self.events: list[dict] = []
        self._event_callback = event_callback

    def _emit(self, event: dict):
        self.events.append(event)
        if self._event_callback:
            self._event_callback(event)

    def on_message(self, role: str, content: str) -> None:
        self._emit({"type": "message", "role": role, "content": content})

    def on_error(self, message: str) -> None:
        self._emit({"type": "error", "message": message})

    def on_tool_start(self, tool_name: str, arguments: dict, call_id: str) -> None:
        self._emit({
            "type": "tool_start",
            "tool_name": tool_name,
            "arguments": arguments,
            "call_id": call_id,
        })

    def on_tool_end(
        self, tool_name: str, arguments: dict, call_id: str,
        result: dict, success: bool,
    ) -> None:
        self._emit({
            "type": "tool_end",
            "tool_name": tool_name,
            "arguments": arguments,
            "call_id": call_id,
            "result": result,
            "success": success,
        })

    def on_turn_start(self, user_input: str) -> None:
        self._emit({"type": "turn_start", "user_input": user_input})

    def on_turn_end(self) -> None:
        self._emit({"type": "turn_end"})

    def on_status(self, kind: str, data: dict) -> None:
        self._emit({"type": "status", "kind": kind, "data": data})
```

- [ ] **Step 4: 运行全部 sinks 测试**

Run: `pytest tests/test_sinks.py -v`
Expected: 13 passed (6 CliSink + 6 old WebTurnSink + 1 new callback test)

- [ ] **Step 5: 跑全量 pytest**

Run: `pytest --tb=no -q`
Expected: 3 pre-existing SOCKS failures in test_api.py, everything else passes

- [ ] **Step 6: 提交**

```bash
git add simple_agent/core/sinks.py tests/test_sinks.py
git commit -m "refactor: WebTurnSink 新增 event_callback + _emit 方法

每个事件同时 append 到 list 并调 callback（如果有的话），为 SSE 流式推送提供桥接点。callback 默认 None，现有行为不变。"
```

---

## Task 2: /api/turn 改为 SSE

**Files:**
- Modify: `simple_agent/web/chat_server.py:1-9,65-97`

- [ ] **Step 1: 修改 imports**

把 `simple_agent/web/chat_server.py` 顶部的 import 行：

```python
from flask import Flask, jsonify, request, send_from_directory
```

改为：

```python
import json
import queue
from flask import Flask, jsonify, request, send_from_directory, Response, stream_with_context
```

- [ ] **Step 2: 替换 api_turn 函数**

把 `chat_server.py` 中整个 `api_turn` 函数（约第 65-97 行）替换为：

```python
@app.route("/api/turn", methods=["POST"])
def api_turn():
    """Execute one conversation turn, streaming events via SSE."""
    if _runtime is None or _sink is None:
        return jsonify({"error": "Runtime not initialized"}), 500

    payload = request.get_json(silent=True) or {}
    user_input = payload.get("input", "")

    if not user_input.strip():
        return jsonify({"error": "empty input"}), 400

    event_queue: queue.Queue = queue.Queue()

    def on_event(event: dict):
        event_queue.put(event)

    def run_turn():
        with _runtime_lock:
            _sink.events.clear()
            _sink._event_callback = on_event
            try:
                result = _runtime.process_input(user_input)
                if result in ("message_processed", "command_processed"):
                    _runtime._run_one_turn()
                elif result == "exit":
                    _sink.on_message("system", "Session ended.")
                else:
                    _sink.on_message("system", result)
            except HookBlockedException as e:
                _sink.on_message("system", f"[BLOCKED] {e}")
            except Exception as e:
                _sink.on_error(f"{type(e).__name__}: {e}")
            finally:
                _sink.on_turn_end()
                event_queue.put(None)  # sentinel: turn finished

    thread = threading.Thread(target=run_turn, daemon=True)
    thread.start()

    def generate():
        while True:
            event = event_queue.get()
            if event is None:
                yield f"data: {json.dumps({'type': 'turn_done', 'session_id': _runtime._session_id})}\n\n"
                break
            yield f"data: {json.dumps(event)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

关键点：
- `_runtime_lock` 在 `run_turn` 线程内持有，SSE 生成器不持锁
- `_sink.on_turn_end()` 在 finally 里显式调用（与 Runtime._run_one_turn 的 try/finally 可能双重发出 turn_end，但前端忽略重复 turn_end，无害）
- `event_queue.put(None)` 是终止标记，generate() 收到后发出 `turn_done` 并结束

- [ ] **Step 3: 跑全量 pytest 确认只有 SSE 相关测试需要重写**

Run: `pytest --tb=line -q 2>&1 | head -30`

Expected: 5-6 failures in `test_web_chat.py` (the old `/api/turn` JSON-format assertions), everything else passes. The failures are because `/api/turn` now returns SSE text, not JSON.

- [ ] **Step 4: 提交**

```bash
git add simple_agent/web/chat_server.py
git commit -m "feat: /api/turn 改为 SSE 流式推送

Runtime 在后台线程执行，事件通过 queue.Queue 桥接到 SSE 生成器，每个事件产生即推送。"
```

---

## Task 3: 重写 /api/turn 测试为 SSE 格式

**Files:**
- Modify: `tests/test_web_chat.py`

- [ ] **Step 1: 添加 SSE 解析辅助函数**

在 `tests/test_web_chat.py` 顶部（fixture 之后）添加：

```python
def parse_sse_events(response_data: bytes) -> list[dict]:
    """Parse SSE response body into a list of event dicts."""
    events = []
    text = response_data.decode("utf-8")
    for part in text.split("\n\n"):
        part = part.strip()
        if not part.startswith("data: "):
            continue
        events.append(json.loads(part[6:]))
    return events
```

同时在文件顶部 imports 中添加 `import json`。

- [ ] **Step 2: 重写 test_api_turn_returns_events_for_plain_message**

替换原测试为：

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
    assert resp.content_type.startswith("text/event-stream")
    events = parse_sse_events(resp.data)
    types = [e["type"] for e in events]
    assert "turn_start" in types
    assert "message" in types
    assert "turn_end" in types
    assert "turn_done" in types
    msg = next(e for e in events if e["type"] == "message")
    assert msg["content"] == "Hi there!"
    turn_done = next(e for e in events if e["type"] == "turn_done")
    assert turn_done["session_id"] == chat_server._runtime._session_id
```

- [ ] **Step 3: 重写 test_api_turn_clears_events_between_turns**

```python
def test_api_turn_clears_events_between_turns(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.return_value = [
        {"role": "assistant", "content": "ok"}
    ]

    client = chat_server.app.test_client()
    resp1 = client.post("/api/turn", json={"input": "first"})
    events1 = parse_sse_events(resp1.data)
    resp2 = client.post("/api/turn", json={"input": "second"})
    events2 = parse_sse_events(resp2.data)

    # 第二轮的 events 不应含第一轮的 turn_start
    first_inputs = [e for e in events2 if e.get("user_input") == "first"]
    assert len(first_inputs) == 0
    second_inputs = [e for e in events2 if e.get("user_input") == "second"]
    assert len(second_inputs) == 1
```

- [ ] **Step 4: 重写 test_api_turn_handles_slash_command**

```python
def test_api_turn_handles_slash_command(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.post("/api/turn", json={"input": "/help"})

    assert resp.status_code == 200
    events = parse_sse_events(resp.data)
    assert any(
        e["type"] == "message" and "Available Commands" in e.get("content", "")
        for e in events
    )
    assert any(e["type"] == "turn_done" for e in events)
```

- [ ] **Step 5: 重写 test_api_turn_handles_exception_via_sink_error**

```python
def test_api_turn_handles_exception_via_sink_error(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.side_effect = RuntimeError("boom")

    client = chat_server.app.test_client()
    resp = client.post("/api/turn", json={"input": "hi"})

    assert resp.status_code == 200
    events = parse_sse_events(resp.data)
    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    assert "boom" in error_events[0]["message"]
```

- [ ] **Step 6: 重写 test_api_turn_emits_turn_end_even_on_exception**

```python
def test_api_turn_emits_turn_end_even_on_exception(tmpcwd):
    """If API raises, the SSE stream should still include turn_end and turn_done."""
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.side_effect = RuntimeError("boom")

    client = chat_server.app.test_client()
    resp = client.post("/api/turn", json={"input": "hi"})

    assert resp.status_code == 200
    events = parse_sse_events(resp.data)
    types = [e["type"] for e in events]
    assert "turn_start" in types
    assert "error" in types
    assert "turn_end" in types
    assert "turn_done" in types
```

- [ ] **Step 7: 跑全部 web_chat 测试**

Run: `pytest tests/test_web_chat.py -v`
Expected: All pass (both SSE tests and untouched sidebar/logs/resume/index tests)

- [ ] **Step 8: 跑全量 pytest**

Run: `pytest --tb=no -q`
Expected: 3 pre-existing SOCKS failures, everything else passes

- [ ] **Step 9: 提交**

```bash
git add tests/test_web_chat.py
git commit -m "test: 重写 /api/turn 测试为 SSE 格式断言

添加 parse_sse_events 辅助函数，所有 turn 相关测试改为解析 SSE 事件流而非 JSON。"
```

---

## Task 4: 前端 sendTurn 改为 SSE 消费

**Files:**
- Modify: `simple_agent/web/static/chat.js:123-144`

- [ ] **Step 1: 替换 sendTurn 函数**

把 `chat.js` 中的 `sendTurn` 函数（第 123-144 行）替换为：

```javascript
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

    if (!resp.ok) {
      const err = await resp.json();
      appendError(`Error: ${err.error || resp.statusText}`);
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split('\n\n');
      buffer = parts.pop();
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data: ')) continue;
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === 'turn_done') continue;
          renderEvent(event);
        } catch (e) {
          console.warn('Failed to parse SSE event', line, e);
        }
      }
    }
    refreshSidebar();
  } catch (e) {
    appendError(`Request failed: ${e.message || e}`);
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = '发送';
  }
}
```

关键点：
- `resp.ok` 检查：400/500 等错误（如 empty input）不走 SSE，仍返回 JSON，提前处理
- `reader.read()` 逐块读取 SSE 流，按 `\n\n` 拆分事件
- `renderEvent(event)` 完全复用，事件格式不变
- `turn_done` 被忽略（结束标记，前端不需要）
- `try/catch` 包裹 JSON.parse 防止格式异常导致整个流崩溃

- [ ] **Step 2: 跑全量 pytest**

Run: `pytest --tb=no -q`
Expected: 不受影响，全部通过（前端文件无 pytest 覆盖）

- [ ] **Step 3: 提交**

```bash
git add simple_agent/web/static/chat.js
git commit -m "feat: 前端 sendTurn 改为 SSE 流式消费

用 fetch + ReadableStream 逐条读取后端推送的事件，每个事件到达即渲染，不再等整轮完成。"
```

---

## 自检结果

**1. Spec coverage:**

| Spec 要求 | 对应 Task |
|-----------|----------|
| WebTurnSink 加 event_callback + _emit | Task 1 |
| 每个 on_* 方法改用 _emit | Task 1 |
| /api/turn 改为 SSE Response | Task 2 |
| 后台线程 + queue.Queue 桥接 | Task 2 |
| _runtime_lock 在 run_turn 内 | Task 2 |
| sentinel None + turn_done | Task 2 |
| Cache-Control / X-Accel-Buffering headers | Task 2 |
| 前端 fetch + ReadableStream | Task 4 |
| SSE 行解析 (data: + \n\n) | Task 4 |
| turn_done 忽略 | Task 4 |
| WebTurnSink callback 测试 | Task 1 |
| SSE 格式测试 (Content-Type, event sequence) | Task 3 |
| 错误场景 SSE 测试 | Task 3 |
| 兼容性（其他路由不变） | Task 2/4 不动其他路由 |

✓ 全部覆盖。

**2. Placeholder scan:** 无 TBD/TODO。每个步骤含完整代码。✓

**3. Type consistency:**
- `WebTurnSink.__init__(event_callback=None)` 签名在 Task 1 定义，Task 2 中 `_sink._event_callback = on_event` 使用同一属性名。✓
- `event_queue: queue.Queue` 和 `event_queue.put(event)` / `event_queue.get()` 类型一致。✓
- SSE 行格式 `data: {json}\n\n` 在 Task 2 生成和 Task 4 解析端一致。✓
- `turn_done` 事件格式 `{'type': 'turn_done', 'session_id': ...}` 在 Task 2 生成、Task 3 断言、Task 4 忽略，全部一致。✓
