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

        return ProcessedCommand(
            content=content,
            allowed_tools=metadata.get("allowed-tools"),
            description=metadata.get("description", "")
        )