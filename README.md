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
2. **Local config** - `.simple-agent/config.yml` (project-specific, highest priority)
3. **Plugin config** - `plugin/config.yml` (plugin-level defaults)
4. **User config** - `~/.config/simple-agent/config.yml` (user-level settings)
5. **Defaults** - Built-in default values

### Example Configuration

By default, the plugin configuration in `plugin/config.yml` includes:

```yaml
paths:
  skills_dirs:
    - ./plugin/skills      # Project-local skills
    - ~/.agents/skills    # User's global skills directory
```

You can create a `.simple-agent/config.yml` file in your project to override these settings:

```yaml
api:
  provider: openai  # or anthropic
  base_url: https://api.openai.com/v1
  api_key: ${OPENAI_API_KEY}  # Can reference environment variables
  model: gpt-4o

paths:
  skills_dirs:
    - ./plugin/skills
    - ~/.agents/skills
  agents_dir: ./plugin/agents
  hooks_dir: ./plugin/hooks
  commands_dir: ./plugin/commands
  tools_dir: ./.simple-agent/tools
  memory_dir: ./.simple-agent/memory

ui:
  theme: dark
  show_thinking: true

logging:
  enabled: true
  log_dir: ./logs/llm  # Optional, defaults to ./.simple-agent/logs
```

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
├── plugin/                # Plugins (skills, agents, hooks, commands)
│   ├── skills/            # Skill definitions
│   ├── agents/            # Agent definitions
│   ├── hooks/             # Hook definitions
│   ├── commands/          # Command definitions
│   └── AGENT.md           # Project-specific instructions
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
> /clear         # Clear conversation history
> /reset         # Reset session (clear history + unload skills/agents)
```

### Plugin System

The `plugin/` directory houses all custom extensions:

- **skills/** - Markdown-based knowledge documents
- **agents/** - Specialized AI agents
- **hooks/** - Event-driven plugins
- **commands/** - Custom slash commands
- **AGENT.md** - Project-specific instructions

See [Commands Documentation](docs/commands.md) for creating custom commands.

## Development

Run tests:

```bash
pytest
```

## Documentation

- [Commands Documentation](docs/commands.md) - Creating and using custom slash commands
- [Subagents Documentation](docs/subagents.md) - Creating and using isolated subagents