# Simple Agent

A Claude Code-like CLI tool with support for hooks, skills, subagents, and slash commands.

## Features

- **Built-in Tools**: File operations (READ, WRITE), shell execution (BASH), pattern search (GREP), web search (WebSearch)
- **Custom Tools**: Register Python functions as tools for LLM function calling
- **Skills**: Markdown-based knowledge documents that guide AI behavior
- **Subagents**: Specialized AI agents for specific tasks
- **Hooks**: Event-driven plugins for custom behavior
- **Commands**: Built-in and custom slash commands
- **Multi-Provider**: Support for OpenAI and Anthropic/Claude APIs
- **Request Logging**: Track LLM requests and responses for analysis

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

The `plugins/config.yml` file contains default settings like UI, logging, and internal paths:

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

**Environment Variables:**
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` - API keys
- `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL` - API URLs
- `SIMPLE_AGENT_LOG_DIR` - Log directory
- `SIMPLE_AGENT_TODOS_PATH` - TODO data file path

For detailed configuration documentation, see [Configuration Documentation](docs/configuration.md).

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

## Project Structure

```
simple-agent/
├── simple_agent/          # Core package
├── plugins/               # Plugins directory
│   └── default/           # Default plugin
│       ├── skills/        # Skill definitions
│       ├── agents/        # Agent definitions
│       ├── hooks/         # Hook definitions
│       ├── commands/      # Command definitions
│       └── AGENT.md       # Project-specific instructions
├── .simple-agent/         # Configuration and runtime data
│   ├── tools/             # Tool implementations
│   ├── memory/            # Auto-generated memory
│   └── logs/              # LLM request/response logs
└── AGENT.md               # Project-specific instructions (optional, deprecated)
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

- **plugins/default/** - Default plugin containing:
  - **skills/** - Markdown-based knowledge documents
  - **agents/** - Specialized AI agents
  - **hooks/** - Event-driven plugins
  - **commands/** - Custom slash commands
  - **AGENT.md** - Project-specific instructions

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