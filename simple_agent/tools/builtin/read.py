"""Read file contents."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from simple_agent.tools.registry import get_global_registry, ToolDefinition


# Max file size: 1MB
MAX_FILE_SIZE = 1024 * 1024

# Max lines to return (default 200)
MAX_LINES = 200


class READ:
    """Read file contents safely."""

    name = "read"
    description = "Read the contents of a file"

    @staticmethod
    def _read(path: str, cwd: Optional[str] = None, start_line: Optional[int] = None) -> Dict[str, Any]:
        """Read file contents with security checks.

        Args:
            path: File path (relative or absolute)
            cwd: Working directory for relative paths (defaults to current directory)
            start_line: Line number to start reading from (1-indexed, defaults to 1)

        Returns:
            Dict with success, content, and optional error
        """
        try:
            # Resolve the file path
            base_dir = Path(cwd) if cwd else Path.cwd()
            file_path = Path(path)

            # Make relative paths relative to cwd
            if not file_path.is_absolute():
                file_path = base_dir / file_path

            # Normalize to prevent path traversal
            try:
                file_path = file_path.resolve()
            except (OSError, RuntimeError):
                return {
                    "success": False,
                    "content": "",
                    "error": "Invalid path"
                }

            # Check if file exists
            if not file_path.exists():
                return {
                    "success": False,
                    "content": "",
                    "error": "File not found"
                }

            if not file_path.is_file():
                return {
                    "success": False,
                    "content": "",
                    "error": "Path is not a file"
                }

            # Check file size
            file_size = file_path.stat().st_size
            if file_size > MAX_FILE_SIZE:
                return {
                    "success": False,
                    "content": "",
                    "error": f"File too large (max {MAX_FILE_SIZE} bytes, got {file_size})"
                }

            # Read file content
            content = file_path.read_text(encoding="utf-8")

            # Process lines
            lines = content.splitlines(keepends=True)

            # Set default start_line to 1
            if start_line is None:
                start_line = 1
            elif start_line < 1:
                return {
                    "success": False,
                    "content": "",
                    "error": f"start_line must be at least 1 (got {start_line})"
                }

            # Get requested lines
            start_index = start_line - 1  # Convert to 0-indexed
            end_index = start_index + MAX_LINES

            if start_index >= len(lines):
                return {
                    "success": False,
                    "content": "",
                    "error": f"start_line {start_line} exceeds file length ({len(lines)} lines)"
                }

            # Get lines from start_line to start_line + MAX_LINES
            selected_lines = lines[start_index:end_index]

            # Check if file was truncated
            is_truncated = end_index < len(lines)
            total_lines = len(lines)
            lines_shown_count = len(selected_lines)
            end_line_shown = start_line + lines_shown_count - 1

            # Build result
            result_lines = selected_lines
            if is_truncated:
                result_lines.append(f"\n\n[文件已被截断，仅显示第 {start_line} ~ {end_line_shown} 行 (共 {total_lines} 行)]\n如需查看更多内容，请使用 start_line={end_line_shown + 1} 参数继续读取。")

            result_content = "".join(result_lines)

            return {
                "success": True,
                "content": result_content,
                "total_lines": total_lines,
                "lines_shown": len(selected_lines),
                "start_line": start_line,
                "is_truncated": is_truncated,
            }
        except PermissionError:
            return {
                "success": False,
                "content": "",
                "error": "Permission denied"
            }
        except UnicodeDecodeError:
            return {
                "success": False,
                "content": "",
                "error": "File is not valid UTF-8 text"
            }
        except Exception as e:
            return {
                "success": False,
                "content": "",
                "error": str(e)
            }

    @staticmethod
    def execute(path: str, cwd: Optional[str] = None, start_line: Optional[int] = None) -> Dict[str, Any]:
        """Read file contents.

        Args:
            path: File path (relative or absolute)
            cwd: Working directory for relative paths (defaults to current directory)
            start_line: Line number to start reading from (1-indexed, defaults to 1)

        Returns:
            Dict with success, content, and optional error
        """
        return READ._read(path, cwd, start_line)


# Auto-register with ToolRegistry
read_tool_def = ToolDefinition(
    name=READ.name,
    description=READ.description,
    fn=READ.execute,
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to read"
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for relative paths (optional)"
            },
            "start_line": {
                "type": "integer",
                "description": "Line number to start reading from (1-indexed, defaults to 1). If file is truncated, use this parameter to continue reading from the specified line."
            }
        },
        "required": ["path"]
    }
)

get_global_registry().register(read_tool_def)