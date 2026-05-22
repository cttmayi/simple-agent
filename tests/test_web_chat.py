import os
import tempfile
import json
from pathlib import Path
import pytest
from unittest.mock import MagicMock
from simple_agent.config.settings import Settings


def parse_sse_events(response_data: bytes) -> list[dict]:
    """Parse SSE response body into a list of event dicts."""
    events = []
    text = response_data.decode("utf-8")
    for part in text.split("\n\n"):
        part = part.strip()
        if not part.startswith("data: "):
            continue
        events.append(json.loads(part[6:]))
    return events


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


def _start_turn_and_stream(client, user_input):
    """Helper: POST /api/turn, then GET /api/turn/stream/<id>, return events."""
    resp = client.post("/api/turn", json={"input": user_input})
    assert resp.status_code == 200
    turn_data = resp.get_json()
    turn_id = turn_data["turn_id"]

    stream_resp = client.get(f"/api/turn/stream/{turn_id}")
    assert stream_resp.status_code == 200
    assert stream_resp.content_type.startswith("text/event-stream")
    return parse_sse_events(stream_resp.data)


def test_api_turn_returns_events_for_plain_message(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.return_value = [
        {"role": "assistant", "content": "Hi there!"}
    ]

    client = chat_server.app.test_client()
    events = _start_turn_and_stream(client, "hello")

    types = [e["type"] for e in events]
    assert "turn_start" in types
    assert "message" in types
    assert "turn_end" in types
    assert "turn_done" in types
    msg = next(e for e in events if e["type"] == "message")
    assert msg["content"] == "Hi there!"
    turn_done = next(e for e in events if e["type"] == "turn_done")
    assert turn_done["session_id"] == chat_server._runtime._session_id


def test_api_turn_clears_events_between_turns(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.return_value = [
        {"role": "assistant", "content": "ok"}
    ]

    client = chat_server.app.test_client()
    events1 = _start_turn_and_stream(client, "first")
    events2 = _start_turn_and_stream(client, "second")

    # 第二轮的 events 不应含第一轮的 turn_start
    first_inputs = [e for e in events2 if e.get("user_input") == "first"]
    assert len(first_inputs) == 0
    second_inputs = [e for e in events2 if e.get("user_input") == "second"]
    assert len(second_inputs) == 1


def test_api_turn_handles_slash_command(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    events = _start_turn_and_stream(client, "/help")

    assert any(
        e["type"] == "message" and "Available Commands" in e.get("content", "")
        for e in events
    )
    assert any(e["type"] == "turn_done" for e in events)


def test_api_turn_handles_exception_via_sink_error(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.side_effect = RuntimeError("boom")

    client = chat_server.app.test_client()
    events = _start_turn_and_stream(client, "hi")

    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    assert "boom" in error_events[0]["message"]


def test_api_turn_rejects_empty_input(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.post("/api/turn", json={"input": ""})

    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_api_turn_rejects_whitespace_input(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.post("/api/turn", json={"input": "   \n  "})

    assert resp.status_code == 400


def test_api_turn_emits_turn_end_even_on_exception(tmpcwd):
    """If API raises, the SSE stream should still include turn_end and turn_done."""
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.side_effect = RuntimeError("boom")

    client = chat_server.app.test_client()
    events = _start_turn_and_stream(client, "hi")

    types = [e["type"] for e in events]
    assert "turn_start" in types
    assert "error" in types
    assert "turn_end" in types
    assert "turn_done" in types


def test_api_turn_stream_unknown_id_returns_404(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.get("/api/turn/stream/nonexistent123")

    assert resp.status_code == 404


def test_api_sidebar_returns_structured_data(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.get("/api/sidebar")

    assert resp.status_code == 200
    data = resp.get_json()
    assert "todos" in data
    assert "loaded_skills" in data
    assert "available_skills" in data
    assert "available_agents" in data
    assert isinstance(data["todos"], list)
    assert isinstance(data["loaded_skills"], list)
    assert isinstance(data["available_skills"], list)
    assert isinstance(data["available_agents"], list)


def test_api_logs_returns_list(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    log_dir = tmpcwd / ".simple-agent" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "llm-20260520-101010.jsonl").write_text("")
    (log_dir / "llm-20260519-101010.jsonl").write_text("")

    client = chat_server.app.test_client()
    resp = client.get("/api/logs")

    assert resp.status_code == 200
    data = resp.get_json()
    assert "logs" in data
    names = [entry["name"] for entry in data["logs"]]
    assert "llm-20260520-101010.jsonl" in names
    assert "llm-20260519-101010.jsonl" in names
    assert all("path" in entry and "name" in entry for entry in data["logs"])


def test_api_resume_replaces_runtime(tmpcwd):
    from simple_agent.web import chat_server

    log_dir = tmpcwd / ".simple-agent" / "logs"
    log_dir.mkdir(parents=True)
    log_file = log_dir / "llm-20260520-101010.jsonl"
    log_file.write_text(
        '{"type": "session_start", "session_id": "old-sess"}\n'
        '{"type": "message", "role": "user", "content": "resumed hi"}\n'
    )

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    old_runtime_id = id(chat_server._runtime)

    client = chat_server.app.test_client()
    resp = client.post("/api/resume", json={"log_file": str(log_file)})

    assert resp.status_code == 200
    assert id(chat_server._runtime) != old_runtime_id
    messages = chat_server._runtime._session.get_messages()
    assert any(m.get("content") == "resumed hi" for m in messages)


def test_index_serves_chat_html(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.get("/")

    assert resp.status_code == 200
    assert b"Simple Agent" in resp.data
    assert b"chat.js" in resp.data
