from typing import List, Dict


class Session:
    def __init__(self):
        self._messages: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str) -> None:
        self._messages.append({"role": role, "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        return self._messages.copy()

    def get_context(self) -> str:
        """Get formatted context string."""
        return "\n\n".join([f"{m['role']}: {m['content']}" for m in self._messages])

    def clear(self) -> None:
        self._messages.clear()
