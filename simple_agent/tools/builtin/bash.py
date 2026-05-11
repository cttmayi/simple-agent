"""Execute shell commands safely."""

import subprocess
import os
from typing import Dict, Any, Optional
from simple_agent.tools.registry import get_global_registry, ToolDefinition


class BASH:
    """Execute shell commands and return output."""

    name = "bash"
    description = "Execute a shell command and return its output"

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
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
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