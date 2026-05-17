"""Tests for GREP tool（统一 stdout/stderr 格式）。"""

import pytest
import tempfile
from pathlib import Path
from simple_agent.tools.builtin.grep import GREP


def test_grep_searches_file():
    """Test GREP searches for pattern in a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("hello world\nfoo bar\nbaz qux")

        result = GREP.execute(str(test_file), "foo")
        assert result["success"] is True
        assert "Found 1 matches" in result["stdout"]
        assert "Line 2: foo bar" in result["stdout"]


def test_grep_searches_directory():
    """Test GREP searches for pattern in directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        (tmpdir / "file1.txt").write_text("hello world")
        (tmpdir / "file2.txt").write_text("foo bar")
        (tmpdir / "subdir").mkdir()
        (tmpdir / "subdir" / "file3.txt").write_text("baz foo")

        result = GREP.execute(str(tmpdir), "foo")
        assert result["success"] is True
        assert "Found 2 matches" in result["stdout"]


def test_grep_skips_hidden_dirs():
    """Test GREP skips hidden directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        (tmpdir / ".hidden").mkdir()
        (tmpdir / ".hidden" / "secret.txt").write_text("foo bar")
        (tmpdir / "visible.txt").write_text("baz qux")

        result = GREP.execute(str(tmpdir), "foo")
        assert result["success"] is True
        assert "No matches found" in result["stdout"]


def test_grep_skips_venv_dir():
    """Test GREP skips .venv directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        (tmpdir / ".venv").mkdir()
        (tmpdir / ".venv" / "file.txt").write_text("foo bar")
        (tmpdir / "visible.txt").write_text("baz qux")

        result = GREP.execute(str(tmpdir), "foo")
        assert result["success"] is True
        assert "No matches found" in result["stdout"]


def test_grep_case_sensitive():
    """Test GREP case sensitivity."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Hello World\nFOO BAR\nfoo bar")

        # Case insensitive (default)
        result = GREP.execute(str(test_file), "foo", case_sensitive=False)
        assert result["success"] is True
        assert "Found 2 matches" in result["stdout"]

        # Case sensitive
        result = GREP.execute(str(test_file), "foo", case_sensitive=True)
        assert result["success"] is True
        assert "Found 1 matches" in result["stdout"]


def test_grep_invalid_pattern():
    """Test GREP with invalid regex pattern."""
    result = GREP.execute(".", "[invalid(")
    assert result["success"] is False
    assert "Invalid pattern" in result["stderr"]


def test_grep_path_not_found():
    """Test GREP with non-existent path."""
    result = GREP.execute("/nonexistent/path", "foo")
    assert result["success"] is False
    assert "Path not found" in result["stderr"]


def test_grep_empty_directory():
    """Test GREP with empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = GREP.execute(tmpdir, "foo")
        assert result["success"] is True
        assert "No matches found" in result["stdout"]