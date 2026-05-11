#!/usr/bin/env python
"""Example session_start hook - displays a greeting message."""

def on_session_start(session_id: str) -> None:
    """Called when session starts.

    Args:
        session_id: The session ID
    """
    print(f"🚀 Session {session_id[:8]} started!")
