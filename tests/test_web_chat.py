import os
import tempfile
import time
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


def _start_turn_and_poll(client, user_input, max_wait=5.0):
    """Helper: POST /api/turn, then poll GET /api/turn/events until done."""
    resp = client.post("/api/turn", json={"input": user_input})
    assert resp.status_code == 200
    turn_id = resp.get_json()["turn_id"]

    all_events = []
    after = 0
    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        poll_resp = client.get(f"/api/turn/events/{turn_id}?after={after}")
        assert poll_resp.status_code == 200
        data = poll_resp.get_json()
        all_events.extend(data["events"])
        after = data["next_after"]
        if data["done"]:
            break

    return all_events


def test_api_turn_returns_events_for_plain_message(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.return_value = [
        {"role": "assistant", "content": "Hi there!"}
    ]

    client = chat_server.app.test_client()
    events = _start_turn_and_poll(client, "hello")

    types = [e["type"] for e in events]
    assert "turn_start" in types
    assert "message" in types
    assert "turn_end" in types
    msg = next(e for e in events if e["type"] == "message")
    assert msg["content"] == "Hi there!"


def test_api_turn_clears_events_between_turns(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.return_value = [
        {"role": "assistant", "content": "ok"}
    ]

    client = chat_server.app.test_client()
    events1 = _start_turn_and_poll(client, "first")
    events2 = _start_turn_and_poll(client, "second")

    first_inputs = [e for e in events2 if e.get("user_input") == "first"]
    assert len(first_inputs) == 0
    second_inputs = [e for e in events2 if e.get("user_input") == "second"]
    assert len(second_inputs) == 1


def test_api_turn_handles_slash_command(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    events = _start_turn_and_poll(client, "/help")

    assert any(
        e["type"] == "message" and "Available Commands" in e.get("content", "")
        for e in events
    )


def test_api_turn_handles_exception_via_sink_error(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.side_effect = RuntimeError("boom")

    client = chat_server.app.test_client()
    events = _start_turn_and_poll(client, "hi")

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
    """If API raises, the event stream should still include turn_end."""
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.side_effect = RuntimeError("boom")

    client = chat_server.app.test_client()
    events = _start_turn_and_poll(client, "hi")

    types = [e["type"] for e in events]
    assert "turn_start" in types
    assert "error" in types
    assert "turn_end" in types


def test_api_turn_events_unknown_id_returns_404(tmpcwd):
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)

    client = chat_server.app.test_client()
    resp = client.get("/api/turn/events/nonexistent123")

    assert resp.status_code == 404


def test_api_turn_events_incremental(tmpcwd):
    """Events should be available incrementally via ?after parameter."""
    from simple_agent.web import chat_server

    config = Settings()
    chat_server.init_runtime(config, skip_api_init=True)
    chat_server._runtime._api_client = MagicMock()
    chat_server._runtime._api_client.send_message.return_value = [
        {"role": "assistant", "content": "ok"}
    ]

    client = chat_server.app.test_client()
    resp = client.post("/api/turn", json={"input": "hello"})
    turn_id = resp.get_json()["turn_id"]

    # First poll: get early events
    poll1 = client.get(f"/api/turn/events/{turn_id}?after=0").get_json()
    assert len(poll1["events"]) > 0
    assert poll1["next_after"] > 0

    # Second poll with after: should only get new events (or none if done)
    poll2 = client.get(f"/api/turn/events/{turn_id}?after={poll1['next_after']}").get_json()
    # All events from poll1 should not appear in poll2
    if poll2["events"]:
        for e in poll2["events"]:
            assert e not in poll1["events"]

    # Cleanup
    client.delete(f"/api/turn/events/{turn_id}")


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
        '{"type": "request", "request_id": "r1", "timestamp": "2026-05-20T10:10:10Z", "model": "gpt-4o", "messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": "resumed hi"}]}\n'
        '{"type": "response", "request_id": "r1", "timestamp": "2026-05-20T10:10:15Z", "content": "hello back"}\n'
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
