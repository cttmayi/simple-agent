# Hooks System

Hooks allow you to execute custom logic when specific events occur.

## Directory Structure

```
.simple-agent/hooks/
├── session_start/
│   ├── init.py
│   └── log.sh
├── message_sent/
│   └── log.py
└── tool_call_before/
    └── security.py
```

## Event Types

| Event Name | Description | Blockable |
|-----------|-------------|-----------|
| session_start | Session started | No |
| session_end | Session ended | No |
| message_sent | Message sent | No |
| message_received | AI response received | No |
| tool_call_before | Before tool call | **Yes** |
| tool_call_after | After tool call | No |
| tool_call_failed | Tool call failed | No |
| skill_loaded | Skill loaded | No |
| subagent_loaded | Subagent loaded | No |
| hook_loaded | Hook loaded | No |
| error_occurred | Error occurred | No |

## Hook Types

| File Type | Handling |
|-----------|-----------|
| `.py` | Python function, supports return value control |
| `.sh` / `.cmd` | Shell command |
| `.md` | Prompt hook (sent to AI) |

## Examples

### session_start - Display welcome message

```python
# .simple-agent/hooks/session_start/welcome.py

def on_session_start(session_id: str) -> None:
    print(f"🚀 Session {session_id[:8]} started!")
```

### tool_call_before - Block dangerous commands

```python
# .simple-agent/hooks/tool_call_before/security.py

def on_tool_call_before(tool_name: str, arguments: dict) -> dict:
    if tool_name == "bash" and "command" in arguments:
        cmd = arguments["command"]
        if "rm -rf" in cmd or "rm -fr" in cmd:
            return {"action": "block", "message": "禁止执行 rm -rf 命令"}
    return {"action": "continue"}
```

### message_sent - Log messages

```bash
# .simple-agent/hooks/message_sent/log.sh
echo "[$(date)] Message sent" >> .simple-agent/message.log
```

## Hook Return Values (Python Only)

Python hooks can return a dict to control execution:

```python
# Block execution
return {"action": "block", "message": "Reason for blocking"}

# Continue (optional, default behavior)
return {"action": "continue"}

# No return value (default: continue)
return None
```

## Event Data

Each hook function receives event data as keyword arguments:

- `session_start`: `session_id: str`
- `session_end`: `session_id: str`
- `message_sent`: `role: str`, `content: str`
- `message_received`: `role: str`, `content: str`
- `tool_call_before`: `tool_name: str`, `arguments: dict`
- `tool_call_after`: `tool_name: str`, `arguments: dict`, `result: dict`
- `tool_call_failed`: `tool_name: str`, `arguments: dict`, `error: str`
- `skill_loaded`: `skill_name: str`
- `subagent_loaded`: `subagent_name: str`
- `hook_loaded`: `hook_name: str`
- `error_occurred`: `error_type: str`, `error_message: str`