"""Web chat server for simple-agent.

Single-session model: one Runtime instance shared by all browser tabs.
"""
import json
import queue
import threading
from pathlib import Path
from typing import Optional
from flask import Flask, jsonify, request, send_from_directory, Response, stream_with_context
from flask_cors import CORS

from simple_agent.config.settings import Settings
from simple_agent.core.runtime import Runtime
from simple_agent.core.sinks import WebTurnSink
from simple_agent.core.events import HookBlockedException


# Module-level singletons (single-session model)
_runtime: Optional[Runtime] = None
_sink: Optional[WebTurnSink] = None
_runtime_lock = threading.Lock()

# Flask app (disable default static folder; we register our own /static route)
app = Flask(__name__, static_folder=None)
CORS(app)


def init_runtime(
    config: Settings,
    resume_log: Optional[str] = None,
    skip_api_init: bool = False,
) -> None:
    """Initialize (or replace) the singleton Runtime with a WebTurnSink injected."""
    global _runtime, _sink

    _sink = WebTurnSink()
    _runtime = Runtime(
        config,
        log_file=resume_log,
        skip_api_init=skip_api_init,
        sink=_sink,
    )

    if resume_log:
        log_path = Path(resume_log)
        if log_path.exists():
            _runtime._session.load_from_log(log_path)

    _runtime.init_session()


@app.route("/api/session", methods=["GET"])
def api_session():
    """Return session metadata for frontend initialization."""
    if _runtime is None:
        return jsonify({"error": "Runtime not initialized"}), 500

    return jsonify({
        "session_id": _runtime._session_id,
        "model": _runtime._config.api.model,
        "provider": _runtime._config.api.provider,
        "messages": _runtime._session.get_messages(),
    })


@app.route("/api/turn", methods=["POST"])
def api_turn():
    """Execute one conversation turn, streaming events via SSE."""
    if _runtime is None or _sink is None:
        return jsonify({"error": "Runtime not initialized"}), 500

    payload = request.get_json(silent=True) or {}
    user_input = payload.get("input", "")

    if not user_input.strip():
        return jsonify({"error": "empty input"}), 400

    event_queue: queue.Queue = queue.Queue()

    def on_event(event: dict):
        event_queue.put(event)

    def run_turn():
        with _runtime_lock:
            _sink.events.clear()
            _sink._event_callback = on_event
            try:
                result = _runtime.process_input(user_input)
                if result in ("message_processed", "command_processed"):
                    _runtime._run_one_turn()
                elif result == "exit":
                    _sink.on_message("system", "Session ended.")
                else:
                    _sink.on_message("system", result)
            except HookBlockedException as e:
                _sink.on_message("system", f"[BLOCKED] {e}")
            except Exception as e:
                _sink.on_error(f"{type(e).__name__}: {e}")
            finally:
                _sink.on_turn_end()
                _sink._event_callback = None  # Clean up callback
                event_queue.put(None)  # sentinel: turn finished

    thread = threading.Thread(target=run_turn, daemon=True)
    thread.start()

    def generate():
        while True:
            event = event_queue.get()
            if event is None:
                yield f"data: {json.dumps({'type': 'turn_done', 'session_id': _runtime._session_id})}\n\n"
                break
            yield f"data: {json.dumps(event)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/sidebar", methods=["GET"])
def api_sidebar():
    """Return sidebar data: todos, loaded skills, available skills/agents."""
    if _runtime is None:
        return jsonify({"error": "Runtime not initialized"}), 500

    todos = _runtime._todo_manager.get_all_tasks() if _runtime._todo_manager else []

    return jsonify({
        "todos": todos,
        "loaded_skills": sorted(_runtime._loaded_skills),
        "available_skills": _runtime._skill_loader.list_skills(),
        "available_agents": _runtime._agent_loader.list_agents(),
    })


@app.route("/api/logs", methods=["GET"])
def api_logs():
    """List available log files for resume, sorted by mtime descending."""
    if _runtime is None:
        return jsonify({"error": "Runtime not initialized"}), 500

    log_dir_str = _runtime._config.logging.log_dir
    log_dir = Path(log_dir_str) if log_dir_str else Path.cwd() / ".simple-agent" / "logs"

    logs = []
    if log_dir.exists():
        files = sorted(
            log_dir.glob("*.jsonl"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        logs = [{"path": str(f), "name": f.name} for f in files]

    return jsonify({"logs": logs})


@app.route("/api/resume", methods=["POST"])
def api_resume():
    """Replace the singleton Runtime with a new one resumed from the given log file."""
    if _runtime is None:
        return jsonify({"error": "Runtime not initialized"}), 500

    payload = request.get_json(silent=True) or {}
    log_file = payload.get("log_file")
    if not log_file:
        return jsonify({"error": "Missing log_file"}), 400

    log_path = Path(log_file)
    if not log_path.exists():
        return jsonify({"error": "Log file not found"}), 404

    with _runtime_lock:
        config = _runtime._config
        skip = _runtime._api_client is None
        init_runtime(config, resume_log=str(log_path), skip_api_init=skip)

    return jsonify({"session_id": _runtime._session_id})


_STATIC_DIR = Path(__file__).parent / "static"


@app.route("/")
def index():
    return send_from_directory(str(_STATIC_DIR), "chat.html")


@app.route("/static/<path:filename>")
def static_file(filename: str):
    return send_from_directory(str(_STATIC_DIR), filename)
