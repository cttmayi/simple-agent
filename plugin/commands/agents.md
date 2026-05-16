---
name: agents
description: List available and loaded agents
usage: /agents [list|load|unload] [name]
---

# Agents

Agents run as isolated subagents with their own execution context and tools.

## Available Agents

{agents_list}

## Loaded Agents

{loaded_agents}

## Usage

- `/agents` - List all agents
- `/agents list` - List all available agents
- `/agents load <name>` - Load a specific agent (deprecated, use run_subagent)
- `/agents unload <name>` - Unload a specific agent

## Subagent Execution

Agents are now invoked using the `run_subagent` tool:

```
Please run the code-analyzer agent to analyze this project.
```

The AI will automatically call `run_subagent(agent_name="code-analyzer", task="...")` to execute the agent in an isolated context.