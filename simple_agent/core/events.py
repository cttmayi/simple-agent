from typing import Callable, Dict, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Event:
    name: str
    data: dict


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
