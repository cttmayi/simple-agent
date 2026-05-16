# Commands 文档

Simple Agent 支持自定义斜杠命令（slash commands），允许用户快速执行常见操作。

## 目录

- [快速开始](#快速开始)
- [内置命令](#内置命令)
- [自定义命令](#自定义命令)
- [命令格式](#命令格式)
- [新功能](#新功能)
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

### `/logs`

显示日志信息（需要启动参数支持）

---

## 命令执行流程

当用户输入命令时，系统按以下顺序处理：

1. **检查是否为命令**：以 `/` 开头的输入被识别为命令
2. **参数解析**：提取命令名和参数列表
3. **命令查找**：在命令目录中查找对应的命令文件
4. **命令处理**：
   - 替换参数（`$1`, `$args`, `$#`）
   - 执行 Bash 命令（`!`cmd``）
   - 包含文件内容（`@filename`）
   - 替换模板变量（`{variable_name}`）
5. **工具限制**：如果设置了 `allowed-tools`，限制可用工具
6. **发送给 AI**：将处理后的内容作为 system message 发送给 AI
7. **工具恢复**：命令完成后恢复完整工具列表

---

## 自定义命令

### 可用命令

以下命令位于 `plugin/commands/` 目录：

| 命令 | 描述 |
|------|------|
| `/version` | 显示版本信息 |
| `/status` | 显示会话状态 |
| `/git-status` | 显示 git 仓库状态（使用 Bash 执行和模板变量） |
| `/config` | 显示或修改配置 |
| `/skills` | 列出 skills |
| `/agents` | 列出 agents |

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
| `allowed-tools` | 否 | 无 | 限制 AI 可用的工具列表（逗号分隔）|

**注意**：`usage` 字段已移除，使用方式固定为 `/name`。

---

## 新功能

### 命名空间 (Namespaces)

命令支持命名空间，用于组织相关命令。命名空间使用 `/` 分隔：

```
plugin/commands/
├── flat.md          # 命令名: /flat
├── git/             # git 命名空间
│   ├── commit.md    # 命令名: /git/commit
│   ├── status.md    # 命令名: /git/status
│   └── push.md      # 命令名: /git/push
└── docker/
    ├── build.md     # 命令名: /docker/build
    └── run.md       # 命令名: /docker/run
```

命名空间使命令更有组织性，便于管理大量命令。

### 参数替换 (Parameters)

命令支持位置参数，允许在命令中使用 `$1` 或 `$args` 来引用命令参数：

```markdown
---
name: greet
description: 向用户打招呼
---

# 欢迎

Hello $1!
```

使用：
```bash
> /greet World
```

输出：
```
# 欢迎

Hello World!
```

**可用参数**：

| 参数 | 说明 | 示例 |
|------|------|------|
| `$1` 或 `$args` | 所有参数（空格连接） | `/search pattern` → `$1` = `pattern` |
| `$#` | 参数数量（1 表示有参数，0 表示无） | `/test` → `$#` = `0`, `/test foo` → `$#` = `1` |

### Bash 命令执行 (Bash Execution)

命令支持在执行时运行 Shell 命令，使用 `!`command`` 语法：

```markdown
---
name: git-status
description: 显示 git 仓库状态
---

# Git Status

```bash
!`git status`
```

## Current Branch

Branch: !`git branch --show-current`
```

使用：
```bash
> /git-status
```

Bash 命令会在命令执行时运行，输出会被替换到命令内容中。

**注意事项**：
- Bash 命令超时时间为 10 秒
- 命令在当前工作目录执行
- 错误输出也会被捕获
- 命令失败不会阻止命令执行

### 文件包含 (File Inclusion)

命令支持包含其他文件的内容，使用 `@filename` 语法：

```markdown
---
name: show-readme
description: 显示 README 内容
---

# README 内容

@README.md
```

使用：
```bash
> /show-readme
```

文件路径相对于当前工作目录。

**注意事项**：
- 文件不存在时会显示错误信息
- 文件内容会原样插入到命令中
- 支持 Markdown 格式的文件

### 工具限制 (Allowed Tools)

命令可以使用 `allowed-tools` 字段限制 AI 在此次会话中可用的工具：

```markdown
---
name: restricted
description: 限制工具的命令
allowed-tools: Bash,Grep
---

你只能使用 Bash 和 Grep 工具来完成以下任务：
...
```

当命令包含 `allowed-tools` 字段时，AI 在响应命令时只能使用指定的工具。这有助于：
- 限制 AI 的行为范围
- 确保特定的工具使用
- 提高安全性和可控性

工具在命令处理后会自动恢复到完整工具列表。

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

### 示例 2：显示 Git 状态（使用 Bash 执行）

```markdown
---
name: git-status
description: 显示 Git 仓库状态
---

# Git 仓库状态

## 当前状态

```bash
!`git status`
```

## 最近提交

```bash
!`git log --oneline -5`
```

## 当前分支

Branch: !`git branch --show-current`

## 项目信息

- Model: {model}
- API Provider: {api_provider}
- Session ID: {session_id}
```

*注意：此命令假设当前目录是 Git 仓库。*

### 示例 3：使用参数和文件包含

```markdown
---
name: show-file
description: 显示文件内容
---

# 文件内容

正在显示文件: $1

文件路径: @$1

---

**提示**：你可以要求 AI 对这个文件进行分析或提出修改建议。
```

使用：
```bash
> /show-file README.md
```

### 示例 4：使用模板变量

```markdown
---
name: info
description: 显示系统信息
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

### 示例 5：复杂的配置查看命令

```markdown
---
name: myconfig
description: 显示自定义配置
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

### 示例 6：带参数和 Bash 的搜索命令

```markdown
---
name: search
description: 搜索文件内容
---

# 文件搜索

搜索模式: $1

正在搜索包含 "$1" 的 Python 文件：

```bash
!`grep -r "$1" --include="*.py" .`
```

---

**提示**：你可以使用 Grep 工具进行更复杂的搜索，如按类型过滤或使用正则表达式。
```

### 示例 7：使用命名空间和工具限制

```markdown
---
name: git/commit
description: 创建 git commit
allowed-tools: Bash,Grep,Read,Write
---

# Git Commit

你是一个 git commit 助手，只能使用 Bash, Grep, Read, Write 工具。

请帮助用户创建一个 git commit，按照以下步骤：

1. 检查当前 git 状态（使用 `git status`）
2. 查看所有变更的文件（使用 `git diff` 或读取文件内容）
3. 根据变更生成一个合适的 commit message
4. 添加所有变更的文件（`git add`）
5. 创建 commit（`git commit -m "message"`）

注意事项：
- 提交信息应该使用中文
- 提交信息应该简明扼要，说明做了什么
- 不要包含敏感信息
```

### 示例 8：完整的功能演示

```markdown
---
name: demo
description: 演示所有新功能
---

# 新功能演示

## 1. 参数替换

你输入的参数是：$1
参数数量：$#

## 2. Bash 执行

当前目录：!`pwd`
当前用户：!`whoami`
系统信息：!`uname -a`

## 3. 文件包含

以下是 README.md 的内容：

@README.md

## 4. 模板变量

- Model: {model}
- Provider: {api_provider}
- Session ID: {session_id}
- Theme: {theme}

## 5. 命名空间

这个命令展示了命名空间功能，其他命名空间命令示例：
- `/git/commit` - Git commit 助手
- `/docker/build` - Docker 构建助手

## 6. 工具限制（通过 allowed-tools 字段）

如果命令包含 `allowed-tools` 字段，AI 将只能使用指定的工具。
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

通过组合使用参数、Bash 执行、文件包含和模板变量，可以创建强大的动态命令：

```markdown
---
name: project-info
description: 显示项目完整信息
---

# 项目信息

## 基本信息

项目路径：!`pwd`
项目名称：!`basename $(pwd)`

## Git 信息

当前分支：!`git branch --show-current`
最近提交：!`git log --oneline -1`

## 文件统计

Python 文件：!`find . -name "*.py" | wc -l`
Markdown 文件：!`find . -name "*.md" | wc -l`

## README 内容

@README.md

## 系统信息

- Model: {model}
- Provider: {api_provider}
- Session ID: {session_id}
```

要实现真正的动态命令，还可以考虑：

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