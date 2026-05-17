# Hook 官方标准示例

本目录包含符合官方标准的 Hook 示例脚本。

## 官方标准（必须遵守）

### 输入格式
Hook 脚本从 stdin 接收 JSON：

```json
{
  "event": "事件名称",
  "payload": { ...事件数据... }
}
```

### 输出格式
Hook 脚本往 stdout 输出 JSON（只能输出这个！）：

```json
{
  "decision": "allow" | "block",
  "message": "CLI 显示的内容",
  "updatedInput": { ...修改后的事件数据... },
  "additionalContext": "追加给 LLM 的内容"
}
```

### 返回字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| decision | string | ✓ | "allow" 放行，"block" 阻止 |
| message | string | ✗ | 在 CLI 中显示的消息 |
| updatedInput | object | ✗ | 修改事件数据（仅对工具调用有效） |
| additionalContext | string | ✗ | 追加给 LLM 的上下文内容 |

## 示例文件

### bash-example.sh
Bash 脚本示例，拦截危险的 `rm -rf` 命令。

### python-example.py
Python 脚本示例，展示更复杂的业务逻辑判断。

## 铁律

1. **读取输入** = `cat` (bash) / `sys.stdin.read()` (Python)
2. **输出只能是一行干净 JSON**，不能有任何其他 print/log
3. **返回结构必须是上述 JSON 格式**

## 常见事件

| 事件名称 | 说明 | payload 结构 |
|---------|------|-------------|
| SessionStart | 会话开始 | {} |
| Stop | 会话结束 | {sessionId} |
| UserPromptSubmit | 用户提交消息 | {userPrompt} |
| PostMessage | AI 返回消息 | {role, userPrompt} |
| PreToolUse | 工具调用前 | {tool, parameters} |
| PostToolUse | 工具调用后 | {tool, parameters, result, error, success} |
| ToolUseFailed | 工具调用失败 | {tool, parameters, error} |
| Error | 发生错误 | {errorType, errorMessage} |

## 输入 JSON 完整格式

### 1) PreToolUse（工具调用前）
```json
{
  "event": "PreToolUse",
  "session": {"id": "..."},
  "project": {"path": "..."},
  "payload": {
    "tool": "Read | Write | Bash | Edit",
    "parameters": {"file_path": "...", "command": "..."}
  }
}
```

### 2) PostToolUse（工具执行后）
```json
{
  "event": "PostToolUse",
  "session": {"id": "..."},
  "project": {"path": "..."},
  "payload": {
    "tool": "...",
    "parameters": {...},
    "result": {...},
    "error": null,
    "success": true
  }
}
```

### 3) UserPromptSubmit（用户提交消息前）
```json
{
  "event": "UserPromptSubmit",
  "session": {"id": "..."},
  "project": {"path": "..."},
  "payload": {
    "userPrompt": "用户输入的内容"
  }
}
```

### 4) SessionStart（会话启动）
```json
{
  "event": "SessionStart",
  "session": {"id": "..."},
  "project": {"path": "..."},
  "payload": {}
}
```