# Hook 机制设计文档

## 概述

重构 Hook 机制，使用目录结构识别事件，支持 Python 函数返回值来控制执行流程。

## 目录结构

```
.simple-agent/hooks/
├── session_start/
│   ├── init.py
│   └── log.sh
├── session_end/
│   └── cleanup.py
├── message_sent/
│   └── log.py
├── message_received/
│   └── analyze.py
├── tool_call_before/
│   ├── validate.py
│   └── security_check.sh
├── tool_call_after/
│   └── log_result.py
├── tool_call_failed/
│   └── retry.py
├── skill_loaded/
│   └── notify.py
├── subagent_loaded/
│   └── init.py
├── hook_loaded/
│   └── verify.py
└── error_occurred/
    └── report.py
```

## 支持的事件

| 事件名 | 描述 | 可阻止 |
|---------|------|--------|
| session_start | 会话启动 | 否 |
| session_end | 会话结束 | 否 |
| message_sent | 消息发送（user/assistant/system/tool） | 否 |
| message_received | 收到 AI 回复 | 否 |
| tool_call_before | 工具调用前 | **是** |
| tool_call_after | 工具调用后 | 否 |
| tool_call_failed | 工具调用失败 | 否 |
| skill_loaded | 技能加载 | 否 |
| subagent_loaded | 子agent 加载 | 否 |
| hook_loaded | Hook 加载 | 否 |
| error_occurred | 发生错误 | 否 |

## Hook 文件类型

| 文件类型 | 处理方式 | 返回值 |
|-----------|-----------|--------|
| `.py` | Python 函数 hook，支持 block | `dict` |
| `.sh` / `.cmd` | Shell 命令，只执行不返回 | 无 |
| `.md` | Prompt hook，发送给 AI | 无 |

## Hook 返回值格式

```python
# 继续执行（或不返回/返回 None）
return {"action": "continue"}

# 阻止执行（仅 tool_call_before 支持）
return {"action": "block", "message": "不允许执行此命令"}
```

## 执行规则

1. 按目录下文件名字母顺序执行
2. 第一个 `block` 立即停止后续 hook 执行
3. 仅 `tool_call_before` 事件的 hook 支持阻止功能

## 事件数据

| 事件 | 数据字段 |
|------|----------|
| session_start | `session_id: str` |
| session_end | `session_id: str` |
| message_sent | `role: str, content: str` |
| message_received | `role: str, content: str` |
| tool_call_before | `tool_name: str, arguments: dict` |
| tool_call_after | `tool_name: str, arguments: dict, result: dict` |
| tool_call_failed | `tool_name: str, arguments: dict, error: str` |
| skill_loaded | `skill_name: str` |
| subagent_loaded | `subagent_name: str` |
| hook_loaded | `hook_name: str` |
| error_occurred | `error_type: str, error_message: str` |

## Hook 函数签名

```python
# tool_call_before.py
def on_tool_call_before(tool_name: str, arguments: dict) -> dict:
    if tool_name == "dangerous_command":
        return {"action": "block", "message": "危险命令被阻止"}
    return {"action": "continue"}

# 其他事件的 hook
def on_event_name(**data) -> Optional[dict]:
    # 处理逻辑
    pass
```

## 阻止行为

当 hook 返回 `{"action": "block", "message": "..."}` 时：

1. **终端显示** - 展示给用户
2. **记录日志** - 写入日志文件
3. **发送给 AI** - 让 AI 知道阻止原因
4. **停止执行** - 后续 hook 不执行，工具不调用

## 实现要点

### 1. HookLoader 修改

- 改为扫描 `hooks/` 目录的子目录
- 每个子目录名 = 事件名
- 扫描目录内所有 `.py`, `.sh`, `.cmd`, `.md` 文件

### 2. Runtime._load_hooks() 修改

- 遍历每个事件目录
- 为每个文件注册 handler
- 按文件名排序保证执行顺序

### 3. Runtime._execute_hook() 增强

- 支持返回值检查
- `tool_call_before` 事件处理 block 逻辑
- block 时多位置输出（终端、日志、AI）

### 4. 事件发布位置

- `session_start` - Runtime.run() 开始
- `session_end` - Runtime.run() 结束
- `message_sent` - Session.add_message() 后
- `message_received` - 收到 API 响应后
- `tool_call_before` - ToolDispatcher.execute() 前
- `tool_call_after` - 工具执行成功后
- `tool_call_failed` - 工具执行失败时
- `skill_loaded` - LoadSubagent 执行后
- `subagent_loaded` - LoadSubagent 执行后
- `hook_loaded` - Runtime._load_hooks() 执行后
- `error_occurred` - 捕获异常时

## 示例 Hook

### tool_call_before - 安全检查

```python
# .simple-agent/hooks/tool_call_before/security_check.py

def on_tool_call_before(tool_name: str, arguments: dict) -> dict:
    # 阻止 rm -rf 命令
    if tool_name == "bash" and "command" in arguments:
        cmd = arguments["command"]
        if "rm -rf" in cmd or "rm -fr" in cmd:
            return {"action": "block", "message": "禁止执行 rm -rf 命令"}
    return {"action": "continue"}
```

### session_start - 记录会话

```python
# .simple-agent/hooks/session_start/init.py

from pathlib import Path

def on_session_start(session_id: str) -> None:
    log_file = Path(".simple-agent") / "sessions.log"
    log_file.parent.mkdir(exist_ok=True)
    with open(log_file, "a") as f:
        f.write(f"Session started: {session_id}\n")
```

### message_sent - 统计

```python
# .simple-agent/hooks/message_sent/analyze.py

from pathlib import Path

_stats_file = Path(".simple-agent") / "message_stats.json"

def on_message_sent(role: str, content: str) -> None:
    import json
    stats = {}
    if _stats_file.exists():
        with open(_stats_file) as f:
            stats = json.load(f)
    stats[f"{role}_count"] = stats.get(f"{role}_count", 0) + 1
    _stats_file.parent.mkdir(exist_ok=True)
    with open(_stats_file, "w") as f:
        json.dump(stats, f)
```