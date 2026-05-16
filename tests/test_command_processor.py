import pytest
from simple_agent.resources.command_processor import CommandProcessor, ProcessedCommand
from simple_agent.config.settings import Settings
from simple_agent.core.llm_logger import LLMLogger

def test_processor_creates_processed_command():
    config = Settings()
    logger = LLMLogger()
    processor = CommandProcessor(config, logger)

    cmd_data = {
        "content": "Hello world",
        "metadata": {}
    }

    result = processor.process(cmd_data, [])

    assert isinstance(result, ProcessedCommand)
    assert result.content == "Hello world"