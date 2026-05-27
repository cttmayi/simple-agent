# AGENT.md 写作指南

AGENT.md 是 Simple Agent 的 system prompt 模板文件，位于插件目录下（默认 `plugins/default/AGENT.md`）。它定义 AI 的行为准则、角色定位和运行环境信息。

## 加载机制

- 启动时从 `plugins/<plugin_dir>/AGENT.md` 读取
- 作为唯一的 system prompt 发送给 LLM
- 如果文件不存在或内容为空，不添加 system prompt
- 每次 API 调用前动态替换占位符

## 占位符

AGENT.md 中可使用 `{{PLACEHOLDER}}` 语法引用动态内容，运行时自动替换：

| 占位符 | 说明 | 示例输出 |
|--------|------|----------|
| `{{DATE}}` | 当前 UTC 日期时间 | `2026-05-28 10:30:00 UTC` |
| `{{CWD}}` | 当前工作目录 | `/Users/ling/workspace/my-project` |
| `{{PLUGIN_DIR}}` | 插件目录路径 | `plugins/default` |
| `{{SESSION_ID}}` | 当前会话 ID | `a1b2c3d4-...` |
| `{{SKILLS}}` | 可用技能列表（名称+描述） | 见下方示例 |
| `{{AGENTS}}` | 可用代理列表（名称+描述+工具） | 见下方示例 |
| `{{TOOLS}}` | 可用工具列表（名称+描述） | 见下方示例 |

占位符替换后的输出格式为 Markdown 列表：

```
- **skill-name**: skill description
```

```
- **agent-name**: agent description
  Tools: tool1, tool2
```

```
- **ToolName**: tool description
```

**注意**：占位符只填充列表内容。标题、说明文字需要在 AGENT.md 中自行编写。如果对应资源为空（无 skills/agents），占位符替换为空字符串。

## 写作建议

1. **行为准则在前**：先定义 AI 的工作原则和风格，再放置环境信息
2. **标题自定**：占位符不含标题，你需要用 `## Available Skills` 等 Markdown 标题自行组织
3. **说明文字**：在占位符前添加使用指引，如 "The following skills are available. Ask to load them by name."
4. **按需选择**：不需要某个占位符就不写，不会自动注入

## 示例

参考 `plugins/default/AGENT.md`：

```markdown
# AGENT.md

## 1. 行为准则

...你的行为准则内容...

## Environment

- **Date**: {{DATE}}
- **Working Directory**: {{CWD}}
- **Session ID**: {{SESSION_ID}}

## Available Skills
The following skills are available. Ask to load them by name.

{{SKILLS}}

## Available Agents
The following agents are available as subagents.

{{AGENTS}}

## Available Tools

{{TOOLS}}
```
