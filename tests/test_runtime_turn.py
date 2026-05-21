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


def test_run_one_turn_calls_api_and_renders_response():
    """_run_one_turn() 应该调 API，处理纯文本响应并 render。"""
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            config = Settings()
            runtime = Runtime(config, skip_api_init=True)
            runtime.init_session()

            # Mock api_client - 返回一条无 tool_calls 的简单响应
            runtime._api_client = MagicMock()
            runtime._api_client.send_message.return_value = [
                {"role": "assistant", "content": "Hello, world!"}
            ]

            # Mock renderer 以验证调用
            runtime._renderer = MagicMock()
            runtime._renderer.console = MagicMock()

            # 用户输入已通过 process_input 加入 session
            runtime._session.add_message("user", "hi")
            runtime._run_one_turn()

            # 验证 send_message 被调用
            runtime._api_client.send_message.assert_called_once()
            # 验证响应被加入 session
            messages = runtime._session.get_messages()
            assert messages[-1]["role"] == "assistant"
            assert messages[-1]["content"] == "Hello, world!"
            # 验证 renderer 收到了响应
            runtime._renderer.render_message.assert_any_call("assistant", "Hello, world!")
    finally:
        os.chdir(old_cwd)


def test_runtime_has_default_cli_sink():
    """Runtime 默认应当持有 CliSink 实例。"""
    from simple_agent.core.sinks import CliSink

    config = Settings()
    runtime = Runtime(config, skip_api_init=True)

    assert isinstance(runtime._sink, CliSink)


def test_runtime_accepts_custom_sink():
    """Runtime 应该接受注入的 sink。"""
    from simple_agent.core.sinks import WebTurnSink

    config = Settings()
    custom_sink = WebTurnSink()
    runtime = Runtime(config, skip_api_init=True, sink=custom_sink)

    assert runtime._sink is custom_sink


def test_run_one_turn_routes_tool_calls_through_sink():
    """_run_one_turn() 在执行 tool_calls 时应触发 sink.on_tool_start / on_tool_end。"""
    from simple_agent.core.sinks import WebTurnSink

    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            config = Settings()
            sink = WebTurnSink()
            runtime = Runtime(config, skip_api_init=True, sink=sink)
            runtime.init_session()

            # Mock api_client：第一次返回 tool_calls，第二次返回最终消息
            runtime._api_client = MagicMock()
            runtime._api_client.send_message.side_effect = [
                [{
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {
                            "name": "Bash",
                            "arguments": '{"command": "echo hi"}',
                        },
                    }],
                }],
                [{"role": "assistant", "content": "Done"}],
            ]

            # Mock tool dispatcher
            runtime._tool_dispatcher = MagicMock()
            runtime._tool_dispatcher.execute.return_value = {
                "success": True,
                "stdout": "hi",
            }

            runtime._session.add_message("user", "run echo")
            runtime._run_one_turn()

            # 验证 sink 收到了 tool_start 和 tool_end 事件
            types = [e["type"] for e in sink.events]
            assert "tool_start" in types
            assert "tool_end" in types
            tool_start_event = next(e for e in sink.events if e["type"] == "tool_start")
            assert tool_start_event["tool_name"] == "Bash"
            assert tool_start_event["call_id"] == "call_1"
            tool_end_event = next(e for e in sink.events if e["type"] == "tool_end")
            assert tool_end_event["success"] is True
    finally:
        os.chdir(old_cwd)


def test_turn_start_and_end_events_are_emitted():
    """完整一轮对话应当发出 turn_start 和 turn_end 事件。"""
    from simple_agent.core.sinks import WebTurnSink

    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            config = Settings()
            sink = WebTurnSink()
            runtime = Runtime(config, skip_api_init=True, sink=sink)
            runtime.init_session()

            runtime._api_client = MagicMock()
            runtime._api_client.send_message.return_value = [
                {"role": "assistant", "content": "OK"}
            ]

            runtime.process_input("hello")
            runtime._run_one_turn()

            types = [e["type"] for e in sink.events]
            assert types[0] == "turn_start"
            assert types[-1] == "turn_end"
            assert sink.events[0]["user_input"] == "hello"
    finally:
        os.chdir(old_cwd)
