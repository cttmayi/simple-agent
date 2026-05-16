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