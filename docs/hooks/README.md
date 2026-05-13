# Hooks 系统

Hooks 允许您在特定事件发生时执行自定义逻辑，扩展 simple-agent 的功能。

## 支持的事件类型

| 事件名称 | 描述 | 可阻止 | 触发时机 |
|---------|------|-------|---------|
| `SessionStart` | 会话开始 | 否 | agent 启动时 |
| `Stop` | 会话结束 | 否 | agent 退出时 |
| `UserPromptSubmit` | 消息发送 | 否 | 用户发送消息后 |
| `PostMessage` | 收到响应 | 否 | AI 响应返回时 |
| `PreToolUse` | 工具调用前 | **是** | 工具执行之前 |
| `PostToolUse` | 工具调用后 | 否 | 工具执行之后 |
| `ToolUseFailed` | 工具调用失败 | 否 | 工具执行出错时 |
| `SkillLoaded` | Skill 加载 | 否 | `/skill` 命令加载 skill 时 |
| `SubagentLoaded` | Subagent 加载 | 否 | `/agent` 命令加载 subagent 时 |
| `hook_loaded` | Hook 加载 | 否 | 每个 hook 加载时 |
| `Error` | 错误发生 | 否 | 运行时出现错误时 |

## 目录结构

```
.simple-agent/hooks/
├── SessionStart/           # 会话开始时触发
│   ├── welcome.py          # 欢迎消息
│   └── init.sh             # 初始化脚本
├── Stop/                  # 会话结束时触发
│   └── cleanup.sh          # 清理工作
├── UserPromptSubmit/         # 消息发送时触发
│   ├── log.py              # 记录消息
│   └── inject.py           # 动态注入
├── PostMessage/             # 收到响应时触发
│   ├── notify.py           # 通知
│   └── format.py           # 格式化
├── PreToolUse/            # 工具调用前触发（可阻止）
│   ├── security.py          # 安全检查
│   └── log.sh              # 记录
├── PostToolUse/             # 工具调用后触发
│   ├── summary.py          # 摘要统计
│   └── format.py           # 格式化
├── ToolUseFailed/            # 工具调用失败时触发
│   ├── alert.py            # 告警
│   └── retry.py            # 重试
├── SkillLoaded/             # Skill 加载时触发
│   └── notify.py
├── SubagentLoaded/          # Subagent 加载时触发
│   └── notify.py
└── hook_loaded/             # Hook 加载时触发
    └── notify.py
```

## Hook 文件类型

| 文件类型 | 说明 | 功能 |
|---------|------|------|
| `.py` | Python 脚本 | 支持返回值控制，可阻止执行 |
| `.sh` / `.cmd` | Shell 脚本 | 执行命令，返回 stdout 作为注入内容 |
| `.md` | Markdown 文件 | Prompt hook，内容会发送给 AI |

## 使用方法

### Python Hook

Python hook 函数名直接使用事件名（如 `session_start`）：

```python
# .simple-agent/hooks/SessionStart/welcome.py

def session_start(session_id: str, hook_context) -> None:
    """会话开始时显示欢迎消息"""
    short_id = session_id[:8] if len(session_id) > 8 else session_id
    print(f"🚀 会话已启动! ID: {short_id}")
```

#### 返回值控制（仅限可阻止的事件）

```python
# .simple-agent/hooks/PreToolUse/safety.py

def pre_tool_use(tool_name: str, arguments: dict, hook_context) -> dict:
    """阻止危险的工具调用"""

    # 阻止执行
    if "dangerous" in arguments:
        return {"action": "block", "message": "危险操作已被阻止"}

    # 继续执行（可选，默认行为）
    return {"action": "continue"}

    # 也可以返回 None，效果等同于 continue
```

### Shell Hook

```bash
#!/bin/bash
# .simple-agent/hooks/UserPromptSubmit/log.sh

LOG_FILE=".simple-agent/messages.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Message sent" >> "$LOG_FILE"
```

Shell hook 的 stdout 会被拼接到用户消息前。

### Prompt Hook (.md)

```markdown
# .simple-agent/hooks/SessionStart/instruction.md

你是专业的编程助手，请使用中文回答所有问题。
```

## 事件数据

每个 hook 函数接收对应事件的数据作为关键字参数（Python hook 还会自动接收 `hook_context` 参数）：

| 事件名称 | 参数 | 类型 | 说明 |
|---------|------|------|------|
| `SessionStart` | `session_id`, `hook_context` | `str`, `HookContext` | 会话 ID、共享状态 |
| `Stop` | `session_id`, `hook_context` | `str`, `HookContext` | 会话 ID、共享状态 |
| `UserPromptSubmit` | `role`, `content`, `hook_context` | `str`, `str`, `HookContext` | 角色、内容、共享状态 |
| `PostMessage` | `role`, `content`, `hook_context` | `str`, `str`, `HookContext` | 角色、内容、共享状态 |
| `PreToolUse` | `tool_name`, `arguments`, `hook_context` | `str`, `dict`, `HookContext` | 工具名、参数、共享状态 |
| `PostToolUse` | `tool_name`, `arguments`, `result`, `hook_context` | `str`, `dict`, `dict`, `HookContext` | 工具名、参数、结果、共享状态 |
| `ToolUseFailed` | `tool_name`, `arguments`, `error`, `hook_context` | `str`, `dict`, `str`, `HookContext` | 工具名、参数、错误信息、共享状态 |
| `SkillLoaded` | `skill_name`, `hook_context` | `str`, `HookContext` | Skill 名称、共享状态 |
| `SubagentLoaded` | `subagent_name`, `hook_context` | `str`, `HookContext` | Subagent 名称、共享状态 |
| `hook_loaded` | `hook_name`, `hook_context` | `str`, `HookContext` | Hook 名称、共享状态 |
| `Error` | `error_type`, `error_message`, `hook_context` | `str`, `str`, `HookContext` | 错误类型、错误消息、共享状态 |

## HookContext 共享状态

`HookContext` 是一个单例对象，允许所有 hook 直接共享内存中的变量，无需通过文件中转。

### 基本用法

```python
# 所有 hook 函数自动接收 hook_context 参数

def session_start(session_id: str, hook_context) -> None:
    # 直接访问共享状态
    hook_context.messages_sent += 1
    hook_context.set("my_key", "my_value")
```

### 内置变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `session_id` | `str` | 会话 ID |
| `start_time` | `datetime` | 会话开始时间 |
| `messages_sent` | `int` | 发送消息数 |
| `messages_received` | `int` | 接收消息数 |
| `tools_called` | `int` | 工具调用总数 |
| `tools_succeeded` | `int` | 工具成功数 |
| `tools_failed` | `int` | 工具失败数 |
| `user_messages` | `List[dict]` | 用户消息列表 |
| `assistant_messages` | `List[dict]` | 助手消息列表 |
| `tools_used` | `List[dict]` | 工具使用记录 |
| `keywords` | `List[str]` | 提取的关键词 |
| `errors` | `List[dict]` | 错误记录 |

### API 方法

#### set(key, value) / get(key, default=None)
设置和获取自定义值：

```python
hook_context.set("user_name", "Alice")
hook_context.set("debug_mode", True)
name = hook_context.get("user_name")
debug = hook_context.get("debug_mode", False)
```

#### increment(key, amount=1)
递增计数器：

```python
count = hook_context.increment("my_counter")  # 返回 1
count = hook_context.increment("my_counter")  # 返回 2
hook_context.increment("score", 10)
```

#### append(key, value, max_items=None)
添加到列表：

```python
hook_context.append("tags", "#python")
hook_context.append("tags", ["#debug", "#test"])

# 限制列表大小（保留最后 N 条）
hook_context.append("messages", new_msg, max_items=10)
```

#### summary()
获取状态摘要：

```python
summary = hook_context.summary()
# {
#   "session_id": "abc123",
#   "duration": "0:05:30",
#   "messages": {"sent": 5, "received": 3},
#   "tools": {"called": 2, "succeeded": 2, "failed": 0},
#   "keywords": ["#debug"],
#   "custom_data": {"user_name": "Alice"}
# }
```

## 消息注入（Message Injection）

`UserPromptSubmit` hook 可以将额外内容注入到用户消息中。

### Python Hook 返回

```python
def user_prompt_submit(role: str, content: str, hook_context) -> dict:
    return {
        "append_to_message": "要注入的内容"
    }
```

### Shell Hook

Shell hook 的 stdout 会被自动注入到用户消息前。

```bash
echo "当前时间: $(date)"
```

### 注入效果

```
用户输入
↓
[Hook 输出]
↓
[用户输入]
↓
发送给 LLM
```

## 完整示例

### 示例 1: 安全检查

阻止危险的 shell 命令：

```python
# .simple-agent/hooks/PreToolUse/safety.py

DANGEROUS_PATTERNS = [
    "rm -rf",
    "rm -fr",
    "rm -Rf",
    ":(){:|:&};:",      # fork bomb
    "mkfs",
    "dd if=/dev/",
]

def pre_tool_use(tool_name: str, arguments: dict, hook_context) -> dict:
    """阻止危险命令"""
    if tool_name != "bash":
        return {"action": "continue"}

    cmd = arguments.get("command", "")

    for pattern in DANGEROUS_PATTERNS:
        if pattern in cmd:
            return {
                "action": "block",
                "message": f"安全警告: 检测到危险命令 '{pattern}'"
            }

    return {"action": "continue"}
```

### 示例 2: 日志记录

```python
# .simple-agent/hooks/PostToolUse/logger.py

import json
from pathlib import Path
from datetime import datetime

def post_tool_use(tool_name: str, arguments: dict, result: dict, hook_context) -> None:
    """记录工具执行结果"""
    log_dir = Path(".simple-agent/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "tools.jsonl"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "arguments": arguments,
        "success": result.get("success", False),
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

### 示例 3: 动态注入

```python
# .simple-agent/hooks/UserPromptSubmit/dynamic_injector.py

import re
from pathlib import Path


def user_prompt_submit(role: str, content: str, hook_context) -> dict:
    """检测消息中的文件名并注入其内容"""
    # 提取 Python 文件名
    files = re.findall(r'[\w/]+\.py', content)
    if not files:
        return {}

    # 收集文件内容
    context_parts = []
    for filename in set(files):
        file_path = Path.cwd() / filename
        if not file_path.exists():
            continue

        try:
            file_content = file_path.read_text()
            # 限制内容长度
            if len(file_content) > 500:
                file_content = file_content[:500] + "\n... (内容已截断)"

            context_parts.append(f"### {filename}\n```python\n{file_content}\n```")
        except Exception:
            pass

    if context_parts:
        return {
            "append_to_message": f"""## 相关代码文件

{chr(10).join(context_parts)}

---
基于以上代码回答问题：
"""
        }

    return {}
```

## Hook 返回值

### Python Hook

| 返回值 | 效果 |
|--------|------|
| `{"action": "block", "message": "..."}` | 阻止执行（仅限 `PreToolUse`） |
| `{"action": "continue"}` | 继续执行（可选，默认行为） |
| `{"append_to_message": "..."}` | 将内容拼接到用户消息前 |
| `None` 或 `{}` | 默认行为（继续执行或不注入） |

### Shell Hook

| 输出 | 效果 |
|------|------|
| stdout | 内容会被拼接到用户消息前 |
| 无输出 | 不注入任何内容 |

## 注意事项

### ✅ 推荐

1. **条件注入**：只在需要时注入内容
   ```python
   if "项目" in content:
       return {"append_to_message": "..."}
   ```

2. **限制长度**：避免注入过长的内容
   ```python
   content = file.read()[:500] + "..."
   ```

3. **明确分隔**：用分隔线区分注入内容和用户输入
   ```python
   return {
       "append_to_message": "...\n---\n"
   }
   ```

### ❌ 避免

1. **无条件注入**：每条消息都注入相同内容
2. **过度注入**：注入大量不相关的内容
3. **循环注入**：Hook 互相触发导致无限注入

## 调试

```python
# .simple-agent/hooks/SessionStart/debug.py

def session_start(session_id: str, hook_context) -> None:
    print(f"[DEBUG] session_id={session_id}")
    print(f"[DEBUG] 当前 system 消息数={len(session._messages)}")

    # 可以临时注入调试信息
    # return {"append_to_message": "[DEBUG] 模式已激活"}
    return {}
```

## 更多示例

详细的示例代码请查看：
- `.simple-agent/hooks/HOOK_CONTEXT.md` - HookContext 使用指南
- `.simple-agent/hooks/MESSAGE_INJECTION.md` - 消息注入指南
- `.simple-agent/hooks/PROMPT_HOOK_GUIDE.md` - Prompt Hook 指南
