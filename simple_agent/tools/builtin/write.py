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
    def _is_safe_path(file_path: Path, base_dir: Path) -> bool:
        """Check if a path is safe (doesn't escape base_dir).

        Args:
            file_path: Resolved absolute path to check
            base_dir: The base directory that the path should be within

        Returns:
            True if path is safe, False otherwise
        """
        try:
            # Resolve both paths to absolute canonical paths
            file_path = file_path.resolve()
            base_dir = base_dir.resolve()

            # Check if file_path is within base_dir or its subdirectories
            try:
                file_path.relative_to(base_dir)
                return True
            except ValueError:
                # file_path is not relative to base_dir
                return False
        except (OSError, RuntimeError):
            return False

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
                base_dir = base_dir.resolve()
            except (OSError, RuntimeError):
                return {
                    "success": False,
                    "path": str(path),
                    "error": "Invalid path"
                }

            # Path traversal check: ensure file is within base_dir
            if not WRITE._is_safe_path(file_path, base_dir):
                return {
                    "success": False,
                    "path": str(path),
                    "error": "Path traversal detected: cannot write files outside the working directory"
                }

            # Additional check: prevent writing to sensitive system files
            # Check if path contains sensitive patterns
            path_str = str(file_path).lower()
            sensitive_patterns = ['/etc/passwd', '/etc/shadow', '/etc/hosts',
                               '/proc/', '/sys/', '/dev/', '~/.ssh/', '~/.aws/']
            if any(pattern in path_str for pattern in sensitive_patterns):
                return {
                    "success": False,
                    "path": str(path),
                    "error": "Writing to sensitive system files is not allowed"
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
            # Check that parent directories are also within base_dir
            parent_dir = file_path.parent
            if not WRITE._is_safe_path(parent_dir, base_dir):
                return {
                    "success": False,
                    "path": str(path),
                    "error": "Cannot create directories outside the working directory"
                }

            parent_dir.mkdir(parents=True, exist_ok=True)

            # Write content
            file_path.write_text(content, encoding="utf-8")

            return {
                "success": True,
                "output": f"File written: {file_path}",  # For CLI/Web display
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