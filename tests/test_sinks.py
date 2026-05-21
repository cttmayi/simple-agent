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
