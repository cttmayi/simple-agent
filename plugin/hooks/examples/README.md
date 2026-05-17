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

## 官方 Hook 事件列表

| 事件名称 | 触发时机 | payload 结构 |
|---------|---------|-------------|
| SessionStart | 全新会话初始化启动 | {} |
| UserPromptSubmit | 用户输入内容提交，送入 LLM 前 | {"userPrompt": "用户输入原始文本"} |
| PreToolUse | LLM 生成工具调用指令，本地执行工具之前 | {"tool": "工具名", "parameters": {}} |
| PostToolUse | 工具执行完成，结果回传给 LLM 之前 | {"tool": "工具名", "parameters": {}, "result": 任意类型, "error": "错误信息/null", "success": 布尔值} |
| Stop | 主代理本轮回答结束、本轮会话轮次终止 | {"responseLength": "本轮回复长度", "usedTools": "本轮调用工具数组"} |
| SkillLoad | 加载 .skill 技能文档时 | {"skillName": "技能标识名", "skillPath": "文件路径", "rawContent": "技能完整原文"} |

**未实现事件（预留）**：
- BeforeBash, AfterBash, BeforeEdit, AfterEdit, PreCompact, PostCompact
- SubagentStart, SubagentStop, Notification, PluginLoad

## 输入 JSON 完整格式

### 1) SessionStart（会话启动）
```json
{
  "event": "SessionStart",
  "session": {"id": "..."},
  "project": {"path": "..."},
  "payload": {}
}
```

### 2) UserPromptSubmit（用户提交消息前）
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

### 3) PreToolUse（工具调用前）
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

### 4) PostToolUse（工具执行后）
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