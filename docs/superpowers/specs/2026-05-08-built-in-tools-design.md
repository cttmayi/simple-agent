# 内置工具设计文档

**日期**: 2026-05-08
**版本**: 1.0

---

## 1. 概述

为 Simple Agent 添加 5 个内置工具：READ、WRITE、BASH、GREP、WebSearch，使 AI 能够读取和写入文件、执行 shell 命令、搜索文件内容以及进行网络搜索。

---

## 2. BASH 工具

### 2.1 功能

执行 shell 命令并返回输出结果。

### 2.2 安全考虑

- 使用 `subprocess.run()` 而非 `os.system()` 或 `shell=True`，防止 shell 注入
- 命令执行超时设置为 30 秒
- 捕获 stdout 和 stderr

### 2.3 参数

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| command | str | 是 | 要执行的命令 |

### 2.4 返回格式

```python
{
    "success": bool,
    "stdout": str,
    "stderr": str,
    "returncode": int
}
```

---

## 3. READ 工具

### 3.1 功能

读取文件内容。

### 3.2 安全考虑

- 限制文件访问在当前工作目录内
- 防止路径遍历攻击（`../`）
- 限制文件大小（最大 1MB）

### 3.3 参数

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| path | str | 是 | 文件路径（相对或绝对） |

### 3.4 返回格式

```python
{
    "success": bool,
    "content": str,
    "error": str
}
```

---

## 4. WRITE 工具

### 4.1 功能

将内容写入文件。

### 4.2 安全考虑

- 限制文件访问在当前工作目录内
- 防止路径遍历攻击
- 限制文件大小（最大 10MB）

### 4.3 参数

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| path | str | 是 | 文件路径 |
| content | str | 是 | 要写入的内容 |

### 4.4 返回格式

```python
{
    "success": bool,
    "path": str,
    "error": str
}
```

---

## 5. GREP 工具

### 5.1 功能

在文件中搜索文本模式。

### 5.2 安全考虑

- 限制文件访问在当前工作目录内
- 防止正则表达式 ReDoS 攻击

### 5.3 参数

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| pattern | str | 是 | 搜索模式 |
| path | str | 是 | 文件路径 |
| case_sensitive | bool | 否 | 是否区分大小写（默认 false） |

### 5.4 返回格式

```python
{
    "success": bool,
    "matches": [
        {
            "file": str,
            "line": int,
            "content": str
        }
    ],
    "error": str
}
```

---

## 6. WebSearch 工具

### 6.1 功能

使用 DuckDuckGo 进行网络搜索，无需 API Key。

### 6.2 安全考虑

- 限制搜索结果数量（最多 10 条）
- 清理 HTML 标签，只返回纯文本摘要

### 6.3 参数

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| query | str | 是 | 搜索关键词 |

### 6.4 返回格式

```python
{
    "success": bool,
    "results": [
        {
            "title": str,
            "url": str,
            "snippet": str
        }
    ],
    "error": str
}
```

---

## 7. 文件结构

```
simple_agent/tools/
├── __init__.py          # 现有，导出 tool, ToolRegistry
├── registry.py           # 现有，工具注册
├── dispatcher.py         # 现有，工具调度
└── builtin/             # 新增，内置工具
    ├── __init__.py      # 导出所有内置工具
    ├── bash.py          # BASH 工具
    ├── read.py          # READ 工具
    ├── write.py         # WRITE 工具
    ├── grep.py          # GREP 工具
    └── websearch.py     # WebSearch 工具
```

---

## 8. 集成方式

### 8.1 自动注册

在 `simple_agent/core/runtime.py` 的 `__init__` 方法中，导入内置工具模块，使其自动注册到全局工具注册表。

### 8.2 使用方式

使用 `@tool` 装饰器定义的工具和内置工具都会自动注册到同一个 ToolRegistry，LLM 可以通过函数调用使用。

---

## 9. 错误处理

### 9.1 BASH 工具

- 命令不存在：success=false, stderr 包含错误信息
- 命令超时：success=false, error="Command timed out"
- 其他错误：success=false, error 包含异常信息

### 9.2 READ/WRITE 工具

- 文件不存在：success=false, error="File not found"
- 路径遍历：success=false, error="Access denied"
- 权限不足：success=false, error="Permission denied"
- 文件过大：success=false, error="File too large"

### 9.3 GREP 工具

- 文件不存在：success=false, error="File not found"
- 正则错误：success=false, error="Invalid pattern"
- 未找到匹配：success=true, matches=[]

### 9.4 WebSearch 工具

- 网络错误：success=false, error="Network error"
- 无结果：success=true, results=[]
- 解析错误：success=false, error="Failed to parse results"

---

## 10. 测试策略

### 10.1 单元测试

每个工具都有独立的测试文件：

- `tests/test_builtin_bash.py`
- `tests/test_builtin_read.py`
- `tests/test_builtin_write.py`
- `tests/test_builtin_grep.py`
- `tests/test_builtin_websearch.py`

### 10.2 测试内容

- 正常功能测试
- 错误情况测试
- 安全限制测试（路径遍历、文件大小限制）
- 集成测试（工具是否正确注册）

---

## 11. 技术栈

- **subprocess**: 命令执行
- **pathlib**: 路径操作和验证
- **re**: 正则表达式搜索
- **requests/httpx**: HTTP 请求（用于 WebSearch）
- **html2text**: HTML 清理（用于 WebSearch）

---

## 12. 依赖更新

需要更新 `pyproject.toml` 添加：

```toml
dependencies = [
    "openai>=1.0.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "rich>=13.0.0",
    "python-frontmatter>=1.0.0",
    "html2text>=2020.1.16",  # 新增
]
```
