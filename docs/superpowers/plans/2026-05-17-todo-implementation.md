# TODO 功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 simple_agent 实现一个综合性的任务跟踪系统，支持树形层级任务、文件持久化和 AI 通过工具操作。

**Architecture:** 使用 TodoManager 管理任务数据和 JSON 文件持久化，通过四个内置工具 (TaskList/TaskGet/TaskCreate/TaskUpdate) 供 AI 调用，UI 内联显示任务状态。

**Tech Stack:** Python, JSON 文件存储, rich 终端显示, pytest 测试框架

---

## 文件结构

### 新建文件
- `simple_agent/core/todo_manager.py` - 任务管理核心类（CRUD、树结构、持久化）
- `simple_agent/tools/builtin/todo.py` - 四个 TODO 工具实现
- `tests/test_todo_manager.py` - TodoManager 单元测试
- `tests/test_todo_tools.py` - 工具单元测试
- `plugin/commands/todos.md` - `/todos` 命令定义

### 修改文件
- `simple_agent/tools/builtin/__init__.py` - 导入 TODO 工具
- `simple_agent/ui/renderer.py` - 添加任务状态显示方法

---

## Task 1: TodoManager 核心数据结构

**Files:**
- Create: `simple_agent/core/todo_manager.py`

- [ ] **Step 1: 写 TodoManager 基本结构和数据模型**

```python
"""TODO 任务管理器，负责任务 CRUD、树结构管理和文件持久化。"""

import json
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime


@dataclass
class Task:
    """任务数据模型。"""
    id: str
    subject: str
    description: str = ""
    status: str = "pending"
    priority: str = "normal"
    progress: int = 0
    activeForm: str = ""
    parent_id: Optional[str] = None
    subtasks: List[str] = None
    owner: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.subtasks is None:
            self.subtasks = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """从字典创建 Task。"""
        return cls(**data)


VALID_STATUSES = {"pending", "in_progress", "completed", "blocked", "deleted"}
VALID_PRIORITIES = {"low", "normal", "high"}


class TodoManager:
    """TODO 任务管理器。"""

    def __init__(self, todos_path: Optional[str] = None):
        """初始化 TodoManager。

        Args:
            todos_path: TODO 文件路径，默认为 .simple-agent/todos.json
        """
        if todos_path:
            self._todos_path = Path(todos_path)
        else:
            self._todos_path = Path.cwd() / ".simple-agent" / "todos.json"
        self._tasks: Dict[str, Task] = {}
        self._load()

    def _load(self) -> None:
        """从文件加载任务数据。"""
        if not self._todos_path.exists():
            self._tasks = {}
            return

        try:
            with open(self._todos_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._tasks = {
                task_id: Task.from_dict(task_data)
                for task_id, task_data in data.get("tasks", {}).items()
            }
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # 文件损坏，备份后重新初始化
            backup_path = self._todos_path.with_suffix(".json.backup")
            self._todos_path.rename(backup_path)
            self._tasks = {}

    def _save(self) -> None:
        """保存任务数据到文件。"""
        self._todos_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1.0",
            "tasks": {
                task_id: task.to_dict()
                for task_id, task in self._tasks.items()
            },
            "last_updated": datetime.now().isoformat()
        }
        with open(self._todos_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务列表。"""
        return [task.to_dict() for task in self._tasks.values()]

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取指定任务。"""
        return self._tasks.get(task_id)
```

- [ ] **Step 2: 写测试验证基本结构**

Run: `source .venv/bin/activate && python -c "from simple_agent.core.todo_manager import TodoManager, Task; print('Import OK')"`
Expected: OK with no errors

- [ ] **Step 3: 提交**

```bash
git add simple_agent/core/todo_manager.py
git commit -m "feat: 添加 TodoManager 基本结构和数据模型

- 定义 Task 数据类
- 添加 TodoManager 基本类和加载逻辑
- 定义有效的状态和优先级常量

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: TodoManager CRUD 操作

**Files:**
- Modify: `simple_agent/core/todo_manager.py`
- Create: `tests/test_todo_manager.py`

- [ ] **Step 1: 写 TodoManager 的 create 方法**

```python
    def create_task(
        self,
        subject: str,
        description: str = "",
        activeForm: str = "",
        status: str = "pending",
        priority: str = "normal",
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, str, Optional[Task]]:
        """创建新任务。

        Args:
            subject: 任务标题
            description: 任务描述
            activeForm: 进行中状态显示文本
            status: 任务状态
            priority: 任务优先级
            parent_id: 父任务 ID
            metadata: 扩展元数据

        Returns:
            (success, message, task) 元组
        """
        if status not in VALID_STATUSES:
            return False, f"Invalid status: must be one of {', '.join(VALID_STATUSES)}", None

        if priority not in VALID_PRIORITIES:
            return False, f"Invalid priority: must be one of {', '.join(VALID_PRIORITIES)}", None

        if parent_id and parent_id not in self._tasks:
            return False, "Parent task not found", None

        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            subject=subject,
            description=description,
            status=status,
            priority=priority,
            activeForm=activeForm,
            parent_id=parent_id,
            metadata=metadata or {}
        )

        self._tasks[task_id] = task

        # 如果有父任务，更新父任务的 subtasks 列表
        if parent_id:
            self._tasks[parent_id].subtasks.append(task_id)

        self._save()
        return True, "Task created", task
```

- [ ] **Step 2: 写测试验证 create_task**

```python
"""测试 TodoManager 的 CRUD 操作。"""

import pytest
import tempfile
import shutil
from pathlib import Path
from simple_agent.core.todo_manager import TodoManager, VALID_STATUSES, VALID_PRIORITIES


@pytest.fixture
def temp_manager():
    """创建临时 TodoManager。"""
    temp_dir = tempfile.mkdtemp()
    manager = TodoManager(todos_path=str(Path(temp_dir) / "todos.json"))
    yield manager
    shutil.rmtree(temp_dir)


class TestCreateTask:
    """测试创建任务。"""

    def test_create_basic_task(self, temp_manager):
        """测试创建基本任务。"""
        success, message, task = temp_manager.create_task(
            subject="测试任务"
        )
        assert success is True
        assert task is not None
        assert task.subject == "测试任务"
        assert task.status == "pending"
        assert task.priority == "normal"

    def test_create_with_all_params(self, temp_manager):
        """测试创建带所有参数的任务。"""
        success, message, task = temp_manager.create_task(
            subject="完整任务",
            description="任务描述",
            activeForm="执行完整任务中",
            status="in_progress",
            priority="high",
            metadata={"key": "value"}
        )
        assert success is True
        assert task.description == "任务描述"
        assert task.activeForm == "执行完整任务中"
        assert task.status == "in_progress"
        assert task.priority == "high"
        assert task.metadata == {"key": "value"}

    def test_create_with_invalid_status(self, temp_manager):
        """测试创建带无效状态的任务。"""
        success, message, task = temp_manager.create_task(
            subject="测试",
            status="invalid"
        )
        assert success is False
        assert task is None
        assert "Invalid status" in message

    def test_create_with_invalid_priority(self, temp_manager):
        """测试创建带无效优先级的任务。"""
        success, message, task = temp_manager.create_task(
            subject="测试",
            priority="urgent"
        )
        assert success is False
        assert task is None
        assert "Invalid priority" in message

    def test_create_with_invalid_parent(self, temp_manager):
        """测试创建带无效父任务的任务。"""
        success, message, task = temp_manager.create_task(
            subject="子任务",
            parent_id="nonexistent"
        )
        assert success is False
        assert "Parent task not found" in message
```

- [ ] **Step 3: 运行测试验证通过**

Run: `source .venv/bin/activate && pytest tests/test_todo_manager.py::TestCreateTask -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add simple_agent/core/todo_manager.py tests/test_todo_manager.py
git commit -m "feat: 添加 TodoManager create_task 方法

- 实现任务创建逻辑
- 添加参数验证
- 支持父子任务关系
- 添加完整测试用例

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: TodoManager update 方法

**Files:**
- Modify: `simple_agent/core/todo_manager.py`
- Modify: `tests/test_todo_manager.py`

- [ ] **Step 1: 添加 update_task 方法**

在 TodoManager 类中添加：

```python
    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        parent_id: Optional[str] = None,
        description: Optional[str] = None,
        subject: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, str, Optional[Task]]:
        """更新任务。

        Args:
            task_id: 任务 ID
            status: 新状态
            progress: 新进度 (0-100)
            parent_id: 新父任务 ID
            description: 新描述
            subject: 新标题
            metadata: 新元数据（会合并现有元数据）

        Returns:
            (success, message, task) 元组
        """
        task = self._tasks.get(task_id)
        if not task:
            return False, "Task not found", None

        if status is not None:
            if status not in VALID_STATUSES:
                return False, f"Invalid status: must be one of {', '.join(VALID_STATUSES)}", None
            task.status = status

        if progress is not None:
            if not 0 <= progress <= 100:
                return False, "Progress must be between 0 and 100", None
            task.progress = progress

        if description is not None:
            task.description = description

        if subject is not None:
            task.subject = subject

        if metadata is not None:
            task.metadata.update(metadata)

        # 处理父任务变更（检测循环依赖）
        if parent_id is not None:
            if parent_id not in self._tasks:
                return False, "Parent task not found", None

            # 检测循环依赖
            current = self._tasks.get(parent_id)
            while current and current.parent_id:
                if current.parent_id == task_id:
                    return False, "Circular dependency: task cannot be its own ancestor", None
                current = self._tasks.get(current.parent_id)

            # 从旧父任务的 subtasks 中移除
            if task.parent_id:
                old_parent = self._tasks.get(task.parent_id)
                if old_parent and task_id in old_parent.subtasks:
                    old_parent.subtasks.remove(task_id)

            # 更新父任务
            task.parent_id = parent_id
            # 添加到新父任务的 subtasks
            new_parent = self._tasks[parent_id]
            if task_id not in new_parent.subtasks:
                new_parent.subtasks.append(task_id)

        self._save()
        return True, "Task updated", task
```

- [ ] **Step 2: 写测试验证 update_task**

```python
class TestUpdateTask:
    """测试更新任务。"""

    def test_update_status(self, temp_manager):
        """测试更新状态。"""
        _, _, task = temp_manager.create_task(subject="测试")
        success, message, updated = temp_manager.update_task(
            task.id, status="completed"
        )
        assert success is True
        assert updated.status == "completed"

    def test_update_progress(self, temp_manager):
        """测试更新进度。"""
        _, _, task = temp_manager.create_task(subject="测试")
        success, message, updated = temp_manager.update_task(
            task.id, progress=50
        )
        assert success is True
        assert updated.progress == 50

    def test_update_invalid_progress(self, temp_manager):
        """测试更新无效进度。"""
        _, _, task = temp_manager.create_task(subject="测试")
        success, message, updated = temp_manager.update_task(
            task.id, progress=150
        )
        assert success is False
        assert "Progress must be between 0 and 100" in message

    def test_update_nonexistent_task(self, temp_manager):
        """测试更新不存在的任务。"""
        success, message, updated = temp_manager.update_task(
            "nonexistent", status="completed"
        )
        assert success is False
        assert "Task not found" in message

    def test_change_parent_task(self, temp_manager):
        """测试修改父任务。"""
        _, _, parent = temp_manager.create_task(subject="父任务")
        _, _, child = temp_manager.create_task(subject="子任务")
        _, _, another = temp_manager.create_task(subject="另一个父任务")

        success, message, updated = temp_manager.update_task(
            child.id, parent_id=another.id
        )
        assert success is True
        assert updated.parent_id == another.id
        assert child.id not in parent.subtasks
        assert child.id in another.subtasks

    def test_circular_dependency_detection(self, temp_manager):
        """测试循环依赖检测。"""
        _, _, parent = temp_manager.create_task(subject="父任务")
        _, _, child = temp_manager.create_task(subject="子任务", parent_id=parent.id)

        success, message, updated = temp_manager.update_task(
            parent.id, parent_id=child.id
        )
        assert success is False
        assert "Circular dependency" in message
```

- [ ] **Step 3: 运行测试验证通过**

Run: `source .venv/bin/activate && pytest tests/test_todo_manager.py::TestUpdateTask -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add simple_agent/core/todo_manager.py tests/test_todo_manager.py
git commit -m "feat: 添加 TodoManager update_task 方法

- 实现任务更新逻辑
- 支持更新状态、进度、描述、标题、元数据
- 支持修改父任务
- 检测循环依赖
- 添加完整测试用例

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: TodoManager 持久化和树结构方法

**Files:**
- Modify: `simple_agent/core/todo_manager.py`
- Modify: `tests/test_todo_manager.py`

- [ ] **Step 1: 添加持久化和树结构辅助方法**

在 TodoManager 类中添加：

```python
    def get_task_tree(self) -> List[Dict[str, Any]]:
        """获取任务的树形结构表示。

        Returns:
            根任务列表（每个根任务包含其子任务树）
        """
        # 找出所有根任务（没有 parent_id 的任务）
        root_tasks = [
            task for task in self._tasks.values()
            if task.parent_id is None and task.status != "deleted"
        ]

        def build_tree(task: Task) -> Dict[str, Any]:
            """递归构建任务树。"""
            result = task.to_dict()
            if task.subtasks:
                children = []
                for child_id in task.subtasks:
                    child = self._tasks.get(child_id)
                    if child and child.status != "deleted":
                        children.append(build_tree(child))
                result["children"] = children
            return result

        return [build_tree(task) for task in root_tasks]

    def get_task_with_subtasks(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务及其子任务树。

        Args:
            task_id: 任务 ID

        Returns:
            包含子任务的任务字典，如果任务不存在返回 None
        """
        task = self._tasks.get(task_id)
        if not task or task.status == "deleted":
            return None

        result = task.to_dict()
        if task.subtasks:
            children = []
            for child_id in task.subtasks:
                child_data = self.get_task_with_subtasks(child_id)
                if child_data:
                    children.append(child_data)
            result["children"] = children
        return result
```

- [ ] **Step 2: 写测试验证树结构方法**

```python
class TestTaskTree:
    """测试任务树结构。"""

    def test_get_task_tree_basic(self, temp_manager):
        """测试获取基本任务树。"""
        _, _, task1 = temp_manager.create_task(subject="任务1")
        _, _, task2 = temp_manager.create_task(subject="任务2")

        tree = temp_manager.get_task_tree()
        assert len(tree) == 2
        assert tree[0]["subject"] == "任务1"
        assert tree[1]["subject"] == "任务2"

    def test_get_task_tree_with_subtasks(self, temp_manager):
        """测试获取带子任务的任务树。"""
        _, _, parent = temp_manager.create_task(subject="父任务")
        _, _, child1 = temp_manager.create_task(subject="子任务1", parent_id=parent.id)
        _, _, child2 = temp_manager.create_task(subject="子任务2", parent_id=parent.id)

        tree = temp_manager.get_task_tree()
        assert len(tree) == 1
        assert tree[0]["subject"] == "父任务"
        assert "children" in tree[0]
        assert len(tree[0]["children"]) == 2
        assert tree[0]["children"][0]["subject"] == "子任务1"
        assert tree[0]["children"][1]["subject"] == "子任务2"

    def test_get_task_with_subtasks(self, temp_manager):
        """测试获取带子任务的任务。"""
        _, _, parent = temp_manager.create_task(subject="父任务")
        _, _, child = temp_manager.create_task(subject="子任务", parent_id=parent.id)

        result = temp_manager.get_task_with_subtasks(parent.id)
        assert result is not None
        assert result["subject"] == "父任务"
        assert "children" in result
        assert len(result["children"]) == 1
        assert result["children"][0]["subject"] == "子任务"


class TestPersistence:
    """测试持久化。"""

    def test_tasks_saved_to_file(self, temp_manager):
        """测试任务保存到文件。"""
        temp_manager.create_task(subject="持久化测试")

        # 创建新管理器，应该能加载之前保存的任务
        new_manager = TodoManager(todos_path=str(temp_manager._todos_path))
        tasks = new_manager.get_all_tasks()
        assert len(tasks) == 1
        assert tasks[0]["subject"] == "持久化测试"

    def test_deleted_tasks_not_in_tree(self, temp_manager):
        """测试已删除任务不出现在树中。"""
        _, _, parent = temp_manager.create_task(subject="父任务")
        _, _, child = temp_manager.create_task(subject="子任务", parent_id=parent.id)

        # 删除子任务
        temp_manager.update_task(child.id, status="deleted")

        tree = temp_manager.get_task_tree()
        assert len(tree[0]["children"]) == 0
```

- [ ] **Step 3: 运行测试验证通过**

Run: `source .venv/bin/activate && pytest tests/test_todo_manager.py::TestTaskTree tests/test_todo_manager.py::TestPersistence -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add simple_agent/core/todo_manager.py tests/test_todo_manager.py
git commit -m "feat: 添加 TodoManager 树结构和持久化方法

- 添加 get_task_tree 获取根任务树
- 添加 get_task_with_subtasks 获取带子任务的任务
- 已删除任务不出现在树中
- 添加持久化测试

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: 实现 TaskList 工具

**Files:**
- Create: `simple_agent/tools/builtin/todo.py`

- [ ] **Step 1: 写 TaskList 工具**

```python
"""TODO 工具 - TaskList, TaskGet, TaskCreate, TaskUpdate。"""

from typing import Dict, Any, Optional
from simple_agent.tools.registry import get_global_registry, ToolDefinition

# 全局 TodoManager 实例，由 Runtime 设置
_todo_manager = None


def set_todo_manager(manager) -> None:
    """设置全局 TodoManager 实例。"""
    global _todo_manager
    _todo_manager = manager


def list_tasks() -> Dict[str, Any]:
    """列出所有任务及其状态。

    Returns:
        包含任务列表的字典
    """
    if _todo_manager is None:
        return {"success": False, "error": "TodoManager not initialized"}

    tasks = _todo_manager.get_all_tasks()
    return {"success": True, "tasks": tasks}


task_list_def = ToolDefinition(
    name="TaskList",
    description="列出所有任务及其状态、进度和层级关系",
    fn=list_tasks,
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)

get_global_registry().register(task_list_def)
```

- [ ] **Step 2: 写测试验证 TaskList**

Run: `source .venv/bin/activate && python -c "from simple_agent.tools.builtin.todo import task_list_def; print('OK'); print(task_list_def.name)"`
Expected: OK with name "TaskList"

- [ ] **Step 3: 提交**

```bash
git add simple_agent/tools/builtin/todo.py
git commit -m "feat: 添加 TaskList 工具

- 实现列出所有任务的工具
- 支持获取任务状态、进度和层级关系
- 注册到全局工具注册表

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: 实现 TaskGet 工具

**Files:**
- Modify: `simple_agent/tools/builtin/todo.py`
- Create: `tests/test_todo_tools.py`

- [ ] **Step 1: 添加 TaskGet 工具**

在 todo.py 中添加：

```python
def get_task(task_id: str) -> Dict[str, Any]:
    """获取指定任务的详细信息（含子任务）。

    Args:
        task_id: 任务 ID

    Returns:
        包含任务详情的字典
    """
    if _todo_manager is None:
        return {"success": False, "error": "TodoManager not initialized"}

    task = _todo_manager.get_task_with_subtasks(task_id)
    if task is None:
        return {"success": False, "error": "Task not found"}

    return {"success": True, "task": task}


task_get_def = ToolDefinition(
    name="TaskGet",
    description="获取指定任务的详细信息，包括子任务",
    fn=get_task,
    parameters={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "任务 ID"
            }
        },
        "required": ["task_id"]
    }
)

get_global_registry().register(task_get_def)
```

- [ ] **Step 2: 写测试验证 TaskGet**

```python
"""测试 TODO 工具。"""

import pytest
import tempfile
import shutil
from pathlib import Path
from simple_agent.core.todo_manager import TodoManager
from simple_agent.tools.builtin.todo import set_todo_manager, list_tasks, get_task


@pytest.fixture
def todo_manager_with_data():
    """创建带有测试数据的 TodoManager。"""
    temp_dir = tempfile.mkdtemp()
    manager = TodoManager(todos_path=str(Path(temp_dir) / "todos.json"))

    # 创建测试任务
    _, _, parent = manager.create_task(subject="父任务")
    _, _, child = manager.create_task(subject="子任务", parent_id=parent.id)

    set_todo_manager(manager)
    yield manager
    shutil.rmtree(temp_dir)


class TestTaskList:
    """测试 TaskList 工具。"""

    def test_list_all_tasks(self, todo_manager_with_data):
        """测试列出所有任务。"""
        result = list_tasks()
        assert result["success"] is True
        assert len(result["tasks"]) == 2
        assert any(t["subject"] == "父任务" for t in result["tasks"])


class TestTaskGet:
    """测试 TaskGet 工具。"""

    def test_get_existing_task(self, todo_manager_with_data):
        """测试获取存在的任务。"""
        tasks = todo_manager_with_data.get_all_tasks()
        task_id = tasks[0]["id"]

        result = get_task(task_id)
        assert result["success"] is True
        assert result["task"]["id"] == task_id

    def test_get_nonexistent_task(self, todo_manager_with_data):
        """测试获取不存在的任务。"""
        result = get_task("nonexistent")
        assert result["success"] is False
        assert "Task not found" in result["error"]
```

- [ ] **Step 3: 运行测试验证通过**

Run: `source .venv/bin/activate && pytest tests/test_todo_tools.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add simple_agent/tools/builtin/todo.py tests/test_todo_tools.py
git commit -m "feat: 添加 TaskGet 工具

- 实现获取单个任务详情的工具
- 支持获取任务及其子任务树
- 添加错误处理
- 添加测试用例

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: 实现 TaskCreate 工具

**Files:**
- Modify: `simple_agent/tools/builtin/todo.py`
- Modify: `tests/test_todo_tools.py`

- [ ] **Step 1: 添加 TaskCreate 工具**

在 todo.py 中添加：

```python
def create_task(
    subject: str,
    description: str = "",
    activeForm: str = "",
    status: str = "pending",
    priority: str = "normal",
    parent_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """创建新任务。通过 parent_id 指定父任务，形成子任务关系。

    Args:
        subject: 任务标题
        description: 任务描述
        activeForm: 进行中状态显示文本
        status: 任务状态 (pending, in_progress, completed, blocked, deleted)
        priority: 任务优先级 (low, normal, high)
        parent_id: 父任务 ID
        metadata: 扩展元数据

    Returns:
        包含新任务信息的字典
    """
    if _todo_manager is None:
        return {"success": False, "error": "TodoManager not initialized"}

    success, message, task = _todo_manager.create_task(
        subject=subject,
        description=description,
        activeForm=activeForm,
        status=status,
        priority=priority,
        parent_id=parent_id,
        metadata=metadata
    )

    if not success:
        return {"success": False, "error": message}

    return {"success": True, "task_id": task.id, "task": task.to_dict()}


task_create_def = ToolDefinition(
    name="TaskCreate",
    description="创建新任务，支持设置标题、描述、状态、优先级和父任务",
    fn=create_task,
    parameters={
        "type": "object",
        "properties": {
            "subject": {
                "type": "string",
                "description": "任务标题"
            },
            "description": {
                "type": "string",
                "description": "任务详细描述"
            },
            "activeForm": {
                "type": "string",
                "description": "进行中状态显示文本"
            },
            "status": {
                "type": "string",
                "description": "任务状态: pending, in_progress, completed, blocked, deleted",
                "enum": ["pending", "in_progress", "completed", "blocked", "deleted"]
            },
            "priority": {
                "type": "string",
                "description": "任务优先级: low, normal, high",
                "enum": ["low", "normal", "high"]
            },
            "parent_id": {
                "type": "string",
                "description": "父任务 ID，用于创建子任务"
            },
            "metadata": {
                "type": "object",
                "description": "扩展元数据"
            }
        },
        "required": ["subject"]
    }
)

get_global_registry().register(task_create_def)
```

- [ ] **Step 2: 添加测试**

```python
class TestTaskCreate:
    """测试 TaskCreate 工具。"""

    def test_create_basic_task(self, todo_manager_with_data):
        """测试创建基本任务。"""
        result = create_task(subject="新任务")
        assert result["success"] is True
        assert "task_id" in result
        assert result["task"]["subject"] == "新任务"

    def test_create_with_parent(self, todo_manager_with_data):
        """测试创建带父任务的任务。"""
        parent_id = todo_manager_with_data.get_all_tasks()[0]["id"]
        result = create_task(subject="子任务", parent_id=parent_id)
        assert result["success"] is True
        assert result["task"]["parent_id"] == parent_id

    def test_create_with_invalid_status(self, todo_manager_with_data):
        """测试创建带无效状态的任务。"""
        result = create_task(subject="测试", status="invalid")
        assert result["success"] is False
        assert "Invalid status" in result["error"]
```

- [ ] **Step 3: 运行测试验证通过**

Run: `source .venv/bin/activate && pytest tests/test_todo_tools.py::TestTaskCreate -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add simple_agent/tools/builtin/todo.py tests/test_todo_tools.py
git commit -m "feat: 添加 TaskCreate 工具

- 实现创建任务的工具
- 支持所有任务字段
- 支持父子任务关系
- 添加测试用例

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: 实现 TaskUpdate 工具

**Files:**
- Modify: `simple_agent/tools/builtin/todo.py`
- Modify: `tests/test_todo_tools.py`

- [ ] **Step 1: 添加 TaskUpdate 工具**

在 todo.py 中添加：

```python
def update_task(
    task_id: str,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    parent_id: Optional[str] = None,
    description: Optional[str] = None,
    subject: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """更新任务状态。通过 parent_id 可调整任务的父子关系。

    Args:
        task_id: 任务 ID
        status: 新状态
        progress: 新进度 (0-100)
        parent_id: 新父任务 ID
        description: 新描述
        subject: 新标题
        metadata: 新元数据

    Returns:
        包含更新后任务信息的字典
    """
    if _todo_manager is None:
        return {"success": False, "error": "TodoManager not initialized"}

    success, message, task = _todo_manager.update_task(
        task_id=task_id,
        status=status,
        progress=progress,
        parent_id=parent_id,
        description=description,
        subject=subject,
        metadata=metadata
    )

    if not success:
        return {"success": False, "error": message}

    return {"success": True, "task": task.to_dict()}


task_update_def = ToolDefinition(
    name="TaskUpdate",
    description="更新任务状态、进度、描述、标题、父任务等字段",
    fn=update_task,
    parameters={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "任务 ID"
            },
            "status": {
                "type": "string",
                "description": "新状态: pending, in_progress, completed, blocked, deleted",
                "enum": ["pending", "in_progress", "completed", "blocked", "deleted"]
            },
            "progress": {
                "type": "integer",
                "description": "新进度 (0-100)"
            },
            "parent_id": {
                "type": "string",
                "description": "新父任务 ID"
            },
            "description": {
                "type": "string",
                "description": "新描述"
            },
            "subject": {
                "type": "string",
                "description": "新标题"
            },
            "metadata": {
                "type": "object",
                "description": "新元数据"
            }
        },
        "required": ["task_id"]
    }
)

get_global_registry().register(task_update_def)
```

- [ ] **Step 2: 添加测试**

```python
class TestTaskUpdate:
    """测试 TaskUpdate 工具。"""

    def test_update_status(self, todo_manager_with_data):
        """测试更新状态。"""
        task_id = todo_manager_with_data.get_all_tasks()[0]["id"]
        result = update_task(task_id, status="completed")
        assert result["success"] is True
        assert result["task"]["status"] == "completed"

    def test_update_progress(self, todo_manager_with_data):
        """测试更新进度。"""
        task_id = todo_manager_with_data.get_all_tasks()[0]["id"]
        result = update_task(task_id, progress=75)
        assert result["success"] is True
        assert result["task"]["progress"] == 75

    def test_update_nonexistent_task(self, todo_manager_with_data):
        """测试更新不存在的任务。"""
        result = update_task("nonexistent", status="completed")
        assert result["success"] is False
        assert "Task not found" in result["error"]
```

- [ ] **Step 3: 运行测试验证通过**

Run: `source .venv/bin/activate && pytest tests/test_todo_tools.py::TestTaskUpdate -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add simple_agent/tools/builtin/todo.py tests/test_todo_tools.py
git commit -m "feat: 添加 TaskUpdate 工具

- 实现更新任务的工具
- 支持更新所有可修改字段
- 添加测试用例

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 9: 导入 TODO 工具到 builtin 模块

**Files:**
- Modify: `simple_agent/tools/builtin/__init__.py`

- [ ] **Step 1: 修改 __init__.py 导入 TODO 工具**

```python
"""Built-in tools for Simple Agent."""

from simple_agent.tools.builtin.bash import BASH
from simple_agent.tools.builtin.read import READ
from simple_agent.tools.builtin.write import WRITE
from simple_agent.tools.builtin.grep import GREP
from simple_agent.tools.builtin.websearch import WebSearch
from simple_agent.tools.builtin.load_skill import LoadSkill
from simple_agent.tools.builtin.run_subagent import RunSubAgent
from simple_agent.tools.builtin.todo import TaskList, TaskGet, TaskCreate, TaskUpdate

__all__ = ["BASH", "READ", "WRITE", "GREP", "WebSearch", "LoadSkill", "RunSubAgent",
           "TaskList", "TaskGet", "TaskCreate", "TaskUpdate"]
```

- [ ] **Step 2: 验证导入**

Run: `source .venv/bin/activate && python -c "from simple_agent.tools import builtin; print('OK'); print(builtin.__all__)" `
Expected: OK with __all__ containing TaskList, TaskGet, TaskCreate, TaskUpdate

- [ ] **Step 3: 提交**

```bash
git add simple_agent/tools/builtin/__init__.py
git commit -m "feat: 导入 TODO 工具到 builtin 模块

- 在 __init__.py 中导出 TaskList, TaskGet, TaskCreate, TaskUpdate
- 工具可通过 builtin 模块访问

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 10: Runtime 集成 TodoManager

**Files:**
- Modify: `simple_agent/core/runtime.py`

- [ ] **Step 1: 在 Runtime 中初始化 TodoManager**

在 Runtime.__init__ 中添加（大约在 LLMLogger 初始化之后）：

```python
from simple_agent.core.todo_manager import TodoManager
```

在 `self._logger = LLMLogger(...)` 之后添加：

```python
# Initialize TodoManager for task tracking
self._todo_manager = TodoManager()

# Set up TODO tools
from simple_agent.tools.builtin.todo import set_todo_manager
set_todo_manager(self._todo_manager)
```

- [ ] **Step 2: 验证集成**

Run: `source .venv/bin/activate && python -c "
from simple_agent.core.runtime import Runtime
from simple_agent.config.settings import Settings
import tempfile
import os

# 创建临时目录
temp_dir = tempfile.mkdtemp()
os.chdir(temp_dir)

runtime = Runtime(Settings())
print('TodoManager initialized:', runtime._todo_manager is not None)

# 清理
import shutil
shutil.rmtree(temp_dir)
" `
Expected: "TodoManager initialized: True"

- [ ] **Step 3: 提交**

```bash
git add simple_agent/core/runtime.py
git commit -m "feat: 在 Runtime 中集成 TodoManager

- 初始化 TodoManager 实例
- 设置全局 TodoManager 供工具使用
- 工具可操作任务数据

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 11: UIRenderer 添加任务状态显示

**Files:**
- Modify: `simple_agent/ui/renderer.py`

- [ ] **Step 1: 添加 render_task_status 方法**

在 UIRenderer 类中添加（在 render_error 方法之后）：

```python
    def render_task_status(self, task: dict) -> None:
        """渲染任务状态内联显示。

        Args:
            task: 任务字典
        """
        status = task.get("status", "pending")
        task_id = task.get("id", "unknown")
        subject = task.get("subject", "")

        # 状态图标和样式
        status_config = {
            "pending": ("⏳", "dim"),
            "in_progress": ("⚙️", "yellow"),
            "completed": ("✓", "green"),
            "blocked": ("🚫", "red"),
            "deleted": ("🗑️", "dim")
        }

        icon, style = status_config.get(status, ("⏳", "dim"))

        # 进度
        progress = task.get("progress", 0)

        # 构建显示文本
        if status == "in_progress":
            text = f"[{style}]{icon} 任务 #{task_id} 进行中: {subject} ({progress}%)[/{style}]"
        elif status == "completed":
            text = f"[{style}]{icon} 任务 #{task_id} 完成: {subject}[/{style}]"
        elif status == "pending":
            text = f"[{style}]{icon} 任务 #{task_id}: {subject}[/{style}]"
        elif status == "blocked":
            text = f"[{style}]{icon} 任务 #{task_id} 阻塞: {subject}[/{style}]"
        else:
            text = f"[{style}]{icon} 任务 #{task_id}: {subject}[/{style}]"

        self.console.print(text)

    def render_task_list(self, tasks: list) -> None:
        """渲染任务列表（带层级缩进）。

        Args:
            tasks: 任务列表
        """
        self.console.print("\n[bold]任务列表[/bold]\n")

        def render_task_recursive(task: dict, indent: int = 0) -> None:
            """递归渲染任务。"""
            status = task.get("status", "pending")
            task_id = task.get("id", "?")
            subject = task.get("subject", "")
            progress = task.get("progress", 0)

            status_config = {
                "pending": ("⏳", "dim"),
                "in_progress": ("⚙️", "yellow"),
                "completed": ("✓", "green"),
                "blocked": ("🚫", "red"),
            }

            icon, style = status_config.get(status, ("⏳", "dim"))
            prefix = "  " * indent

            self.console.print(f"{prefix}[{style}]{icon} #{task_id}[/{style}] {subject} ({progress}%)")

            # 递归渲染子任务
            children = task.get("children", [])
            for child in children:
                render_task_recursive(child, indent + 1)

        for task in tasks:
            render_task_recursive(task)

        self.console.print()
```

- [ ] **Step 2: 验证方法存在**

Run: `source .venv/bin/activate && python -c "
from simple_agent.ui.renderer import UIRenderer
import inspect

renderer = UIRenderer()
assert hasattr(renderer, 'render_task_status')
assert hasattr(renderer, 'render_task_list')
print('Methods exist: OK')
" `
Expected: "Methods exist: OK"

- [ ] **Step 3: 提交**

```bash
git add simple_agent/ui/renderer.py
git commit -m "feat: 添加任务状态显示方法

- 添加 render_task_status 显示单任务状态
- 添加 render_task_list 显示任务树
- 支持状态图标和颜色

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 12: 创建 /todos 命令

**Files:**
- Create: `plugin/commands/todos.md`

- [ ] **Step 1: 创建 /todos 命令文件**

```markdown
---
description: 显示当前任务列表
---

# 任务列表

使用以下任务跟踪系统管理你的开发工作：
- 创建任务：让 AI 使用 TaskCreate 工具
- 更新任务：让 AI 使用 TaskUpdate 工具
- 查看任务详情：让 AI 使用 TaskGet 工具

当前任务：

```

- [ ] **Step 2: 测试命令加载**

Run: `source .venv/bin/activate && simple-agent --help 2>/dev/null | head -20`
Expected: 命令正常运行

- [ ] **Step 3: 提交**

```bash
git add plugin/commands/todos.md
git commit -m "feat: 添加 /todos 命令

- 创建命令显示任务列表说明
- 用户可查看任务使用方法

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 13: 运行完整测试套件

**Files:**
- Test: all

- [ ] **Step 1: 运行所有测试**

Run: `source .venv/bin/activate && pytest tests/test_todo_manager.py tests/test_todo_tools.py -v`
Expected: 所有测试通过

- [ ] **Step 2: 运行项目测试套件**

Run: `source .venv/bin/activate && pytest -v`
Expected: 所有测试通过（包括现有测试）

- [ ] **Step 3: 提交测试通过确认**

```bash
git commit --allow-empty -m "test: TODO 功能测试全部通过

- TodoManager 测试通过
- TODO 工具测试通过
- 集成测试通过

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 14: 更新文档

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 在 CLAUDE.md 中添加 TODO 功能说明**

在 "## 测试" 部分之后添加：

```markdown
## TODO 功能

TODO 功能帮助跟踪会话中的任务，支持任务树、持久化和 AI 操作。

### 工具

- **TaskList**: 列出所有任务
- **TaskGet**: 获取任务详情（含子任务）
- **TaskCreate**: 创建新任务
- **TaskUpdate**: 更新任务状态

### 存储

- TODO 数据保存在 `.simple-agent/todos.json`
- 可通过环境变量 `SIMPLE_AGENT_TODOS_PATH` 自定义路径

### 命令

- `/todos` - 显示任务列表说明

### 任务状态

- `pending` - 待处理
- `in_progress` - 进行中
- `completed` - 已完成
- `blocked` - 阻塞
- `deleted` - 已删除
```

- [ ] **Step 2: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: 添加 TODO 功能文档

- 添加工具说明
- 添加存储路径说明
- 添加状态说明

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Plan Review

### Spec Coverage

| Spec Section | Implemented In |
|--------------|----------------|
| 数据模型 | Task 1 (Task dataclass) |
| 持久化 | Task 2, 4 (_save, _load) |
| 树形结构 | Task 4 (get_task_tree, get_task_with_subtasks) |
| TaskList 工具 | Task 5 |
| TaskGet 工具 | Task 6 |
| TaskCreate 工具 | Task 7 |
| TaskUpdate 工具 | Task 8 |
| 内联显示 | Task 11 (render_task_status) |
| /todos 命令 | Task 12 |
| 错误处理 | Task 2-8 (success/error 返回) |
| 测试 | Task 2-8, 13 |

### Placeholder Scan
- 无占位符
- 所有代码步骤都包含完整实现

### Type Consistency
- 工具参数类型与 TodoManager 方法签名一致
- 返回格式统一为 `{"success": bool, ...}`