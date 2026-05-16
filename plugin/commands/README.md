# Commands

This directory contains custom slash commands for simple-agent as flat `.md` files.

## Command Format

Each command is a `.md` file with frontmatter:

```markdown
---
name: command-name
description: A brief description of what the command does
---

# Command Title

Command help text goes here...
```

## Features

- **Parameter replacement**: Use `$1` or `$args` to insert command arguments
- **Bash command execution**: Use !`command` to execute and include output
- **File inclusion**: Use @filename to include file content

## Available Commands

- `/version` - Show the current version
- `/clear` - Clear conversation history
- `/reset` - Reset session (clear history and unload skills/agents)
- `/status` - Show current session status
- `/config` - Show or modify configuration
- `/skills` - List available skills
- `/agents` - List available agents

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
---

# Hello

Hello, $1!

Welcome to simple-agent.
```