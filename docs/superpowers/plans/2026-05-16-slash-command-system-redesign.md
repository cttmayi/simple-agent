# Slash Command System Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Simple Agent's slash command system to support parameter replacement, bash execution, file inclusion, allowed tools, and namespace organization.

**Architecture:** Introduce CommandProcessor as a new component that processes command templates. Commands are loaded with namespace support, processed through the processor, and the result is sent to AI as a system message.

**Tech Stack:** Python 3.14+, pytest, subprocess, pathlib, re, dataclasses

---

## File Structure

**New Files:**
- `simple_agent/resources/command_processor.py` - Template processor for commands
- `tests/test_command_processor.py` - CommandProcessor unit tests
- `tests/test_command_loader_namespace.py` - Namespace loader tests
- `tests/test_runtime_commands_integration.py` - Integration tests

**Modified Files:**
- `simple_agent/tools/registry.py` - Add snapshot/restore/filter methods
- `simple_agent/resources/commands.py` - Add namespace support
- `simple_agent/core/runtime.py` - Integrate CommandProcessor
- `tests/test_commands.py` - Update for new features
- `tests/test_runtime_commands.py` - Update integration tests

---

### Task 1: ToolRegistry - Add snapshot/restore methods

**Files:**
- Modify: `simple_agent/tools/registry.py`

- [ ] **Step 1: Write failing test for snapshot**

```python
# tests/test_tool_registry_snapshot.py
import pytest
from simple_agent.tools.registry import ToolRegistry, ToolDefinition
from simple_agent.tools import builtin  # noqa: F401

def test_registry_snapshot():
    registry = get_global_registry()

    # Get initial tool count
    initial_count = len(registry._tools)

    # Save snapshot
    snapshot = registry.snapshot()

    # Snapshot should be a copy
    assert snapshot == registry._tools
    assert snapshot is not registry._tools
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_tool_registry_snapshot.py::test_registry_snapshot -v
```
Expected: FAIL with "'ToolRegistry' object has no attribute 'snapshot'"

- [ ] **Step 3: Add snapshot and restore methods to ToolRegistry**

```python
# simple_agent/tools/registry.py
class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def snapshot(self) -> Dict[str, ToolDefinition]:
        """Save current tool state as a copy."""
        return self._tools.copy()

    def restore(self, snapshot: Dict[str, ToolDefinition]) -> None:
        """Restore tool state from snapshot."""
        self._tools = snapshot
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_tool_registry_snapshot.py::test_registry_snapshot -v
```
Expected: PASS

- [ ] **Step 5: Add test for restore**

```python
# tests/test_tool_registry_snapshot.py
def test_registry_restore():
    registry = ToolRegistry()

    # Register a tool
    tool1 = ToolDefinition(name="test1", description="Test 1", fn=lambda: None, parameters={})
    registry.register(tool1)

    # Save snapshot
    snapshot = registry.snapshot()

    # Register another tool
    tool2 = ToolDefinition(name="test2", description="Test 2", fn=lambda: None, parameters={})
    registry.register(tool2)

    # Should have 2 tools
    assert len(registry._tools) == 2

    # Restore snapshot
    registry.restore(snapshot)

    # Should have 1 tool again
    assert len(registry._tools) == 1
    assert "test1" in registry._tools
    assert "test2" not in registry._tools
```

- [ ] **Step 6: Run test to verify it passes**

```bash
pytest tests/test_tool_registry_snapshot.py::test_registry_restore -v
```
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add simple_agent/tools/registry.py tests/test_tool_registry_snapshot.py
git commit -m "feat: ToolRegistry 新增 snapshot/restore 方法

允许保存和恢复工具注册表状态，用于命令执行时临时限制工具。
"
```

---

### Task 2: ToolRegistry - Add filter method

**Files:**
- Modify: `simple_agent/tools/registry.py`

- [ ] **Step 1: Write failing test for filter**

```python
# tests/test_tool_registry_filter.py
import pytest
from simple_agent.tools.registry import ToolRegistry, ToolDefinition

def test_registry_filter_simple():
    registry = ToolRegistry()

    # Register multiple tools
    registry.register(ToolDefinition(name="bash", description="Bash", fn=lambda: None, parameters={}))
    registry.register(ToolDefinition(name="read", description="Read", fn=lambda: None, parameters={}))
    registry.register(ToolDefinition(name="write", description="Write", fn=lambda: None, parameters={}))

    # Save snapshot
    snapshot = registry.snapshot()

    # Filter to only bash and read
    registry.filter(["bash", "read"])

    # Should only have bash and read
    assert len(registry._tools) == 2
    assert "bash" in registry._tools
    assert "read" in registry._tools
    assert "write" not in registry._tools
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_tool_registry_filter.py::test_registry_filter_simple -v
```
Expected: FAIL with "'ToolRegistry' object has no attribute 'filter'"

- [ ] **Step 3: Add filter method to ToolRegistry**

```python
# simple_agent/tools/registry.py
class ToolRegistry:
    # ... existing methods ...

    def filter(self, allowed: List[str]) -> None:
        """Filter tools to only include those in the allowed list.

        Args:
            allowed: List of tool names to allow
        """
        allowed_set = set(allowed)
        self._tools = {
            name: tool for name, tool in self._tools.items()
            if name in allowed_set
        }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_tool_registry_filter.py::test_registry_filter_simple -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add simple_agent/tools/registry.py tests/test_tool_registry_filter.py
git commit -m "feat: ToolRegistry 新增 filter 方法

允许根据白名单过滤工具，用于命令执行时限制可用工具。
"
```

---

### Task 3: Create CommandProcessor base structure

**Files:**
- Create: `simple_agent/resources/command_processor.py`
- Test: `tests/test_command_processor.py`

- [ ] **Step 1: Write failing test for basic processor**

```python
# tests/test_command_processor.py
import pytest
from simple_agent.resources.command_processor import CommandProcessor, ProcessedCommand
from simple_agent.config.settings import Settings
from simple_agent.core.llm_logger import LLMLogger

def test_processor_creates_processed_command():
    config = Settings()
    logger = LLMLogger()
    processor = CommandProcessor(config, logger)

    cmd_data = {
        "content": "Hello world",
        "metadata": {}
    }

    result = processor.process(cmd_data, [])

    assert isinstance(result, ProcessedCommand)
    assert result.content == "Hello world"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_command_processor.py::test_processor_creates_processed_command -v
```
Expected: FAIL with "No module named 'simple_agent.resources.command_processor'"

- [ ] **Step 3: Create ProcessedCommand dataclass and CommandProcessor skeleton**

```python
# simple_agent/resources/command_processor.py
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

from simple_agent.config.settings import Settings
from simple_agent.core.llm_logger import LLMLogger


@dataclass
class ProcessedCommand:
    """Processed command result."""
    content: str
    allowed_tools: Optional[str]
    description: str


class CommandProcessor:
    """Process command templates by replacing parameters, executing bash, and including files."""

    def __init__(self, config: Settings, logger: LLMLogger):
        self._config = config
        self._logger = logger

    def process(self, command_data: dict, args: List[str]) -> ProcessedCommand:
        """Process command and return processed content.

        Args:
            command_data: Command data with 'content' and 'metadata'
            args: Command arguments

        Returns:
            ProcessedCommand with processed content
        """
        content = command_data.get("content", "")
        metadata = command_data.get("metadata", {})

        return ProcessedCommand(
            content=content,
            allowed_tools=metadata.get("allowed-tools"),
            description=metadata.get("description", "")
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_command_processor.py::test_processor_creates_processed_command -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add simple_agent/resources/command_processor.py tests/test_command_processor.py
git commit -m "feat: 新增 CommandProcessor 基础结构

添加 ProcessedCommand 数据类和 CommandProcessor 骨架。
"
```

---

### Task 4: CommandProcessor - Add parameter replacement

**Files:**
- Modify: `simple_agent/resources/command_processor.py`
- Modify: `tests/test_command_processor.py`

- [ ] **Step 1: Write failing test for parameter replacement**

```python
# tests/test_command_processor.py
def test_parameter_replacement_single():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Fix bug: $1", "metadata": {}}
    result = processor.process(cmd_data, ["login issue"])

    assert "Fix bug: login issue" in result.content

def test_parameter_replacement_with_spaces():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Commit: $1", "metadata": {}}
    result = processor.process(cmd_data, ["fix login bug and add tests"])

    assert "Commit: fix login bug and add tests" in result.content

def test_parameter_replacement_args_var():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Task: $args", "metadata": {}}
    result = processor.process(cmd_data, ["hello", "world"])

    assert "Task: hello world" in result.content

def test_parameter_replacement_no_args():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Task: $1", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Task: " in result.content

def test_parameter_replacement_has_args():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Args: $#", "metadata": {}}
    result = processor.process(cmd_data, ["test"])

    assert "Args: 1" in result.content

def test_parameter_replacement_no_args_count():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Args: $#", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Args: 0" in result.content
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_command_processor.py::test_parameter_replacement_single -v
```
Expected: FAIL (content not replaced)

- [ ] **Step 3: Add parameter replacement method**

```python
# simple_agent/resources/command_processor.py
class CommandProcessor:
    # ... existing code ...

    def process(self, command_data: dict, args: List[str]) -> ProcessedCommand:
        content = command_data.get("content", "")
        metadata = command_data.get("metadata", {})

        # Replace parameters
        content = self._replace_positional_params(content, args)

        return ProcessedCommand(
            content=content,
            allowed_tools=metadata.get("allowed-tools"),
            description=metadata.get("description", "")
        )

    def _replace_positional_params(self, content: str, args: List[str]) -> str:
        """Replace positional parameters ($1, $args, $#).

        Args:
            content: Content with parameters
            args: Command arguments

        Returns:
            Content with parameters replaced
        """
        # All args joined into one string
        arg_value = " ".join(args)

        # Replace $1 and $args
        content = content.replace("$1", arg_value)
        content = content.replace("$args", arg_value)

        # Replace $# with count (1 if has args, 0 otherwise)
        content = content.replace("$#", "1" if arg_value else "0")

        return content
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_command_processor.py -v -k "parameter_replacement"
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add simple_agent/resources/command_processor.py tests/test_command_processor.py
git commit -m "feat: CommandProcessor 支持参数替换

支持 $1, $args, $# 参数占位符，将命令参数替换到内容中。
"
```

---

### Task 5: CommandProcessor - Add bash command execution

**Files:**
- Modify: `simple_agent/resources/command_processor.py`
- Modify: `tests/test_command_processor.py`

- [ ] **Step 1: Write failing test for bash execution**

```python
# tests/test_command_processor.py
def test_bash_execution():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Status: !`echo OK`", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Status: OK" in result.content

def test_bash_execution_with_command_output():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Files: !`ls tests/`", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Files:" in result.content
    assert "test_" in result.content or "command_" in result.content

def test_bash_execution_timeout():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Result: !`sleep 15`", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Result: [Command timed out]" in result.content

def test_bash_execution_error():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Result: !`exit 1`", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Result:" in result.content  # No output, but should not crash
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_command_processor.py::test_bash_execution -v
```
Expected: FAIL (backticks not processed)

- [ ] **Step 3: Add bash execution method**

```python
# simple_agent/resources/command_processor.py
import subprocess
import re

class CommandProcessor:
    # ... existing code ...

    def process(self, command_data: dict, args: List[str]) -> ProcessedCommand:
        content = command_data.get("content", "")
        metadata = command_data.get("metadata", {})

        # Replace parameters
        content = self._replace_positional_params(content, args)

        # Execute bash commands
        content = self._execute_bash_commands(content)

        return ProcessedCommand(
            content=content,
            allowed_tools=metadata.get("allowed-tools"),
            description=metadata.get("description", "")
        )

    def _execute_bash_commands(self, content: str) -> str:
        """Execute bash commands in !`cmd` syntax.

        Args:
            content: Content with bash commands

        Returns:
            Content with commands replaced by their output
        """
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
                output = result.stdout.strip() or result.stderr.strip()
                return output
            except subprocess.TimeoutExpired:
                return "[Command timed out]"
            except Exception as e:
                return f"[Error: {str(e)}]"

        return re.sub(pattern, replace, content)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_command_processor.py -v -k "bash_execution"
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add simple_agent/resources/command_processor.py tests/test_command_processor.py
git commit -m "feat: CommandProcessor 支持 bash 命令执行

支持 !\`command\` 语法执行 bash 命令并替换为输出。
10 秒超时保护。
"
```

---

### Task 6: CommandProcessor - Add file inclusion

**Files:**
- Modify: `simple_agent/resources/command_processor.py`
- Modify: `tests/test_command_processor.py`

- [ ] **Step 1: Write failing test for file inclusion**

```python
# tests/test_command_processor.py
import tempfile
from pathlib import Path

def test_file_inclusion():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory
        import os
        old_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Create test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello from file")

            processor = CommandProcessor(Settings(), LLMLogger())
            cmd_data = {"content": "Content: @test.txt", "metadata": {}}
            result = processor.process(cmd_data, [])

            assert "Content: Hello from file" in result.content
        finally:
            os.chdir(old_cwd)

def test_file_inclusion_not_found():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Content: @nonexistent.md", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Content: [File not found: nonexistent.md]" in result.content

def test_file_inclusion_with_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Create subdirectory and file
            subdir = Path(tmpdir) / "sub"
            subdir.mkdir()
            test_file = subdir / "test.txt"
            test_file.write_text("Nested content")

            processor = CommandProcessor(Settings(), LLMLogger())
            cmd_data = {"content": "Content: @sub/test.txt", "metadata": {}}
            result = processor.process(cmd_data, [])

            assert "Content: Nested content" in result.content
        finally:
            os.chdir(old_cwd)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_command_processor.py::test_file_inclusion -v
```
Expected: FAIL (@ not processed)

- [ ] **Step 3: Add file inclusion method**

```python
# simple_agent/resources/command_processor.py
class CommandProcessor:
    # ... existing code ...

    def process(self, command_data: dict, args: List[str]) -> ProcessedCommand:
        content = command_data.get("content", "")
        metadata = command_data.get("metadata", {})

        # Replace parameters
        content = self._replace_positional_params(content, args)

        # Execute bash commands
        content = self._execute_bash_commands(content)

        # Include files
        content = self._include_files(content)

        return ProcessedCommand(
            content=content,
            allowed_tools=metadata.get("allowed-tools"),
            description=metadata.get("description", "")
        )

    def _include_files(self, content: str) -> str:
        """Include file content using @filename syntax.

        Args:
            content: Content with file references

        Returns:
            Content with files replaced by their content
        """
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

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_command_processor.py -v -k "file_inclusion"
```
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add simple_agent/resources/command_processor.py tests/test_command_processor.py
git commit -m "feat: CommandProcessor 支持文件引用

支持 @filename 语法包含文件内容，相对项目根目录。
"
```

---

### Task 7: CommandProcessor - Add template variable replacement

**Files:**
- Modify: `simple_agent/resources/command_processor.py`
- Modify: `tests/test_command_processor.py`

- [ ] **Step 1: Write failing test for template variables**

```python
# tests/test_command_processor.py
def test_template_variables():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Session: {api_provider}, Model: {model}", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Session:" in result.content
    assert "Model:" in result.content
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_command_processor.py::test_template_variables -v
```
Expected: FAIL (braces not replaced)

- [ ] **Step 3: Add template variable replacement (reuse Runtime logic)**

```python
# simple_agent/resources/command_processor.py
class CommandProcessor:
    # ... existing code ...

    def process(self, command_data: dict, args: List[str]) -> ProcessedCommand:
        content = command_data.get("content", "")
        metadata = command_data.get("metadata", {})

        # Replace parameters
        content = self._replace_positional_params(content, args)

        # Execute bash commands
        content = self._execute_bash_commands(content)

        # Include files
        content = self._include_files(content)

        # Replace template variables
        content = self._replace_template_variables(content)

        return ProcessedCommand(
            content=content,
            allowed_tools=metadata.get("allowed-tools"),
            description=metadata.get("description", "")
        )

    def _replace_template_variables(self, content: str) -> str:
        """Replace template variables like {api_provider}, {model}, etc.

        Args:
            content: Content with template variables

        Returns:
            Content with variables replaced
        """
        # Configuration variables
        replacements = {
            '{api_provider}': self._config.api.provider,
            '{model}': self._config.api.model,
            '{base_url}': self._config.api.base_url or "default",
            '{skills_dirs}': ", ".join(self._config.paths.skills_dirs),
            '{agents_dir}': self._config.paths.agents_dir,
            '{hooks_dir}': self._config.paths.hooks_dir,
            '{commands_dir}': self._config.paths.commands_dir,
            '{theme}': self._config.ui.theme,
            '{show_thinking}': str(self._config.ui.show_thinking),
            '{logging_enabled}': str(self._config.logging.enabled),
            '{log_dir}': self._config.logging.log_dir or "default",
        }

        for var, value in replacements.items():
            content = content.replace(var, str(value))

        return content
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_command_processor.py::test_template_variables -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add simple_agent/resources/command_processor.py tests/test_command_processor.py
git commit -m "feat: CommandProcessor 支持模板变量替换

支持 {api_provider}, {model} 等配置变量替换。
"
```

---

### Task 8: CommandLoader - Add namespace support

**Files:**
- Modify: `simple_agent/resources/commands.py`
- Create: `tests/test_command_loader_namespace.py`

- [ ] **Step 1: Write failing test for namespace support**

```python
# tests/test_command_loader_namespace.py
import tempfile
from pathlib import Path
from simple_agent.resources.commands import CommandLoader

def test_namespace_from_subdirectory():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create subdirectory with command
        subdir = Path(tmpdir) / "git"
        subdir.mkdir()
        cmd_file = subdir / "commit.md"
        cmd_file.write_text("---\nname: commit\ndescription: Commit\n---\nContent")

        loader = CommandLoader(tmpdir)
        commands = loader.list_commands()

        # Should have command with namespace
        assert len(commands) == 1
        assert commands[0]["name"] == "git/commit"

def test_namespace_flat_commands():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create flat command
        cmd_file = Path(tmpdir) / "help.md"
        cmd_file.write_text("---\nname: help\ndescription: Help\n---\nContent")

        loader = CommandLoader(tmpdir)
        commands = loader.list_commands()

        # Should have command without namespace prefix
        assert len(commands) == 1
        assert commands[0]["name"] == "help"

def test_nested_namespace():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create nested subdirectory
        subdir = Path(tmpdir) / "frontend" / "test"
        subdir.mkdir(parents=True)
        cmd_file = subdir / "run.md"
        cmd_file.write_text("---\nname: run\ndescription: Run tests\n---\nContent")

        loader = CommandLoader(tmpdir)
        commands = loader.list_commands()

        assert len(commands) == 1
        assert commands[0]["name"] == "frontend/test/run"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_command_loader_namespace.py::test_namespace_from_subdirectory -v
```
Expected: FAIL (namespace not in name)

- [ ] **Step 3: Modify CommandLoader to support namespace**

```python
# simple_agent/resources/commands.py
class CommandLoader:
    """Loader for command resources (supports .md files with namespace)."""

    def __init__(self, base_dir: Path):
        self._base_dir = Path(base_dir)

    def list_commands(self) -> List[dict]:
        """List all available commands."""
        if not self._base_dir.exists():
            return []

        commands = []
        for md_file in self._base_dir.rglob("*.md"):
            if md_file.name == "README.md":
                continue

            # Calculate relative path as command name with namespace
            rel_path = md_file.relative_to(self._base_dir)
            command_name = str(rel_path.with_suffix('')).replace('\\', '/')

            parsed = frontmatter.load(md_file)
            # Use filename without extension as default name
            name = parsed.get("name", command_name)

            commands.append({
                "name": name,
                "description": parsed.get("description", ""),
                "path": str(md_file),
                "metadata": parsed.metadata,
                "content": parsed.content,
            })
        return commands

    def get_command(self, name: str) -> Optional[dict]:
        """Get a specific command by name."""
        commands = self.list_commands()
        for cmd in commands:
            if cmd["name"] == name:
                return cmd
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_command_loader_namespace.py -v
```
Expected: All PASS

- [ ] **Step 5: Update existing tests for compatibility**

```bash
pytest tests/test_commands.py -v
```
If tests fail, update them to use the new flat namespace format.

- [ ] **Step 6: Commit**

```bash
git add simple_agent/resources/commands.py tests/test_command_loader_namespace.py tests/test_commands.py
git commit -m "feat: CommandLoader 支持命名空间

使用 rglob 支持子目录，命令名称包含命名空间路径。
"
```

---

### Task 9: Runtime - Integrate CommandProcessor

**Files:**
- Modify: `simple_agent/core/runtime.py`

- [ ] **Step 1: Add CommandProcessor import and initialization**

```python
# simple_agent/core/runtime.py
from simple_agent.resources.commands import CommandLoader
from simple_agent.resources.command_processor import CommandProcessor  # Add this

class Runtime:
    def __init__(self, config: Settings, log_file: Optional[str] = None, skip_api_init: bool = False):
        # ... existing initialization ...
        self._command_loader = CommandLoader(base_dir / config.paths.commands_dir)
        self._command_processor = CommandProcessor(config, self._logger)  # Add this
```

- [ ] **Step 2: Modify _handle_slash_command to use CommandProcessor**

```python
# simple_agent/core/runtime.py
    def _handle_slash_command(self, command: str, args: List[str]) -> str:
        """Handle a slash command."""
        # Handle builtin commands first
        if command == "help":
            return self._cmd_help()
        elif command == "exit" or command == "quit":
            return "exit"

        # Handle special commands with actions
        if command == "clear":
            self._session.clear()
            self._loaded_skills.clear()
            self._loaded_agents.clear()
            return self._load_command("clear", args)
        elif command == "reset":
            self._session.clear()
            self._loaded_skills.clear()
            self._loaded_agents.clear()
            return self._load_command("reset", args)

        # Load command
        cmd_data = self._command_loader.get_command(command)
        if not cmd_data:
            return f"Unknown command: /{command}"

        # Use CommandProcessor to process
        processed = self._command_processor.process(cmd_data, args)

        # Apply allowed tools restriction
        if processed.allowed_tools:
            saved_tools = self._tool_registry.snapshot()
            allowed = [t.strip() for t in processed.allowed_tools.split(",")]
            self._tool_registry.filter(allowed)
        else:
            saved_tools = None

        # Add to session as system message
        self._session.add_message("system", processed.content)

        # Restore tools
        if saved_tools:
            self._tool_registry.restore(saved_tools)

        # Return special marker to indicate API call needed
        return "command_processed"
```

- [ ] **Step 3: Update main loop to handle command_processed**

The main loop in `run()` already handles "message_processed", which will work for "command_processed" too since it sends to API.

- [ ] **Step 4: Write integration test**

```python
# tests/test_runtime_commands_integration.py
import tempfile
from pathlib import Path
from simple_agent.config.settings import load_config
from simple_agent.core.runtime import Runtime
from simple_agent.core.session import Session

def test_command_processor_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test command
        cmd_dir = Path(tmpdir) / "commands"
        cmd_dir.mkdir()
        cmd_file = cmd_dir / "test.md"
        cmd_file.write_text("---\nname: test\ndescription: Test\n---\nHello $1")

        # Create runtime with custom command dir
        config = load_config()
        config.paths.commands_dir = str(cmd_dir)
        runtime = Runtime(config, skip_api_init=True)

        # Reload command loader with new path
        from simple_agent.resources.commands import CommandLoader
        runtime._command_loader = CommandLoader(cmd_dir)

        # Process command
        result = runtime._handle_slash_command("test", ["World"])

        assert result == "command_processed"

        # Check session has system message
        messages = runtime._session.get_messages()
        system_msgs = [m for m in messages if m.get("role") == "system"]
        assert len(system_msgs) > 0
        assert "Hello World" in system_msgs[-1].get("content", "")
```

- [ ] **Step 5: Run integration test**

```bash
pytest tests/test_runtime_commands_integration.py::test_command_processor_integration -v
```
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add simple_agent/core/runtime.py tests/test_runtime_commands_integration.py
git commit -m "feat: Runtime 集成 CommandProcessor

命令处理通过 CommandProcessor 执行，结果作为系统消息发送给 AI。
支持 allowed-tools 临时限制工具。
"
```

---

### Task 10: Update help command to show namespaces

**Files:**
- Modify: `simple_agent/core/runtime.py`

- [ ] **Step 1: Write test for help command with namespaces**

```python
# tests/test_runtime_commands_integration.py
def test_help_command_shows_namespaces():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create commands with namespaces
        cmd_dir = Path(tmpdir) / "commands"
        cmd_dir.mkdir()
        git_dir = cmd_dir / "git"
        git_dir.mkdir()

        (cmd_dir / "flat.md").write_text("---\nname: flat\ndescription: Flat command\n---\nContent")
        (git_dir / "commit.md").write_text("---\nname: git/commit\ndescription: Git commit\n---\nContent")

        config = load_config()
        config.paths.commands_dir = str(cmd_dir)
        runtime = Runtime(config, skip_api_init=True)

        from simple_agent.resources.commands import CommandLoader
        runtime._command_loader = CommandLoader(cmd_dir)

        help_output = runtime._cmd_help()

        assert "/flat" in help_output
        assert "/git/commit" in help_output
```

- [ ] **Step 2: Run test to verify it passes**

```bash
pytest tests/test_runtime_commands_integration.py::test_help_command_shows_namespaces -v
```
Expected: PASS (help already uses command name from loader)

- [ ] **Step 3: Commit**

```bash
git add tests/test_runtime_commands_integration.py
git commit -m "test: 添加 help 命令命名空间测试

验证 help 命令正确显示命名空间命令。
"
```

---

### Task 11: Update existing command examples

**Files:**
- Modify: `plugin/commands/*.md`

- [ ] **Step 1: Update version.md**

```markdown
# plugin/commands/version.md
---
name: version
description: Show the current version of simple-agent
---

# Version

Simple Agent CLI - Version 0.1.0

A Claude Code-like CLI tool with support for hooks, skills, agents, and commands.
```

- [ ] **Step 2: Update status.md**

```markdown
# plugin/commands/status.md
---
name: status
description: Show current session status
---

# Session Status

- **Session ID**: {session_id}
- **Message Count**: {message_count}
- **API Provider**: {api_provider}
- **Model**: {model}
- **Base URL**: {base_url}

## Paths

- **Skills**: {skills_dirs}
- **Agents**: {agents_dir}
- **Hooks**: {hooks_dir}
- **Commands**: {commands_dir}

## UI

- **Theme**: {theme}
- **Show Thinking**: {show_thinking}

## Logging

- **Enabled**: {logging_enabled}
- **Log Dir**: {log_dir}
```

- [ ] **Step 3: Add example command with new features**

```markdown
# plugin/commands/git-status.md
---
name: git/status
description: Show git status with context
allowed-tools: Bash(git *)
---

## Git Status

!`git status`

## Modified Files

!`git diff --name-only`

Please review the changes and suggest next actions.
```

- [ ] **Step 4: Commit**

```bash
git add plugin/commands/
git commit -m "docs: 更新命令示例文件

移除 usage 字段，更新版本和状态命令，添加 git/status 示例。
"
```

---

### Task 12: Update documentation

**Files:**
- Modify: `docs/commands.md`

- [ ] **Step 1: Update commands documentation**

```markdown
# Commands Documentation

## Command Format

Each command is a `.md` file with frontmatter:

```markdown
---
name: command-name
description: A brief description of what the command does
allowed-tools: Bash, Read, Grep
---

Command content goes here...
```

## Command Syntax

### Parameters

- `$1` - First parameter (all args joined as one string)
- `$args` - All parameters
- `$#` - 1 if has parameters, 0 otherwise

Example:
```markdown
---
description: Create git commit
---

Create commit with message: $1
```

Usage: `/commit Fix the login bug`

### Bash Execution

- ``!`command` `` - Execute bash and replace with output

Example:
```markdown
---
description: Show git status
---

Current status: !`git status`
```

### File Inclusion

- `@filename` - Include file content (relative to project root)

Example:
```markdown
---
description: Review configuration
---

Config content: @config.yml
```

### Template Variables

- `{api_provider}`, `{model}`, `{base_url}`
- `{skills_dirs}`, `{agents_dir}`, `{hooks_dir}`, `{commands_dir}`
- `{theme}`, `{show_thinking}`
- `{logging_enabled}`, `{log_dir}`

## Namespace Organization

Commands can be organized in subdirectories:

```
plugin/commands/
├── git/
│   ├── commit.md      # Creates /git/commit
│   └── status.md      # Creates /git/status
└── help.md            # Creates /help
```

## Available Commands

- `/help` - Show help message
- `/exit` - Exit the agent
- `/clear` - Clear conversation history
- `/reset` - Reset session (clear history and unload skills/agents)
- `/status` - Show current session status
- `/version` - Show version information
- `/config` - Show or modify configuration
- `/skills` - List available and loaded skills
- `/agents` - List available and loaded agents
```

- [ ] **Step 2: Update README**

```markdown
# Simple Agent

A Claude Code-like CLI tool with support for hooks, skills, subagents, and slash commands.

## Features

- **Built-in Tools**: File operations (READ, WRITE), shell execution (BASH), pattern search (GREP), web search (WebSearch)
- **Custom Tools**: Register Python functions as tools for LLM function calling
- **Skills**: Markdown-based knowledge documents that guide AI behavior
- **Subagents**: Specialized AI agents for specific tasks
- **Hooks**: Event-driven plugins for custom behavior
- **Commands**: Built-in and custom slash commands with parameter replacement, bash execution, and file inclusion
- **Multi-Provider**: Support for OpenAI and Anthropic/Claude APIs
- **Request Logging**: Track LLM requests and responses for analysis
```

- [ ] **Step 3: Commit**

```bash
git add docs/commands.md README.md
git commit -m "docs: 更新命令文档和 README

添加新功能说明：参数替换、bash 执行、文件引用、命名空间。
"
```

---

### Task 13: Final integration test

**Files:**
- Modify: `tests/test_runtime_commands_integration.py`

- [ ] **Step 1: Write comprehensive integration test**

```python
# tests/test_runtime_commands_integration.py
def test_full_command_with_all_features():
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Create test file for inclusion
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Test content")

            # Create command with all features
            cmd_dir = Path(tmpdir) / "commands"
            cmd_dir.mkdir()
            cmd_file = cmd_dir / "full.md"
            cmd_file.write_text("""---
name: full
description: Full feature test
allowed-tools: Read
---

Parameters: $1
Args count: $#

File content: @test.txt

Bash output: !`echo hello`

Config: {model}
""")

            config = load_config()
            config.paths.commands_dir = str(cmd_dir)
            runtime = Runtime(config, skip_api_init=True)

            from simple_agent.resources.commands import CommandLoader
            runtime._command_loader = CommandLoader(cmd_dir)

            # Process command
            result = runtime._handle_slash_command("full", ["test arg"])

            assert result == "command_processed"

            # Check session
            messages = runtime._session.get_messages()
            system_msgs = [m for m in messages if m.get("role") == "system"]
            content = system_msgs[-1].get("content", "")

            assert "Parameters: test arg" in content
            assert "Args count: 1" in content
            assert "Test content" in content
            assert "hello" in content
            assert config.model in content

            # Check tool restriction
            tools = runtime._tool_registry._tools
            # Should have read, filter only keeps allowed tools
            assert any(t.name == "Read" for t in tools.values())
        finally:
            os.chdir(old_cwd)
```

- [ ] **Step 2: Run all tests**

```bash
pytest tests/ -v -k "command"
```
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_runtime_commands_integration.py
git commit -m "test: 添加完整功能集成测试

验证命令的所有功能：参数、bash、文件、模板变量、工具限制。
"
```

---

## Self-Review

**Spec Coverage Check:**
- [x] 参数支持 ($1, $args) - Task 4
- [x] Bash 命令执行 (!`command`) - Task 5
- [x] 文件引用 (@filename) - Task 6
- [x] Allowed Tools - Task 9, 13
- [x] 命名空间组织 - Task 8
- [x] Template variables - Task 7
- [x] Runtime 集成 - Task 9
- [x] 测试 - Multiple tasks
- [x] 文档 - Task 12

**Placeholder Scan:** None found.

**Type Consistency Check:**
- `CommandProcessor.process()` returns `ProcessedCommand` - consistent across tasks
- ToolRegistry methods use correct parameter types - consistent
- File paths use `Path` - consistent

**All requirements covered.**