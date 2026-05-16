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