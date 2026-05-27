# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在处理本仓库代码时提供指导。

## 开发命令

```bash
# 安装 (开发模式)
pip install -e .

# 运行 agent
simple-agent

# 使用自定义插件
simple-agent -p ./plugins/custom
simple-agent --plugin ~/my-plugins/awesome-plugin

# 运行
python ...

# 运行测试
pytest

# 运行特定测试文件
pytest tests/test_tools.py

# 运行特定测试
pytest tests/test_tools.py::test_register_tool

# 启动 Web 服务 (日志分析 + 聊天 UI)
simple-agent                          # 默认端口 5001(分析) + 5002(聊天)
simple-agent --port 8080              # 指定聊天端口
simple-agent --resume                 # 从最近日志恢复
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

**配置加载优先级**：`环境变量` → `./.simple-agent/config.yml` → `~/.config/simple-agent/config.yml` → `plugins/default/config.yml` → `plugins/config.yml` → 内置默认值

**重要**：资源路径 (agents, skills, hooks, commands) 由 `plugins/default/.claude-plugin/plugin.json` 控制，YAML 配置文件可以添加额外路径（合并而非覆盖）。

### 配置选项列表

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| **API 配置** ||||
| `api.provider` | string | `openai` | API 提供者：`openai` 或 `anthropic` |
| `api.base_url` | string | `null` | API 基础 URL |
| `api.api_key` | string | `null` | API 密钥，支持 `${VAR}` 引用环境变量 |
| `api.model` | string | `gpt-4o` | 模型名称 |
| **路径配置** ||||
| `paths.tools_dir` | string | `./.simple-agent/tools` | 工具目录路径 |
| `paths.memory_dir` | string | `./.simple-agent/memory` | 记忆目录路径 |
| `paths.logs_dir` | string | `./.simple-agent/logs` | 日志目录路径 |
| `paths.skills_dir` | string/array | `null` | 额外的技能目录（与 plugin.json 合并） |
| `paths.agents_dir` | string/array | `null` | 额外的代理目录（与 plugin.json 合并） |
| `paths.hooks_dir` | string/array | `null` | 额外的钩子目录（与 plugin.json 合并） |
| `paths.commands_dir` | string/array | `null` | 额外的命令目录（与 plugin.json 合并） |
| **UI 配置** ||||
| `ui.theme` | string | `dark` | 主题：`dark` 或 `light` |
| `ui.show_thinking` | boolean | `true` | 是否显示 AI 思考过程 |
| **日志配置** ||||
| `logging.enabled` | boolean | `true` | 是否启用日志记录 |
| `logging.log_dir` | string | `null` | 日志目录，默认使用 `.simple-agent/logs` |

**支持的环境变量：**
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` - API 密钥
- `OPENAI_BASE_URL` / `ANTHROPIC_BASE_URL` - API 基础 URL
- `SIMPLE_AGENT_LOG_DIR` - 日志目录路径
- `SIMPLE_AGENT_TODOS_PATH` - TODO 数据文件路径

使用环境变量覆盖：
```bash
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1
simple-agent
```

### 插件系统

插件目录 `plugins/` 包含自定义扩展：
- **plugins/config.yml** - 共享的默认配置文件，所有插件都会使用此配置
- **plugins/default/** - 默认插件，包含 skills, agents, hooks, commands 和 AGENT.md
- **plugins/default/.claude-plugin/plugin.json** - 定义默认插件的资源路径
- 使用 `-p` 或 `--plugin` 标志指定不同插件
- `plugin.json` 定义资源路径，支持字符串或数组格式

plugin.json 示例：
```json
{
  "skills": ["./skills", "~/.agents/skills"],
  "agents": ["./agents", "~/custom/agents"],
  "hooks": ["./hooks"],
  "commands": ["./commands"]
}
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

## Slash 命令

内置命令：
- `/help` - 显示所有可用命令
- `/version` - 显示版本信息
- `/status` - 显示会话状态
- `/git-status` - 显示 git 仓库状态
- `/clear` - 清除对话历史
- `/reset` - 重置会话（清除历史并卸载 skills/agents）

自定义命令支持：
- **参数传递**：使用 `$1` 或 `$args`
- **Bash 执行**：使用 `!command`
- **文件包含**：使用 `@filename`
- **模板变量**：使用 `{variable_name}`
- **命名空间**：使用 `/` 分隔符（如 `/git/commit`）
- **工具限制**：通过 `allowed-tools` 字段限制可用工具