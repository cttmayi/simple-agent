# Hooks 系统

Hooks 允许您在特定事件发生时执行自定义脚本，扩展 simple-agent 的功能。

## 官方协议

所有 hook 脚本使用 **stdin/stdout JSON 协议**：
- **输入**：通过 stdin 接收 JSON
- **输出**：通过 stdout 返回 JSON

## 支持的事件类型

| 事件名称 | 描述 | 可阻止 | 触发时机 |
|---------|------|-------|---------|
| `SessionStart` | 全新会话初始化启动 | 否 | agent 启动时 |
| `Stop` | 主代理本轮回答结束、本轮会话轮次终止 | 否 | agent 退出时（包括 `/exit` 和 `Ctrl+C`） |
| `UserPromptSubmit` | 用户输入内容提交，送入 LLM 前 | 否 | 用户发送消息后，发送给 LLM 前 |
| `PreToolUse` | LLM 生成工具调用指令，本地执行工具之前 | **是** | 工具执行之前 |
| `PostToolUse` | 工具执行完成，结果回传给 LLM 之前（成功 / 失败都走此事件） | 否 | 工具执行完成后 |
| `BeforeBash` | 执行 Bash 命令前置钩子 | 否 | Bash 命令执行前 |
| `AfterBash` | Bash 命令执行完毕后置钩子 | 否 | Bash 命令执行后 |
| `BeforeEdit` | 文件编辑 / 写入操作执行前 | 否 | 文件编辑前 |
| `AfterEdit` | 文件编辑完成后 | 否 | 文件编辑后 |
| `PreCompact` | 对话上下文压缩合并之前 | 否 | 上下文压缩前（预留） |
| `PostCompact` | 上下文压缩完成之后 | 否 | 上下文压缩后（预留） |
| `SubagentStart` | 子代理 / 子任务正式启动 | 否 | 子代理启动时 |
| `SubagentStop` | 子代理运行结束销毁 | 否 | 子代理停止时 |
| `Notification` | 系统通知弹窗 / 权限提示触发 | 否 | 系统通知时（预留） |
| `PluginLoad` | 会话加载外部插件时 | 否 | 插件加载时（预留） |
| `SkillLoad` | 加载 .skill 技能文档时 | 否 | `load_skill` 工具加载 skill 时 |

## 目录结构

```
plugin/hooks/
├── SessionStart/           # 会话开始时触发
│   ├── welcome.py          # 欢迎消息
│   ├── log.sh              # 记录日志
│   └── prompt.md           # 注入 Prompt
├── Stop/                  # 会话结束时触发
│   ├── cleanup.sh          # 清理工作
│   └── summary.py          # 会话摘要
├── UserPromptSubmit/       # 消息发送时触发
│   ├── log.py              # 记录消息
│   └── inject.sh           # 动态注入
├── PreToolUse/            # 工具调用前触发（可阻止）
│   ├── security.py         # 安全检查
│   └── log.sh              # 记录
├── PostToolUse/           # 工具调用后触发
│   ├── summary.py          # 摘要统计
│   └── logger.py           # 记录日志
├── SkillLoad/             # Skill 加载时触发
│   └── notify.py           # 通知
└── examples/              # 官方示例
    ├── bash-example.sh
    ├── python-example.py
    └── javascript-example.js
```

## Hook 文件类型

| 文件类型 | 说明 |
|---------|------|
| `.py` | Python 脚本 |
| `.sh` / `.cmd` | Shell 脚本 |
| `.js` | JavaScript 脚本 |
| `.md` | Markdown 文件（作为 additionalContext 发送给 AI） |

## 输入 JSON 格式

所有 hook 都通过 stdin 接收统一格式的 JSON：

```json
{
  "event": "事件名称",
  "session": {
    "id": "会话ID"
  },
  "project": {
    "path": "/项目路径"
  },
  "payload": {
    // 事件特定的数据
  }
}
```

### 各事件 payload 结构

| 事件名称 | Payload 字段 | 类型 | 说明 |
|---------|-------------|------|------|
| `SessionStart` | (无) | - | 空 payload |
| `Stop` | `responseLength` | int | 响应长度 |
| | `usedTools` | array | 使用的工具列表 |
| `UserPromptSubmit` | `userPrompt` | string | 用户消息内容 |
| `PreToolUse` | `tool` | string | 工具名称 |
| | `parameters` | object | 工具参数 |
| `PostToolUse` | `tool` | string | 工具名称 |
| | `parameters` | object | 工具参数 |
| | `result` | object | 工具执行结果 |
| | `success` | boolean | 执行是否成功 |
| | `error` | string (可选) | 错误信息 |
| `BeforeBash` | `command` | string | 执行命令 |
| | `cwd` | string | 工作目录 |
| | `timeout` | int | 超时秒数 |
| `AfterBash` | `command` | string | 执行命令 |
| | `stdout` | string | 标准输出 |
| | `stderr` | string | 标准错误 |
| | `exitCode` | int | 退出码 |
| | `success` | boolean | 是否成功 |
| `BeforeEdit` | `filePath` | string | 文件路径 |
| | `oldContent` | string | 原文件内容 |
| | `newContent` | string | 待写入内容 |
| `AfterEdit` | `filePath` | string | 文件路径 |
| | `finalContent` | string | 最终文件内容 |
| | `success` | boolean | 是否成功 |
| `PreCompact` | `rawContext` | string | 压缩前完整上下文文本 |
| `PostCompact` | `compressedContext` | string | 压缩后文本 |
| | `savedTokens` | int | 节省token数量 |
| `SubagentStart` | `subagentId` | string | 子代理ID |
| | `taskTitle` | string | 任务标题 |
| | `parentSessionId` | string | 父会话ID |
| `SubagentStop` | `subagentId` | string | 子代理ID |
| | `finishReason` | string | 结束原因 |
| | `duration` | float | 运行时长(秒) |
| `Notification` | `type` | string | 通知类型 |
| | `message` | string | 通知文案 |
| | `scope` | string | 作用域 |
| `PluginLoad` | `pluginName` | string | 插件名 |
| | `pluginVersion` | string | 版本号 |
| | `pluginRoot` | string | 插件目录路径 |
| `SkillLoad` | `skillName` | string | Skill 名称 |
| | `skillPath` | string | Skill 路径 |
| | `rawContent` | string | Skill 原始内容 |

#### Payload 示例

**SessionStart**
```json
{
  "event": "SessionStart",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {}
}
```

**Stop**
```json
{
  "event": "Stop",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "responseLength": 1000,
    "usedTools": ["read", "bash"]
  }
}
```

**UserPromptSubmit**
```json
{
  "event": "UserPromptSubmit",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "userPrompt": "帮我读取 README 文件"
  }
}
```

**PreToolUse**
```json
{
  "event": "PreToolUse",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "tool": "read",
    "parameters": {
      "file_path": "README.md"
    }
  }
}
```

**PostToolUse**
```json
{
  "event": "PostToolUse",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "tool": "read",
    "parameters": {
      "file_path": "README.md"
    },
    "result": {
      "success": true,
      "content": "# README\n..."
    },
    "success": true
  }
}
```

**BeforeBash**
```json
{
  "event": "BeforeBash",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "command": "ls -la",
    "cwd": "/path/to/project",
    "timeout": 30
  }
}
```

**AfterBash**
```json
{
  "event": "AfterBash",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "command": "ls -la",
    "stdout": "drwxr-xr-x  ...",
    "stderr": "",
    "exitCode": 0,
    "success": true
  }
}
```

**BeforeEdit**
```json
{
  "event": "BeforeEdit",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "filePath": "README.md",
    "oldContent": "# Old content",
    "newContent": "# New content"
  }
}
```

**AfterEdit**
```json
{
  "event": "AfterEdit",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "filePath": "README.md",
    "finalContent": "# New content",
    "success": true
  }
}
```

**PreCompact**
```json
{
  "event": "PreCompact",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "rawContext": "Full conversation context..."
  }
}
```

**PostCompact**
```json
{
  "event": "PostCompact",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "compressedContext": "Compressed summary...",
    "savedTokens": 1500
  }
}
```

**SubagentStart**
```json
{
  "event": "SubagentStart",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "subagentId": "sub-xyz789",
    "taskTitle": "Analyze the codebase",
    "parentSessionId": "abc123"
  }
}
```

**SubagentStop**
```json
{
  "event": "SubagentStop",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "subagentId": "sub-xyz789",
    "finishReason": "completed",
    "duration": 12.5
  }
}
```

**Notification**
```json
{
  "event": "Notification",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "type": "info",
    "message": "Task completed successfully",
    "scope": "global"
  }
}
```

**PluginLoad**
```json
{
  "event": "PluginLoad",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "pluginName": "my-plugin",
    "pluginVersion": "1.0.0",
    "pluginRoot": "/path/to/plugin"
  }
}
```

**SkillLoad**
```json
{
  "event": "SkillLoad",
  "session": {"id": "abc123"},
  "project": {"path": "/path/to/project"},
  "payload": {
    "skillName": "code-review",
    "skillPath": "/path/to/skill",
    "rawContent": "# Code Review\n..."
  }
}
```

## 输出 JSON 格式

所有 hook 都通过 stdout 返回 JSON：

```json
{
  "decision": "allow",           // 可选：allow 或 block，默认 allow
  "message": "显示在CLI的内容",  // 可选
  "updatedInput": {},            // 可选：修改输入数据
  "additionalContext": "发送给AI的内容"  // 可选
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `decision` | 否 | `"allow"` 或 `"block"`，默认为 `"allow"` |
| `message` | 否 | 显示在 CLI 的内容 |
| `updatedInput` | 否 | 修改输入数据（如工具参数） |
| `additionalContext` | 否 | 发送给 AI 的额外内容 |

## 编写 Hook

### Bash Hook

```bash
#!/bin/bash
# plugin/hooks/SessionStart/welcome.sh

# 读取 stdin JSON
INPUT_JSON=$(cat)

# 提取 session_id
SESSION_ID=$(echo "$INPUT_JSON" | grep -o '"id"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')
SHORT_ID=${SESSION_ID:0:8}

# 输出 JSON（必须使用 heredoc 避免转义问题）
# decision 是可选的，默认为 allow
cat <<EOF
{
  "message": "🚀 会话已启动! ID: $SHORT_ID"
}
EOF
```

### Python Hook

```python
#!/usr/bin/env python3
# plugin/hooks/UserPromptSubmit/log.py

import sys
import json

# 读取 stdin
input_json = sys.stdin.read()
data = json.loads(input_json)

# 解析 payload
payload = data.get("payload", {})
user_prompt = payload.get("userPrompt", "")
session_id = data.get("session", {}).get("id", "")

# 记录日志（可选）
log_file = ".simple-agent/messages.log"
with open(log_file, "a") as f:
    f.write(f"{session_id}: {user_prompt[:50]}...\n")

# 输出 JSON（decision 是可选的，默认为 allow）
output = {
    "message": f"📤 消息已发送: {user_prompt[:30]}..."
}
print(json.dumps(output, ensure_ascii=False))
```

### JavaScript Hook

```javascript
#!/usr/bin/env node
// plugin/hooks/PreToolUse/security.js

// 读取 stdin
let input = '';
process.stdin.on('data', chunk => input += chunk);
process.stdin.on('end', () => {
    const data = JSON.parse(input);
    const payload = data.payload || {};

    // 安全检查
    const tool = payload.tool || '';
    const dangerousTools = ['rm', 'dd', 'mkfs'];

    if (dangerousTools.includes(tool)) {
        console.log(JSON.stringify({
            decision: "block",
            message: `⚠️ 危险工具被阻止: ${tool}`
        }));
        return;
    }

    // 放行（decision 是可选的，默认为 allow）
    console.log(JSON.stringify({}));
});
```

### Markdown Hook (.md)

Markdown 文件内容会自动作为 `additionalContext` 发送给 AI：

```markdown
# plugin/hooks/SessionStart/instruction.md

你是专业的编程助手，专注于 Python 开发。

## 通信风格
- 使用中文回答
- 代码示例要完整可运行
- 解释要清晰易懂
```

## 完整示例

### 示例 1: 安全检查（阻止危险命令）

```python
#!/usr/bin/env python3
# plugin/hooks/PreToolUse/safety.py

import sys
import json

input_json = sys.stdin.read()
data = json.loads(input_json)
payload = data.get("payload", {})

tool = payload.get("tool", "")
params = payload.get("parameters", {})

# 危险命令模式
DANGEROUS = ["rm -rf", "rm -fr", "dd if=/dev/", "mkfs", ":(){:|:&};:"]

if tool == "bash":
    cmd = params.get("command", "")
    for pattern in DANGEROUS:
        if pattern in cmd:
            print(json.dumps({
                "decision": "block",
                "message": f"🚫 危险命令被阻止: {pattern}"
            }))
            sys.exit(0)

print(json.dumps({"decision": "allow"}))
```

### 示例 2: 工具日志记录

```python
#!/usr/bin/env python3
# plugin/hooks/PostToolUse/logger.py

import sys
import json
from datetime import datetime

input_json = sys.stdin.read()
data = json.loads(input_json)
payload = data.get("payload", {})

tool = payload.get("tool", "unknown")
success = payload.get("success", False)

LOG_FILE = ".simple-agent/tools.log"
status = "✓" if success else "✗"

with open(LOG_FILE, "a") as f:
    f.write(f"[{datetime.now()}] Tool: {tool} {status}\n")

print(json.dumps({"decision": "allow"}))
```

### 示例 3: 动态注入文件上下文

```python
#!/usr/bin/env python3
# plugin/hooks/UserPromptSubmit/file_injector.py

import sys
import json
import re
from pathlib import Path

input_json = sys.stdin.read()
data = json.loads(input_json)
payload = data.get("payload", {})
user_prompt = payload.get("userPrompt", "")

# 提取 Python 文件名
files = re.findall(r'[\w/]+\.py', user_prompt)
if not files:
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)

# 收集文件内容
context_parts = []
for filename in set(files):
    file_path = Path.cwd() / filename
    if not file_path.exists():
        continue

    content = file_path.read_text()
    if len(content) > 500:
        content = content[:500] + "\n... (已截断)"

    context_parts.append(f"### {filename}\n```python\n{content}\n```")

if context_parts:
    additional_context = "## 相关代码文件\n\n" + "\n\n".join(context_parts) + "\n\n---\n基于以上代码回答问题："
    print(json.dumps({
        "decision": "allow",
        "additionalContext": additional_context
    }))
else:
    print(json.dumps({"decision": "allow"}))
```

### 示例 4: LLM 提示词注入

```python
#!/usr/bin/env python3
# plugin/hooks/UserPromptSubmit/code_guidance.py

import sys
import json

# 读取 stdin
input_json = sys.stdin.read()
data = json.loads(input_json)

# 解析 payload
payload = data.get("payload", {})
user_prompt = payload.get("userPrompt", "")

# 检查是否需要注入
keywords = ["代码", "Python", "函数", "类", "bug", "调试"]
need_injection = any(keyword in user_prompt for keyword in keywords)

if need_injection:
    # 注入系统提示词到 LLM
    additional_context = """## 代码开发指导原则

请遵循以下原则回答用户关于代码的问题：
1. 使用有意义的变量名和函数名
2. 添加必要的注释和文档字符串
3. 遵循 PEP 8 代码风格规范
"""

    print(json.dumps({
        "additionalContext": additional_context
    }, ensure_ascii=False))
else:
    # 不需要注入
    print(json.dumps({}))

```bash
#!/bin/bash
# plugin/hooks/Stop/summary.sh

INPUT_JSON=$(cat)
SESSION_ID=$(echo "$INPUT_JSON" | grep -o '"id"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')
SHORT_ID=${SESSION_ID:0:8}

# 从日志文件统计（如果存在）
TOOLS_LOG=".simple-agent/tools.log"
if [ -f "$TOOLS_LOG" ]; then
    TOOL_COUNT=$(grep -c "$SHORT_ID" "$TOOLS_LOG" 2>/dev/null || echo "0")
else
    TOOL_COUNT="0"
fi

cat <<EOF
{
  "decision": "allow",
  "message": "👋 会话结束 (ID: $SHORT_ID, 工具调用: $TOOL_COUNT)"
}
EOF
```

## 调试

### 启用调试输出

设置环境变量 `HOOK_DEBUG=1` 启用详细调试信息：

```bash
HOOK_DEBUG=1 simple-agent
```

或先设置环境变量：

```bash
export HOOK_DEBUG=1
simple-agent
```

调试输出会显示：
- Hook 触发事件和目录
- Hook 输入 JSON
- Hook 输出和返回码
- Hook 解析结果
- 异常堆栈追踪

### Hook 内调试

在 hook 脚本中添加调试输出：

```python
import sys

# 调试信息输出到 stderr（不影响 JSON 返回）
sys.stderr.write(f"[DEBUG] Processing hook...\n")
```

```bash
# Shell 中调试
echo "[DEBUG] Processing..." >&2
```

## 注意事项

### ✅ 推荐

1. **使用 heredoc 输出 JSON**（Bash）
   ```bash
   cat <<EOF
   {"decision": "allow"}
   EOF
   ```

2. **及时释放资源**
   ```python
   import sys
   try:
       # 处理逻辑
       pass
   finally:
       sys.stdout.flush()
   ```

3. **限制输出长度**
   ```python
   content = content[:500] + "..." if len(content) > 500 else content
   ```

### ❌ 避免

1. **不要使用 echo 直接输出 JSON**（容易转义错误）
   ```bash
   # 错误
   echo '{"decision": "allow"}'
   ```

2. **不要在 hook 中无限循环**
3. **不要超时执行**（默认 10 秒超时）

## 官方示例

完整的官方示例请查看：
- `plugin/hooks/examples/bash-example.sh`
- `plugin/hooks/examples/python-example.py`
- `plugin/hooks/examples/javascript-example.js`