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


def test_api_turn_returns_events_for_plain_message(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.return_value = [
        {"role": "assistant", "content": "Hi there!"}
    ]

    client = chat_server.app.test_client()
    resp = client.post("/api/turn", json={"input": "hello"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert "events" in data
    types = [e["type"] for e in data["events"]]
    assert "turn_start" in types
    assert "message" in types
    assert "turn_end" in types
    msg = next(e for e in data["events"] if e["type"] == "message")
    assert msg["content"] == "Hi there!"
    assert data["session_id"] == chat_server._runtime._session_id


def test_api_turn_clears_events_between_turns(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.return_value = [
        {"role": "assistant", "content": "ok"}
    ]

    client = chat_server.app.test_client()
    data1 = client.post("/api/turn", json={"input": "first"}).get_json()
    data2 = client.post("/api/turn", json={"input": "second"}).get_json()

    first_inputs = [e for e in data2["events"] if e.get("user_input") == "first"]
    assert len(first_inputs) == 0
    second_inputs = [e for e in data2["events"] if e.get("user_input") == "second"]
    assert len(second_inputs) == 1


def test_api_turn_handles_slash_command(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.post("/api/turn", json={"input": "/help"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert any(
        e["type"] == "message" and "Available Commands" in e.get("content", "")
        for e in data["events"]
    )


def test_api_turn_handles_exception_via_sink_error(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.side_effect = RuntimeError("boom")

    client = chat_server.app.test_client()
    resp = client.post("/api/turn", json={"input": "hi"})

    assert resp.status_code == 200
    data = resp.get_json()
    error_events = [e for e in data["events"] if e["type"] == "error"]
    assert len(error_events) == 1
    assert "boom" in error_events[0]["message"]
