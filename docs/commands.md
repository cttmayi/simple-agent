# Commands 文档

Simple Agent 支持自定义斜杠命令（slash commands），允许用户快速执行常见操作。

## 目录

- [快速开始](#快速开始)
- [内置命令](#内置命令)
- [自定义命令](#自定义命令)
- [命令格式](#命令格式)
- [模板变量](#模板变量)
- [示例命令](#示例命令)

---

## 快速开始

### 使用命令

在 CLI 中输入命令：

```bash
> /help          # 显示帮助信息
> /version       # 显示版本信息
> /status        # 显示会话状态
> /clear         # 清除对话历史
> /reset         # 重置会话
```

### 创建新命令

1. 在 `plugin/commands/` 目录创建 `.md` 文件：

```bash
# plugin/commands/mycommand.md
---
name: mycommand
description: My custom command
usage: /mycommand [arg]
---

# My Command

Hello from my command!
```

2. 重启 simple-agent

```bash
simple-agent
```

3. 使用新命令

```bash
> /mycommand
```

---

## 内置命令

以下命令由 runtime 直接处理，不能被自定义命令覆盖：

### `/help`

显示帮助信息，包括所有可用命令列表。

### `/exit` / `/quit`

退出 simple-agent 程序。

### `/clear`

清除当前会话的对话历史，但保留已加载的 skills 和 agents。

### `/reset`

重置当前会话：
- 清除对话历史
- 卸载所有已加载的 skills
- 卸载所有已加载的 agents

---

## 自定义命令

### 可用命令

以下命令位于 `plugin/commands/` 目录：

| 命令 | 描述 | 用法 |
|------|------|------|
| `/version` | 显示版本信息 | `/version` |
| `/status` | 显示会话状态 | `/status` |
| `/config` | 显示或修改配置 | `/config [get\|set] [key] [value]` |
| `/skills` | 列出 skills | `/skills [list\|load\|unload] [name]` |
| `/agents` | 列出 agents | `/agents [list\|load\unload] [name]` |

---

## 命令格式

每个命令是一个 Markdown 文件，包含 frontmatter 和内容：

```markdown
---
name: command-name              # 命令名称（必需）
description: 简短描述              # 命令描述（必需）
usage: /command [optional] [args]    # 用法字符串（可选，默认为 /{name}）
---

# 命令标题

命令的详细内容...

支持模板变量：{variable_name}
```

### Frontmatter 字段

| 字段 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | 是 | 无 | 命令名称，用于调用 |
| `description` | 是 | 无 | 命令的简短描述 |
| `usage` | 否 | `/name` | 命令用法字符串 |

---

## 模板变量

命令内容支持以下模板变量，用于动态生成输出：

### 会话相关

| 变量 | 说明 |
|------|------|
| `{session_id}` | 当前会话 ID |
| `{message_count}` | 会话中的消息数量 |

### 配置相关

| 变量 | 说明 |
|------|------|
| `{api_provider}` | API 提供商（openai / anthropic） |
| `{model}` | 模型名称 |
| `{base_url}` | API 基础 URL |

### 路径相关

| 变量 | 说明 |
|------|------|
| `{skills_dirs}` | Skills 目录列表 |
| `{agents_dir}` | Agents 目录 |
| `{hooks_dir}` | Hooks 目录 |
| `{commands_dir}` | Commands 目录 |

### UI 相关

| 变量 | 说明 |
|------|------|
| `{theme}` | UI 主题（dark / light） |
| `{show_thinking}` | 是否显示思考过程（true / false） |

### 日志相关

| 变量 | 说明 |
|------|------|
| `{logging_enabled}` | 日志是否启用（true / false） |
| `{log_dir}` | 日志目录 |

### 资源相关

| 变量 | 说明 |
|------|------|
| `{skills_count}` | 已加载的 skills 数量 |
| `{agents_count}` | 已加载的 agents 数量 |
| `{total_skills}` | 可用的 skills 总数 |
| `{total_agents}` | 可用的 agents 总数 |
| `{skills_list}` | 可用 skills 列表（格式化后的 markdown） |
| `{loaded_skills}` | 已加载 skills 列表 |
| `{agents_list}` | 可用 agents 列表（格式化后的 markdown） |
| `{loaded_agents}` | 已加载 agents 列表 |

---

## 示例命令

### 示例 1：简单的帮助命令

```markdown
---
name: greet
description: 向用户打招呼
usage: /greet
---

# 欢迎！

欢迎使用 Simple Agent CLI！

这是一个功能强大的 AI 助手，支持：
- 文件操作（READ, WRITE）
- Shell 命令执行（BASH）
- 模式搜索（GREP）
- 自定义技能（Skills）
- 专用代理（Agents）
- 事件驱动插件（Hooks）

祝你使用愉快！
```

### 示例 2：显示 Git 状态

```markdown
---
name: gitstatus
description: 显示 Git 仓库状态
usage: /gitstatus
---

# Git 仓库状态

```bash
git status
git log --oneline -5
```

*注意：此命令假设当前目录是 Git 仓库。*
```

### 示例 3：使用模板变量

```markdown
---
name: info
description: 显示系统信息
usage: /info
---

# 系统信息

## 会话信息
- Session ID: {session_id}
- 消息数量: {message_count}

## 配置信息
- API 提供商: {api_provider}
- 模型: {model}
- 主题: {theme}

## 资源统计
- 可用 Skills: {total_skills}
- 已加载 Skills: {skills_count}
- 可用 Agents: {total_agents}
- 已加载 Agents: {agents_count}
```

### 示例 4：复杂的配置查看命令

```markdown
---
name: myconfig
description: 显示自定义配置
usage: /myconfig
---

# 我的配置

## API 配置
- Provider: {api_provider}
- Model: {model}
- Base URL: {base_url}

## 目录配置
- Skills 目录:
{skills_dirs}
- Agents 目录: {agents_dir}
- Hooks 目录: {hooks_dir}
- Commands 目录: {commands_dir}

## UI 配置
- 主题: {theme}
- 显示思考: {show_thinking}

## 日志配置
- 启用日志: {logging_enabled}
- 日志目录: {log_dir}

## 加载的资源
### Skills
{loaded_skills}

### Agents
{loaded_agents}
```

### 示例 5：带参数的命令

```markdown
---
name: search
description: 搜索文件内容
usage: /search <pattern>
---

# 文件搜索

搜索模式: {pattern}

```bash
grep -r "{pattern}" --include="*.py" --include="*.md" .
```

*注意：此命令使用 Grep 工具进行递归搜索。*
```

---

## 最佳实践

### 命令命名

- 使用小写字母和连字符：`my-command`, `git-status`
- 保持简短而描述性：`status` 而非 `show_current_status`
- 避免与内置命令冲突

### 内容组织

1. **清晰的标题**：以 `#` 开头
2. **分组内容**：使用 `##` 创建子章节
3. **代码块**：使用 ` ```markdown ` 包裹代码
4. **列表**：使用 `-` 或 `1.` 创建列表

### 模板变量使用

- 使用 `{variable_name}` 语法
- 变量不存在时会显示原样
- 对于列表变量，使用换行符分隔

### 文档

- 在命令内容中包含必要的文档说明
- 添加使用示例（如果命令需要参数）
- 说明任何限制或注意事项

### 测试

创建命令后，重启 simple-agent 并测试：

```bash
simple-agent

# 测试命令
> /your-new-command

# 检查帮助
> /help
```

---

## 故障排查

### 命令未显示在 `/help` 中

1. 检查文件是否在 `plugin/commands/` 目录
2. 检查文件扩展名是否为 `.md`
3. 检查 frontmatter 是否正确（`---` 包裹）

### 命令执行出错

1. 检查模板变量语法是否正确
2. 查看 simple-agent 启动日志
3. 验证命令文件是否为有效的 Markdown

### 模板变量未被替换

1. 确保变量名使用 `{}` 包裹
2. 检查变量名是否在可用变量列表中
3. 变量名区分大小写

---

## 高级用法

### 动态命令

虽然命令内容是静态的，但可以通过模板变量显示动态信息。要实现真正的动态命令，可以考虑：

1. **Hooks**：使用 PreToolUse 或 PostToolUse hooks 动态执行操作
2. **Skills**：加载包含复杂逻辑的 skills
3. **Agents**：使用专用 agent 处理特定任务

### 命令组合

某些命令可以组合使用：

```bash
> /clear         # 清除历史
> /reset        # 完全重置
> /skills        # 查看 skills
> /help         # 查看帮助
```

### 跨平台兼容性

命令文件使用标准 Markdown 格式，可跨平台使用：
- Windows
- macOS
- Linux

确保文件编码为 UTF-8。

---

## 相关文档

- [Skills 文档](./skills.md)
- [Agents 文档](./agents.md)
- [Subagents 文档](./subagents.md)
- [Hooks 文档](./hooks.md)
- [README.md](../README.md)