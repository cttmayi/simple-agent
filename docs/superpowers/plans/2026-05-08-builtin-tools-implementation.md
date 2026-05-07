# 内置工具实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Simple Agent 添加 5 个内置工具（READ、WRITE、BASH、GREP、WebSearch），使 AI 能够读取和写入文件、执行 shell 命令、搜索文件内容以及进行网络搜索。

**Architecture:** 所有工具通过 `@tool` 装饰器或直接调用 `tool_registry.register()` 注册，集成到现有 ToolRegistry 系统。

**Tech Stack:** Python 3.11+, subprocess（BASH）、pathlib（文件操作）、html2text（搜索结果清理）、requests/httpx（WebSearch HTTP 请求）

---

## Task 1: 创建内置工具模块结构

**Files:**
- Create: `simple_agent/tools/builtin/__init__.py`
- Test: `tests/test_builtin/__init__.py`

**Steps:**

- [ ] **Step 1: 创建 builtin 包目录和 __init__.py**

```python
# simple_agent/tools/builtin/__init__.py

"""Built-in tools for Simple Agent."""

__all__ = []
```

- [ ] **Step 2: 编写测试**

```python
# tests/test_builtin/__init__.py

import pytest

def test_builtin_module_exists():
    from simple_agent.tools.builtin import BASH, READ, WRITE, GREP, WebSearch

    # 验证所有内置工具类都可以导入
    assert BASH is not None
    assert READ is not None
    assert WRITE is not None
    assert GREP is not None
    assert WebSearch is not None
```

- [ ] **Step 3: 运行测试验证模块存在**

```bash
pytest tests/test_builtin/__init__.py -v
```

Expected: FAIL with import errors (tools not implemented yet)

- [ ] **Step 4: 提交**

```bash
git add simple_agent/tools/builtin/__init__.py tests/test_builtin/__init__.py
git commit -m "feat: add builtin tools package structure"
```

---

## Task 2: 实现 BASH 工具

**Files:**
- Create: `simple_agent/tools/builtin/bash.py`
- Test: `tests/test_builtin/test_bash.py`

**Steps:**

- [ ] **Step 1: 写测试**

```python
# tests/test_builtin/test_bash.py

import pytest
from simple_agent.tools.builtin import bash

def test_bash_execute_basic_command():
    result = bash.execute("echo hello")
    assert result["success"] is True
    assert result["stdout"] == "hello\n"
    assert result["returncode"] == 0

def test_bash_command_not_found():
    result = bash.execute("nonexistent_command_xyz")
    assert result["success"] is False
    assert "command not found" in result["stderr"]

def test_bash_timeout():
    result = bash.execute("sleep 0.001")  # 非常退出，1ms超时
    # 睡次可能失败，重试
    assert result["success"] is False
    assert "timed out" in result["stderr"]
```

- [ ] **Step 2: 运行测试（应该失败）**

```bash
pytest tests/test_builtin/test_bash.py -v
```

Expected: FAIL with ModuleNotFoundError (bash tool not implemented)

- [ ] **Step 3: 实现 BASH 工具**

```python
# simple_agent/tools/builtin/bash.py

import subprocess
import sys
from typing import Dict, Any


def execute(command: str, cwd: str = None, timeout: int = 30) -> Dict[str, Any]:
    """Execute a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stderr": f"Command timed out after {timeout} seconds",
            "returncode": -1
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stderr": f"Directory not found: {cwd}",
            "returncode": -2
        }
    except Exception as e:
        return {
            "success": False,
            "stderr": f"Error executing command: {str(e)}",
            "returncode": -3
        }
```

- [ ] **Step 4: 更新 __init__.py**

```python
# simple_agent/tools/builtin/__init__.py

"""Built-in tools for Simple Agent."""

from simple_agent.tools.builtin import bash as bash_tool

__all__ = ["bash_tool"]
```

- [ ] **Step 5: 运行测试**

```bash
pytest tests/test_builtin/test_bash.py -v
```

Expected: PASS all tests

- [ ] **Step 6: 提交**

```bash
git add simple_agent/tools/builtin/bash.py simple_agent/tools/builtin/__init__.py tests/test_builtin/test_bash.py
git commit -m "feat: add BASH tool"
```

---

## Task 3: 实现 READ 工具

**Files:**
- Create: `simple_agent/tools/builtin/read.py`
- Test: `tests/test_builtin/test_read.py`

**Steps:**

- [ ] **Step 1: 写测试**

```python
# tests/test_builtin/test_read.py

import pytest
import tempfile
from pathlib import Path
from simple_agent.tools.builtin import read

def test_read_file_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = tmpdir / "test.txt"
        test_file.write_text("Hello World")

        result = read.execute(str(test_file))
        assert result["success"] is True
        assert result["content"] == "Hello World"

def test_read_nonexistent_file():
    result = read.execute("/nonexistent_file_xyz.txt")
    assert result["success"] is False
    assert "File not found" in result["error"]

def test_read_file_too_large():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建 1.1MB 文件（超过 1MB 限制）
        large_file = tmpdir / "large.txt"
        large_file.write_text("x" * 1024 * 1024)  # 1MB + 1KB

        result = read.execute(str(large_file))
        assert result["success"] is False
        assert "File too large" in result["error"]
```

- [ ] **Step 2: 运行测试（应该失败）**

```bash
pytest tests/test_builtin/test_read.py -v
```

Expected: FAIL with ModuleNotFoundError (read tool not implemented)

- [ ] **Step 3: 实现 READ 工具**

```python
# simple_agent/tools/builtin/read.py

import os
from pathlib import Path
from typing import Dict, Any

# 工作目录白名单
ALLOWED_DIRS = {cwd}  # 当前工作目录

# 文件大小限制（1MB）
MAX_FILE_SIZE = 1024 * 1024  # 1MB

# 路径验证
def _is_allowed_path(path: str, cwd: str) -> bool:
    """检查路径是否在允许目录内。"""
    abs_path = Path(path).resolve()
    cwd_path = Path(cwd).resolve()

    # 只允许访问当前工作目录
    return cwd_path == abs_path or cwd_path in abs_path.parents


def execute(path: str, cwd: str = None) -> Dict[str, Any]:
    """读取文件内容。"""
    # 路径安全检查
    if not _is_allowed_path(path, cwd or "."):
        return {
            "success": False,
            "error": f"Access denied: cannot access '{path}' from directory '{cwd or '.'}'"
        }

    # 转换为绝对路径
    abs_path = Path(path).resolve()

    # 检查文件是否存在
    if not abs_path.exists():
        return {
            "success": False,
            "error": f"File not found: '{path}'"
        }

    # 检查文件大小
    file_size = abs_path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        return {
            "success": False,
            "error": f"File too large: {file_size / 1024 / 1024:.1f} MB (limit is 1MB)"
        }

    # 读取文件内容
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            "success": True,
            "content": content,
            "path": str(abs_path)
        }
    except PermissionError as e:
        return {
            "success": False,
            "error": f"Permission denied: cannot read '{path}': {str(e)}"
        }
    except UnicodeDecodeError as e:
        return {
            "success": False,
            "error": f"Encoding error reading '{path}': {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error reading '{path}': {str(e)}"
        }
```

- [ ] **Step 4: 更新 __init__.py**

```python
# simple_agent/tools/builtin/__init__.py

"""Built-in tools for Simple Agent."""

from simple_agent.tools.builtin import bash as bash_tool
from simple_agent.tools.builtin import read as read_tool

__all__ = ["bash_tool", "read_tool"]
```

- [ ] **Step 5: 运行测试**

```bash
pytest tests/test_builtin/test_read.py -v
```

Expected: PASS all tests

- [ ] **Step 6: 提交**

```bash
git add simple_agent/tools/builtin/read.py simple_agent/tools/builtin/__init__.py tests/test_builtin/test_read.py
git commit -m "feat: add READ tool"
```

---

## Task 4: 实现 WRITE 工具

**Files:**
- Create: `simple_agent/tools/builtin/write.py`
- Test: `tests/test_builtin/test_write.py`

**Steps:**

- [ ] **Step 1: 写测试**

```python
# tests/test_builtin/test_write.py

import pytest
import tempfile
from pathlib import Path
from simple_agent.tools.builtin import write

def test_write_file_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = tmpdir / "test.txt"
        test_file.write_text("Hello World")

        result = write.execute(str(test_file), "Test content")
        assert result["success"] is True
        assert result["path"] == str(test_file)

def test_write_nonexistent_path():
    result = write.execute("/nonexistent_dir/test.txt", "Test content")
    assert result["success"] is False
        assert "Directory not found" in result["error"]

def test_write_too_large():
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建 11MB 文件（超过 10MB 限制）
        test_file = tmpdir / "large.txt"
        test_file.write_text("x" * 1024 * 1024 * 10)  # 10MB

        result = write.execute(str(test_file), "Large content")
        assert result["success"] is False
        assert "File too large" in result["error"]
```

- [ ] **Step 2: 运行测试（应该失败）**

```bash
pytest tests/test_builtin/test_write.py -v
```

Expected: FAIL with ModuleNotFoundError (write tool not implemented)

- [ ] **Step 3: 实现 WRITE 工具**

```python
# simple_agent/tools/builtin/write.py

import os
import tempfile
from pathlib import Path
from typing import Dict, Any

# 文件大小限制（10MB）
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# 路径安全检查
def _is_allowed_path(path: str, cwd: str) -> bool:
    """检查路径是否在允许目录内。"""
    abs_path = Path(path).resolve()
    cwd_path = Path(cwd).resolve()

    # 只允许访问当前工作目录
    return cwd_path == abs_path or cwd_path in abs_path.parents


def execute(path: str, content: str, cwd: str = None) -> Dict[str, Any]:
    """将内容写入文件。"""
    # 路径安全检查
    if not _is_allowed_path(path, cwd):
        return {
            "success": False,
            "error": f"Access denied: cannot write to '{path}' from directory '{cwd or '.'}'"
        }

    # 转换为绝对路径
    abs_path = Path(path).resolve()

    # 检查父目录是否存在
    try:
        abs_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return {
            "success": False,
            "error": f"Cannot create directory '{abs_path.parent}': {str(e)}"
        }

    # 检查文件大小（创建前检查，避免创建过大的文件）
    content_size = len(content.encode('utf-8'))

    if content_size > MAX_FILE_SIZE:
        return {
            "success": False,
            "error": f"Content too large: {content_size / 1024 / 1024:.1f} MB (limit is 10MB)"
        }

    try:
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return {
            "success": True,
            "path": str(abs_path)
        }
    except PermissionError as e:
        return {
            "success": False,
            "error": f"Permission denied: cannot write '{path}': {str(e)}"
        }
    except OSError as e:
        return {
            "success": False,
            "error": f"OS error writing '{path}': {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error writing '{path}': {str(e)}"
        }
```

- [ ] **Step 4: 更新 __init__.py**

```python
# simple_agent/tools/builtin/__init__.py

"""Built-in tools for Simple Agent."""

from simple_agent.tools.builtin import bash as bash_tool
from simple_agent.tools.builtin import read as read_tool
from simple_agent.tools.builtin import write as write_tool

__all__ = ["bash_tool", "read_tool", "write_tool"]
```

- [ ] **Step 5: 运行测试**

```bash
pytest tests/test_builtin/test_write.py -v
```

Expected: PASS all tests

- [ ] **Step 6: 提交**

```bash
git add simple_agent/tools/builtin/write.py simple_agent/tools/builtin/__init__.py tests/test_builtin/test_write.py
git commit -m "feat: add WRITE tool"
```

---

## Task 5: 实现 GREP 工具

**Files:**
- Create: `simple_agent/tools/builtin/grep.py`
- Test: `tests/test_builtin/test_grep.py`

**Steps:**

- [ ] **Step 1: 写测试**

```python
# tests/test_builtin/test_grep.py

import pytest
import tempfile
from pathlib import Path
from simple_agent.tools.builtin import grep

def test_grep_basic_search():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = tmpdir / "test.txt"
        test_file.write_text("Hello\nWorld\nPython\nGoodbye")

        result = grep.execute(str(test_file), "World")
        assert result["success"] is True
        assert len(result["matches"]) == 2
        assert result["matches"][0]["content"] == "World\nPython"
        assert result["matches"][1]["content"] == "Goodbye"

def test_grep_case_insensitive():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = tmpdir / "test.txt"
        test_file.write_text("Hello\nWorld\nPython")

        result = grep.execute(str(test_file), "python", case_sensitive=False)
        assert result["success"] is True
        assert any("python" in match["content"] for match in result["matches"])

def test_grep_nonexistent_file():
    result = grep.execute("/nonexistent_file_xyz.txt", "test")
        assert result["success"] is False
        assert "File not found" in result["error"]
```

- [ ] **Step 2: 运行测试（应该失败）**

```bash
pytest tests/test_builtin/test_grep.py -v
```

Expected: FAIL with ModuleNotFoundError (grep tool not implemented)

- [ ] **Step 3: 实现 GREP 工具**

```python
# simple_agent/tools/builtin/grep.py

import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List

# 文件安全检查
def _is_allowed_path(path: str, cwd: str) -> bool:
    """检查路径是否在允许目录内。"""
    abs_path = Path(path).resolve()
    cwd_path = Path(cwd).resolve()

    # 只允许访问当前工作目录
    return cwd_path == abs_path or cwd_path in abs_path.parents


def execute(path: str, pattern: str, cwd: str = None, case_sensitive: bool = False) -> Dict[str, Any]:
    """在文件中搜索文本模式。"""
    # 路径安全检查
    if not _is_allowed_path(path, cwd):
        return {
            "success": False,
            "error": f"Access denied: cannot access '{path}' from directory '{cwd or '.'}'"
        }

    # 转换为绝对路径
    abs_path = Path(path).resolve()

    # 检查文件是否存在
    if not abs_path.exists():
        return {
            "success": False,
            "error": f"File not found: '{path}'"
        }

    # 正则表达式检查（防止 ReDoS 攻击）
    if case_sensitive:
        # 允许更宽松的正则
        pass
    else:
        # 严格检查正则
        if re.search(r'[\[\{\}\*\+\)\|\)\|<>]', pattern):
            return {
                "success": False,
                "error": f"Invalid pattern: '{pattern}' (potential ReDoS)"
            }

    matches = []
    try:
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    match = re.search(pattern, line)
                    if match:
                        matches.append({
                            "file": str(abs_path),
                            "line": line_num + 1,
                            "content": match.group(0)
                        })
                except re.error:
                    return {
                        "success": False,
                        "error": f"Regex error at line {line_num + 1}: {str(e)}"
                    }

    return {
        "success": True,
        "matches": matches
    }
    except PermissionError as e:
        return {
            "success": False,
            "error": f"Permission denied: cannot read '{path}': {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error reading '{path}': {str(e)}"
        }
```

- [ ] **Step 4: 更新 __init__.py**

```python
# simple_agent/tools/builtin/__init__.py

"""Built-in tools for Simple Agent."""

from simple_agent.tools.builtin import bash as bash_tool
from simple_agent.tools.builtin import read as read_tool
from simple_agent.tools.builtin import write as write_tool
from simple_agent.tools.builtin import grep as grep_tool

__all__ = ["bash_tool", "read_tool", "write_tool", "grep_tool"]
```

- [ ] **Step 5: 运行测试**

```bash
pytest tests/test_builtin/test_grep.py -v
```

Expected: PASS all tests

- [ ] **Step 6: 提交**

```bash
git add simple_agent/tools/builtin/grep.py simple_agent/tools/builtin/__init__.py tests/test_builtin/test_grep.py
git commit -m "feat: add GREP tool"
```

---

## Task 6: 实现 WebSearch 工具

**Files:**
- Create: `simple_agent/tools/builtin/websearch.py`
- Test: `tests/test_builtin/test_websearch.py`

**Steps:**

- [ ] **Step 1: 写测试**

```python
# tests/test_builtin/test_websearch.py

import pytest
from unittest.mock import patch
from simple_agent.tools.builtin import websearch

def test_websearch_basic_search():
    with patch('simple_agent.tools.builtin.websearch.requests') as mock_requests:
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "AbstractHTML": f"...summary...",
            "AbstractURL": f"...url...",
            "result": "search results"
        }
        mock_response.json.return_value = {
            "Heading": "Test Title",
            "URL": "https://example.com/test",
            "Snippet": "...content..."
        }
        mock_requests.get.return_value.return_value.json.return_value = [mock_response]

        result = websearch.execute("test query")
        assert result["success"] is True
        assert len(result["results"]) == 1

def test_websearch_no_results():
    with patch('simple_agent.tools.builtin.websearch.requests') as mock_requests:
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "AbstractHTML": "...",
            "result": "no results"
        }
        mock_requests.get.return_value.json.return_value = [mock_response]

        result = websearch.execute("no results")
        assert result["success"] is True
        assert len(result["results"]) == 0

def test_websearch_http_error():
    with patch('simple_agent.tools.builtin.websearch.requests') as mock_requests:
        mock_requests.get.side_effect = Exception("Network error")

        result = websearch.execute("test")
        assert result["success"] is False
        assert "Network error" in result["error"]
```

- [ ] **Step 2: 运行测试（应该失败）**

```bash
pytest tests/test_builtin/test_websearch.py -v
```

Expected: FAIL with ModuleNotFoundError (websearch tool not implemented)

- [ ] **Step 3: 实现 WebSearch 工具**

```python
# simple_agent/tools/builtin/websearch.py

import requests
from typing import Dict, Any, List

# DuckDuckGo Instant Answer API
DUCKDUCK_API = "https://api.duckduckgo.com/"

def _parse_abstract(html: str) -> str:
    """解析 DuckDuckGo 的 AbstractHTML 响应，提取摘要。"""
    # 简单的文本提取（移除 HTML 标签）
    if not html:
        return ""

    # 提取 <abstract> 标签内容
    abstract_match = re.search(r'<abstract[^>]*>(.*?)</abstract>', html, re.IGNORECASE | re.DOTALL)
    if abstract_match:
        return abstract_match.group(1).strip()

    return ""

def _clean_html(html: str) -> str:
    """清理 HTML 标签，只返回纯文本。"""
    # 移除常见的 HTML 标签
    if not html:
        return ""

    # 移除 HTML 标签
    html = re.sub(r'<[^>]+>', ' ', html)
    html = re.sub(r'</[^>]+>', ' ', html)
    html = re.sub(r'<[^>]+/>', ' ', html)
    html = re.sub(r'&[^;]+;', ';', html)
    html = html.replace('&lt;', '<')
    html = html.replace('&gt;', '>')
    html = html.replace('&quot;', '"')
    html = html.replace('&amp;', '&')

    # 移除多余空格
    html = ' '.join(html.split())

    return html.strip()


def execute(query: str) -> Dict[str, Any]:
    """使用 DuckDuckGo 进行网络搜索。"""
    # 构建请求参数
    params = {
        "q": query,
        "format": "json",
        "pretty": "1",
        "no_html": "1",
        "skip_disambiguation": "1",
        "no_redirect": "1"
    }

    try:
        response = requests.get(DUCKDUCK_API, params=params, timeout=10)
        response.raise_for_status()

        # 解析响应
        abstract = _parse_abstract(response.text)
        results = []

        # 提取即时答案
        if response.json.get("RelatedTopics"):
            for topic in response.json["RelatedTopics"]:
                results.append({
                    "title": topic.get("FirstURL", "").get("Text", ""),
                    "url": topic.get("FirstURL", {}).get("URL", ""),
                    "snippet": topic.get("Result", "") if topic.get("Result", "") else ""
                })

        return {
            "success": True,
            "results": results,
            "abstract": abstract
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Search timed out after 10 seconds"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }
```

- [ ] **Step 4: 更新 __init__.py**

```python
# simple_agent/tools/builtin/__init__.py

"""Built-in tools for Simple Agent."""

from simple_agent.tools.builtin import bash as bash_tool
from simple_agent.tools.builtin import read as read_tool
from simple_agent.tools.builtin import write as write_tool
from simple_agent.tools.builtin import grep as grep_tool
from simple_agent.tools.builtin import websearch as websearch_tool

__all__ = ["bash_tool", "read_tool", "write_tool", "grep_tool", "websearch_tool"]
```

- [ ] **Step 5: 运行测试**

```bash
pytest tests/test_builtin/test_websearch.py -v
```

Expected: PASS all tests

- [ ] **Step 6: 提交**

```bash
git add simple_agent/tools/builtin/websearch.py simple_agent/tools/builtin/__init__.py tests/test_builtin/test_websearch.py
git commit -m "feat: add WebSearch tool"
```

---

## Task 7: 更新 __init__.py 导出所有内置工具

**Files:**
- Modify: `simple_agent/tools/builtin/__init__.py`

**Steps:**

- [ ] **Step 1: 更新导入**

```python
# simple_agent/tools/builtin/__init__.py

"""Built-in tools for Simple Agent."""

from simple_agent.tools.builtin import bash
from simple_agent.tools.builtin import read
from simple_agent.tools.builtin import write
from simple_agent.tools.builtin import grep
from simple_agent.tools.builtin import websearch

__all__ = ["bash_tool", "read_tool", "write_tool", "grep_tool", "websearch_tool"]
```

- [ ] **Step 2: 提交**

```bash
git add simple_agent/tools/builtin/__init__.py
git commit -m "feat: export all built-in tools"
```

---

## Task 8: 更新 pyproject.toml 添加依赖

**Files:**
- Modify: `pyproject.toml`

**Steps:**

- [ ] **Step 1: 添加 requests 和 html2text 依赖**

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-mock>=3.10.0",
    "requests>=2.31.0",
    "html2text>=2020.1.16",
]

[project.dependencies]
requests = ">=2.31.0"
html2text = ">=2020.1.16"
```

- [ ] **Step 2: 提交**

```bash
git add pyproject.toml
git commit -m "feat: add websearch dependencies"
```

---

## Task 9: 更新 runtime.py 自动注册内置工具

**Files:**
- Modify: `simple_agent/core/runtime.py`

**Steps:**

- [ ] **Step 1: 添加内置工具导入**

```python
# simple_agent/core/runtime.py 修改

# 在文件顶部添加导入
from simple_agent.tools.builtin import (
    bash,
    read,
    write,
    grep,
    websearch
)
```

- [ ] **Step 2: 在 __init__ 方法中注册内置工具**

```python
# simple_agent/core/runtime.py 修改

class Runtime:
    def __init__(self, config: Settings):
        # ... 现有代码 ...
        self._config = config
        self._event_bus = EventBus()
        self._session = Session()
        self._renderer = UIRenderer()
        self._api_client = APIClient(config.api)
        self._tool_registry = ToolRegistry()
        self._tool_dispatcher = ToolDispatcher(self._tool_registry)

        # 初始化资源加载器
        self._skill_loader = SkillLoader(Path(config.paths.skills_dir))
        self._subagent_loader = SubagentLoader(Path(config.paths.subagents_dir))
        self._hook_loader = HookLoader(Path(config.paths.hooks_dir))
        self._command_loader = CommandLoader(Path(config.paths.commands_dir))

        # ... 现有代码 ...

        # 加载并注册内置工具
        self._load_builtin_tools()
```

- [ ] **Step 3: 添加 _load_builtin_tools 方法**

```python
# simple_agent/core/runtime.py 添加

    def _load_builtin_tools(self):
        """加载并注册所有内置工具到全局工具注册表。"""
        for tool in [bash, read, write, grep, websearch]:
            try:
                # 尝试获取工具函数
                tool_fn = getattr(tool, "execute", None)
                if tool_fn is not None:
                    self._tool_registry.register(ToolDefinition(
                        name=tool.__name__.upper(),
                        description=f"Built-in {tool.__name__} tool",
                        fn=tool_fn,
                        parameters={
                            "type": "object",
                            "properties": tool_fn.parameters if hasattr(tool_fn, "parameters") else {},
                            "description": f"Built-in {tool.__name__} tool",
                        }
                    ))
            except AttributeError:
                # 工具模块可能没有实现，跳过
                pass
```

- [ ] **Step 4: 提交**

```bash
git add simple_agent/core/runtime.py
git commit -m "feat: auto-register builtin tools"
```

---

## Task 10: 更新 README.md 文档

**Files:**
- Modify: `README.md`

**Steps:**

- [ ] **Step 1: 添加内置工具说明**

```markdown
# Simple Agent

## Features

- **Tools**: Register Python functions as tools for LLM function calling
- **Skills**: Markdown-based knowledge documents that guide AI behavior
- **Subagents**: Specialized AI agents for specific tasks
- **Hooks**: Event-driven plugins for custom behavior
- **Commands**: Built-in and custom slash commands
- **Multi-Provider**: Support for OpenAI and Anthropic/Claude APIs

## Built-in Tools

Simple Agent 包含以下 5 个内置工具：

### 1. BASH 工具
- **功能**: 执行 shell 命令并返回输出
- **使用**: `bash.execute(command)`

### 2. READ 工具
- **功能**: 读取文件内容
- **使用**: `read.execute(path)`
- **安全**: 限制在当前工作目录内，文件大小限制 1MB

### 3. WRITE 工具
- **功能**: 将内容写入文件
- **使用**: `write.execute(path, content)`
- **安全**: 限制在当前工作目录内，文件大小限制 10MB

### 4. GREP 工具
- **功能**: 在文件中搜索文本模式
- **使用**: `grep.execute(path, pattern, case_sensitive)`
- **安全**: 防止路径遍历和 ReDoS 攻击

### 5. WebSearch 工具
- **功能**: 使用 DuckDuckGo 进行网络搜索，无需 API Key
- **使用**: `websearch.execute(query)`
- **安全**: 限制搜索结果最多 10 条，清理 HTML 标签
```

## Installation

```bash
pip install -e .
```

## Configuration

创建一个 `.simple-agent/config.yml` 文件：

```yaml
api:
  provider: openai  # or anthropic
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
```

---

## 使用示例

### BASH 工具
```python
# 可以直接通过工具调用，LLM 会自动识别

user: "运行 ls 命令"
assistant: 我将为您列出当前目录的文件和文件夹。
```

### READ 工具
```python
# 可以通过工具调用读取文件

user: "查看 setup.py 的内容"
assistant: <tool_calls>[{name: "read", "arguments": {"path": "setup.py"}}]</tool_calls>
```

### WRITE 工具
```python
# 可以通过工具调用写入文件

user: "在 config.yml 中添加新的配置项"
assistant: <tool_calls>[{name: "write", "arguments": {"path": "config.yml", "content": "new_config: true"}}]</tool_calls>
```

### GREP 工具
```python
# 可以通过工具调用搜索文件中的内容

user: "在代码中查找所有包含 'TODO' 的注释"
assistant: <tool_calls>[{name: "grep", "arguments": {"path": ".", "pattern": "TODO"}}]</tool_calls>
```

### WebSearch 工具
```python
# 可以通过工具调用进行网络搜索

user: "搜索 Python 文件操作的最佳实践"
assistant: <tool_calls>[{name: "websearch", "arguments": {"query": "python pathlib file operations"}}]</tool_calls>
<result>
```

## Development

```bash
pip install -e .
pytest
```

## Project Structure

```
simple_agent/
├── simple_agent/          # Core package
│   ├── config/          # Configuration
│   ├── core/            # Core runtime
│   │   ├── events.py       # Event bus
│   │   ├── session.py      # Session management
│   │   └── runtime.py     # Main runtime with builtin tools
│   ├── tools/           # Tool system
│   │   ├── registry.py    # Tool registry
│   │   ├── dispatcher.py  # Tool dispatcher
│   │   └── builtin/       # Built-in tools
│   │       ├── __init__.py
│   │       ├── bash.py        # BASH tool
│   │       ├── read.py        # READ tool
│   │       ├── write.py       # WRITE tool
│   │       ├── grep.py        # GREP tool
│   │       └── websearch.py   # WebSearch tool
│   ├── resources/       # Resource loaders
│   ├── ui/              # Terminal UI
│   └── builtin/        # Built-in tools
├── skills/             # Skill definitions
├── subagents/          # Subagent definitions
├── hooks/              # Hook definitions
├── commands/           # Command definitions
├── tools/             # Tool implementations
├── memory/             # Auto-generated memory
└── AGENT.md            # Project-specific instructions
```
