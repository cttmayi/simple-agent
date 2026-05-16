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