"""TODO 工具 - TaskList, TaskGet, TaskCreate, TaskUpdate。"""

from typing import Dict, Any, Optional
from simple_agent.tools.registry import get_global_registry, ToolDefinition

# 全局 TodoManager 实例，由 Runtime 设置
_todo_manager = None


def set_todo_manager(manager) -> None:
    """设置全局 TodoManager 实例。"""
    global _todo_manager
    _todo_manager = manager


# Tool classes for direct import (matches the pattern used in bash.py)

class TaskList:
    """列出所有任务及其状态。"""
    name = "TaskList"
    description = "列出所有任务及其状态、进度和层级关系"


class TaskGet:
    """获取指定任务的详细信息。"""
    name = "TaskGet"
    description = "获取指定任务的详细信息，包括子任务"


class TaskCreate:
    """创建新任务。"""
    name = "TaskCreate"
    description = "创建新任务，支持设置标题、描述、状态、优先级和父任务"


class TaskUpdate:
    """更新任务状态。"""
    name = "TaskUpdate"
    description = "更新任务状态、进度、描述、标题、父任务等字段"


def _get_status_icon(status: str) -> str:
    """获取状态图标。"""
    return {
        "pending": "⏳",
        "in_progress": "⚙️",
        "completed": "✓",
        "blocked": "🚫",
        "deleted": "🗑️"
    }.get(status, "⏳")


def list_tasks() -> Dict[str, Any]:
    """列出所有任务及其状态，体现父子层级关系。

    Returns:
        包含任务列表的字典
    """
    if _todo_manager is None:
        return {"success": False, "stdout": "", "stderr": "TodoManager not initialized"}

    tree = _todo_manager.get_task_tree()

    # Build stdout string with tree indentation
    stdout_lines = []

    def render_tree(items, depth):
        indent = "  " * depth
        for t in items:
            status_icon = _get_status_icon(t.get("status", "pending"))
            stdout_lines.append(f"{indent}{status_icon} [#{t.get('id', '?')}] {t.get('subject', 'N/A')}")
            if t.get("children"):
                render_tree(t["children"], depth + 1)

    if tree:
        render_tree(tree, 0)
    else:
        stdout_lines.append("No tasks found")

    return {
        "success": True,
        "stdout": "\n".join(stdout_lines),
        "stderr": "",
    }


task_list_def = ToolDefinition(
    name=TaskList.name,
    description=TaskList.description,
    fn=list_tasks,
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)

get_global_registry().register(task_list_def)


def get_task(task_id: str) -> Dict[str, Any]:
    """获取指定任务的详细信息（含子任务）。

    Args:
        task_id: 任务 ID

    Returns:
        包含任务详情的字典
    """
    if _todo_manager is None:
        return {"success": False, "stdout": "", "stderr": "TodoManager not initialized"}

    task = _todo_manager.get_task_with_subtasks(task_id)
    if task is None:
        return {"success": False, "stdout": "", "stderr": "Task not found"}

    # Build stdout string for display
    # task may already be a dict or an object with to_dict()
    if hasattr(task, 'to_dict'):
        task_dict = task.to_dict()
    else:
        task_dict = task

    status_icon = _get_status_icon(task_dict.get("status", "pending"))

    stdout_lines = [
        f"{status_icon} Task: {task_dict.get('subject', 'N/A')}",
        f"  ID: #{task_dict.get('id', '?')}",
        f"  Status: {task_dict.get('status', 'pending')}",
        f"  Priority: {task_dict.get('priority', 'normal')}",
        f"  Progress: {task_dict.get('progress', 0)}%",
    ]
    if task_dict.get('description'):
        stdout_lines.append(f"  Description: {task_dict['description']}")

    # Show subtasks
    children = task_dict.get('children', [])
    if children:
        stdout_lines.append(f"  Subtasks ({len(children)}):")
        for child in children:
            child_status = _get_status_icon(child.get("status", "pending"))
            stdout_lines.append(f"    {child_status} [#{child.get('id', '?')}] {child.get('subject', 'N/A')}")

    return {
        "success": True,
        "stdout": "\n".join(stdout_lines),
        "stderr": "",
    }


task_get_def = ToolDefinition(
    name=TaskGet.name,
    description=TaskGet.description,
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
        return {"success": False, "stdout": "", "stderr": "TodoManager not initialized"}

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
        return {"success": False, "stdout": "", "stderr": message}

    status_icon = _get_status_icon(status)
    return {
        "success": True,
        "stdout": f"{status_icon} Task created: [#{task.id}] {subject}",
        "stderr": "",
        "task_id": task.id,
    }


task_create_def = ToolDefinition(
    name=TaskCreate.name,
    description=TaskCreate.description,
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
        return {"success": False, "stdout": "", "stderr": "TodoManager not initialized"}

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
        return {"success": False, "stdout": "", "stderr": message}

    task_dict = task.to_dict()
    status_icon = _get_status_icon(task_dict.get("status", "pending"))

    return {
        "success": True,
        "stdout": f"{status_icon} Task updated: [#{task.id}] {task_dict.get('subject', 'N/A')} (status: {task_dict.get('status', 'pending')}, progress: {task_dict.get('progress', 0)}%)",
        "stderr": "",
        "task_id": task.id,
    }


task_update_def = ToolDefinition(
    name=TaskUpdate.name,
    description=TaskUpdate.description,
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