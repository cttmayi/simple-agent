import subprocess
import re
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

from simple_agent.config.settings import Settings
from simple_agent.core.llm_logger import LLMLogger


@dataclass
class ProcessedCommand:
    """Processed command result."""
    content: str
    allowed_tools: Optional[str]
    description: str


class CommandProcessor:
    """Process command templates by replacing parameters, executing bash, and including files."""

    def __init__(self, config: Settings, logger: LLMLogger):
        self._config = config
        self._logger = logger

    def process(self, command_data: dict, args: List[str]) -> ProcessedCommand:
        """Process command and return processed content.

        Args:
            command_data: Command data with 'content' and 'metadata'
            args: Command arguments

        Returns:
            ProcessedCommand with processed content
        """
        content = command_data.get("content", "")
        metadata = command_data.get("metadata", {})

        # Replace parameters
        content = self._replace_positional_params(content, args)

        # Execute bash commands
        content = self._execute_bash_commands(content)

        # Include files
        content = self._include_files(content)

        # Replace template variables
        content = self._replace_template_variables(content)

        return ProcessedCommand(
            content=content,
            allowed_tools=metadata.get("allowed-tools"),
            description=metadata.get("description", "")
        )

    def _replace_positional_params(self, content: str, args: List[str]) -> str:
        """Replace positional parameters ($1, $args, $#).

        Args:
            content: Content with parameters
            args: Command arguments

        Returns:
            Content with parameters replaced
        """
        # All args joined into one string
        arg_value = " ".join(args)

        # Replace $1 and $args
        content = content.replace("$1", arg_value)
        content = content.replace("$args", arg_value)

        # Replace $# with count (1 if has args, 0 otherwise)
        content = content.replace("$#", "1" if arg_value else "0")

        return content

    def _execute_bash_commands(self, content: str) -> str:
        """Execute bash commands in !`cmd` syntax.

        Args:
            content: Content with bash commands

        Returns:
            Content with commands replaced by their output
        """
        pattern = r'!`([^`]*)`'

        def replace(match):
            cmd = match.group(1)
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=Path.cwd(),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                output = result.stdout.strip() or result.stderr.strip()
                return output
            except subprocess.TimeoutExpired:
                return "[Command timed out]"
            except Exception as e:
                return f"[Error: {str(e)}]"

        return re.sub(pattern, replace, content)

    def _include_files(self, content: str) -> str:
        """Include file content using @filename syntax.

        Args:
            content: Content with file references

        Returns:
            Content with files replaced by their content
        """
        pattern = r'@(\S+)'

        def replace(match):
            filepath = Path.cwd() / match.group(1)
            try:
                return filepath.read_text()
            except FileNotFoundError:
                return f"[File not found: {match.group(1)}]"
            except Exception as e:
                return f"[Error reading file: {str(e)}]"

        return re.sub(pattern, replace, content)

    def _replace_template_variables(self, content: str) -> str:
        """Replace template variables like {api_provider}, {model}, etc.

        Args:
            content: Content with template variables

        Returns:
            Content with variables replaced
        """
        # Configuration variables
        replacements = {
            '{api_provider}': self._config.api.provider,
            '{model}': self._config.api.model,
            '{base_url}': self._config.api.base_url or "default",
            '{skills_dirs}': ", ".join(self._config.paths.skills_dirs),
            '{agents_dir}': self._config.paths.agents_dir,
            '{hooks_dir}': self._config.paths.hooks_dir,
            '{commands_dir}': self._config.paths.commands_dir,
            '{theme}': self._config.ui.theme,
            '{show_thinking}': str(self._config.ui.show_thinking),
            '{logging_enabled}': str(self._config.logging.enabled),
            '{log_dir}': self._config.logging.log_dir or "default",
        }

        for var, value in replacements.items():
            content = content.replace(var, str(value))

        return content