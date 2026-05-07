"""Search for patterns in files."""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from simple_agent.tools.registry import get_global_registry, ToolDefinition


class GREP:
    """Search for text patterns in files."""

    name = "grep"
    description = "Search for a pattern in a file"

    @staticmethod
    def _grep(path: str, pattern: str, case_sensitive: bool = False, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Search for a pattern in a file with safety checks.

        Args:
            path: File path (relative or absolute)
            pattern: Regular expression pattern to search for
            case_sensitive: Whether the search is case sensitive (default False)
            cwd: Working directory for relative paths (defaults to current directory)

        Returns:
            Dict with success, matches list, and optional error
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
                    "matches": [],
                    "error": "Invalid path"
                }

            # Check if file exists
            if not file_path.exists():
                return {
                    "success": False,
                    "matches": [],
                    "error": "File not found"
                }

            if not file_path.is_file():
                return {
                    "success": False,
                    "matches": [],
                    "error": "Path is not a file"
                }

            # Compile the pattern with safety limits
            flags = 0 if case_sensitive else re.IGNORECASE

            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return {
                    "success": False,
                    "matches": [],
                    "error": f"Invalid pattern: {e}"
                }

            # Read file and search for matches
            matches = []
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        try:
                            for match in regex.finditer(line):
                                matches.append({
                                    "file": str(file_path),
                                    "line": line_num,
                                    "content": line.rstrip('\n\r'),
                                    "match": match.group(),
                                })
                        except (re.error, Exception):
                            # Skip problematic lines to prevent ReDoS
                            continue
            except PermissionError:
                return {
                    "success": False,
                    "matches": [],
                    "error": "Permission denied"
                }
            except UnicodeDecodeError:
                return {
                    "success": False,
                    "matches": [],
                    "error": "File is not valid UTF-8 text"
                }

            return {
                "success": True,
                "matches": matches,
            }
        except Exception as e:
            return {
                "success": False,
                "matches": [],
                "error": str(e)
            }

    @staticmethod
    def execute(path: str, pattern: str, case_sensitive: bool = False, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Search for a pattern in a file.

        Args:
            path: File path (relative or absolute)
            pattern: Regular expression pattern to search for
            case_sensitive: Whether the search is case sensitive (default False)
            cwd: Working directory for relative paths (defaults to current directory)

        Returns:
            Dict with success, matches list, and optional error
        """
        return GREP._grep(path, pattern, case_sensitive, cwd)


# Auto-register with ToolRegistry
grep_tool_def = ToolDefinition(
    name=GREP.name,
    description=GREP.description,
    fn=GREP.execute,
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to search"
            },
            "pattern": {
                "type": "string",
                "description": "Regular expression pattern to search for"
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether the search is case sensitive (default False)"
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for relative paths (optional)"
            }
        },
        "required": ["path", "pattern"]
    }
)

get_global_registry().register(grep_tool_def)