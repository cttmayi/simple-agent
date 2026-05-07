"""Write content to files."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from simple_agent.tools.registry import get_global_registry, ToolDefinition


# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


class WRITE:
    """Write content to files safely."""

    name = "write"
    description = "Write content to a file"

    @staticmethod
    def _write(path: str, content: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Write content to a file with security checks.

        Args:
            path: File path (relative or absolute)
            content: Content to write
            cwd: Working directory for relative paths (defaults to current directory)

        Returns:
            Dict with success, path, and optional error
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
                    "path": str(path),
                    "error": "Invalid path"
                }

            # Check content size
            content_size = len(content.encode("utf-8"))
            if content_size > MAX_FILE_SIZE:
                return {
                    "success": False,
                    "path": str(path),
                    "error": f"Content too large (max {MAX_FILE_SIZE} bytes, got {content_size})"
                }

            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            file_path.write_text(content, encoding="utf-8")

            return {
                "success": True,
                "path": str(file_path),
            }
        except PermissionError:
            return {
                "success": False,
                "path": str(path),
                "error": "Permission denied"
            }
        except Exception as e:
            return {
                "success": False,
                "path": str(path),
                "error": str(e)
            }

    @staticmethod
    def execute(path: str, content: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Write content to a file.

        Args:
            path: File path (relative or absolute)
            content: Content to write
            cwd: Working directory for relative paths (defaults to current directory)

        Returns:
            Dict with success, path, and optional error
        """
        return WRITE._write(path, content, cwd)


# Auto-register with ToolRegistry
write_tool_def = ToolDefinition(
    name=WRITE.name,
    description=WRITE.description,
    fn=WRITE.execute,
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to write"
            },
            "content": {
                "type": "string",
                "description": "Content to write"
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for relative paths (optional)"
            }
        },
        "required": ["path", "content"]
    }
)

get_global_registry().register(write_tool_def)