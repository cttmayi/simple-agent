---
name: agents
description: List available and loaded agents
---

# Agents

Agents run as isolated subagents with their own execution context and tools.

## Available Agents

{agents_list}

## Loaded Agents

{loaded_agents}

## Subagent Execution

Agents are now invoked using the `run_subagent` tool:

```
Please run the code-analyzer agent to analyze this project.
```

The AI will automatically call `run_subagent(agent_name="code-analyzer", task="...")` to execute the agent in an isolated context.