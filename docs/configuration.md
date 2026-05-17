# Simple Agent Configuration

本文档说明 Simple Agent 的配置系统，包括配置文件位置、优先级以及各种配置选项。

## 配置优先级

配置按以下优先级加载（从高到低）：

1. **环境变量** - 覆盖所有其他设置
2. **项目配置** - `.simple-agent/config.yml`（项目特定，覆盖其他配置）
3. **用户配置** - `~/.config/simple-agent/config.yml`（用户级别）
4. **插件特定配置** - `plugins/default/config.yml`（覆盖共享配置）
5. **共享插件配置** - `plugins/config.yml`（默认配置）
6. **内置默认值** - 代码中的默认值

## 配置文件说明

### plugins/config.yml

共享的默认配置文件，所有插件都会使用此配置作为基础。这是放置默认配置的最佳位置。

### plugins/default/config.yml

默认插件的特定配置，可以覆盖 `plugins/config.yml` 中的设置。

### .simple-agent/config.yml

项目级配置文件，可以覆盖所有其他配置。此文件不包含在版本控制中（添加到 `.gitignore`）。

### ~/.config/simple-agent/config.yml

用户级配置文件，可以在多个项目间共享配置。

## 配置选项

### API 配置

```yaml
api:
  provider: openai  # 或 anthropic
  base_url: https://api.openai.com/v1  # 可选，覆盖默认 API 地址
  api_key: ${OPENAI_API_KEY}  # 可引用环境变量
  model: gpt-4o  # 使用的模型
```

**支持的提供者：**
- `openai` - OpenAI API
- `anthropic` - Anthropic/Claude API

**环境变量：**
- `OPENAI_API_KEY` - OpenAI API 密钥
- `ANTHROPIC_API_KEY` - Anthropic API 密钥
- `OPENAI_BASE_URL` - OpenAI API 基础 URL
- `ANTHROPIC_BASE_URL` - Anthropic API 基础 URL

### 路径配置

```yaml
paths:
  # 内部路径（可在 YAML 中配置）
  tools_dir: ./.simple-agent/tools
  memory_dir: ./.simple-agent/memory
  logs_dir: ./.simple-agent/logs

  # 额外的资源路径（与 plugin.json 合并，不覆盖）
  skills_dir: ["~/.agents/skills", "~/custom/skills"]  # 额外的技能目录
  agents_dir: "~/custom/agents"  # 额外的代理目录（支持字符串或数组）
  commands_dir: "~/custom/commands"  # 额外的命令目录
```

### UI 配置

```yaml
ui:
  theme: dark  # 或 light
  show_thinking: true  # 是否显示 AI 思考过程
```

### 日志配置

```yaml
logging:
  enabled: true
  log_dir: ./.simple-agent/logs  # 可选，默认使用 ./.simple-agent/logs
```

## 完整配置选项列表

### API 配置 (api)

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api.provider` | string | `"openai"` | API 提供者：`openai` 或 `anthropic` |
| `api.base_url` | string | `null` | API 基础 URL，覆盖默认地址 |
| `api.api_key` | string | `null` | API 密钥，支持 `${VAR}` 引用环境变量 |
| `api.model` | string | `"gpt-4o"` | 使用的模型名称 |

**支持的环境变量（覆盖对应配置）：**
- `OPENAI_API_KEY` - OpenAI API 密钥
- `ANTHROPIC_API_KEY` - Anthropic API 密钥
- `OPENAI_BASE_URL` - OpenAI API 基础 URL
- `ANTHROPIC_BASE_URL` - Anthropic API 基础 URL

### 路径配置 (paths)

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `paths.tools_dir` | string | `"./.simple-agent/tools"` | 工具目录路径 |
| `paths.memory_dir` | string | `"./.simple-agent/memory"` | 记忆目录路径 |
| `paths.logs_dir` | string | `"./.simple-agent/logs"` | 日志目录路径 |
| `paths.plugin_dir` | string | `"./plugins/default"` | 插件目录路径（自动设置） |
| `paths.skills_dir` | string/array | `null` | 额外的技能目录（与 plugin.json 合并） |
| `paths.agents_dir` | string/array | `null` | 额外的代理目录（与 plugin.json 合并） |
| `paths.commands_dir` | string/array | `null` | 额外的命令目录（与 plugin.json 合并） |

**支持的环境变量：**
- `SIMPLE_AGENT_LOG_DIR` - 日志目录路径
- `SIMPLE_AGENT_TODOS_PATH` - TODO 数据文件路径

### UI 配置 (ui)

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ui.theme` | string | `"dark"` | 主题：`dark` 或 `light` |
| `ui.show_thinking` | boolean | `true` | 是否显示 AI 思考过程 |

### 日志配置 (logging)

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `logging.enabled` | boolean | `true` | 是否启用日志记录 |
| `logging.log_dir` | string | `null` | 日志目录，默认使用 `.simple-agent/logs` |

### plugin.json 配置

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | - | 插件名称 |
| `description` | string | - | 插件描述 |
| `version` | string | - | 插件版本 |
| `skills` | string/array | - | 技能目录路径（基础路径） |
| `agents` | string/array | - | 代理目录路径（基础路径） |
| `commands` | string/array | - | 命令目录路径（基础路径） |

## 资源路径配置

资源路径（skills, agents, commands）可以同时在两个地方配置：

1. **plugin.json** - 定义基础资源路径
2. **YAML 配置文件** - 定义额外的资源路径（与 plugin.json 合并）

两者都会生效，YAML 配置中的路径会被添加到 plugin.json 路径的末尾。

### plugin.json 配置示例

**基础路径（在 plugin.json 中定义）：**

```json
{
  "name": "default-plugin",
  "description": "Simple Agent 默认插件",
  "version": "1.0.0",
  "skills": ["./plugins/default/skills"],
  "agents": ["./plugins/default/agents"],
  "commands": ["./plugins/default/commands"]
}
```

**额外路径（在 YAML 配置中添加）：**

```yaml
paths:
  skills_dir: ["~/.agents/skills", "~/custom/skills"]
  agents_dir: "~/custom/agents"
  commands_dir: "~/custom/commands"
```

**最终合并结果：**

- skills_dirs: `["./plugins/default/skills", "~/.agents/skills", "~/custom/skills"]`
- agents_dirs: `["./plugins/default/agents", "~/custom/agents"]`
- commands_dirs: `["./plugins/default/commands", "~/custom/commands"]`

**路径格式说明：**

- **相对路径**：`./skills` - 相对于项目根目录
- **绝对路径**：`/path/to/skills` - 绝对路径
- **用户目录**：`~/skills` - 用户主目录
- **数组格式**：支持多个路径，按优先级顺序查找

## 完整配置示例

### plugins/config.yml（默认配置）

```yaml
# Simple Agent 共享默认配置
paths:
  tools_dir: ./.simple-agent/tools
  memory_dir: ./.simple-agent/memory
  logs_dir: ./.simple-agent/logs

  # 可选：添加额外的资源路径（与 plugin.json 合并）
  # skills_dir: ["~/.agents/skills"]

ui:
  theme: dark
  show_thinking: true

logging:
  enabled: true
```

### .simple-agent/config.yml（项目配置）

```yaml
# 项目特定配置
api:
  provider: openai
  base_url: https://api.openai.com/v1
  model: gpt-4o

ui:
  theme: light  # 覆盖默认的 dark 主题

logging:
  log_dir: ./logs/llm  # 自定义日志目录
```

### ~/.config/simple-agent/config.yml（用户配置）

```yaml
# 用户级别配置
api:
  api_key: ${MY_API_KEY}  # 使用自定义环境变量

ui:
  show_thinking: false  # 禁用思考过程显示
```

## 环境变量优先级

环境变量具有最高优先级，会覆盖配置文件中的所有设置：

```bash
# API 密钥
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# API 地址
export OPENAI_BASE_URL=https://api.openai.com/v1
export ANTHROPIC_BASE_URL=https://api.anthropic.com

# 日志目录
export SIMPLE_AGENT_LOG_DIR=./custom/logs

# TODO 路径
export SIMPLE_AGENT_TODOS_PATH=./custom/todos.json
```

## 查看配置

使用 `--plugin-info` 标志查看当前配置：

```bash
simple-agent --plugin-info
```

这将显示：
- 插件元数据（名称、描述、版本）
- 插件配置（skills, agents, commands 路径）
- 实际解析的路径

## Hooks 配置 (hooks.json)

Hooks 通过 `plugins/default/hooks.json` 配置文件定义。Hooks 是在特定事件发生时执行的脚本，可以用于验证、修改或拦截操作。

### hooks.json 格式

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "pattern",
        "hooks": [
          {
            "type": "python|command|markdown",
            "file": "path/to/file.py",
            "command": "shell command",
            "content": "markdown content",
            "async": false
          }
        ]
      }
    ]
  }
}
```

### Hooks 类型

#### Python Hook

执行 Python 脚本，通过 stdin 接收 JSON 输入，通过 stdout 返回 JSON 结果。

```json
{
  "type": "python",
  "file": "/path/to/hook.py",
  "async": false
}
```

**Python Hook 输入格式：**
```json
{
  "event": "EventName",
  "payload": { ...事件数据... }
}
```

**Python Hook 输出格式：**
```json
{
  "decision": "allow|block",
  "message": "显示消息",
  "additionalContext": "发送给 LLM 的内容",
  "updatedInput": { ...修改后的数据... }
}
```

#### Command Hook

执行 shell 命令，通过 stdin 接收 JSON 输入，通过 stdout 返回 JSON 结果。

```json
{
  "type": "command",
  "command": "echo 'Hello'",
  "async": false
}
```

#### Markdown Hook

直接将 markdown 内容作为附加上下文发送给 LLM。

```json
{
  "type": "markdown",
  "content": "You are running in test environment.\nSession ID: {{session_id}}"
}
```

支持模板变量：`{{session_id}}`, `{{event_name}}`

### Hook 决策字段

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `decision` | string | 否 | `"allow"` (默认) 或 `"block"` |
| `message` | string | 否 | 显示给用户的消息 |
| `additionalContext` | string | 否 | 发送给 LLM 的额外上下文 |
| `updatedInput` | object | 否 | 修改事件数据 |

### Matcher 字段

`matcher` 是一个可选的正则表达式，用于过滤 hook 执行时机。如果提供了 `context` 参数且匹配该正则，hook 才会执行。

```json
{
  "matcher": "startup|clear|compact",
  "hooks": [...]
}
```

### hooks.json 示例

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Session started'",
            "async": false
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "markdown",
            "content": "Processing user input..."
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "python",
            "file": "./hooks/validate-tools.py",
            "async": false
          }
        ]
      }
    ]
  }
}
```

### 支持的事件

- `SessionStart` - 会话开始时
- `UserPromptSubmit` - 用户提交提示时
- `PreToolUse` - 工具使用前
- `PreAPICall` - API 调用前
- `PostAPICall` - API 调用后
- `ToolCallFailed` - 工具调用失败时

## 配置验证

配置使用 Pydantic 进行验证，如果配置无效，会显示错误信息。

**常见错误：**

1. **无效的 provider 值**：必须是 `openai` 或 `anthropic`
2. **不存在的路径**：配置的目录不存在时会显示警告
3. **JSON 格式错误**：plugin.json 格式不正确会导致无法加载

## 最佳实践

1. **使用环境变量存储敏感信息**：API 密钥等敏感信息应通过环境变量配置
2. **项目配置使用相对路径**：`.simple-agent/config.yml` 中的路径应使用相对路径
3. **共享默认配置**：将通用配置放在 `plugins/config.yml` 中
4. **插件特定配置**：插件特定的设置放在 `plugins/default/config.yml` 中
5. **版本控制**：忽略 `.simple-agent/` 目录，但可以提交 `plugins/config.yml`

## 故障排除

### 配置未生效

1. 检查配置优先级，确认是否有更高优先级的配置覆盖了你的设置
2. 使用 `--plugin-info` 查看实际加载的配置
3. 确认配置文件格式正确（YAML/JSON 语法）

### 资源未找到

1. 检查 `plugin.json` 中的资源路径配置
2. 确认路径存在且可访问
3. 注意 `~/` 会展开为用户主目录

### API 调用失败

1. 确认 API 密钥已通过环境变量或配置文件设置
2. 检查 `base_url` 是否正确
3. 确认模型名称与提供者匹配