---
name: config
description: Show or modify configuration
usage: /config [get|set] [key] [value]
---

# Configuration

## Current Configuration

### API
- **Provider**: {api_provider}
- **Base URL**: {base_url}
- **Model**: {model}

### Paths
- **Skills Directories**: {skills_dirs}
- **Agents Directory**: {agents_dir}
- **Hooks Directory**: {hooks_dir}
- **Commands Directory**: {commands_dir}

### UI
- **Theme**: {theme}
- **Show Thinking**: {show_thinking}

### Logging
- **Enabled**: {logging_enabled}
- **Log Directory**: {log_dir}

## Usage

- `/config` - Show all configuration
- `/config get <key>` - Get a specific configuration value
- `/config set <key> <value>` - Set a configuration value