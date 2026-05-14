from typing import List, Dict, Any, Optional
import json
from pathlib import Path


class Session:
    def __init__(self):
        self._messages: List[Dict[str, Any]] = []
        self._session_id: Optional[str] = None
        self._skills_loaded: set = set()
        self._agents_loaded: set = set()

    def load_from_log(self, log_file: Path) -> None:
        """Load conversation history from a log file.

        Args:
            log_file: Path to the log file
        """
        self._messages = []
        self._skills_loaded = set()
        self._agents_loaded = set()
        self._session_id = None

        if not log_file or not log_file.exists():
            return

        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)

                    if entry.get("type") == "session_start":
                        self._session_id = entry.get("session_id")
                    elif entry.get("type") == "message":
                        self._messages.append({
                            "role": entry.get("role"),
                            "content": entry.get("content", ""),
                            "tool_call_id": entry.get("tool_call_id"),
                            "tool_calls": entry.get("tool_calls"),
                        })
                    elif entry.get("type") == "skill_loaded":
                        self._skills_loaded.add(entry.get("skill_name"))
                    elif entry.get("type") == "agent_loaded":
                        self._agents_loaded.add(entry.get("agent_name"))

                except (json.JSONDecodeError, KeyError):
                    continue

    def add_message(self, role: str, content: str, tool_call_id: Optional[str] = None, tool_calls: Optional[List[Dict[str, Any]]] = None) -> None:
        """Add a message to the session.

        Args:
            role: Message role (user, assistant, tool, system)
            content: Message content
            tool_call_id: For tool role messages, ID of the tool call being responded to
            tool_calls: For assistant messages, list of tool calls
        """
        # Skip empty assistant messages to avoid cluttering session
        if role == "assistant" and not content.strip() and not tool_calls and not tool_call_id:
            return

        msg: Dict[str, Any] = {"role": role, "content": content}
        if tool_call_id:
            msg["tool_call_id"] = tool_call_id
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self._messages.append(msg)

    def get_messages(self) -> List[Dict[str, Any]]:
        return self._messages.copy()

    def get_loaded_skills(self) -> set:
        """Get set of loaded skill names."""
        return self._skills_loaded.copy()

    def get_loaded_agents(self) -> set:
        """Get set of loaded agent names."""
        return self._agents_loaded.copy()

    def set_loaded_skills(self, skills: set) -> None:
        """Set loaded skills."""
        self._skills_loaded = skills.copy()

    def set_loaded_agents(self, agents: set) -> None:
        """Set loaded agents."""
        self._agents_loaded = agents.copy()

    def get_context(self) -> str:
        """Get formatted context string."""
        return "\n".join([f"{m['role']}: {m['content']}" for m in self._messages])

    def clear(self) -> None:
        self._messages.clear()
