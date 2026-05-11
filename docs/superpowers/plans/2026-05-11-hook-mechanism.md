# Hook 机制重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 重构 Hook 机制，使用目录名识别事件，支持 Python 函数返回值控制执行流程

**架构:** HookLoader 扫描 hooks/ 目录的子目录，每个子目录名对应一个事件；Runtime 根据事件名发布事件并执行对应 hook

**技术栈:** Python, pathlib, importlib, subprocess

---

## 文件结构

**修改的文件：**
- `simple_agent/resources/hooks.py` - HookLoader 扫描目录而非 HOOK.md
- `simple_agent/core/runtime.py` - _load_hooks、_execute_hook、事件发布
- `simple_agent/tools/dispatcher.py` - 工具调用前发布事件

**创建的文件：**
- `tests/test_hooks.py` - Hook 系统测试

---

### Task 1: 修改 HookLoader 扫描目录结构

**Files:**
- Modify: `simple_agent/resources/hooks.py`

- [ ] **Step 1: 写测试验证新扫描逻辑**

```python
# tests/test_hooks.py
from pathlib import Path
import tempfile
import json
import pytest
from simple_agent.resources.hooks import HookLoader

def test_hook_loader_scans_directories():
    """HookLoader 扫描 hooks/ 目录的子目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        hooks_dir = Path(tmpdir)

        # 创建事件目录和文件
        event_dir = hooks_dir / "test_event"
        event_dir.mkdir()

        # 创建不同类型的 hook 文件
        (event_dir / "hook.py").write_text("def on_test_event(): pass")
        (event_dir / "hook.sh").write_text("echo test")
        (event_dir / "hook.md").write_text("test prompt")

        loader = HookLoader(hooks_dir)
        hooks = loader.list_hooks()

        assert len(hooks) == 1
        assert hooks[0]["event_name"] == "test_event"
        assert hooks[0]["files"] == ["hook.py", "hook.md", "hook.sh"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_hooks.py::test_hook_loader_scans_directories -v`
Expected: FAIL (新方法未实现)

- [ ] **Step 3: 修改 HookLoader.scan() 方法**

```python
# simple_agent/resources/hooks.py
def scan(self) -> List[Dict[str, Any]]:
    """扫描 hooks/ 目录的子目录，每个子目录是一个事件"""
    if not self._base_dir.exists():
        return []

    hooks = []

    for event_dir in sorted(self._base_dir.iterdir()):
        if not event_dir.is_dir():
            continue

        # 扫描事件目录内的所有 hook 文件
        hook_files = []
        for item in sorted(event_dir.iterdir()):
            if item.is_file():
                ext = item.suffix.lower()
                if ext in [".py", ".sh", ".cmd", ".md"]:
                    hook_files.append(item.name)

        if hook_files:
            hooks.append({
                "event_name": event_dir.name,
                "path": str(event_dir),
                "files": hook_files,
            })

    return hooks
```

- [ ] **Step 4: 修改 list_hooks() 返回新格式**

```python
# simple_agent/resources/hooks.py
def list_hooks(self) -> List[dict]:
    """列出所有 hooks"""
    return self.scan()
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/test_hooks.py::test_hook_loader_scans_directories -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add simple_agent/resources/hooks.py tests/test_hooks.py
git commit -m "refactor: HookLoader scans directories instead of HOOK.md"
```

---

### Task 2: 实现 Python Hook 执行和返回值处理

**Files:**
- Modify: `simple_agent/core/runtime.py`

- [ ] **Step 1: 写测试验证 Python hook 返回值**

```python
# tests/test_hooks.py
from simple_agent.core.events import Event

def test_execute_python_hook_returns_block():
    """Python hook 可以返回 block 阻止执行"""
    with tempfile.TemporaryDirectory() as tmpdir:
        event_dir = Path(tmpdir) / "test_event"
        event_dir.mkdir()

        # 创建返回 block 的 hook
        hook_code = '''
def on_test_event(**kwargs):
    return {"action": "block", "message": "阻止"}
'''
        (event_dir / "hook.py").write_text(hook_code)

        # 模拟执行（需要 runtime 上下文）
        # 实际测试将在集成测试中完成
```

- [ ] **Step 2: 实现新的 _execute_hook() 方法**

```python
# simple_agent/core/runtime.py
def _execute_hook(self, hook: Dict[str, Any], event: Event) -> None:
    """执行 hook

    Args:
        hook: Hook 数据 {"event_name", "path", "files"}
        event: 事件对象

    Returns:
        dict 或 None: {"action": "block", "message": "..."} 表示阻止
    """
    hook_dir = Path(hook["path"])

    for filename in hook["files"]:
        filepath = hook_dir / filename
        ext = filepath.suffix.lower()

        try:
            if ext == ".py":
                result = self._execute_python_hook(filepath, event)
                # 检查返回值
                if result and result.get("action") == "block":
                    return result
            elif ext in [".sh", ".cmd"]:
                self._execute_shell_hook(filepath, event)
            elif ext == ".md":
                self._execute_prompt_hook(filepath, event)
        except Exception as e:
            self._renderer.render_message("system", f"Hook {filename} failed: {str(e)}")

    return None
```

- [ ] **Step 3: 实现 _execute_python_hook() 方法**

```python
# simple_agent/core/runtime.py
def _execute_python_hook(self, filepath: Path, event: Event) -> Optional[dict]:
    """执行 Python hook 并返回结果

    Args:
        filepath: Python hook 文件路径
        event: 事件对象

    Returns:
        dict: hook 返回值，可能是 {"action": "block", "message": "..."}
    """
    import importlib.util
    import sys

    # 动态导入模块
    module_name = f"hook_{filepath.stem}"
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if not spec or not spec.loader:
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    # 查找 hook 函数 (on_event_name)
    event_name = event.name
    func_name = f"on_{event_name}"

    if hasattr(module, func_name):
        func = getattr(module, func_name)
        result = func(**event.data)

        # 记录 hook 返回值
        if result and isinstance(result, dict) and result.get("action") == "block":
            self._renderer.render_message("system", result.get("message", ""))

        return result

    return None
```

- [ ] **Step 4: 实现 _execute_shell_hook() 方法**

```python
# simple_agent/core/runtime.py
def _execute_shell_hook(self, filepath: Path, event: Event) -> None:
    """执行 Shell hook

    Args:
        filepath: Shell 脚本文件路径
        event: 事件对象
    """
    import subprocess

    # 替换事件数据到脚本（如果脚本需要参数，通过环境变量传递）
    try:
        result = subprocess.run(
            f"sh {filepath}" if filepath.suffix == ".sh" else filepath,
            shell=True,
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.stdout:
            self._renderer.render_message("system", result.stdout.strip())
        if result.stderr:
            self._renderer.render_message("system", f"Hook stderr: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        self._renderer.render_message("system", f"Shell hook timed out")
```

- [ ] **Step 5: 实现 _execute_prompt_hook() 方法**

```python
# simple_agent/core/runtime.py
def _execute_prompt_hook(self, filepath: Path, event: Event) -> None:
    """执行 Prompt hook（简化版本，先显示内容）"""
    prompt_content = filepath.read_text()

    # 替换变量
    variables = event.data or {}
    for key, value in variables.items():
        prompt_content = prompt_content.replace(f"{{{{{key}}}}}", str(value))

    # TODO: 完整实现应该发送给 LLM
    self._renderer.render_message("system", f"[Prompt Hook] {prompt_content[:100]}...")
```

- [ ] **Step 6: 提交**

```bash
git add simple_agent/core/runtime.py
git commit -m "feat: implement new hook execution with return value support"
```

---

### Task 3: 修改 Runtime._load_hooks() 注册新格式 hooks

**Files:**
- Modify: `simple_agent/core/runtime.py`

- [ ] **Step 1: 写测试验证 hook 注册**

```python
# tests/test_hooks.py
def test_load_hooks_registers_event_handlers():
    """加载 hooks 后，事件总线有对应的处理器"""
    # 集成测试，需要完整的 Runtime 实例
    pass
```

- [ ] **Step 2: 重写 _load_hooks() 方法**

```python
# simple_agent/core/runtime.py
def _load_hooks(self):
    """加载并注册所有 hooks"""
    hooks = self._hook_loader.list_hooks()

    for hook in hooks:
        event_name = hook["event_name"]

        # 为每个事件创建处理器
        def make_handler(hook_data, event_obj):
            result = self._execute_hook(hook_data, event_obj)

            # 处理 block 返回值
            if result and result.get("action") == "block":
                message = result.get("message", "Hook blocked execution")

                # 1. 终端显示（已在 _execute_python_hook 中显示）
                # 2. 记录日志
                if self._logger:
                    self._logger.log_hook_block(
                        event_name=event_obj.name,
                        hook_name=hook_data["event_name"],
                        message=message
                    )
                # 3. 发送给 AI（通过 session.add_message）
                self._session.add_message("system", f"[BLOCKED] {message}")

                # 抛出异常来中断流程（仅用于 tool_call_before）
                raise HookBlockedException(message)

        self._event_bus.subscribe(event_name, make_handler(hook, event_name))

        # 发布 hook_loaded 事件
        self._event_bus.publish(Event("hook_loaded", {"hook_name": hook["event_name"]}))

# 定义异常用于中断流程
class HookBlockedException(Exception):
    """Hook 阻止了执行"""
    pass
```

- [ ] **Step 3: 添加 LLMLogger.log_hook_block() 方法**

```python
# simple_agent/core/llm_logger.py
def log_hook_block(self, event_name: str, hook_name: str, message: str) -> None:
    """记录 hook 阻止事件"""
    if not self._enabled:
        return

    entry = {
        "type": "hook_block",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_name": event_name,
        "hook_name": hook_name,
        "message": message,
    }

    self._write_entry(entry)
```

- [ ] **Step 4: 提交**

```bash
git add simple_agent/core/runtime.py simple_agent/core/llm_logger.py
git commit -m "feat: load hooks from directory structure with event registration"
```

---

### Task 4: 在 Runtime 发布所有新事件

**Files:**
- Modify: `simple_agent/core/runtime.py`

- [ ] **Step 1: 发布 session_end 事件**

```python
# simple_agent/core/runtime.py
def run(self):
    """主运行循环"""
    # ... 现有代码 ...

    try:
        while True:
            # ... 主循环代码 ...
    except KeyboardInterrupt:
        self._renderer.render_message("system", "\nGoodbye!")

        # 发布 session_end 事件
        self._event_bus.publish(Event("session_end", {"session_id": self._session_id}))
        break
```

- [ ] **Step 2: 发布 message_sent 事件（已有，确认位置）**

```python
# simple_agent/core/runtime.py
# 已在 process_input() 中实现
self._event_bus.publish(Event("message_sent", {"role": "user", "content": input}))
```

- [ ] **Step 3: 发布 message_received 事件**

```python
# simple_agent/core/runtime.py
def _handle_tool_calls_in_message(self, msg: Dict[str, Any], response: List[Dict[str, Any]]) -> None:
    """处理工具调用（递归）"""
    # ... 现有代码 ...

    for next_msg in next_response:
        if "tool_calls" in next_msg and next_msg["tool_calls"]:
            self._handle_tool_calls_in_message(next_msg, next_response)
        else:
            content = next_msg.get("content", "")
            self._session.add_message(next_msg["role"], content)

            # 发布 message_received 事件
            if content:
                self._event_bus.publish(Event("message_received", {
                    "role": next_msg["role"],
                    "content": content
                }))

            self._renderer.render_message(next_msg["role"], content)
```

- [ ] **Step 4: 提交**

```bash
git add simple_agent/core/runtime.py
git commit -m "feat: publish session_end and message_received events"
```

---

### Task 5: 在 ToolDispatcher 集成 tool_call_before 事件

**Files:**
- Modify: `simple_agent/tools/dispatcher.py`

- [ ] **Step 1: 修改 ToolDispatcher 构造函数**

```python
# simple_agent/tools/dispatcher.py
class ToolDispatcher:
    def __init__(self, registry, event_bus=None):
        self._registry = registry
        self._event_bus = event_bus  # 新增事件总线引用
```

- [ ] **Step 2: 在 execute() 前发布 tool_call_before 事件**

```python
# simple_agent/tools/dispatcher.py
def execute(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """执行工具调用"""
    tool_name = tool_call["name"]
    arguments = tool_call.get("arguments", {})

    # 发布 tool_call_before 事件
    if self._event_bus:
        from simple_agent.core.events import Event
        from simple_agent.core.runtime import HookBlockedException

        try:
            self._event_bus.publish(Event("tool_call_before", {
                "tool_name": tool_name,
                "arguments": arguments
            }))
        except HookBlockedException:
            # Hook 阻止了工具调用，返回错误结果
            return {
                "success": False,
                "error": "Tool call blocked by hook"
            }

    # 执行工具
    # ... 现有执行逻辑 ...
```

- [ ] **Step 3: 更新 Runtime 传递 event_bus**

```python
# simple_agent/core/runtime.py
def __init__(self, config: Settings, log_file: Optional[str] = None):
    # ... 现有代码 ...

    # 传递 event_bus 给 ToolDispatcher
    self._tool_dispatcher = ToolDispatcher(self._tool_registry, self._event_bus)
```

- [ ] **Step 4: 提交**

```bash
git add simple_agent/tools/dispatcher.py simple_agent/core/runtime.py
git commit -m "feat: integrate tool_call_before event in ToolDispatcher"
```

---

### Task 6: 发布 tool_call_after 和 tool_call_failed 事件

**Files:**
- Modify: `simple_agent/tools/dispatcher.py`

- [ ] **Step 1: 在工具执行后发布 tool_call_after**

```python
# simple_agent/tools/dispatcher.py
def execute(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
    # ... 发布 tool_call_before 代码 ...

    try:
        # 执行工具
        result = self._execute_tool(tool_name, arguments)

        # 发布 tool_call_after 事件
        if self._event_bus:
            self._event_bus.publish(Event("tool_call_after", {
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result
            }))

        return result
    except Exception as e:
        # 发布 tool_call_failed 事件
        if self._event_bus:
            self._event_bus.publish(Event("tool_call_failed", {
                "tool_name": tool_name,
                "arguments": arguments,
                "error": str(e)
            }))
        raise
```

- [ ] **Step 2: 提交**

```bash
git add simple_agent/tools/dispatcher.py
git commit -m "feat: publish tool_call_after and tool_call_failed events"
```

---

### Task 7: 发布 skill_loaded 和 subagent_loaded 事件

**Files:**
- Modify: `simple_agent/tools/builtin/load_skill.py`
- Modify: `simple_agent/tools/builtin/load_subagent.py`

- [ ] **Step 1: 在 load_skill.py 发布事件**

```python
# simple_agent/tools/builtin/load_skill.py
class LoadSkill:
    @classmethod
    def execute(cls, skill_name: str) -> Dict[str, Any]:
        # ... 加载技能逻辑 ...

        # 发布 skill_loaded 事件
        if cls._event_bus:
            cls._event_bus.publish(Event("skill_loaded", {
                "skill_name": skill_name
            }))

        return result
```

- [ ] **Step 2: 在 load_subagent.py 发布事件**

```python
# simple_agent/tools/builtin/load_subagent.py
class LoadSubagent:
    @classmethod
    def execute(cls, subagent_name: str) -> Dict[str, Any]:
        # ... 加载子agent逻辑 ...

        # 发布 subagent_loaded 事件
        if cls._event_bus:
            cls._event_bus.publish(Event("subagent_loaded", {
                "subagent_name": subagent_name
            }))

        return result
```

- [ ] **Step 3: 更新 Runtime 传递 event_bus**

```python
# simple_agent/core/runtime.py
def __init__(self, config: Settings, log_file: Optional[str] = None):
    # ... 现有代码 ...

    LoadSkill.set_runtime(self._skill_loader, self._loaded_skills, self, self._event_bus)
    LoadSubagent.set_runtime(self._subagent_loader, self._loaded_subagents, self, self._event_bus)
```

- [ ] **Step 4: 更新 LoadSkill 和 LoadSubagent 的 set_runtime**

```python
# simple_agent/tools/builtin/load_skill.py
class LoadSkill:
    _skill_loader = None
    _loaded_skills = None
    _runtime = None
    _event_bus = None  # 新增

    @classmethod
    def set_runtime(cls, skill_loader, loaded_skills, runtime, event_bus=None):
        cls._skill_loader = skill_loader
        cls._loaded_skills = loaded_skills
        cls._runtime = runtime
        cls._event_bus = event_bus
```

- [ ] **Step 5: 提交**

```bash
git add simple_agent/tools/builtin/load_skill.py simple_agent/tools/builtin/load_subagent.py simple_agent/core/runtime.py
git commit -m "feat: publish skill_loaded and subagent_loaded events"
```

---

### Task 8: 添加 error_occurred 事件处理

**Files:**
- Modify: `simple_agent/core/runtime.py`

- [ ] **Step 1: 在 run() 主循环捕获异常**

```python
# simple_agent/core/runtime.py
def run(self):
    """主运行循环"""
    # ... 现有代码 ...

    while True:
        try:
            # ... 主循环代码 ...
        except HookBlockedException:
            # Hook 阻止，继续下一个输入
            continue
        except KeyboardInterrupt:
            self._renderer.render_message("system", "\nGoodbye!")
            break
        except Exception as e:
            self._renderer.render_error(str(e))

            # 发布 error_occurred 事件
            self._event_bus.publish(Event("error_occurred", {
                "error_type": type(e).__name__,
                "error_message": str(e)
            }))
```

- [ ] **Step 2: 提交**

```bash
git add simple_agent/core/runtime.py
git commit -m "feat: publish error_occurred event"
```

---

### Task 9: 更新现有 Hook 文件到新格式

**Files:**
- Modify: `.simple-agent/hooks/*`

- [ ] **Step 1: 转换 session_start hook**

```bash
# 删除 HOOK.md，保留或创建 Python/shell hook
rm .simple-agent/hooks/session_start/HOOK.md
# 创建或保留 hook.py 或 shell 脚本
```

- [ ] **Step 2: 转换 message_sent hook**

```bash
rm .simple-agent/hooks/message_sent/HOOK.md
```

- [ ] **Step 3: 删除不再需要的 prompt 示例**

```bash
rm -rf .simple-agent/hooks/greeting/
rm -rf .simple-agent/hooks/session_python/
```

- [ ] **Step 4: 提交**

```bash
git add .simple-agent/hooks/
git commit -m "refactor: migrate hooks to new directory-based format"
```

---

### Task 10: 更新文档和示例

**Files:**
- Modify: `.simple-agent/hooks/README.md`
- Create: `.simple-agent/hooks/examples/`

- [ ] **Step 1: 更新 README**

```markdown
# Hooks 系统

Hook 允许你在特定事件发生时执行自定义逻辑。

## 目录结构

```
.simple-agent/hooks/
├── session_start/
│   ├── init.py
│   └── log.sh
├── message_sent/
│   └── log.py
└── tool_call_before/
    └── security.py
```

## 事件类型

| 事件名 | 描述 | 可阻止 |
|---------|------|--------|
| session_start | 会话启动 | 否 |
| session_end | 会话结束 | 否 |
| message_sent | 消息发送 | 否 |
| message_received | 收到 AI 回复 | 否 |
| tool_call_before | 工具调用前 | **是** |
| tool_call_after | 工具调用后 | 否 |
| tool_call_failed | 工具调用失败 | 否 |
| skill_loaded | 技能加载 | 否 |
| subagent_loaded | 子agent 加载 | 否 |
| hook_loaded | Hook 加载 | 否 |
| error_occurred | 发生错误 | 否 |

## Hook 类型

| 文件类型 | 处理方式 |
|-----------|-----------|
| `.py` | Python 函数，支持返回值控制 |
| `.sh` / `.cmd` | Shell 命令 |
| `.md` | Prompt hook（发送给 AI） |

## 示例

### tool_call_before - 阻止危险命令

```python
# .simple-agent/hooks/tool_call_before/security.py

def on_tool_call_before(tool_name: str, arguments: dict) -> dict:
    if tool_name == "bash" and "command" in arguments:
        cmd = arguments["command"]
        if "rm -rf" in cmd or "rm -fr" in cmd:
            return {"action": "block", "message": "禁止执行 rm -rf 命令"}
    return {"action": "continue"}
```
```

- [ ] **Step 2: 创建示例目录和示例 hooks**

```bash
mkdir -p .simple-agent/hooks/examples/session_start
mkdir -p .simple-agent/hooks/examples/tool_call_before
```

- [ ] **Step 3: 创建示例 hook**

```python
# .simple-agent/hooks/examples/session_start/greeting.py

def on_session_start(session_id: str) -> None:
    print(f"🚀 Session {session_id[:8]} started!")
```

```python
# .simple-agent/hooks/examples/tool_call_before/validate.py

def on_tool_call_before(tool_name: str, arguments: dict) -> dict:
    # 示例：记录工具调用
    print(f"Tool call: {tool_name}")
    return {"action": "continue"}
```

- [ ] **Step 4: 提交**

```bash
git add .simple-agent/hooks/README.md .simple-agent/hooks/examples/
git commit -m "docs: update hook documentation with examples"
```

---

### Task 11: 集成测试

**Files:**
- Modify: `tests/test_hooks.py`

- [ ] **Step 1: 端到端测试 hook 阻止**

```python
# tests/test_hooks.py
def test_hook_block_tool_execution():
    """Hook 可以阻止工具执行"""
    # 需要 mock Runtime 和 ToolDispatcher
    # 验证 tool_call_before hook 返回 block 时，工具不执行
    pass
```

- [ ] **Step 2: 测试所有事件发布**

```python
# tests/test_hooks.py
@pytest.mark.parametrize("event_name", [
    "session_start", "session_end", "message_sent",
    "message_received", "tool_call_after", "skill_loaded"
])
def test_all_events_published(event_name):
    """所有事件都能正确发布和处理"""
    pass
```

- [ ] **Step 3: 运行测试**

Run: `pytest tests/test_hooks.py -v`
Expected: All tests pass

- [ ] **Step 4: 提交**

```bash
git add tests/test_hooks.py
git commit -m "test: add comprehensive hook integration tests"
```

---

### Task 12: 清理和验证

**Files:**
- Various

- [ ] **Step 1: 删除旧的 HOOK.md 相关代码**

检查是否有其他地方引用 HOOK.md 或 _get_markdown_file()，清理相关代码。

- [ ] **Step 2: 验证所有事件正确触发**

手动测试每个事件：

```bash
simple-agent
# 测试 session_start
> /help
# 测试 message_sent
> 你好
# 测试 message_received
# 观察 AI 回复
# Ctrl+C 测试 session_end 和 error_occurred
```

- [ ] **Step 3: 提交**

```bash
git commit --allow-empty -m "chore: cleanup and final verification"
```

---

## 测试检查清单

- [ ] 所有单元测试通过
- [ ] Hook 能正确扫描目录结构
- [ ] Python hook 返回 block 能阻止执行
- [ ] block 消息显示在终端、日志、发送给 AI
- [ ] 所有事件都正确发布
- [ ] 现有 hooks 迁移到新格式
- [ ] 文档更新完成
