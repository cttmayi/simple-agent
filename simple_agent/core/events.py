from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Event:
    name: str
    data: dict


class HookBlockedException(Exception):
    """Hook blocked execution."""
    pass


class HookContext:
    """Shared context for all hooks - allows direct variable sharing without files.

    This singleton object is initialized at session start and can be accessed
    by all hooks to share state without needing file I/O.
    """
    _instance: Optional['HookContext'] = None

    def __new__(cls) -> 'HookContext':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.session_id: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self._custom_data: Dict[str, Any] = {}

        # Built-in counters
        self.messages_sent = 0
        self.messages_received = 0
        self.tools_called = 0
        self.tools_succeeded = 0
        self.tools_failed = 0

        # Built-in collections
        self.user_messages: List[Dict[str, Any]] = []
        self.assistant_messages: List[Dict[str, Any]] = []
        self.tools_used: List[Dict[str, Any]] = []
        self.keywords: List[str] = []
        self.errors: List[Dict[str, Any]] = []

        self._initialized = True

    def reset(self, session_id: str) -> None:
        """Reset context for a new session."""
        self.session_id = session_id
        self.start_time = datetime.now()

        self.messages_sent = 0
        self.messages_received = 0
        self.tools_called = 0
        self.tools_succeeded = 0
        self.tools_failed = 0

        self.user_messages = []
        self.assistant_messages = []
        self.tools_used = []
        self.keywords = []
        self.errors = []
        self._custom_data = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a custom value from the shared context."""
        return self._custom_data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a custom value in the shared context."""
        self._custom_data[key] = value

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter value."""
        current = self.get(key, 0)
        new_value = current + amount
        self.set(key, new_value)
        return new_value

    def append(self, key: str, value: Any, max_items: Optional[int] = None) -> None:
        """Append a value to a list in the shared context."""
        if not isinstance(value, list):
            value = [value]

        items = self.get(key, [])
        items.extend(value)

        if max_items and len(items) > max_items:
            items = items[-max_items:]

        self.set(key, items)

    def summary(self) -> Dict[str, Any]:
        """Get a summary of the shared context."""
        duration = None
        if self.start_time:
            duration = str(datetime.now() - self.start_time)

        return {
            "session_id": self.session_id,
            "duration": duration,
            "messages": {
                "sent": self.messages_sent,
                "received": self.messages_received,
            },
            "tools": {
                "called": self.tools_called,
                "succeeded": self.tools_succeeded,
                "failed": self.tools_failed,
                "used": [t["tool"] for t in self.tools_used],
            },
            "keywords": self.keywords,
            "custom_data": self._custom_data.copy(),
        }


class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable[[Event], None]]] = {}

    def subscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """Subscribe a handler to an event."""
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """Unsubscribe a handler from an event."""
        if event_name in self._handlers:
            try:
                self._handlers[event_name].remove(handler)
            except ValueError:
                pass

    def publish(self, event: Event) -> None:
        """Publish an event to all subscribed handlers."""
        handlers = self._handlers.get(event.name, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in handler for event {event.name}: {e}")
