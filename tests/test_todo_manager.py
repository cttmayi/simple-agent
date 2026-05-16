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

    def test_remove_parent_task(self, temp_manager):
        """测试移除父任务（设置 parent_id=None）。"""
        _, _, parent = temp_manager.create_task(subject="父任务")
        _, _, child = temp_manager.create_task(subject="子任务", parent_id=parent.id)

        # 验证初始状态：子任务有父任务，父任务有子任务
        assert child.parent_id == parent.id
        assert child.id in parent.subtasks

        # 移除父任务
        success, message, updated = temp_manager.update_task(
            child.id, parent_id=None
        )
        assert success is True
        assert updated.parent_id is None
        assert child.id not in parent.subtasks


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