---
name: agents
description: List available agents
---

# Agents

Agents are loaded from `./plugin/agents` directory.

## Subagent Execution

Agents are invoked using the `run_subagent` tool:

```
Please run the code-analyzer agent to analyze this project.
```

The AI will automatically call `run_subagent(agent_name="code-analyzer", task="...")` to execute the agent in an isolated context.