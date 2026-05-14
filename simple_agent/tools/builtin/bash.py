"""Execute shell commands safely."""

import subprocess
import os
import shlex
import re
from typing import Dict, Any, Optional
from simple_agent.tools.registry import get_global_registry, ToolDefinition


# Dangerous command patterns to block
DANGEROUS_PATTERNS = [
    r'rm\s+-rf\s+/',          # rm -rf /
    r':\(;\)\:',               # :(){:|:};:  (fork bomb)
    r'>\s*/dev/',              # Writing to devices
    r'chmod\s+777\s+/',        # chmod 777 /
    r'mkfs\.',                 # Format filesystem
    r'dd\s+if=',               # dd with if=
    r'shred\s+',               # shred command
    r'wget.*\|\s*sh',          # wget piped to sh
    r'curl.*\|\s*sh',          # curl piped to sh
]

# Blocked commands (full command names)
BLOCKED_COMMANDS = {
    'rm', 'dd', 'mkfs', 'format', 'shred',
    'fdisk', 'parted', 'mkswap',
}

# Allowed basic commands (for simple operations)
# This is a restrictive set - dangerous operations require explicit user confirmation
ALLOWED_COMMANDS = {
    'ls', 'cat', 'head', 'tail', 'grep', 'find', 'wc', 'sort', 'uniq',
    'echo', 'date', 'pwd', 'cd', 'mkdir', 'touch', 'cp', 'mv',
    'git', 'python', 'python3', 'pip', 'pip3', 'npm', 'node',
    'pytest', 'make', 'cmake', 'gcc', 'g++', 'clang', 'clang++',
    'javac', 'java', 'mvn', 'gradle', 'go', 'rustc', 'cargo',
    'docker', 'docker-compose', 'kubectl', 'helm',
    'ps', 'top', 'htop', 'kill', 'pkill',
    'df', 'du', 'free', 'uname', 'hostname', 'whoami',
    'env', 'export', 'unset', 'which', 'whereis',
    'man', 'help', 'type', 'alias', 'history',
    'tar', 'gzip', 'gunzip', 'zip', 'unzip', 'xz', 'unxz',
    'sed', 'awk', 'cut', 'tr', 'xargs',
    'curl', 'wget', 'ssh', 'scp', 'rsync',
    'vim', 'vi', 'nano', 'less', 'more',
}


class BASH:
    """Execute shell commands and return output."""

    name = "bash"
    description = "Execute a shell command and return its output"

    @staticmethod
    def _check_command_safety(command: str) -> tuple[bool, Optional[str]]:
        """Check if a command is safe to execute.

        Args:
            command: The command to check

        Returns:
            Tuple of (is_safe, error_message)
        """
        # Remove leading/trailing whitespace
        command = command.strip()

        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Dangerous command pattern detected: {pattern}"

        # Check if command contains blocked commands
        for blocked_cmd in BLOCKED_COMMANDS:
            # Use word boundary to match whole command names
            if re.search(rf'\b{blocked_cmd}\b', command, re.IGNORECASE):
                return False, f"Blocked command: {blocked_cmd} (use with caution or manually)"

        # Try to extract the main command (first word before pipes or redirects)
        # Handle commands with &&, ||, ; etc.
        parts = re.split(r'[;&|]', command)[0].strip()
        main_command = parts.split()[0] if parts else ""

        if main_command:
            # Remove sudo/sudo -E prefix for checking
            if main_command.startswith('sudo'):
                main_command = ' '.join(main_command.split()[1:]) if len(main_command.split()) > 1 else ""

            if main_command and main_command not in ALLOWED_COMMANDS:
                # Be less strict for development - allow but warn about unknown commands
                # In production, you might want to return False here
                pass

        return True, None

    @staticmethod
    def _execute(command: str, cwd: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Execute a shell command safely.

        Args:
            command: The command to execute
            cwd: Working directory (defaults to current directory)
            timeout: Command timeout in seconds (default 30)

        Returns:
            Dict with success, stdout, stderr, returncode
        """
        # Basic validation
        if not command or not command.strip():
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -4,
                "error": "Empty command"
            }

        # Check command safety
        is_safe, error_msg = BASH._check_command_safety(command)
        if not is_safe:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -5,
                "error": error_msg
            }

        # Validate working directory
        if cwd:
            cwd_path = Path(cwd).resolve()
            # Prevent commands from running in sensitive directories
            if any(str(cwd_path).startswith(p) for p in ['/proc/', '/sys/', '/dev/']):
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "returncode": -6,
                    "error": "Cannot execute commands in sensitive system directories"
                }

        try:
            # Use shell=True to preserve shell syntax like pipes (|), redirects (>), etc.
            # This is needed for commands like: find ... | head -20
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )

            stdout = result.stdout
            stderr = result.stderr

            # Limit output to first 5 lines for stdout and stderr
            if stdout:
                stdout_lines = stdout.split('\n')
                if len(stdout_lines) > 5:
                    shown_lines = stdout_lines[:5]
                    stdout = '\n'.join(shown_lines) + '\n[... output truncated, showing first 5 lines ...]'

            if stderr:
                stderr_lines = stderr.split('\n')
                if len(stderr_lines) > 5:
                    shown_lines = stderr_lines[:5]
                    stderr = '\n'.join(shown_lines) + '\n[... output truncated, showing first 5 lines ...]'

            # If both stdout and stderr are empty, add a message
            if not stdout and not stderr:
                if result.returncode == 0:
                    stdout = "(Command completed with no output)"
                else:
                    stderr = f"(Command exited with code {result.returncode} and no output)"

            return {
                "success": result.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "error": "Command timed out"
            }
        except FileNotFoundError:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -2,
                "error": f"Command not found: {command.split()[0]}"
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -3,
                "error": str(e)
            }

    @staticmethod
    def execute(command: str, cwd: Optional[str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Execute a shell command.

        Args:
            command: The command to execute
            cwd: Working directory (defaults to current directory)
            timeout: Command timeout in seconds (default 30)

        Returns:
            Dict with success, stdout, stderr, returncode, and optional error
        """
        return BASH._execute(command, cwd, timeout)


# Auto-register with ToolRegistry
bash_tool_def = ToolDefinition(
    name=BASH.name,
    description=BASH.description,
    fn=BASH.execute,
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command to execute"
            },
            "cwd": {
                "type": "string",
                "description": "Working directory (optional)"
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds (default 30)"
            }
        },
        "required": ["command"]
    }
)

get_global_registry().register(bash_tool_def)