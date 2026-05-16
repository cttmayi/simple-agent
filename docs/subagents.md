# Subagents Documentation

Simple Agent supports subagents - specialized AI agents that run in isolated execution contexts.

## 目录

- [快速开始](#快速开始)
- [Subagent vs Agent](#subagent-vs-agent)
- [创建 Subagent](#创建-subagent)
- [Subagent 结构](#subagent-结构)
- [执行流程](#执行流程)
- [事件系统](#事件系统)
- [示例](#示例)

---

## 快速开始

### 使用 Subagent

在对话中直接请求使用特定的 subagent：

```
请使用 code-analyzer 分析这个项目。
```

AI 会自动调用 `run_subagent` 工具来执行 subagent。

### 可用的 Subagents

查看可用的 subagents：

```
> /agents
```

---

## Subagent vs Agent

| 特性 | Agent (旧方式) | Subagent (新方式) |
|------|---------------|------------------|
| 执行上下文 | 共享主 agent 会话 | 独立隔离的会话 |
| 工具使用 | 使用主 agent 的所有工具 | 可以限制为特定工具集 |
| 消息历史 | 污染主 agent 上下文 | 不影响主 agent |
| 执行方式 | load_agent 加载内容 | run_subagent 执行任务 |
| 适用场景 | 简单提示词 | 独立任务、专业分析 |

---

## 创建 Subagent

Subagent 定义在 `plugin/agents/` 目录下，每个 subagent 是一个子目录，包含 `AGENT.md` 文件：

```
plugin/agents/
├── code-analyzer/
│   └── AGENT.md
├── doc-generator/
│   └── AGENT.md
└── test-runner/
    └── AGENT.md
```

---

## Subagent 结构

### AGENT.md 文件格式

```markdown
---
name: code-analyzer
description: 代码分析和审查专用 agent
tools:
  - read
  - grep
---

# Code Analyzer Agent

You are a specialized agent focused on analyzing code quality...
```

### Frontmatter 字段

| 字段 | 必需 | 说明 |
|------|------|------|
| `name` | 是 | Subagent 名称 |
| `description` | 是 | 简短描述 |
| `tools` | 否 | Subagent 可用的工具列表（默认为所有工具） |

---

## 执行流程

### 1. 用户请求

```
请使用 code-analyzer 分析 src/ 目录的代码质量。
```

### 2. AI 识别 subagent

AI 识别到需要使用 `code-analyzer` subagent。

### 3. 调用 run_subagent 工具

```json
{
  "name": "run_subagent",
  "arguments": {
    "agent_name": "code-analyzer",
    "task": "分析 src/ 目录的代码质量，包括：
1. 代码组织结构
2. 命名规范
3. 潜在的 bug
4. 改进建议",
    "max_turns": 10
  }
}
```

### 4. Subagent 执行

SubAgentRunner：
1. 创建独立的 Session
2. 加载 subagent 的 AGENT.md 内容作为 system prompt
3. 执行用户任务，可能多次调用工具
4. 返回最终结果

### 5. 返回结果给主 agent

主 agent 收到 subagent 的响应，继续处理或展示给用户。

---

## 事件系统

Subagent 执行过程中会发布以下事件：

| 事件 | 说明 |
|------|------|
| `SubAgentStart` | Subagent 开始执行 |
| `SubAgentComplete` | Subagent 执行完成 |
| `SubAgentError` | Subagent 执行出错 |

### 示例 Hook

创建 `plugin/hooks/SubAgentStart/log.py`：

```python
def handler(event):
    """Log subagent start."""
    agent_name = event.data.get("agent_name")
    task = event.data.get("task")
    print(f"[SubAgent] {agent_name} started: {task[:50]}...")
```

---

## 示例

### 示例 1：Code Analyzer

```markdown
---
name: code-analyzer
description: 代码分析和审查专用 agent
tools:
  - read
  - grep
---

# Code Analyzer Agent

You are a specialized agent focused on analyzing code quality, structure, and patterns.

## Purpose

Your primary goal is to analyze code repositories and provide insights about code quality, architecture, and potential issues.

## Analysis Framework

When analyzing code, follow this structure:

### 1. Overview
- What type of project is this?
- What are the main components?
- What technologies are used?

### 2. Code Quality
- Code organization and structure
- Naming conventions
- Documentation quality
- Error handling

### 3. Architecture
- Design patterns used
- Module boundaries
- Dependencies between components

### 4. Potential Issues
- Security concerns
- Performance bottlenecks
- Code smells
- Technical debt

### 5. Recommendations
- Prioritized list of improvements
- Specific code examples where relevant

## Output Format

Structure your responses using markdown with clear sections and code examples.
```

### 示例 2：Test Runner

```markdown
---
name: test-runner
description: 测试执行和结果分析专用 agent
tools:
  - bash
  - grep
  - read
---

# Test Runner Agent

You are a specialized agent for running tests and analyzing results.

## Purpose

Execute test suites and provide detailed analysis of test results.

## Testing Approach

1. Discover test files
2. Run tests
3. Analyze failures
4. Provide recommendations

## Output Format

```
## Test Results
- Total: X
- Passed: Y
- Failed: Z

## Failures
...
```

### 示例 3：Doc Generator

```markdown
---
name: doc-generator
description: 文档生成专用 agent
tools:
  - read
  - write
  - grep
---

# Doc Generator Agent

You are a specialized agent for generating documentation from code.

## Purpose

Generate clear, comprehensive documentation from source code.

## Documentation Types

- API docs
- User guides
- Developer docs
- Changelogs
```

---

## 最佳实践

### Subagent 设计

1. **专注单一职责** - 每个 subagent 负责一个特定领域
2. **清晰的目标** - 在开头明确说明 subagent 的目的
3. **结构化输出** - 定义清晰的输出格式
4. **限制工具集** - 只给 subagent 需要的工具

### 工具限制

通过 `tools` 字段限制 subagent 可用的工具：

```yaml
tools:
  - read
  - grep
```

可用工具：
- `bash` - Shell 命令执行
- `read` - 读取文件
- `write` - 写入文件
- `grep` - 搜索模式
- `web_search` - Web 搜索

### 任务描述

调用 subagent 时，提供清晰的任务描述：

```
请使用 code-analyzer 完成以下任务：
1. 分析 src/ 目录的代码组织
2. 识别潜在的性能问题
3. 提供至少 3 个改进建议
```

### 最大轮数

默认情况下，subagent 最多执行 10 轮对话。可以通过 `max_turns` 参数调整：

```json
{
  "agent_name": "complex-analyzer",
  "task": "...",
  "max_turns": 20
}
```

---

## 故障排查

### Subagent 未找到

1. 检查 subagent 是否在 `plugin/agents/` 目录
2. 检查 AGENT.md 文件是否存在
3. 检查 frontmatter 中的 name 字段

### Subagent 执行失败

1. 检查 API 配置是否正确
2. 查看日志文件了解详细错误
3. 验证 subagent 请求的工具是否可用

### 结果未返回

1. 检查 `max_turns` 是否足够
2. 检查 subagent 是否陷入无限循环
3. 查看 subagent 的内部对话历史

---

## 相关文档

- [Commands 文档](./commands.md)
- [Skills 文档](./skills.md)
- [Hooks 文档](./hooks.md)
- [README.md](../README.md)