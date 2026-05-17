# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在处理本仓库代码时提供指导。

## 开发命令

```bash
# 运行 agent
source .venv/bin/activate && simple-agent

# 运行
source .venv/bin/activate && python ...

# 运行测试
source .venv/bin/activate && pytest

# 运行特定测试文件
source .venv/bin/activate && pytest tests/test_tools.py

# 运行特定测试
source .venv/bin/activate && pytest tests/test_tools.py::test_register_tool
```

## 提交代码
- 提交代码前, 请考虑编写测试用例, 确保测试用例通过。
- 提交代码前, 请考虑修正文档, 确保文档与代码保持一致。
- 提交代码前,确认 pytest 执行是否通过。
    - 如不能通过, 请修复测试用例或者修复代码中的问题
使用中文撰写提交信息，提交。

```bash
git add ...
git commit -m "提交信息"
```

## 代码结构


## 架构概览

代码库采用插件式架构，包含以下关键模式：

### 核心组件

- **simple_agent/core/runtime.py**: 主应用循环，编排 API 调用、工具执行和 UI
- **simple_agent/core/session.py**: 维护对话历史，支持 tool_calls 和 tool_call_id
- **simple_agent/tools/registry.py**: 工具的全局单例注册表。使用 `get_global_registry()` 访问
- **simple_agent/tools/dispatcher.py**: 通过注册表执行工具，包含错误处理
- **simple_agent/api/client.py** & **providers.py**: OpenAI 和 Anthropic 的统一 API 客户端

### 工具系统

工具在全局注册表中注册。内置工具在导入时自动注册：
- 导入 `simple_agent.tools.builtin` 以加载所有内置工具
- 使用 `@tool` 装饰器注册自定义函数
- 工具必须返回至少包含 `success` 布尔字段的字典
- `ToolDispatcher.execute()` 包装器添加错误处理，但内置工具包含自己的错误处理

AI 期望的工具结果格式：
```python
{
    "success": True/False,
    "stdout": "...",      # 用于 BASH
    "content": "...",     # 用于 READ
    "matches": [...],     # 用于 GREP
    "results": [...],     # 用于 WebSearch
    "error": "...",       # 可选，当 success=False 时
}
```

当工具执行失败时，错误会以 `[TOOL_ERROR]` 前缀发送给 AI，以便它理解并重试。

### 多步工具调用

运行时自动处理递归工具调用：
1. AI 返回 tool_calls → 执行所有工具 → 将结果发送回 API
2. AI 可能返回更多 tool_calls → 执行 → 将结果发送回 → 重复
3. AI 返回不带 tool_calls 的最终内容 → 显示给用户

此流程在 `Runtime._handle_tool_calls_in_message()` 中处理。

### 配置系统

配置加载优先级：`环境变量` → `./.simple-agent/config.yml` → `plugins/default/config.yml` → `~/.config/simple-agent/config.yml` → 内置默认值

Skills 路径默认在 `plugins/default/config.yml` 中配置，包含 `./plugins/default/skills` 和 `~/.agents/skills`。用户可以在项目配置中覆盖这些路径。

使用环境变量覆盖：
```bash
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1
simple-agent
```

### 日志系统

- LLM 请求/响应记录到 `logs/llm/llm-YYYY-MM-DD.jsonl`（JSONL 格式）
- 使用 `simple-agent --logs` 以人类可读格式查看
- 日志条目包括：request_id、timestamp、model、messages、tool_calls、usage、tool executions

**工具执行日志**：所有工具执行都记录到日志文件（而不仅仅是会话中）。
- 日志捕获：tool_name、tool_call_id、arguments 和完整的 result dict
- 使用 `simple-agent --logs` 查看工具执行结果

### 资源加载

Skills、agents、hooks 和 commands 使用 `python-frontmatter` 从 frontmatter markdown 文件加载。加载器类（`SkillLoader`、`AgentLoader` 等）提供 `list_*()` 和 `get_*()` 方法。

### 会话和消息格式

Session 维护消息历史，支持工具调用：
```python
session.add_message(
    role="user",                    # user, assistant, tool, system
    content="...",                   # 消息内容
    tool_call_id="...",                # 可选，用于 tool 角色
    tool_calls=[...]                  # 可选，用于带 tool_calls 的 assistant 角色
)
```

消息直接传递给 OpenAI API，API 期望函数调用的 `tool_calls` 和 `tool_call_id` 字段。

### UI 渲染

`UIRenderer` 使用 `rich` 库进行终端输出。它有以下方法：
- `render_message(role, content)`: 常规聊天消息
- `render_tool_result(tool_name, result)`: 格式化的工具执行输出
- `render_error(message)`: 错误消息

### 测试

测试使用 pytest 并按模块组织：
- `test_config.py`: 配置加载
- `test_tools.py`: 工具注册和分发
- `test_runtime.py`: 运行时行为
- `test_api.py`: API 客户端和提供者
- `test_ui.py`: UI 渲染
- `test_session.py`: 会话管理

添加新功能时，在相应的文件中添加对应的测试。

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