from unittest.mock import MagicMock
from simple_agent.core.sinks import CliSink, WebTurnSink


def test_cli_sink_on_message_calls_renderer():
    renderer = MagicMock()
    sink = CliSink(renderer)

    sink.on_message("assistant", "hello")

    renderer.render_message.assert_called_once_with("assistant", "hello")


def test_cli_sink_on_error_calls_renderer():
    renderer = MagicMock()
    sink = CliSink(renderer)

    sink.on_error("boom")

    renderer.render_error.assert_called_once_with("boom")


def test_cli_sink_on_tool_start_prints_inline():
    renderer = MagicMock()
    sink = CliSink(renderer)

    sink.on_tool_start("READ", {"path": "/tmp/x"}, "call_1")

    # 应该用 end="" 调用 console.print 显示工具名+参数
    args, kwargs = renderer.console.print.call_args
    assert "READ" in args[0]
    assert "path" in args[0]
    assert kwargs.get("end") == ""


def test_cli_sink_on_tool_end_prints_status_and_result():
    renderer = MagicMock()
    sink = CliSink(renderer)
    result = {"success": True, "stdout": "ok"}

    sink.on_tool_end("READ", {"path": "/tmp/x"}, "call_1", result, True)

    # 应该先 print 一个绿色 ✓，再 render_tool_result
    assert renderer.console.print.called
    renderer.render_tool_result.assert_called_once_with("READ", result, {"path": "/tmp/x"})


def test_cli_sink_on_tool_end_failure_prints_red_x():
    renderer = MagicMock()
    sink = CliSink(renderer)
    result = {"success": False, "error": "oops"}

    sink.on_tool_end("READ", {}, "call_1", result, False)

    # 找到那次 print 调用，验证含红 ✗
    printed = [str(c) for c in renderer.console.print.call_args_list]
    assert any("✗" in s for s in printed)


def test_cli_sink_turn_and_status_are_noops():
    renderer = MagicMock()
    sink = CliSink(renderer)

    sink.on_turn_start("hi")
    sink.on_turn_end()
    sink.on_status("skill_loaded", {"name": "x"})

    # 这些是 no-op，不应触发 renderer
    renderer.render_message.assert_not_called()
    renderer.render_error.assert_not_called()


def test_web_sink_on_message_appends_event():
    sink = WebTurnSink()

    sink.on_message("assistant", "hello")

    assert sink.events == [
        {"type": "message", "role": "assistant", "content": "hello"}
    ]


def test_web_sink_on_error_appends_event():
    sink = WebTurnSink()

    sink.on_error("boom")

    assert sink.events == [{"type": "error", "message": "boom"}]


def test_web_sink_tool_start_and_end():
    sink = WebTurnSink()

    sink.on_tool_start("READ", {"path": "/x"}, "c1")
    sink.on_tool_end("READ", {"path": "/x"}, "c1", {"success": True, "stdout": "ok"}, True)

    assert len(sink.events) == 2
    assert sink.events[0] == {
        "type": "tool_start",
        "tool_name": "READ",
        "arguments": {"path": "/x"},
        "call_id": "c1",
    }
    assert sink.events[1] == {
        "type": "tool_end",
        "tool_name": "READ",
        "arguments": {"path": "/x"},
        "call_id": "c1",
        "result": {"success": True, "stdout": "ok"},
        "success": True,
    }


def test_web_sink_turn_start_end():
    sink = WebTurnSink()

    sink.on_turn_start("hi")
    sink.on_turn_end()

    assert sink.events == [
        {"type": "turn_start", "user_input": "hi"},
        {"type": "turn_end"},
    ]


def test_web_sink_status_event():
    sink = WebTurnSink()

    sink.on_status("skill_loaded", {"name": "brainstorming"})

    assert sink.events == [
        {"type": "status", "kind": "skill_loaded", "data": {"name": "brainstorming"}}
    ]


def test_web_sink_events_can_be_cleared():
    sink = WebTurnSink()
    sink.on_message("assistant", "first")
    sink.events.clear()
    sink.on_message("assistant", "second")

    assert sink.events == [
        {"type": "message", "role": "assistant", "content": "second"}
    ]


def test_web_sink_callback_is_called_on_each_event():
    callback = MagicMock()
    sink = WebTurnSink(event_callback=callback)

    sink.on_message("assistant", "hi")
    sink.on_tool_start("READ", {"path": "/x"}, "c1")
    sink.on_tool_end("READ", {"path": "/x"}, "c1", {"success": True}, True)
    sink.on_error("boom")
    sink.on_turn_start("hello")
    sink.on_turn_end()
    sink.on_status("skill_loaded", {"name": "x"})

    assert callback.call_count == 7
    # Verify callback receives same dict as in events list
    for i, call in enumerate(callback.call_args_list):
        assert call[0][0] == sink.events[i]
