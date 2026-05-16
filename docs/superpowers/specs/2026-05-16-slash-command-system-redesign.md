# Slash Command 系统重设计

**日期**: 2026-05-16
**作者**: Claude

## 概述

重新设计 Simple Agent 的 slash command 系统，将命令升级为可执行的工作流程模板。命令内容经过模板处理器执行后，作为系统消息发送给 AI，指导 AI 执行特定任务。

## 功能需求

1. **参数支持** - 支持单个字符串参数（`$1`, `$args`）
2. **Bash 命令执行** - 支持 ``!`command` `` 语法执行 bash 命令
3. **文件引用** - 支持 `@filename` 语法包含文件内容
4. **Allowed Tools** - 在 frontmatter 中指定允许 AI 使用的工具
5. **命名空间组织** - 支持子目录组织命令（如 `/git/commit`）

## 架构设计

### 组件

1. **CommandLoader** - 从 `plugin/commands/` 加载命令文件（支持子目录）
2. **CommandProcessor** - 新增的模板处理器，负责解析和执行命令
3. **Runtime** - 集成处理器，将处理后的内容发送给 AI

### 数据流

```
用户输入 /commit Fix the login bug
    ↓
Runtime._handle_slash_command()
    ↓
CommandProcessor.process(command, args)
    ↓
模板处理（参数、bash、文件）
    ↓
系统消息发送给 AI
```

## 命令文件格式

### Frontmatter 字段

```yaml
---
name: commit                    # 命令名称（可选，默认使用文件名）
description: Create git commit  # 命令描述
allowed-tools: Bash, Read, Grep # 可选：限制 AI 可用的工具
argument-hint: [message]        # 可选：参数提示
---

命令内容...
```

### 内容语法

- **位置参数**：`$1`, `$args` 引用参数（只支持单个参数）
- **Bash 执行**：``!`command` `` 执行 bash 并替换为输出
- **文件引用**：`@filename` 替换为文件内容（相对路径）

### 示例

```markdown
---
name: commit
description: Create a git commit
allowed-tools: Bash(git *)
---

## Context

- Current status: !`git status`
- Current diff: !`git diff HEAD`

## Task

Create a git commit with message: $1

Review the changes and ensure they're correct before committing.
```

## CommandProcessor 实现

### 核心方法

```python
class CommandProcessor:
    def __init__(self, config: Settings, logger: LLMLogger):
        self._config = config
        self._logger = logger

    def process(self, command_data: dict, args: List[str]) -> ProcessedCommand:
        """处理命令并返回处理后的内容"""
        content = command_data["content"]

        # 1. 替换参数
        content = self._replace_positional_params(content, args)

        # 2. 执行 bash 命令 !`cmd`
        content = self._execute_bash_commands(content)

        # 3. 包含文件 @filename
        content = self._include_files(content)

        # 4. 替换模板变量 {session_id} 等（保留现有）
        content = self._replace_template_variables(content)

        return ProcessedCommand(
            content=content,
            allowed_tools=command_data["metadata"].get("allowed-tools"),
            description=command_data["description"]
        )
```

### 参数处理

```python
def _replace_positional_params(self, content: str, args: List[str]) -> str:
    # 所有参数连接成一个字符串
    arg_value = " ".join(args)

    # 替换 $1 和 $args
    content = content.replace("$1", arg_value)
    content = content.replace("$args", arg_value)

    # $# - 是否有参数（1 或 0）
    content = content.replace("$#", "1" if arg_value else "0")

    return content
```

### Bash 命令执行

```python
def _execute_bash_commands(self, content: str) -> str:
    import subprocess
    import re

    pattern = r'!`([^`]*)`'

    def replace(match):
        cmd = match.group(1)
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() or result.stderr.strip()
        except subprocess.TimeoutExpired:
            return "[Command timed out]"
        except Exception as e:
            return f"[Error: {str(e)}]"

    return re.sub(pattern, replace, content)
```

### 文件引用

```python
def _include_files(self, content: str) -> str:
    import re
    pattern = r'@(\S+)'

    def replace(match):
        filepath = Path.cwd() / match.group(1)
        try:
            return filepath.read_text()
        except FileNotFoundError:
            return f"[File not found: {match.group(1)}]"
        except Exception as e:
            return f"[Error reading file: {str(e)}]"

    return re.sub(pattern, replace, content)
```

## 命名空间组织

### 目录结构

```
plugin/commands/
├── git/
│   ├── commit.md      # /git/commit
│   └── status.md      # /git/status
├── frontend/
│   └── test.md        # /frontend/test
└── help.md            # /help (内置命令，不可覆盖)
```

### CommandLoader 修改

```python
def list_commands(self) -> List[dict]:
    commands = []

    for md_file in self._base_dir.rglob("*.md"):
        if md_file.name == "README.md":
            continue

        # 计算相对路径作为命令名
        rel_path = md_file.relative_to(self._base_dir)
        command_name = str(rel_path.with_suffix('')).replace('/', '/')

        parsed = frontmatter.load(md_file)
        name = parsed.get("name", command_name)

        commands.append({
            "name": name,
            "description": parsed.get("description", ""),
            "path": str(md_file),
            "metadata": parsed.metadata,
            "content": parsed.content,
        })

    return commands
```

## Allowed Tools

### 格式

```yaml
---
allowed-tools: Bash, Read, Grep
---
```

### 行为

- 逗号分隔的工具名称列表
- 支持 glob 模式：`Bash(git *)` 限制 git 相关命令
- 省略表示不限制工具
- 临时修改 tool_registry，命令执行后恢复

## Runtime 集成

```python
def _handle_slash_command(self, command: str, args: List[str]) -> str:
    # 内置命令
    if command == "help":
        return self._cmd_help()
    elif command == "exit" or command == "quit":
        return "exit"
    elif command == "clear":
        self._session.clear()
        self._loaded_skills.clear()
        self._loaded_agents.clear()
        return self._load_command("clear", args)
    elif command == "reset":
        self._session.clear()
        self._loaded_skills.clear()
        self._loaded_agents.clear()
        return self._load_command("reset", args)

    # 加载命令
    cmd_data = self._command_loader.get_command(command)
    if not cmd_data:
        return f"Unknown command: /{command}"

    # 使用 CommandProcessor 处理
    processor = CommandProcessor(self._config, self._logger)
    processed = processor.process(cmd_data, args)

    # 保存工具快照（用于限制工具）
    saved_tools = processor._apply_allowed_tools(processed.allowed_tools)

    # 添加到 session 作为系统消息
    self._session.add_message("system", processed.content)

    # 恢复工具
    if saved_tools:
        processor._restore_tools(saved_tools)

    # 返回特殊标记，让主循环知道需要发送给 API
    return "command_processed"
```

## 错误处理

### 错误类型

1. **Bash 超时** - 10 秒超时，显示 `[Command timed out]`
2. **文件不存在** - 显示 `[File not found: filename]`
3. **参数越界** - 参数不存在时替换为空字符串
4. **命令不存在** - 返回 `Unknown command: /{command}`

### 边界情况

- 空参数列表
- 空命令内容
- 命令没有 frontmatter
- 命令参数包含特殊字符

## 测试策略

### 测试文件

1. `test_command_processor.py` - CommandProcessor 测试
   - 参数替换
   - Bash 命令执行
   - 文件引用
   - 组合处理

2. `test_command_loader_namespace.py` - 命名空间测试
   - 子目录加载
   - 命令名称解析

3. `test_runtime_commands_integration.py` - 集成测试
   - 端到端命令执行
   - 工具限制验证

### 示例测试

```python
def test_parameter_replacement():
    processor = CommandProcessor(config, logger)
    cmd_data = {"content": "Fix bug: $1"}
    result = processor.process(cmd_data, ["login issue"])
    assert "Fix bug: login issue" in result.content

def test_bash_execution():
    processor = CommandProcessor(config, logger)
    cmd_data = {"content": "Status: !`echo OK`"}
    result = processor.process(cmd_data, [])
    assert "Status: OK" in result.content
```

## 工具注册表扩展

ToolRegistry 需要新增以下方法：

```python
class ToolRegistry:
    def snapshot(self) -> dict:
        """保存当前工具状态"""
        return self._tools.copy()

    def restore(self, snapshot: dict):
        """恢复工具状态"""
        self._tools = snapshot

    def filter_tools(self, allowed: List[str]):
        """根据允许的工具过滤"""
        # 实现工具过滤逻辑
        pass
```

## 依赖文件修改

- `simple_agent/resources/commands.py` - CommandLoader 支持子目录
- `simple_agent/tools/registry.py` - 新增 snapshot/restore/filter 方法
- `simple_agent/core/runtime.py` - 集成 CommandProcessor
- `tests/test_commands.py` - 更新现有测试
- 新增 `tests/test_command_processor.py`
- 新增 `tests/test_command_loader_namespace.py`