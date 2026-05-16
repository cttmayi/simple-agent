import pytest
import tempfile
from pathlib import Path
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

def test_parameter_replacement_single():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Fix bug: $1", "metadata": {}}
    result = processor.process(cmd_data, ["login issue"])

    assert "Fix bug: login issue" in result.content

def test_parameter_replacement_with_spaces():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Commit: $1", "metadata": {}}
    result = processor.process(cmd_data, ["fix login bug and add tests"])

    assert "Commit: fix login bug and add tests" in result.content

def test_parameter_replacement_args_var():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Task: $args", "metadata": {}}
    result = processor.process(cmd_data, ["hello", "world"])

    assert "Task: hello world" in result.content

def test_parameter_replacement_no_args():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Task: $1", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Task: " in result.content

def test_parameter_replacement_has_args():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Args: $#", "metadata": {}}
    result = processor.process(cmd_data, ["test"])

    assert "Args: 1" in result.content

def test_parameter_replacement_no_args_count():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Args: $#", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Args: 0" in result.content

def test_bash_execution():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Status: !`echo OK`", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Status: OK" in result.content

def test_bash_execution_with_command_output():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Files: !`ls tests/`", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Files:" in result.content
    assert "test_" in result.content or "command_" in result.content

def test_bash_execution_timeout():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Result: !`sleep 15`", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Result: [Command timed out]" in result.content

def test_bash_execution_error():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Result: !`exit 1`", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Result:" in result.content  # No output, but should not crash

def test_file_inclusion():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory
        import os
        old_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Create test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello from file")

            processor = CommandProcessor(Settings(), LLMLogger())
            cmd_data = {"content": "Content: @test.txt", "metadata": {}}
            result = processor.process(cmd_data, [])

            assert "Content: Hello from file" in result.content
        finally:
            os.chdir(old_cwd)

def test_file_inclusion_not_found():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Content: @nonexistent.md", "metadata": {}}
    result = processor.process(cmd_data, [])

    assert "Content: [File not found: nonexistent.md]" in result.content

def test_file_inclusion_with_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        import os
        old_cwd = os.getcwd()
        os.chdir(tmpdir)

        try:
            # Create subdirectory and file
            subdir = Path(tmpdir) / "sub"
            subdir.mkdir()
            test_file = subdir / "test.txt"
            test_file.write_text("Nested content")

            processor = CommandProcessor(Settings(), LLMLogger())
            cmd_data = {"content": "Content: @sub/test.txt", "metadata": {}}
            result = processor.process(cmd_data, [])

            assert "Content: Nested content" in result.content
        finally:
            os.chdir(old_cwd)

def test_template_variables():
    processor = CommandProcessor(Settings(), LLMLogger())

    cmd_data = {"content": "Session: {api_provider}, Model: {model}", "metadata": {}}
    result = processor.process(cmd_data, [])

    # Verify the braces were replaced
    assert "{api_provider}" not in result.content
    assert "{model}" not in result.content
    assert "Session:" in result.content
    assert "Model:" in result.content