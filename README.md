# Simple Agent

A Claude Code-like CLI tool with support for hooks, skills, subagents, and slash commands.

## Features

- **Built-in Tools**: File operations (Read, Write, Edit), shell execution (Bash), pattern search (Grep), file matching (Glob), web search (WebSearch)
- **Custom Tools**: Register Python functions as tools for LLM function calling
- **Skills**: Markdown-based knowledge documents that guide AI behavior
- **Subagents**: Specialized AI agents for specific tasks
- **Hooks**: Event-driven plugins for custom behavior (JSON-based configuration)
- **Commands**: Built-in and custom slash commands (skills can be invoked as commands)
- **Multi-Provider**: Support for OpenAI and Anthropic/Claude APIs
- **Request Logging**: Track LLM requests and responses for analysis
- **Tool Filtering**: Disable specific tools via configuration

## Installation

```bash
pip install -e .
```

## Configuration

Configuration can be set at multiple levels, with the following priority (highest to lowest):

1. **Environment variables** - Override all other settings
2. **Local config** - `.simple-agent/config.yml` (project-specific)
3. **User config** - `~/.config/simple-agent/config.yml` (user-level settings)
4. **Plugin-specific config** - `plugins/default/config.yml` (overrides shared config)
5. **Shared plugin config** - `plugins/config.yml` (default for all plugins)
6. **Defaults** - Built-in default values

**Important**: Resource paths (agents, skills, hooks, commands) are controlled by `plugins/default/.claude-plugin/plugin.json`, and additional paths can be added via YAML config files (merged, not replaced).

### Example Configuration

By default, the plugin metadata in `plugins/default/.claude-plugin/plugin.json` defines resource paths:

```json
{
  "agents": "./agents",
  "skills": "./skills",
  "hooks": "./hooks",
  "commands": "./commands"
}
```

The `plugins/config.yml` file contains default settings like UI, logging, tools, and internal paths:

```yaml
paths:
  tools_dir: ./.simple-agent/tools
  memory_dir: ./.simple-agent/memory
  logs_dir: ./.simple-agent/logs

ui:
  theme: dark
  show_thinking: true

logging:
  enabled: true

# Tool configuration - disable specific tools as needed
tools:
  Bash: true
  Read: true
  Write: true
  Edit: true
  Grep: true
  Glob: true
```

You can optionally create a `.simple-agent/config.yml` file in your project to override settings:

```yaml
api:
  provider: openai  # or anthropic
  base_url: https://api.openai.com/v1
  api_key: ${OPENAI_API_KEY}  # Can reference environment variables
  model: gpt-4o

ui:
  theme: light  # Override the default 'dark' theme

logging:
  log_dir: ./logs/llm  # Override the default ./.simple-agent/logs
```

**Note**: Resource paths (skills, agents, hooks, commands) can be configured in two places:
1. `plugin.json` - Base paths for the plugin
2. YAML config files - Additional paths that are merged with the base paths

**Option 1: Add paths in plugin.json**

```json
{
  "skills": ["./skills", "~/.agents/skills"],
  "agents": ["./agents"],
  "hooks": ["./hooks"],
  "commands": ["./commands"]
}
```

**Option 2: Add paths in YAML config (e.g., plugins/config.yml or .simple-agent/config.yml)**

```yaml
paths:
  skills_dir: ["~/.agents/skills", "~/custom/skills"]
  agents_dir: "~/custom/agents"
  hooks_dir: "~/custom/hooks"
  commands_dir: "~/custom/commands"
```

### Configuration Options Reference

| Section | Option | Type | Default | Description |
|---------|--------|------|---------|-------------|
| **api** | `provider` | string | `openai` | API provider: `openai` or `anthropic` |
| | `base_url` | string | `null` | API base URL |
| | `api_key` | string | `null` | API key (supports `${VAR}`) |
| | `model` | string | `gpt-4o` | Model name |
| **paths** | `tools_dir` | string | `./.simple-agent/tools` | Tools directory |
| | `memory_dir` | string | `./.simple-agent/memory` | Memory directory |
| | `logs_dir` | string | `./.simple-agent/logs` | Logs directory |
| | `skills_dir` | string/array | `null` | Additional skills paths (merged) |
| | `agents_dir` | string/array | `null` | Additional agents paths (merged) |
| | `hooks_dir` | string/array | `null` | Additional hooks paths (merged) |
| | `commands_dir` | string/array | `null` | Additional commands paths (merged) |
| **ui** | `theme` | string | `dark` | Theme: `dark` or `light` |
| | `show_thinking` | boolean | `true` | Show AI thinking process |
| **logging** | `enabled` | boolean | `true` | Enable logging |
| | `log_dir` | string | `null` | Log directory |
| **tools** | `Bash` | boolean | `true` | Enable Bash command execution |
| | `Read` | boolean | `true` | Enable file reading |
| | `Write` | boolean | `true` | Enable file writing |
| | `Edit` | boolean | `true` | Enable file editing |
| | `Grep` | boolean | `true` | Enable pattern search |
| | `Glob` | boolean | `true` | Enable file pattern matching |
| | `Skill` | boolean | `true` | Enable Skill tool |
| | `Agent` | boolean | `true` | Enable Agent tool |
| | `TaskCreate` | boolean | `true` | Enable task creation |
| | `TaskGet` | boolean | `true` | Enable task retrieval |
| | `TaskUpdate` | boolean | `true` | Enable task updates |
| | `TaskList` | boolean | `true` | Enable task listing |

**Environment Variables:**
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` - API keys
- `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL` - API URLs
- `SIMPLE_AGENT_LOG_DIR` - Log directory
- `SIMPLE_AGENT_TODOS_PATH` - TODO data file path

For detailed configuration documentation, see [Configuration Documentation](docs/configuration.md).

### Tool Filtering

You can disable specific tools to prevent the LLM from using them:

```yaml
# Example: Disable Bash for read-only mode
tools:
  Bash: false

# Example: Disable all TODO tools
tools:
  TaskCreate: false
  TaskGet: false
  TaskUpdate: false
  TaskList: false
```

Tools not listed in the configuration default to `true` (enabled). Tool name matching is case-insensitive (`bash`, `Bash`, `BASH` all work).

### Log Analysis

LLM requests and responses are logged to daily JSONL files (`logs/llm/llm-YYYY-MM-DD.jsonl`).

View logs in human-readable format:

```bash
# View all conversations from today
simple-agent --logs

# View recent 5 conversations
simple-agent --logs -r 5

# Search for specific text
simple-agent --logs -s "error"

# List only conversation IDs
simple-agent --logs -i

# View specific date
simple-agent-logs logs/llm/llm-2024-01-01.jsonl
```

Programmatic analysis:

```python
from simple_agent.core.llm_logger import parse_log_file, get_conversation

# Parse all entries
entries = parse_log_file(Path("logs/llm/llm-2024-01-01.jsonl"))

# Get a specific conversation
conv = get_conversation(entries, request_id="...")
print(f"Model: {conv['request']['model']}")
print(f"Tokens: {conv['response']['usage']}")
```

## Usage

```bash
simple-agent
```

## Web 聊天 UI

simple-agent 提供浏览器内的交互式聊天界面：

```bash
# 启动 Web 聊天服务
simple-agent --web-chat

# 指定端口
simple-agent --web-chat --port 8080

# 从最近的日志恢复会话
simple-agent --web-chat --resume

# 从指定日志恢复
simple-agent --web-chat --resume .simple-agent/logs/llm-20260520-101010.jsonl
```

浏览器打开 http://localhost:5002（默认端口）即可使用。

特性：
- 实时对话，工具调用过程以可折叠卡片显示
- 侧边栏显示 TODOs / 已加载 Skills / 可用 Skills 与 Agents
- 支持斜杠命令（`/help`、`/clear` 等，与 CLI 一致）
- Markdown 渲染 + 代码语法高亮
- 一键从历史日志恢复会话

## Project Structure

```
simple-agent/
├── simple_agent/          # Core package
├── plugins/               # Plugins directory
│   ├── config.yml         # Shared default configuration
│   └── default/           # Default plugin
│       ├── .claude-plugin/
│       │   └── plugin.json    # Plugin metadata & resource paths
│       ├── skills/            # Skill definitions (SKILL.md)
│       ├── agents/            # Agent definitions (AGENT.md)
│       ├── hooks/             # Hook definitions (hooks.json)
│       ├── commands/          # Command definitions (.md files)
│       └── config.yml         # Plugin-specific configuration
├── .simple-agent/         # Configuration and runtime data
│   ├── config.yml         # Project-specific configuration
│   ├── tools/             # Tool implementations
│   ├── memory/            # Auto-generated memory
│   └── logs/              # LLM request/response logs
├── docs/                  # Documentation
└── tests/                 # Test suite
```

## Usage

```bash
simple-agent
```

### Slash Commands

Simple Agent supports slash commands for quick operations. See [Commands Documentation](docs/commands.md) for details.

```bash
> /help          # Show all available commands
> /version       # Show version information
> /status        # Show session status
> /git-status    # Show git repository status (with bash execution)
> /clear         # Clear conversation history
> /reset         # Reset session (clear history + unload skills/agents)
```

#### Command Features

Custom commands support powerful features:

- **Parameters**: Use `$1` or `$args` to pass arguments
- **Bash execution**: Use `!`command`` to run shell commands
- **File inclusion**: Use `@filename` to include file content
- **Template variables**: Use `{variable_name}` for dynamic values
- **Namespaces**: Organize commands with `/` separator (e.g., `/git/commit`)
- **Tool restrictions**: Use `allowed-tools` field to limit available tools

### Plugin System

The `plugins/` directory houses custom extensions:

- **plugins/config.yml** - Shared default configuration for all plugins
- **plugins/default/** - Default plugin containing:
  - **skills/** - Markdown-based knowledge documents (SKILL.md files)
  - **agents/** - Specialized AI agents (AGENT.md files)
  - **hooks/** - Event-driven plugins (hooks.json)
  - **commands/** - Custom slash commands (Markdown files)
  - **.claude-plugin/plugin.json** - Plugin metadata and resource paths
  - **config.yml** - Plugin-specific configuration

**Features:**
- Skills are automatically loaded as commands - use `/skill-name` to invoke them
- Resource directories are auto-discovered if not specified in plugin.json
- Hooks use JSON configuration with event matching (e.g., `matcher: "startup|clear|compact"`)

Use the `-p` or `--plugin` flag to specify a different plugin:

```bash
simple-agent -p ./plugins/custom
simple-agent --plugin ~/my-plugins/awesome-plugin
```

See [Commands Documentation](docs/commands.md) for creating custom commands.

## Development

Run tests:

```bash
pytest
```

## Documentation

- [Configuration Documentation](docs/configuration.md) - Configuration files, priority, and options
- [Commands Documentation](docs/commands.md) - Creating and using custom slash commands
- [Subagents Documentation](docs/subagents.md) - Creating and using isolated subagents