# TODO 功能设计文档

**日期**: 2026-05-17
**作者**: Claude Code
**状态**: 设计阶段

## 概述

为 simple_agent 实现综合性的任务跟踪系统，支持任务管理、会话持久化和 AI 协作。

### 目标

- 帮助用户跟踪当前会话中的开发任务、bug 修复等
- 保存任务状态以便下次继续工作
- 让 AI 能够创建、更新和跟踪它自己识别的任务

### 核心特性

- 树形层级任务结构（子任务）
- 五种状态：pending、in_progress、completed、blocked、deleted
- 文件持久化（JSON）
- 四个专用工具供 AI 操作
- 终端内联显示当前活动任务

---

## 架构设计

### 组件概览

```
simple_agent/
├── core/
│   ├── todo_manager.py      # TODO 管理器和持久化
│   └── runtime.py           # 扩展：集成 TodoManager
├── tools/builtin/
│   ├── todo.py              # 四个 TODO 工具实现
│   └── __init__.py          # 扩展：导入 TODO 工具
└── ui/
    └── renderer.py          # 扩展：内联显示 TODO 状态
```

### 数据流

```
用户输入 → Runtime → API → AI 调用 TaskCreate/Update 工具
                 ↓
            TodoManager (更新内存和文件)
                 ↓
            UIRenderer (内联显示)
```

---

## 数据模型

### 任务结构

```json
{
  "tasks": {
    "<task_id>": {
      "id": "1",
      "subject": "修复登录 bug",
      "description": "用户在登录时遇到 500 错误",
      "status": "in_progress",
      "priority": "high",
      "progress": 50,
      "activeForm": "修复登录 bug 中",
      "parent_id": null,
      "subtasks": ["2", "3"],
      "owner": null,
      "metadata": {}
    }
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 任务唯一标识符（自动生成） |
| subject | string | 任务标题 |
| description | string | 任务详细描述 |
| status | enum | pending, in_progress, completed, blocked, deleted |
| priority | enum | low, normal, high |
| progress | int | 0-100 进度百分比 |
| activeForm | string | 进行中状态显示文本 |
| parent_id | string\|null | 父任务 ID（用于子任务） |
| subtasks | string[] | 子任务 ID 列表 |
| owner | string\|null | 任务所有者（可选） |
| metadata | dict | 扩展元数据 |

---

## API 设计

### 工具接口

#### TaskList

列出所有任务（含状态、进度、依赖）

```python
def list_tasks() -> dict:
    """列出所有任务及其状态。"""
    return {
        "success": True,
        "tasks": [...]
    }
```

#### TaskGet

查询单个任务详情（含 subtasks）

```python
def get_task(task_id: str) -> dict:
    """获取指定任务的详细信息。"""
    return {
        "success": True,
        "task": {...}
    }
```

#### TaskCreate

新建任务（支持 subject/desc/优先级/父任务）

```python
def create_task(
    subject: str,
    description: str = "",
    activeForm: str = "",
    status: str = "pending",
    priority: str = "normal",
    parent_id: str = None,
    metadata: dict = None
) -> dict:
    """创建新任务。通过 parent_id 指定父任务，形成子任务关系。"""
    return {
        "success": True,
        "task_id": "1",
        "task": {...}
    }
```

#### TaskUpdate

更新任务（状态、进度、完成标记、父任务）

```python
def update_task(
    task_id: str,
    status: str = None,
    progress: int = None,
    parent_id: str = None,
    description: str = None,
    subject: str = None,
    metadata: dict = None
) -> dict:
    """更新任务状态。通过 parent_id 可调整任务的父子关系。"""
    return {
        "success": True,
        "task": {...}
    }
```

---

## UI 设计

### 内联显示

当任务状态变化时，在终端显示：

```
[⚙️ 任务 #1 进行中: 修复登录 bug]
```

使用 `rich` 的 `Text` 组件，带图标和颜色：
- `⚙️` - in_progress (黄色)
- `✓` - completed (绿色)
- `⏳` - pending (灰色)
- `🚫` - blocked (红色)
- `🗑️` - deleted (灰色)

### `/todos` 命令

显示完整任务列表，层级结构缩进显示：

```
# 任务列表

[⚙️ #1] 修复登录 bug (50%)
  [✓ #2] 复现问题
  [⏳ #3] 修复代码

[⏳ #4] 添加单元测试
```

---

## 存储设计

### 文件位置

```
.simple-agent/todos.json
```

### 文件格式

```json
{
  "version": "1.0",
  "tasks": {
    "1": {
      "id": "1",
      ...
    }
  },
  "last_updated": "2026-05-17T12:00:00Z"
}
```

### 持久化策略

- 每次任务修改时立即写入文件
- 文件不存在时自动创建
- 环境变量 `SIMPLE_AGENT_TODOS_PATH` 可自定义路径

---

## 错误处理

### 工具错误

- 任务不存在：`{"success": false, "error": "Task not found"}`
- 无效状态：`{"success": false, "error": "Invalid status: must be one of pending, in_progress, completed, blocked, deleted"}`
- 循环依赖：`{"success": false, "error": "Circular dependency: task cannot be its own ancestor"}`
- 无效父任务：`{"success": false, "error": "Parent task not found"}`

### 文件错误

- 写入失败：记录到日志，保持内存状态
- 损坏文件：备份后重新初始化

---

## 测试策略

### 单元测试

- `test_todo_manager.py` - 测试 CRUD 操作、树结构、持久化
- `test_todo_tools.py` - 测试四个工具的各种场景

### 集成测试

- 测试 AI 通过工具操作 TODO
- 测试 UI 显示正确性

---

## 实现顺序

1. TodoManager 核心逻辑
2. 四个工具实现
3. UIRenderer 扩展
4. Runtime 集成
5. `/todos` 命令
6. 测试