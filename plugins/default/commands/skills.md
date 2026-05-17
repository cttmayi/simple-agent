---
name: skills
description: List available skills
---

# Available Skills

Skills are loaded from directories configured in `plugins/default/.claude-plugin/plugin.json`.

By default, skills are loaded from `./plugins/default/skills`. To add custom paths like `~/.agents/skills`, update the `plugin.json` file:

```json
{
  "skills": ["./skills", "~/.agents/skills"]
}
```