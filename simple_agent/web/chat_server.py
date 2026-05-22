"""Web chat server for simple-agent.

Single-session model: one Runtime instance shared by all browser tabs.
"""
import threading
import uuid
from pathlib import Path
from typing import Optional
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from simple_agent.config.settings import Settings
from simple_agent.core.runtime import Runtime
from simple_agent.core.sinks import WebTurnSink
from simple_agent.core.events import HookBlockedException


# Module-level singletons (single-session model)
_runtime: Optional[Runtime] = None
_sink: Optional[WebTurnSink] = None
_runtime_lock = threading.Lock()

# Active turns: turn_id -> {"events": list, "done": bool}
_turns: dict[str, dict] = {}

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
    """Start a conversation turn. Returns turn_id for polling events."""
    if _runtime is None or _sink is None:
        return jsonify({"error": "Runtime not initialized"}), 500

    payload = request.get_json(silent=True) or {}
    user_input = payload.get("input", "")

    if not user_input.strip():
        return jsonify({"error": "empty input"}), 400

    turn_id = uuid.uuid4().hex[:12]
    turn_state = {"events": [], "done": False}
    _turns[turn_id] = turn_state

    def on_event(event: dict):
        turn_state["events"].append(event)

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
                _sink._event_callback = None
                turn_state["done"] = True

    thread = threading.Thread(target=run_turn, daemon=True)
    thread.start()

    return jsonify({"turn_id": turn_id})


@app.route("/api/turn/events/<turn_id>")
def api_turn_events(turn_id: str):
    """Poll for new events since index `after`."""
    if turn_id not in _turns:
        return jsonify({"error": "Unknown turn_id"}), 404

    turn_state = _turns[turn_id]
    after = request.args.get("after", 0, type=int)
    events = turn_state["events"][after:]

    return jsonify({
        "events": events,
        "done": turn_state["done"],
        "next_after": len(turn_state["events"]),
    })


@app.route("/api/turn/events/<turn_id>", methods=["DELETE"])
def api_turn_events_cleanup(turn_id: str):
    """Clean up turn state after frontend is done."""
    _turns.pop(turn_id, None)
    return jsonify({"ok": True})


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
    resp = send_from_directory(str(_STATIC_DIR), filename)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
