"""Web chat server for simple-agent.

Single-session model: one Runtime instance shared by all browser tabs.
"""
import threading
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

# Flask app
app = Flask(__name__)
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
