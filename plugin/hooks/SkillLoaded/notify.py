#!/usr/bin/env python3
"""Skill 加载时记录"""

def SkillLoaded(skill_name: str, hook_context) -> None:
    """记录已加载的 Skill"""
    print(f"✓ Skill 已加载: {skill_name}")