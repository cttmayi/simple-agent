---
name: config
description: Show or modify configuration
---

# Configuration

Use environment variables or `~/.config/simple-agent/config.yml` to configure the agent.

### API Configuration
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` - API key
- `OPENAI_BASE_URL` or `ANTHROPIC_BASE_URL` - API base URL

### Example Config
```bash
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1
simple-agent
```