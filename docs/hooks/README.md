# Hooks 系统

Hooks 允许您在特定事件发生时执行自定义脚本，扩展 simple-agent 的功能。

## 官方协议

所有 hook 脚本使用 **stdin/stdout JSON 协议**：
- **输入**：通过 stdin 接收 JSON
- **输出**：通过 stdout 返回 JSON

## 支持的事件类型

| 事件名称 | 描述 | 可阻止 | 触发时机 |
|---------|------|-------|---------|
| `SessionStart` | 会话开始 | 否 | agent 启动时 |
| `Stop` | 会话结束 | 否 | agent 退出时 |
| `UserPromptSubmit` | 消息发送 | 否 | 用户发送消息后 |
| `PreToolUse` | 工具调用前 | **是** | 工具执行之前 |
| `PostToolUse` | 工具调用后 | 否 | 工具执行之后 |
| `SkillLoad` | Skill 加载 | 否 | `load_skill` 工具加载 skill 时 |

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

#### SessionStart
```json
{
  "payload": {}
}
```

#### Stop
```json
{
  "payload": {}
}
```

#### UserPromptSubmit
```json
{
  "payload": {
    "userPrompt": "用户消息内容"
  }
}
```

#### PreToolUse
```json
{
  "payload": {
    "tool": "工具名称",
    "parameters": {
      // 工具参数
    }
  }
}
```

#### PostToolUse
```json
{
  "payload": {
    "tool": "工具名称",
    "parameters": {},
    "result": {},
    "success": true
  }
}
```

#### SkillLoad
```json
{
  "payload": {
    "skillName": "skill名称",
    "skillPath": "/path/to/skill",
    "rawContent": "skill内容"
  }
}
```

## 输出 JSON 格式

所有 hook 都通过 stdout 返回 JSON：

```json
{
  "decision": "allow",           // 必填：allow 或 block
  "message": "显示在CLI的内容",  // 可选
  "updatedInput": {},            // 可选：修改输入数据
  "additionalContext": "发送给AI的内容"  // 可选
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `decision` | 是 | `"allow"` 或 `"block"` |
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
cat <<EOF
{
  "decision": "allow",
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

# 输出 JSON
output = {
    "decision": "allow",
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

    // 放行
    console.log(JSON.stringify({
        decision: "allow"
    }));
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

### 示例 4: 会话结束统计

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