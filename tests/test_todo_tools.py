"""测试 TODO 工具（统一 stdout/stderr 格式）。"""

import pytest
import tempfile
import shutil
from pathlib import Path
from simple_agent.core.todo_manager import TodoManager
from simple_agent.tools.builtin.todo import set_todo_manager, list_tasks, get_task, create_task, update_task


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
        assert "父任务" in result["stdout"]
        assert "子任务" in result["stdout"]
        # 子任务缩进应比父任务多
        parent_idx = result["stdout"].index("父任务")
        child_idx = result["stdout"].index("子任务")
        assert child_idx > parent_idx


class TestTaskGet:
    """测试 TaskGet 工具。"""

    def test_get_existing_task(self, todo_manager_with_data):
        """测试获取存在的任务。"""
        tasks = todo_manager_with_data.get_all_tasks()
        task_id = tasks[0]["id"]

        result = get_task(task_id)
        assert result["success"] is True
        assert "Task: 父任务" in result["stdout"]

    def test_get_nonexistent_task(self, todo_manager_with_data):
        """测试获取不存在的任务。"""
        result = get_task("nonexistent")
        assert result["success"] is False
        assert "Task not found" in result["stderr"]


class TestTaskCreate:
    """测试 TaskCreate 工具。"""

    def test_create_basic_task(self, todo_manager_with_data):
        """测试创建基本任务。"""
        result = create_task(subject="新任务")
        assert result["success"] is True
        assert "Task created:" in result["stdout"]

    def test_create_with_parent(self, todo_manager_with_data):
        """测试创建带父任务的任务。"""
        parent_id = todo_manager_with_data.get_all_tasks()[0]["id"]
        result = create_task(subject="子任务", parent_id=parent_id)
        assert result["success"] is True

    def test_create_with_invalid_status(self, todo_manager_with_data):
        """测试创建带无效状态的任务。"""
        result = create_task(subject="测试", status="invalid")
        assert result["success"] is False
        assert "Invalid status" in result["stderr"]


class TestTaskUpdate:
    """测试 TaskUpdate 工具。"""

    def test_update_status(self, todo_manager_with_data):
        """测试更新状态。"""
        task_id = todo_manager_with_data.get_all_tasks()[0]["id"]
        result = update_task(task_id, status="completed")
        assert result["success"] is True
        assert "Task updated:" in result["stdout"]
        assert "completed" in result["stdout"]

    def test_update_progress(self, todo_manager_with_data):
        """测试更新进度。"""
        task_id = todo_manager_with_data.get_all_tasks()[0]["id"]
        result = update_task(task_id, progress=75)
        assert result["success"] is True
        assert "Task updated:" in result["stdout"]
        assert "75%" in result["stdout"]

    def test_update_nonexistent_task(self, todo_manager_with_data):
        """测试更新不存在的任务。"""
        result = update_task("nonexistent", status="completed")
        assert result["success"] is False
        assert "Task not found" in result["stderr"]