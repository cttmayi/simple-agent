from typing import List, Dict, Any, Optional


class Session:
    def __init__(self):
        self._messages: List[Dict[str, Any]] = []

    def add_message(self, role: str, content: str, tool_call_id: Optional[str] = None, tool_calls: Optional[List[Dict[str, Any]]] = None) -> None:
        """Add a message to the session.

        Args:
            role: Message role (user, assistant, tool, system)
            content: Message content
            tool_call_id: For tool role messages, the ID of the tool call being responded to
            tool_calls: For assistant messages, the list of tool calls
        """
        msg: Dict[str, Any] = {"role": role, "content": content}
        if tool_call_id:
            msg["tool_call_id"] = tool_call_id
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self._messages.append(msg)

    def get_messages(self) -> List[Dict[str, Any]]:
        return self._messages.copy()

    def get_context(self) -> str:
        """Get formatted context string."""
        return "\n\n".join([f"{m['role']}: {m['content']}" for m in self._messages])

    def clear(self) -> None:
        self._messages.clear()
