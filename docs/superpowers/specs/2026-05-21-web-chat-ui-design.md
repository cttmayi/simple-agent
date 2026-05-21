# Web 聊天 UI 设计

## 背景与目标

simple-agent 当前只有 CLI 交互方式（`simple-agent` 命令，基于 rich + prompt_toolkit）。本项目为 simple-agent 增加一个浏览器内的交互式对话界面，让用户在 Web 中与 agent 实时对话，能看到工具调用过程、TODO 进度、加载的 skills 等信息。

现有 `simple_agent/web/` 目录里已经存在一个只读的日志分析器（`server.py` + `analyzer.html`），与本项目无关，将保持不变。

## 关键决定

- **单会话模式**：一个 Web server 进程对应一个 agent session，与 CLI 行为一致。所有打开页面的浏览器看到同一个 session。
- **独立 Web 服务**：通过 `simple-agent --web-chat` 启动，不与 CLI 同时运行。
- **一次性返回（轮询）**：不引入 SSE/WebSocket。前端 `POST /api/turn` 后等待完整回合（含所有递归工具调用）后一次性收到事件列表。
- **支持从日志 resume**：与 CLI `--resume` 一致，可加载历史日志继续对话。
- **方案 B：Runtime 解耦**：把 Runtime 中输出到用户的调用收敛到一个 `OutputSink` 接口，CLI 和 Web 各自实现，长期架构更干净。

## 架构总览

```
┌────────────────────────────────────────────────────────────┐
│                      Runtime (核心引擎)                    │
│  - 构造时注入 OutputSink                                   │
│  - 不直接 import UIRenderer                                │
│  - process_input / API call / tool_calls 递归全部内部进行  │
│  - 所有给用户看的输出都调用 self._sink.xxx(...)            │
└──────────────────────┬─────────────────────────────────────┘
                       │ OutputSink 接口
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼─────────┐         ┌─────────▼─────────────┐
│  CliSink        │         │  WebTurnSink           │
│  (包 UIRenderer) │        │  (攒事件到 list)        │
└─────────────────┘         └────────────────────────┘
        │                             │
   CLI 入口                      Web Flask 路由
   simple-agent                  simple-agent --web-chat
                                       │
                                  http://localhost:5002
                                       │
                                  ┌────▼────────┐
                                  │ 单页 HTML/JS │
                                  │  - 消息流    │
                                  │  - 输入框    │
                                  │  - 侧边栏    │
                                  │  - 工具卡片  │
                                  └─────────────┘
```

- 一个 `Runtime` 实例 = 一个会话，以**模块级单例**保存在 `chat_server.py` 中。
- Web 端通过 `POST /api/turn { input: "..." }` 触发一轮，server 同步等到 Runtime 处理完整轮后返回攒到的事件列表。
- 端口 5002（避开现有 analyzer 的 5001）。

## OutputSink 接口

把 Runtime 当前对 `self._renderer` 和直接 `print` 的所有调用归纳为 7 个语义事件：

```python
class OutputSink(Protocol):
    def on_message(self, role: str, content: str) -> None: ...
        # role ∈ {assistant, system}; 用户消息由前端发起，无需推送

    def on_error(self, message: str) -> None: ...

    def on_tool_start(self, tool_name: str, arguments: dict, call_id: str) -> None: ...
        # 工具开始执行（CLI: 打印 "tool_name [args=...]" 不换行）

    def on_tool_end(self, tool_name: str, arguments: dict, call_id: str,
                    result: dict, success: bool) -> None: ...
        # 工具执行完成（CLI: 打印 ✓/✗ 后调用 render_tool_result）

    def on_turn_start(self, user_input: str) -> None: ...
        # 用户提交一条输入开始处理

    def on_turn_end(self) -> None: ...
        # 本轮 LLM 不再产出 tool_calls，回合结束

    def on_status(self, kind: str, data: dict) -> None: ...
        # 扩展点：todo 变动、skill 加载等结构化状态事件
```

### 两个实现

**`CliSink`**（薄包装，调用现有 `UIRenderer` 和 `console.print`）

| 接口方法 | 行为 |
|----------|------|
| `on_message` | `renderer.render_message(role, content)` |
| `on_error` | `renderer.render_error(message)` |
| `on_tool_start` | `console.print(name + args_str, end="")` |
| `on_tool_end` | `console.print(" ✓/✗")` 然后 `renderer.render_tool_result(...)` |
| `on_turn_start` / `on_turn_end` / `on_status` | no-op |

**`WebTurnSink`**（一个长生命周期的实例，每轮开始时清空 events 列表）

每个方法把参数序列化成 `{"type": "...", ...payload}` 追加到 `self.events`。Flask 路由 `/api/turn` 返回前把 events 拷贝出来一次性 jsonify 返回。

事件结构示例：

```json
{"type": "message", "role": "assistant", "content": "..."}
{"type": "error", "message": "..."}
{"type": "tool_start", "tool_name": "READ", "arguments": {"path": "..."}, "call_id": "..."}
{"type": "tool_end", "tool_name": "READ", "arguments": {...}, "call_id": "...", "result": {...}, "success": true}
{"type": "turn_start", "user_input": "..."}
{"type": "turn_end"}
{"type": "status", "kind": "skill_loaded", "data": {"name": "..."}}
```

## Runtime 改动

| 改动 | 说明 |
|------|------|
| 构造函数加 `sink: OutputSink` 参数 | 默认 `CliSink(UIRenderer())`，保持向后兼容 |
| 抽出 `init_session()` 方法 | 当前在 `run()` 开头：生成 session_id、reset HookContext、log_session_start、发 SessionStart 事件、render 启动横幅 |
| 抽出 `_run_one_turn()` 方法 | 当前 `run()` 循环里：`_prepare_messages_with_context` → `api_client.send_message` → 遍历响应（递归 tool_calls 已存在）→ 把最终 assistant 消息加入 session 并 render |
| `run()` 重写 | 改为 `init_session()` + `while True: input → process_input → _run_one_turn()`，行为不变 |
| `process_input` 入口加 `sink.on_turn_start` | 与 UserPromptSubmit 事件并列 |
| `_run_one_turn` 末尾加 `sink.on_turn_end` | 在最后一条 assistant content 之后 |
| `_handle_tool_calls_in_message` 内 | 工具开始/结束的打印 → `sink.on_tool_start` / `sink.on_tool_end`；最终 assistant 文本 → `sink.on_message("assistant", content)` |
| `self._renderer` 保留 | hooks、slash command 输出短期内仍走 renderer；本项目不一次性清理。`CliSink` 内部持有同一个 renderer 实例 |

估计 Runtime 内 5–10 处调用点替换，新增 `core/sinks.py` 文件约 120 行。

## Web 后端

**单文件 `simple_agent/web/chat_server.py`**，基于 Flask（已是依赖）。

### 模块级状态

```python
_runtime: Optional[Runtime] = None     # 单例
_sink: Optional[WebTurnSink] = None    # 长生命周期
_runtime_lock = threading.Lock()       # 串行化对话回合
```

启动时由 `main.py` 调 `init_runtime(config, resume_log=None)` 构建 Runtime 并注入长生命周期的 `WebTurnSink`。

### HTTP 路由

| 方法 | 路径 | 用途 |
|------|------|------|
| `GET /` | 返回 `chat.html` | 主界面 |
| `GET /static/<path>` | 静态资源 | CSS/JS |
| `GET /api/session` | `{session_id, model, provider, messages: [...]}` | 前端初始化 |
| `POST /api/turn` body=`{input: "..."}` | `{events: [...], session_id}` | 核心对话接口 |
| `GET /api/sidebar` | `{todos, loaded_skills, available_skills, available_agents}` | 侧边栏数据 |
| `GET /api/logs` | 列出历史日志文件 | 供 resume 选择 |
| `POST /api/resume` body=`{log_file: "..."}` | 重建 runtime 加载指定日志 | 切换历史会话 |

### `/api/turn` 处理流程

```python
with _runtime_lock:
    _sink.events.clear()
    try:
        result = _runtime.process_input(payload["input"])
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
    return jsonify({
        "events": list(_sink.events),
        "session_id": _runtime._session_id,
    })
```

### Resume 流程

`POST /api/resume {log_file}` → 重建 Runtime（`init_runtime(config, resume_log=log_file)`）→ 旧 runtime GC。前端随后 `GET /api/session` 拿到完整 messages 重绘聊天历史。

### main.py 入口

```python
if "--web-chat" in sys.argv:
    from simple_agent.web.chat_server import init_runtime, app
    init_runtime(config, resume_log=resume_log)
    print("Web chat: http://localhost:5002")
    app.run(host='127.0.0.1', port=5002)
```

### 错误与边界

- **并发 turn**：`_runtime_lock` 串行化，第二个请求拿到锁前会等。
- **单会话约束**：所有打开此 URL 的浏览器看到同一个 session。
- **LLM/工具异常**：捕获后通过 `sink.on_error` 传到前端，不影响下一轮。
- **session_id 生成**：`init_session()` 中生成 uuid（CLI 和 Web 共用同一段代码）。

## 前端

### 文件结构

```
simple_agent/web/
├── server.py           # 现有日志分析器，保持不动
├── analyzer.html       # 现有，保持不动
├── chat_server.py      # 新增
└── static/
    ├── chat.html       # 新增 - 单页 SPA
    ├── chat.css        # 新增
    └── chat.js         # 新增
```

不引入 React/Vue 或构建步骤。用原生 JS + 两个 CDN 库：

- **marked.js**（Markdown 渲染）
- **highlight.js**（代码高亮）

### 页面布局

```
┌──────────────────────────────────────────────────────────────┐
│ Simple Agent  [session: abc123…]  [model: gpt-4o]    ⟳ 刷新  │ ← header
├─────────────────────────┬────────────────────────────────────┤
│                         │                                    │
│  ┌─ TODOs ───────┐      │  ┌──────────────────────────────┐  │
│  │ ☐ task 1      │      │  │ assistant: 你好...             │  │
│  │ ☑ task 2      │      │  └──────────────────────────────┘  │
│  └───────────────┘      │  ┌──────────────────────────────┐  │
│                         │  │ user: 帮我读 README            │  │
│  ┌─ Skills ──────┐      │  └──────────────────────────────┘  │
│  │ • brainstorm  │      │  ┌─ tool: READ [path=README] ✓ ┐  │
│  │ • debugging   │      │  │ ▶ (click to expand result)   │  │
│  └───────────────┘      │  └──────────────────────────────┘  │
│                         │  ┌──────────────────────────────┐  │
│  ┌─ Agents ──────┐      │  │ assistant: 这是项目...         │  │
│  │ • Explore     │      │  │ ```python                    │  │
│  └───────────────┘      │  │ def hello(): ...             │  │
│                         │  │ ```                          │  │
│                         │  └──────────────────────────────┘  │
│                         ├────────────────────────────────────┤
│                         │ [ 输入消息或 /命令...        ] [发送] │
└─────────────────────────┴────────────────────────────────────┘
```

### 核心 JS 逻辑

**初始化**：

```js
fetch('/api/session') → 拿到 session_id, model, messages[]
→ 遍历 messages 渲染历史
fetch('/api/sidebar') → 渲染 TODOs / skills / agents
```

**发送一轮**：

```js
async function sendTurn(input) {
  appendUserBubble(input);
  setInputLoading(true);
  const { events } = await fetch('/api/turn', {
    method: 'POST', body: JSON.stringify({input})
  }).then(r => r.json());
  for (const ev of events) renderEvent(ev);
  setInputLoading(false);
  refreshSidebar();   // TODOs/skills 可能变了
}
```

**事件 → DOM 映射**：

| 事件类型 | 渲染方式 |
|----------|----------|
| `message` (role=assistant) | 消息气泡，content 经 marked.js + highlight.js |
| `message` (role=system) | 浅色 system 气泡 |
| `error` | 红框气泡 |
| `tool_start` + `tool_end` | 前端按 `call_id` 合并为一个工具卡片。一次性返回模式下 `tool_start` 信息已含在 `tool_end` 里，前端可只渲染 `tool_end`；后端保留两个事件是为未来切流式留接口 |
| `turn_start` / `turn_end` | 用于 loading 指示器（可由 fetch 本身决定，可选） |
| `status` | 暂不显示，保留扩展点 |

**工具卡片**：默认折叠，标题显示 `工具名 [关键参数] ✓/✗`，点击展开看完整 arguments 和 result（result 用 `<pre>` 显示 JSON）。

**斜杠命令**：输入框内容以 `/` 开头时不做特殊处理，直接发到 `/api/turn` —— 后端 `process_input` 已经能识别斜杠命令。前端可加浮动提示"输入 /help 查看命令"。

**Resume UI**：header 加 ⟳ 按钮，点击弹出小对话框列出 `/api/logs` 返回的日志文件，选一个 → `POST /api/resume` → 刷新页面。

### 不做的（YAGNI）

- 不做用户登录/权限（本地工具）
- 不做多 tab 同步（单会话模式下天然一致，不引入 WebSocket）
- 不做主题切换（先暗色，与 analyzer 一致）
- 不做消息编辑/重新发送（CLI 也没有）
- 不做附件上传（CLI 也没有）

## 测试

新增 `tests/test_web_chat.py`：

- `WebTurnSink` 各 `on_*` 方法生成正确事件结构（每种事件 type 一个断言）
- `CliSink` 各 `on_*` 方法调用 `UIRenderer` 对应方法（用 mock 验证）
- `/api/turn` 走 mock 的 `APIClient`：
  - 模拟一次纯文本回复 → events 含 `message`
  - 模拟一次带 tool_calls 的回复 → events 含 `tool_start`、`tool_end`、最终 `message`
- `/api/session` 返回 session 元数据正确
- `/api/resume` 切换 runtime 后 `/api/session` 反映新的 messages
- `Runtime.init_session()` 单测：session_id 被设置、SessionStart 事件被发布
- `Runtime._run_one_turn()` 单测：mock api_client，验证 sink 收到 turn_start/message/turn_end

CLAUDE.md 要求提交前 pytest 通过 —— 视为硬要求。前端不写自动化测试（本地工具，手动验证成本更低）。

## 开发顺序（供 writing-plans 参考）

1. 新增 `core/sinks.py`，定义 `OutputSink` 协议 + `CliSink` + `WebTurnSink`，写单元测试
2. 抽出 `Runtime.init_session()` 和 `_run_one_turn()`，CLI `run()` 改写为调用这两个方法，跑 pytest 验证 CLI 行为不变
3. Runtime 构造函数注入 sink，把 5–10 处调用点改为走 sink，CLI 跑通
4. 新增 `web/chat_server.py`，实现 `/api/session`、`/api/turn`，用 mock api_client 写后端测试
5. 实现 `/api/sidebar`、`/api/logs`、`/api/resume`
6. 新增 `web/static/chat.html` / `chat.css` / `chat.js`，本地手动验证全部交互
7. `main.py` 加 `--web-chat` 入口
8. 更新 `CLAUDE.md` 和 `README.md`，记录新命令
