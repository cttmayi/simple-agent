"""TODO 任务管理器，负责任务 CRUD、树结构管理和文件持久化。"""

import json
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
        self._next_id: int = 1
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
            # 计算 _next_id：取现有数字 ID 最大值 + 1
            if self._tasks:
                numeric_ids = []
                for tid in self._tasks:
                    try:
                        numeric_ids.append(int(tid))
                    except ValueError:
                        pass
                if numeric_ids:
                    self._next_id = max(numeric_ids) + 1
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

    def clear(self) -> None:
        """清空所有任务并保存。"""
        self._tasks = {}
        self._next_id = 1
        self._save()

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务列表。"""
        return [task.to_dict() for task in self._tasks.values()]

    def _resolve_task_id(self, task_id: str) -> Optional[str]:
        """解析任务 ID，支持完整 ID 或前缀匹配。

        Args:
            task_id: 完整或截断的任务 ID

        Returns:
            完整的任务 ID，未找到返回 None
        """
        # 精确匹配
        if task_id in self._tasks:
            return task_id
        # 前缀匹配
        matches = [tid for tid in self._tasks if tid.startswith(task_id)]
        if len(matches) == 1:
            return matches[0]
        return None

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取指定任务（支持完整 ID 或前缀匹配）。"""
        full_id = self._resolve_task_id(task_id)
        if full_id:
            return self._tasks[full_id]
        return None

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

        if parent_id:
            resolved_parent = self._resolve_task_id(parent_id)
            if not resolved_parent:
                return False, f"Parent task not found: {parent_id}", None
            parent_id = resolved_parent

        task_id = str(self._next_id)
        self._next_id += 1
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
        full_id = self._resolve_task_id(task_id)
        if not full_id:
            return False, f"Task not found: {task_id}", None
        task = self._tasks[full_id]

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
            resolved_parent = self._resolve_task_id(parent_id)
            if not resolved_parent:
                return False, f"Parent task not found: {parent_id}", None

            # 检测循环依赖
            current = self._tasks.get(resolved_parent)
            while current and current.parent_id:
                if current.parent_id == full_id:
                    return False, "Circular dependency: task cannot be its own ancestor", None
                current = self._tasks.get(current.parent_id)

            # 从旧父任务的 subtasks 中移除
            if task.parent_id:
                old_parent = self._tasks.get(task.parent_id)
                if old_parent and full_id in old_parent.subtasks:
                    old_parent.subtasks.remove(full_id)

            # 更新父任务
            task.parent_id = resolved_parent
            # 添加到新父任务的 subtasks
            new_parent = self._tasks[resolved_parent]
            if full_id not in new_parent.subtasks:
                new_parent.subtasks.append(full_id)
        else:
            # parent_id=None: 移除父任务
            if task.parent_id:
                old_parent = self._tasks.get(task.parent_id)
                if old_parent and full_id in old_parent.subtasks:
                    old_parent.subtasks.remove(full_id)
            task.parent_id = None

        self._save()
        return True, "Task updated", task

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
        task = self.get_task(task_id)
        if not task or task.status == "deleted":
            return None

        result = task.to_dict()
        children = []
        for child_id in task.subtasks:
            child_data = self.get_task_with_subtasks(child_id)
            if child_data:
                children.append(child_data)
        result["children"] = children
        return result