import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from simple_agent.core.runtime import Runtime
from simple_agent.config.settings import Settings


def test_init_session_sets_session_id():
    """init_session() 应该生成 session_id 并发布 SessionStart 事件。"""
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            config = Settings()
            runtime = Runtime(config, skip_api_init=True)

            assert runtime._session_id is None
            runtime.init_session()
            assert runtime._session_id is not None
            assert len(runtime._session_id) > 0
    finally:
        os.chdir(old_cwd)


def test_init_session_publishes_session_start_event():
    """init_session() 应该发布 SessionStart 事件。"""
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            config = Settings()
            runtime = Runtime(config, skip_api_init=True)

            received_events = []
            runtime._event_bus.subscribe(
                "SessionStart",
                lambda e: received_events.append(e),
            )

            runtime.init_session()

            assert len(received_events) == 1
            assert received_events[0].data.get("context") == "startup"
            assert received_events[0].data.get("session_id") == runtime._session_id
    finally:
        os.chdir(old_cwd)
