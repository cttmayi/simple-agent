# Commands

This directory contains custom slash commands for simple-agent as flat `.md` files.

## Command Format

Each command is a `.md` file with frontmatter:

```markdown
---
name: command-name
description: A brief description of what the command does
usage: /command-name [optional-args]
---

# Command Title

Command help text goes here...

You can use template variables:
- `{session_id}` - Current session ID
- `{message_count}` - Number of messages in session
- `{api_provider}` - API provider name
- `{model}` - Model name
- `{base_url}` - API base URL
- `{skills_dirs}` - Skills directories
- `{agents_dir}` - Agents directory
- `{hooks_dir}` - Hooks directory
- `{commands_dir}` - Commands directory
- `{theme}` - UI theme
- `{show_thinking}` - Show thinking setting
- `{logging_enabled}` - Logging enabled setting
- `{log_dir}` - Log directory
- `{skills_count}` - Number of loaded skills
- `{agents_count}` - Number of loaded agents
- `{total_skills}` - Total available skills
- `{total_agents}` - Total available agents
- `{skills_list}` - List of available skills
- `{loaded_skills}` - List of loaded skills
- `{agents_list}` - List of available agents
- `{loaded_agents}` - List of loaded agents
```

## Available Commands

- `/version` - Show the current version
- `/clear` - Clear conversation history
- `/reset` - Reset session (clear history and unload skills/agents)
- `/status` - Show current session status
- `/config` - Show or modify configuration
- `/skills` - List available and loaded skills
- `/agents` - List available and loaded agents

## Creating a New Command

1. Create a new `.md` file in `plugin/commands/`
2. Add frontmatter and content
3. Restart simple-agent
4. Use `/help` to see your new command

## Builtin Commands

These commands are handled by the runtime and cannot be overridden:

- `/help` - Show help message
- `/exit` - Exit the agent
- `/quit` - Alias for `/exit`

## Example

Create `plugin/commands/greet.md`:

```markdown
---
name: greet
description: Say hello to the user
usage: /greet [name]
---

# Hello

Hello, {name}!

Welcome to simple-agent. We hope you have a great experience using this tool.
```