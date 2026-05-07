import pytest

def test_builtin_module_exists():
    from simple_agent.tools.builtin import BASH, READ, WRITE, GREP, WebSearch

    # 验证所有内置工具类都可以导入
    assert BASH is not None
    assert READ is not None
    assert WRITE is not None
    assert GREP is not None
    assert WebSearch is not None
