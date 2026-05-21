"""OutputSink protocol and implementations for decoupling Runtime from UI."""
from typing import Protocol, runtime_checkable
from simple_agent.ui.renderer import UIRenderer


@runtime_checkable
class OutputSink(Protocol):
    """Abstract output channel for Runtime - implemented by CLI and Web."""

    def on_message(self, role: str, content: str) -> None: ...
    def on_error(self, message: str) -> None: ...
    def on_tool_start(self, tool_name: str, arguments: dict, call_id: str) -> None: ...
    def on_tool_end(
        self, tool_name: str, arguments: dict, call_id: str,
        result: dict, success: bool,
    ) -> None: ...
    def on_turn_start(self, user_input: str) -> None: ...
    def on_turn_end(self) -> None: ...
    def on_status(self, kind: str, data: dict) -> None: ...


def _format_tool_args(arguments: dict) -> str:
    """Format arguments dict as compact bracket string for inline display."""
    if not arguments or not isinstance(arguments, dict):
        return ""
    no_truncate_keys = {"command"}
    skip_keys = {"cwd", "timeout", "case_sensitive", "description", "metadata"}
    priority_keys = ["subject", "command", "path", "task_id", "query", "skill_name", "agent_name"]
    parts = []
    shown = set()
    for k in priority_keys:
        if k in arguments and k not in skip_keys:
            v = str(arguments[k])
            if k not in no_truncate_keys and len(v) > 30:
                v = v[:29] + "…"
            parts.append(f"{k}={v}")
            shown.add(k)
    for k, v in arguments.items():
        if k in shown or k in skip_keys:
            continue
        if len(parts) >= 4:
            parts.append("…")
            break
        v = str(v)
        if len(v) > 20:
            v = v[:19] + "…"
        parts.append(f"{k}={v}")
    return f"[{', '.join(parts)}]" if parts else ""


class CliSink:
    """OutputSink implementation that wraps the existing UIRenderer for CLI mode."""

    def __init__(self, renderer: UIRenderer):
        self._renderer = renderer

    def on_message(self, role: str, content: str) -> None:
        self._renderer.render_message(role, content)

    def on_error(self, message: str) -> None:
        self._renderer.render_error(message)

    def on_tool_start(self, tool_name: str, arguments: dict, call_id: str) -> None:
        from rich.markup import escape
        args_str = _format_tool_args(arguments)
        if args_str:
            self._renderer.console.print(f"{tool_name} {escape(args_str)}", end="")
        else:
            self._renderer.console.print(f"{tool_name}", end="")

    def on_tool_end(
        self, tool_name: str, arguments: dict, call_id: str,
        result: dict, success: bool,
    ) -> None:
        status = "[bold green]✓[/bold green]" if success else "[bold red]✗[/bold red]"
        self._renderer.console.print(f" {status}")
        self._renderer.render_tool_result(tool_name, result, arguments)

    def on_turn_start(self, user_input: str) -> None:
        pass  # CLI 不需要这个事件

    def on_turn_end(self) -> None:
        pass

    def on_status(self, kind: str, data: dict) -> None:
        pass


class WebTurnSink:
    """OutputSink implementation that accumulates events into a list for HTTP return.

    When event_callback is provided, each event is also passed to the callback
    immediately (used by SSE streaming). Without callback, behavior is unchanged.
    """

    def __init__(self, event_callback=None):
        self.events: list[dict] = []
        self._event_callback = event_callback

    def _emit(self, event: dict):
        self.events.append(event)
        if self._event_callback:
            self._event_callback(event)

    def on_message(self, role: str, content: str) -> None:
        self._emit({"type": "message", "role": role, "content": content})

    def on_error(self, message: str) -> None:
        self._emit({"type": "error", "message": message})

    def on_tool_start(self, tool_name: str, arguments: dict, call_id: str) -> None:
        self._emit({
            "type": "tool_start",
            "tool_name": tool_name,
            "arguments": arguments,
            "call_id": call_id,
        })

    def on_tool_end(
        self, tool_name: str, arguments: dict, call_id: str,
        result: dict, success: bool,
    ) -> None:
        self._emit({
            "type": "tool_end",
            "tool_name": tool_name,
            "arguments": arguments,
            "call_id": call_id,
            "result": result,
            "success": success,
        })

    def on_turn_start(self, user_input: str) -> None:
        self._emit({"type": "turn_start", "user_input": user_input})

    def on_turn_end(self) -> None:
        self._emit({"type": "turn_end"})

    def on_status(self, kind: str, data: dict) -> None:
        self._emit({"type": "status", "kind": kind, "data": data})
