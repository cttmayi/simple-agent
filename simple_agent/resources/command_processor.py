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