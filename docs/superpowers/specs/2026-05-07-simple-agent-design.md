# Simple Agent 设计文档

**日期**: 2026-05-07
**版本**: 1.0

---

## 1. 概述

Simple Agent 是一个类似 Claude Code 的 CLI 工具，支持 hook、skill、subagent 等自定义扩展，以及 slash 命令。使用 Python 实现，支持 OpenAI 和 Claude API（可配置 base_url 和 api_key）。

---

## 2. 核心架构

### 2.1 核心运行时

核心运行时是整个系统的心脏，负责：

- **会话管理**：维护对话上下文、消息历史、token管理
- **API客户端**：统一的OpenAI/Claude API接口，支持配置base_url和api_key
- **工具调度器**：管理工具注册、调用、结果返回
- **资源加载器**：扫描并加载skills、subagents、hooks、commands
- **事件总线**：在适当时机发布事件供hooks监听

### 2.2 目录结构

```
simple-agent/
├── simple_agent/          # 核心包
│   ├── __init__.py
│   ├── core/               # 核心运行时
│   │   ├── __init__.py
│   │   ├── runtime.py      # 主运行时
│   │   ├── session.py      # 会话管理
│   │   └── events.py       # 事件总线
│   ├── api/                # API客户端
│   │   ├── __init__.py
│   │   ├── client.py       # 统一API客户端
│   │   └── providers.py    # OpenAI/Claude适配器
│   ├── tools/              # 工具系统
│   │   ├── __init__.py
│   │   ├── registry.py     # 工具注册
│   │   └── dispatcher.py   # 工具调度
│   ├── resources/          # 资源加载器
│   │   ├── __init__.py
│   │   ├── skills.py       # Skill加载
│   │   ├── subagents.py    # Subagent加载
│   │   ├── hooks.py        # Hook加载
│   │   └── commands.py     # Command加载
│   ├── ui/                 # 终端UI
│   │   ├── __init__.py
│   │   └── renderer.py     # Rich渲染器
│   └── config/              # 配置管理
│       ├── __init__.py
│       └── settings.py     # 配置加载
├── skills/                 # 技能目录（用户）
├── subagents/              # 子代理目录（用户）
├── hooks/                  # Hook目录（用户）
├── commands/               # 命令目录（用户）
├── tools/                  # 工具目录（用户）
├── memory/                 # 记忆目录（自动生成）
├── AGENT.md                # 项目配置
├── pyproject.toml          # 项目配置
├── README.md
└── tests/                  # 测试
```

---

## 3. 组件详解

### 3.1 Skill 系统

**本质**：Skill 是一份 markdown 格式的"操作手册"或"知识库"，告诉 AI 如何处理某类任务。

**结构**：
```
skills/
└── my-skill/
    ├── SKILL.md          # skill定义（名称、描述、触发条件、内容）
    ├── script/           # Python脚本目录
    │   ├── __init__.py
    │   └── handler.py
    └── resources/        # 资源文件目录
```

**SKILL.md 格式**：
```markdown
---
name: skill-name
description: 简短描述，用于LLM判断何时使用
---

# 技能名称

## 使用场景
描述何时使用此技能

## 具体操作
详细说明如何执行相关任务
```

**触发机制**：
1. 系统扫描 skills 目录，解析每个 SKILL.md 的 frontmatter（name, description）
2. LLM 根据用户请求和 description 判断哪个 skill 可能相关
3. LLM 主动请求加载相关 skill 的完整 SKILL.md 内容
4. SKILL.md 被注入到对话上下文中
5. AI 根据指导调用相关 tool 完成任务

### 3.2 Tool 系统

**本质**：Tool 是可被 LLM 直接调用的 Python 函数。

**结构**：
```
tools/
└── my-tools/
    ├── __init__.py
    ├── file_tools.py
    ├── git_tools.py
    └── ...
```

**定义方式**：
```python
from simple_agent import tool

@tool(name="search_files", description="Search for files by pattern")
def search_files(pattern: str) -> list[str]:
    # 实现逻辑
    pass
```

**与 Skill 的关系**：
- **Tool**：Python 函数，提供具体能力（如读取文件、调用 API）
- **Skill**：Markdown 文档，提供知识和指导（如如何处理 PDF、如何调试）
- AI 调用 tool 执行具体操作，参考 skill 文档理解如何正确使用 tool 完成任务

### 3.3 Subagent 系统

**本质**：独立的 AI 代理，有特定的工具集和能力，用于处理专门的任务。

**结构**：
```
subagents/
└── my-subagent/
    ├── AGENT.md          # subagent定义（类型、能力、工具列表）
    ├── script/           # Python脚本目录
    │   ├── __init__.py
    │   └── agent.py
    └── resources/        # 资源文件目录
        └── templates/
```

**AGENT.md 格式**：
```markdown
---
name: subagent-name
description: 子代理的描述
tools: [Read, Glob, Grep]
type: explore
---

# 子代理名称

描述子代理的用途和能力
```

**触发方式**：
主 LLM 根据任务复杂度和专业性，决定是否委托给 subagent 处理。支持：
- 独立任务：subagent 完全自主完成
- 并行任务：多个 subagent 同时工作
- 依赖任务：subagent 间有依赖关系

### 3.4 Hook 系统

**本质**：监听特定事件并执行自定义逻辑的插件。

**结构**：
```
hooks/
└── my-hook/
    ├── HOOK.md           # hook定义（事件类型、触发时机）
    ├── script/           # Python脚本目录
    │   ├── __init__.py
    │   └── handler.py
    └── resources/        # 资源文件目录
```

**核心事件类型**（与 Claude Code 一致）：
- `message_send_before` - 消息发送前
- `message_send_after` - 消息发送后
- `tool_call_before` - 工具调用前
- `tool_call_after` - 工具调用后
- `session_start` - 会话开始
- `session_end` - 会话结束
- `error_occurred` - 错误发生

### 3.5 Command 系统

**本质**：Slash 命令，提供固定和动态两种形式。

**结构**：
```
commands/
└── my-command/
    ├── COMMAND.md        # 命令定义（名称、用法、处理逻辑）
    ├── script/           # Python脚本目录
    │   ├── __init__.py
    │   └── handler.py
    └── resources/        # 资源文件目录
```

**命令类型**：
- **固定命令**：内置的命令，如 `/help`, `/exit`
- **动态命令**：从 commands 目录加载的用户自定义命令

### 3.6 AGENT.md

**本质**：项目根目录的配置文件，类似 Claude Code 的 CLAUDE.md。

**用途**：
- 定义项目的技术栈和架构
- 说明代码规范和约定
- 列出常用的命令和工具
- 提供上下文信息帮助 AI 更好理解项目

**加载时机**：会话开始时自动读取，内容注入到对话上下文。

---

## 4. 数据流

### 4.1 主消息流

```
用户输入
  ↓
解析（检测slash命令）
  ↓
如果是命令 → 执行command
  ↓
触发 message_send_before hooks
  ↓
调用API（工具循环）
  ↓
触发 message_send_after hooks
  ↓
渲染输出
  ↓
等待下一次输入
```

### 4.2 工具调用循环

```
检测模型返回的工具调用
  ↓
触发 tool_call_before hooks
  ↓
执行工具（tool函数）
  ↓
如果skill被触发 → 加载skill内容，根据定义处理
  ↓
如果subagent被触发 → 启动subagent工作流
  ↓
触发 tool_call_after hooks
  ↓
将结果发回模型
  ↓
重复直到完成
```

---

## 5. 配置管理

### 5.1 配置优先级

命令行参数 > 环境变量 > 配置文件 > 默认值

### 5.2 配置文件位置

- `./.simple-agent/config.yml`
- `~/.config/simple-agent/config.yml`

### 5.3 配置内容

```yaml
api:
  provider: openai  # 或 anthropic
  base_url: https://api.openai.com/v1
  api_key: ${OPENAI_API_KEY}
  model: gpt-4o

paths:
  skills_dir: ./skills
  subagents_dir: ./subagents
  hooks_dir: ./hooks
  commands_dir: ./commands
  tools_dir: ./tools
  memory_dir: ./memory

ui:
  theme: dark
  show_thinking: true
```

---

## 6. API 客户端

统一的抽象层，处理 OpenAI 和 Claude API 的差异：

- 标准化的请求/响应格式
- 流式响应处理
- 错误重试和超时处理
- 配置来源：环境变量、配置文件、命令行参数

---

## 7. UI 系统

使用 `rich` 库实现 Claude Code 风格的终端 UI：

- 美化的消息输出（markdown 渲染）
- 代码高亮和语法显示
- 进度条和加载指示器
- 错误和警告的样式化输出

---

## 8. 错误处理

- **API 调用失败**：自动重试（指数退避）
- **工具执行失败**：返回详细错误信息给 LLM，让模型决定如何处理
- **Hook 异常**：记录日志但不中断主流程，允许继续执行
- **Subagent 失败**：主 Agent 接管并尝试替代方案

---

## 9. 测试策略

- **单元测试**：核心组件（API客户端、工具调度器、事件总线）
- **集成测试**：插件加载、skill/subagent 解析
- **端到端测试**：完整的对话流程测试
- **Mock 测试**：模拟 API 响应用于测试

**测试工具**：pytest + pytest-mock + responses（模拟 HTTP 请求）

---

## 10. 技术栈

- **语言**: Python 3.11+
- **UI**: rich
- **测试**: pytest
- **API 客户端**: openai（支持 OpenAI 兼容 API）
- **配置**: pydantic
