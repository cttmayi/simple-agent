"""Search for patterns in files."""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from simple_agent.tools.registry import get_global_registry, ToolDefinition


# Directories to skip when searching
SKIP_DIRS = {
    '.git', '.venv', 'venv', 'env', '__pycache__',
    '.pytest_cache', 'node_modules', '.mypy_cache',
    '.tox', '.eggs', 'build', 'dist',
    '.simple-agent',  # Skip .simple-agent directory (contains logs/state)
}

# Maximum matches to return (prevent memory issues)
MAX_MATCHES = 1000

# Maximum file size to search (in bytes, 10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


class GREP:
    """Search for text patterns in files."""

    name = "grep"
    description = "Search for a pattern in a file or directory (recursively searches all files in directory)"

    @staticmethod
    def _grep(path: str, pattern: str, case_sensitive: bool = False, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Search for a pattern in a file or directory with safety checks.

        Args:
            path: File or directory path (relative or absolute)
            pattern: Regular expression pattern to search for
            case_sensitive: Whether the search is case sensitive (default False)
            cwd: Working directory for relative paths (defaults to current directory)

        Returns:
            Dict with success, stdout, and stderr
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
                    "stdout": "",
                    "stderr": "Invalid path"
                }

            # Check if path exists
            if not file_path.exists():
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "Path not found"
                }

            # Compile the pattern with safety limits
            flags = 0 if case_sensitive else re.IGNORECASE

            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"Invalid pattern: {e}"
                }

            # Read file and search for matches
            matches = []

            def search_file(fpath: Path):
                """Search for pattern in a single file."""
                nonlocal matches
                try:
                    # Check file size before reading
                    if fpath.stat().st_size > MAX_FILE_SIZE:
                        return  # Skip large files

                    with open(fpath, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            try:
                                # Check if pattern matches at all
                                match = regex.search(line)
                                if match:
                                    # Only record each line once, even if there are multiple matches
                                    matches.append({
                                        "file": str(fpath),
                                        "line": line_num,
                                        "content": line.rstrip('\n\r'),
                                        "match": match.group(),
                                    })
                                    # Stop if we have too many matches
                                    if len(matches) >= MAX_MATCHES:
                                        return
                            except (re.error, Exception):
                                # Skip problematic lines to prevent ReDoS
                                continue
                except (PermissionError, UnicodeDecodeError):
                    # Skip files we can't read
                    pass

            def search_directory(dpath: Path):
                """Recursively search all files in directory, skipping certain dirs."""
                for item in dpath.iterdir():
                    # Skip hidden files/dirs
                    if item.name.startswith('.'):
                        continue
                    # Skip known skip directories
                    if item.name in SKIP_DIRS:
                        continue
                    if item.is_file():
                        search_file(item)
                    elif item.is_dir():
                        search_directory(item)

            if file_path.is_file():
                # Search single file
                search_file(file_path)
            elif file_path.is_dir():
                # Recursively search all files in directory
                search_directory(file_path)
            else:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "Path is not a file or directory"
                }

            # Build stdout string for display
            stdout_lines = []
            if matches:
                stdout_lines.append(f"Found {len(matches)} matches:")
                for m in matches[:100]:  # Limit to 100 matches in output
                    stdout_lines.append(f"  Line {m['line']}: {m['content']}")
                if len(matches) > 100:
                    stdout_lines.append(f"  ... and {len(matches) - 100} more matches")
            else:
                stdout_lines.append("No matches found")

            # Build stderr string for warnings
            stderr_lines = []
            if len(matches) >= MAX_MATCHES:
                stderr_lines.append(f"Search stopped at {MAX_MATCHES} matches (more may exist)")

            return {
                "success": True,
                "stdout": "\n".join(stdout_lines),
                "stderr": "\n".join(stderr_lines),
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e)
            }

    @staticmethod
    def execute(path: str, pattern: str, case_sensitive: bool = False, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Search for a pattern in a file or directory.

        Args:
            path: File or directory path (relative or absolute)
            pattern: Regular expression pattern to search for
            case_sensitive: Whether the search is case sensitive (default False)
            cwd: Working directory for relative paths (defaults to current directory)

        Returns:
            Dict with success, stdout, and stderr
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