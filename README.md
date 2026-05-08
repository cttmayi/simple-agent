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

Create a `.simple-agent/config.yml` file:

```yaml
api:
  provider: openai  # or anthropic
  base_url: https://api.openai.com/v1
  api_key: ${OPENAI_API_KEY}
  model: gpt-4o

paths:
  skills_dir: ./skills
  subagents_dir: ./subagents
  hooks_dir: ./hooks
  commands_dir: ./commands
  tools_dir: ./tools
  memory_dir: ./memory

ui:
  theme: dark
  show_thinking: true

logging:
  enabled: true
  log_dir: ./logs/llm  # Optional, defaults to ./logs/llm
```

### Log Analysis

LLM requests and responses are logged to daily JSONL files (`logs/llm/llm-YYYY-MM-DD.jsonl`).

To analyze logs:

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
├── skills/                 # Skill definitions
├── subagents/              # Subagent definitions
├── hooks/                  # Hook definitions
├── commands/               # Command definitions
├── tools/                  # Tool implementations
├── memory/                 # Auto-generated memory
└── AGENT.md                # Project-specific instructions
```

## Development

Run tests:

```bash
pytest
```