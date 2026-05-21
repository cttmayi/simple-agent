import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import MagicMock
from simple_agent.config.settings import Settings


@pytest.fixture
def tmpcwd():
    old = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        yield Path(tmp)
        os.chdir(old)


def test_init_runtime_creates_singleton(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    assert chat_server._runtime is not None
    assert chat_server._sink is not None
    assert chat_server._runtime._session_id is not None


def test_init_runtime_injects_web_sink(tmpcwd):
    from simple_agent.web import chat_server
    from simple_agent.core.sinks import WebTurnSink

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    assert isinstance(chat_server._sink, WebTurnSink)
    assert chat_server._runtime._sink is chat_server._sink
