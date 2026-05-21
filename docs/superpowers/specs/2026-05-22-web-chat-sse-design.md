# Web Chat SSE 流式推送设计

## 背景与目标

当前 Web Chat 的 `/api/turn` 端点同步执行一整轮对话（含所有递归 tool_calls），攒完事件后一次性 JSON 返回。用户在等待期间看不到任何进展（工具调用、中间状态），体验差。

本设计将传输层从"一次性返回"改为 SSE (Server-Sent Events) 流式推送：每个事件（tool_start、tool_end、message、error、turn_end）产生时立即推送到前端。

**不涉及 LLM token 级流式**——assistant 文本仍等 LLM 返回完整段落后一次推送；工具调用事件即时推送。

## 关键决定

- **SSE (Server-Sent Events)**：单向推送标准协议，Flask 原生支持，前端用 `fetch` + `ReadableStream` 消费，不引入新依赖
- **事件级粒度**：每个 WebTurnSink 事件产生即推送，不需要改 APIClient 的 streaming 模式
- **后台线程执行 Runtime**：SSE 生成器在请求线程 yield，Runtime 在 daemon 线程跑，通过 `queue.Queue` 桥接

## 架构

```
浏览器                     Flask 请求线程              Runtime 线程
  │                            │                          │
  │── POST /api/turn ────────>│                          │
  │                            │  创建 Queue + Thread     │
  │                            │  thread.start()          │
  │                            │                          │
  │<── data: {turn_start} ────│<── queue.put(event) ────│ sink.on_turn_start()
  │                            │                          │
  │<── data: {tool_start} ────│<── queue.put(event) ────│ sink.on_tool_start()
  │<── data: {tool_end} ──────│<── queue.put(event) ────│ sink.on_tool_end()
  │                            │                          │
  │<── data: {message} ───────│<── queue.put(event) ────│ sink.on_message()
  │<── data: {turn_end} ──────│<── queue.put(event) ────│ sink.on_turn_end()
  │                            │                          │
  │<── data: {turn_done} ─────│<── queue.put(None) ─────│ (sentinel)
  │                            │                          │
```

## WebTurnSink 改动

新增 `event_callback` 参数，每产出一个事件同时 append 到 `events` list 并调 callback：

```python
class WebTurnSink:
    def __init__(self, event_callback=None):
        self.events: list[dict] = []
        self._event_callback = event_callback

    def _emit(self, event: dict):
        self.events.append(event)
        if self._event_callback:
            self._event_callback(event)
```

每个 `on_*` 方法内部改为调 `self._emit({...})` 替代直接 `self.events.append(...)`。

`event_callback` 默认 None，现有行为不变（测试仍可断言 `sink.events`）。

## /api/turn 改动

从 `return jsonify(...)` 改为 SSE Response：

```python
@app.route("/api/turn", methods=["POST"])
def api_turn():
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
                _sink.on_turn_end()   # 确保总是发出
                event_queue.put(None) # sentinel: turn finished

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

注意：`_runtime_lock` 在 `run_turn` 线程内持有，SSE 生成器不持锁（只读 queue）。`_sink.on_turn_end()` 在 finally 里显式调用，确保 `turn_done` 之前总有 `turn_end`。

## 前端改动

`chat.js` 的 `sendTurn` 改为 SSE 消费，其余代码不变：

```javascript
async function sendTurn(input) {
  appendBubble('user', input);
  inputBox.value = '';
  setInputLoading(true);

  try {
    const resp = await fetch('/api/turn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input }),
    });

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
        const event = JSON.parse(line.slice(6));
        if (event.type === 'turn_done') continue;
        renderEvent(event);
      }
    }
    refreshSidebar();
  } catch (e) {
    appendError(`Request failed: ${e.message || e}`);
  } finally {
    setInputLoading(false);
  }
}
```

关键点：
- `renderEvent(event)` 完全复用，事件格式与之前 `events[]` 每条一致
- 用 `fetch` + `ReadableStream` 而非 `EventSource`（因为 SSE 端点是 POST，`EventSource` 只支持 GET）
- `turn_done` 是结束标记，前端忽略其内容

## 测试

### WebTurnSink 测试

- 现有 6 个测试仍通过（callback 默认 None）
- 新增：传 mock callback，验证 `_emit` 同时 append + callback 调用
- 新增：验证 callback 接收的 event dict 与 `sink.events[-1]` 相同

### /api/turn SSE 测试

- 验证响应 Content-Type 为 `text/event-stream`
- 读取完整响应体，解析 SSE 行，验证事件序列包含 turn_start → message → turn_end → turn_done
- 带 tool_calls 场景：验证 tool_start/tool_end 在 turn_start 和 turn_end 之间
- 错误场景：验证 error 事件后仍有 turn_end + turn_done

### 兼容性

- `/api/session`、`/api/sidebar`、`/api/logs`、`/api/resume` 全部不变
- `CliSink` 不变
- 前端侧边栏、resume 对话框、输入框快捷键不变

## 不做的（YAGNI）

- 不做 LLM token 级流式
- 不做 SSE 断线重连
- 不做前端进度条（已有 loading spinner）
