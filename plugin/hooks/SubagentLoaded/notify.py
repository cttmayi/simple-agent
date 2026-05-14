#!/usr/bin/env python3
"""Subagent 加载时记录"""

def SubagentLoaded(subagent_name: str, hook_context) -> None:
    """记录已加载的 Subagent"""
    print(f"✓ Subagent 已加载: {subagent_name}")