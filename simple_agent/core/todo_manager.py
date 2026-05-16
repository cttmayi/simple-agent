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