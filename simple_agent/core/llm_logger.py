"""LLM API request/response logger for analysis."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from threading import Lock


class LLMLogger:
    """Logger for LLM API requests and responses."""

    def __init__(self, log_dir: Optional[Path] = None, enabled: bool = True, log_file: Optional[str] = None):
        """Initialize the LLM logger.

        Args:
            log_dir: Directory to store log files (defaults to ./.simple-agent/logs/llm)
            enabled: Whether logging is enabled
            log_file: Specific log file path (for resuming sessions). If None, creates a new file with timestamp.
        """
        self._enabled = enabled
        self._lock = Lock()

        if log_dir is None:
            log_dir = Path.cwd() / ".simple-agent" / "logs"

        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Use log_file if provided, otherwise create a timestamped file
        if log_file:
            self._log_file = Path(log_file)
        else:
            # Format: llm-YYYYMMDD-HHMMSS.jsonl
            now = datetime.now(timezone.utc)
            timestamp = now.strftime("%Y%m%d-%H%M%S")
            self._log_file = self._log_dir / f"llm-{timestamp}.jsonl"

    def log_request(
        self,
        request_id: str,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        subagent_call_id: Optional[str] = None,
        subagent_agent_name: Optional[str] = None,
    ) -> None:
        """Log an LLM API request.

        Args:
            request_id: Unique identifier for this request
            model: Model name being used
            messages: Message history sent to the API
            tools: Tools available to the LLM
            subagent_call_id: Unique identifier for subagent call (if this is a subagent request)
            subagent_agent_name: Name of the subagent (if this is a subagent request)
        """
        if not self._enabled:
            return

        entry = {
            "type": "request",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "messages": self._sanitize_messages(messages),
            "tools": tools if tools else [],
        }

        # Add subagent context if present
        if subagent_call_id:
            entry["subagent_call_id"] = subagent_call_id
        if subagent_agent_name:
            entry["subagent_agent_name"] = subagent_agent_name

        self._write_entry(entry)

    def log_response(
        self,
        request_id: str,
        content: Optional[str],
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        usage: Optional[Dict[str, int]] = None,
        finish_reason: Optional[str] = None,
        subagent_call_id: Optional[str] = None,
        subagent_agent_name: Optional[str] = None,
    ) -> None:
        """Log an LLM API response.

        Args:
            request_id: Unique identifier for the corresponding request
            content: Response content
            tool_calls: Tool calls made by the LLM
            usage: Token usage information
            finish_reason: Reason the response finished
            subagent_call_id: Unique identifier for subagent call (if this is a subagent response)
            subagent_agent_name: Name of the subagent (if this is a subagent response)
        """
        if not self._enabled:
            return

        entry = {
            "type": "response",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content": content,
            "tool_calls": tool_calls if tool_calls else [],
            "usage": usage,
            "finish_reason": finish_reason,
        }

        # Add subagent context if present
        if subagent_call_id:
            entry["subagent_call_id"] = subagent_call_id
        if subagent_agent_name:
            entry["subagent_agent_name"] = subagent_agent_name

        self._write_entry(entry)

    def log_tool_execution(
        self,
        request_id: str,
        tool_name: str,
        tool_call_id: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
        subagent_call_id: Optional[str] = None,
        subagent_agent_name: Optional[str] = None,
    ) -> None:
        """Log a tool execution.

        Args:
            request_id: Unique identifier for the associated request
            tool_name: Name of the tool being executed
            tool_call_id: ID of the tool call
            arguments: Arguments passed to the tool
            result: Result returned by the tool
            subagent_call_id: Unique identifier for subagent call (if this is a subagent tool call)
            subagent_agent_name: Name of the subagent (if this is a subagent tool call)
        """
        if not self._enabled:
            return

        entry = {
            "type": "tool_execution",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "arguments": arguments,
            "result": result,
        }

        # Add subagent context if present
        if subagent_call_id:
            entry["subagent_call_id"] = subagent_call_id
        if subagent_agent_name:
            entry["subagent_agent_name"] = subagent_agent_name

        self._write_entry(entry)

    def log_session_start(self, session_id: str) -> None:
        """Log a session start.

        Args:
            session_id: Unique identifier for this session
        """
        if not self._enabled:
            return

        entry = {
            "type": "session_start",
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._write_entry(entry)

    def log_skill_loaded(self, skill_name: str) -> None:
        """Log a skill being loaded.

        Args:
            skill_name: Name of the loaded skill
        """
        if not self._enabled:
            return

        entry = {
            "type": "SkillLoaded",
            "skill_name": skill_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._write_entry(entry)

    def log_agent_loaded(self, agent_name: str) -> None:
        """Log an agent being loaded.

        Args:
            agent_name: Name of the loaded agent
        """
        if not self._enabled:
            return

        entry = {
            "type": "AgentLoaded",
            "agent_name": agent_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._write_entry(entry)

    def log_subagent_invoked(self, agent_name: str, task: str) -> str:
        """Log a subagent being invoked.

        Args:
            agent_name: Name of the subagent
            task: The task/question for the subagent

        Returns:
            A unique subagent_call_id for tracking this subagent execution
        """
        subagent_call_id = str(uuid.uuid4())

        if not self._enabled:
            return subagent_call_id

        entry = {
            "type": "SubAgentInvoked",
            "subagent_call_id": subagent_call_id,
            "agent_name": agent_name,
            "task": task,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._write_entry(entry)
        return subagent_call_id

    def log_subagent_complete(self, subagent_call_id: str, agent_name: str, tool_calls_count: int, turns_used: int, success: bool) -> None:
        """Log a subagent execution complete.

        Args:
            subagent_call_id: Unique identifier for the subagent call
            agent_name: Name of the subagent
            tool_calls_count: Number of tool calls made
            turns_used: Number of conversation turns used
            success: Whether the subagent execution was successful
        """
        if not self._enabled:
            return

        entry = {
            "type": "SubAgentComplete",
            "subagent_call_id": subagent_call_id,
            "agent_name": agent_name,
            "tool_calls_count": tool_calls_count,
            "turns_used": turns_used,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._write_entry(entry)

    def log_hook_block(self, event_name: str, hook_name: str, message: str) -> None:
        """Log a hook blocking an event.

        Args:
            event_name: Name of the event being blocked
            hook_name: Name of the hook that blocked the event
            message: Block message from the hook
        """
        if not self._enabled:
            return

        entry = {
            "type": "hook_block",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_name": event_name,
            "hook_name": hook_name,
            "message": message,
        }

        self._write_entry(entry)

    def _write_entry(self, entry: Dict[str, Any]) -> None:
        """Write a log entry to the log file.

        Args:
            entry: The log entry to write
        """
        with self._lock:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    @staticmethod
    def _sanitize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sanitize messages for logging (remove sensitive data).

        Args:
            messages: Original messages

        Returns:
            Sanitized messages
        """
        sanitized = []
        for msg in messages:
            sanitized_msg = {
                "role": msg.get("role"),
                "content": msg.get("content", ""),
            }
            if "tool_calls" in msg:
                sanitized_msg["tool_calls"] = msg["tool_calls"]
            if "tool_call_id" in msg:
                sanitized_msg["tool_call_id"] = msg["tool_call_id"]
            sanitized.append(sanitized_msg)
        return sanitized

    @classmethod
    def generate_request_id(cls) -> str:
        """Generate a unique request ID.

        Returns:
            A unique request ID string
        """
        return str(uuid.uuid4())

    def get_log_file_path(self) -> Path:
        """Get the current log file path.

        Returns:
            Path to the current log file
        """
        return self._log_file


def parse_log_file(log_file: Path) -> List[Dict[str, Any]]:
    """Parse a log file into a list of entries.

    Args:
        log_file: Path to the log file

    Returns:
        List of log entries
    """
    entries = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def get_conversation(log_entries: List[Dict[str, Any]], request_id: str) -> Optional[Dict[str, Any]]:
    """Get a complete conversation by request ID.

    Args:
        log_entries: All log entries
        request_id: The request ID to look up

    Returns:
        Dictionary with the complete conversation or None
    """
    conversation = {
        "request_id": request_id,
        "request": None,
        "response": None,
        "tool_executions": [],
        "messages": []
    }

    for entry in log_entries:
        if entry.get("request_id") != request_id:
            continue

        if entry["type"] == "request":
            conversation["request"] = entry
        elif entry["type"] == "response":
            conversation["response"] = entry
        elif entry["type"] == "tool_execution":
            conversation["tool_executions"].append(entry)
        elif entry["type"] == "message":
            conversation["messages"].append({
                "role": entry.get("role"),
                "content": entry.get("content", ""),
                "tool_call_id": entry.get("tool_call_id"),
                "tool_calls": entry.get("tool_calls"),
            })
        elif entry["type"] == "SessionStart":
            conversation["session_id"] = entry.get("session_id")
        elif entry["type"] == "SkillLoaded":
            conversation.setdefault("skills_loaded", set()).add(entry.get("skill_name"))
        elif entry["type"] == "AgentLoaded":
            conversation.setdefault("agents_loaded", set()).add(entry.get("agent_name"))

    if conversation["request"] is None:
        return None

    return conversation


def get_all_conversations(log_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Get all parsed conversations from all log files.

    Args:
        log_dir: Optional log directory path (defaults to ./.simple-agent/logs/llm)

    Returns:
        List of all conversations with their requests, responses, and tool executions
    """
    if log_dir is None:
        log_dir = Path.cwd() / ".simple-agent" / "logs"
    else:
        log_dir = Path(log_dir)

    conversations = {}

    if log_dir.exists():
        for log_file in sorted(log_dir.glob("*.jsonl")):
            log_file_name = log_file.name  # Store log file name
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            entry = json.loads(line)

                            if entry["type"] == "request":
                                request_id = entry["request_id"]
                                if request_id not in conversations:
                                    conversations[request_id] = {
                                        "id": request_id,
                                        "timestamp": entry["timestamp"],
                                        "model": entry["model"],
                                        "request": entry,
                                        "response": None,
                                        "tool_executions": [],
                                        "messages": [],
                                        "session_id": None,
                                        "skills_loaded": set(),
                                        "agents_loaded": set(),
                                        "log_file": log_file_name,  # Add log file name
                                    }
                                else:
                                    conversations[request_id]["request"] = entry

                            elif entry["type"] == "response":
                                request_id = entry.get("request_id")
                                if request_id and request_id in conversations:
                                    conversations[request_id]["response"] = entry

                            elif entry["type"] == "tool_execution":
                                request_id = entry.get("request_id")
                                if request_id and request_id in conversations:
                                    conversations[request_id]["tool_executions"].append(entry)

                            elif entry["type"] == "message":
                                request_id = entry.get("request_id")
                                if request_id and request_id in conversations:
                                    conversations[request_id]["messages"].append({
                                        "role": entry.get("role"),
                                        "content": entry.get("content", ""),
                                        "tool_call_id": entry.get("tool_call_id"),
                                        "tool_calls": entry.get("tool_calls"),
                                    })

                            elif entry["type"] == "session_start":
                                session_id = entry.get("session_id")
                                if session_id and session_id not in conversations:
                                    conversations[session_id] = {
                                        "id": session_id,
                                        "timestamp": entry["timestamp"],
                                        "model": None,
                                        "request": None,
                                        "response": None,
                                        "tool_executions": [],
                                        "messages": [],
                                        "session_id": session_id,
                                        "skills_loaded": set(),
                                        "agents_loaded": set(),
                                    }

                            elif entry["type"] == "SkillLoaded":
                                request_id = entry.get("request_id")
                                if request_id and request_id in conversations:
                                    conversations[request_id].setdefault("skills_loaded", set()).add(entry.get("skill_name"))

                            elif entry["type"] == "AgentLoaded":
                                request_id = entry.get("request_id")
                                if request_id and request_id in conversations:
                                    conversations[request_id].setdefault("agents_loaded", set()).add(entry.get("agent_name"))

                        except (json.JSONDecodeError, KeyError):
                            continue

            except (IOError, OSError):
                continue

    # Filter out conversations without a request (keep only actual API calls)
    result = [conv for conv in conversations.values() if conv.get("request") is not None]

    # Convert sets to lists for JSON serialization
    for conv in result:
        if "skills_loaded" in conv:
            conv["skills_loaded"] = list(conv["skills_loaded"])
        if "agents_loaded" in conv:
            conv["agents_loaded"] = list(conv["agents_loaded"])

    # Sort by timestamp descending (use empty string if timestamp is None)
    result.sort(key=lambda x: x.get("timestamp", "") or "", reverse=True)
    return result
