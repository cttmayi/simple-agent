from simple_agent.core.session import Session

def test_session_add_message():
    session = Session()
    session.add_message("user", "Hello")
    messages = session.get_messages()
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"

def test_session_get_context():
    session = Session()
    session.add_message("user", "Hello")
    session.add_message("assistant", "Hi there!")
    context = session.get_context()
    assert "Hello" in context
    assert "Hi there!" in context

def test_session_clear():
    session = Session()
    session.add_message("user", "Hello")
    session.clear()
    messages = session.get_messages()
    assert len(messages) == 0
