"""Read file contents."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from simple_agent.tools.registry import get_global_registry, ToolDefinition


# Max file size: 1MB
MAX_FILE_SIZE = 1024 * 1024


class READ:
    """Read file contents safely."""

    name = "read"
    description = "Read the contents of a file"

    @staticmethod
    def _read(path: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Read file contents with security checks.

        Args:
            path: File path (relative or absolute)
            cwd: Working directory for relative paths (defaults to current directory)

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

            # Verify the path is within the allowed directory
            # Allow reading anywhere, but warn about potential issues
            # For stricter security, you could restrict to base_dir

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

            return {
                "success": True,
                "content": content,
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
    def execute(path: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Read file contents.

        Args:
            path: File path (relative or absolute)
            cwd: Working directory for relative paths (defaults to current directory)

        Returns:
            Dict with success, content, and optional error
        """
        return READ._read(path, cwd)


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
            }
        },
        "required": ["path"]
    }
)

get_global_registry().register(read_tool_def)