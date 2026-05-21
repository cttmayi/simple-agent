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


def test_api_session_returns_metadata(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    config.api.model = "gpt-4o-test"
    config.api.provider = "openai"
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.get("/api/session")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["session_id"] == chat_server._runtime._session_id
    assert data["model"] == "gpt-4o-test"
    assert data["provider"] == "openai"
    assert "messages" in data
    assert isinstance(data["messages"], list)


def test_api_session_includes_existing_messages(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._session.add_message("user", "hi")
    chat_server._runtime._session.add_message("assistant", "hello")

    client = chat_server.app.test_client()
    data = client.get("/api/session").get_json()

    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"
