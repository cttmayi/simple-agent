from simple_agent.core.events import EventBus, Event


def test_event_creation():
    event = Event(name="test_event", data={"key": "value"})
    assert event.name == "test_event"
    assert event.data == {"key": "value"}


def test_event_bus_subscribe():
    bus = EventBus()
    called = []

    def handler(event: Event):
        called.append(event)

    bus.subscribe("test_event", handler)
    bus.publish(Event(name="test_event", data={}))
    assert len(called) == 1


def test_event_bus_unsubscribe():
    bus = EventBus()
    called = []

    def handler(event: Event):
        called.append(event)

    bus.subscribe("test_event", handler)
    bus.unsubscribe("test_event", handler)
    bus.publish(Event(name="test_event", data={}))
    assert len(called) == 0


def test_event_bus_multiple_handlers():
    bus = EventBus()
    results = []

    def handler1(event: Event):
        results.append("handler1")

    def handler2(event: Event):
        results.append("handler2")

    bus.subscribe("test_event", handler1)
    bus.subscribe("test_event", handler2)
    bus.publish(Event(name="test_event", data={}))
    assert results == ["handler1", "handler2"]


def test_event_bus_handler_exception():
    bus = EventBus()
    called = []

    def failing_handler(event: Event):
        raise Exception("Handler failed")

    def working_handler(event: Event):
        called.append(event)

    bus.subscribe("test_event", failing_handler)
    bus.subscribe("test_event", working_handler)
    bus.publish(Event(name="test_event", data={}))
    assert len(called) == 1  # Handler exception shouldn't stop other handlers
