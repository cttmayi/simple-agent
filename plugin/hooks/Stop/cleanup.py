#!/usr/bin/env python3
"""会话结束时显示摘要"""

def Stop(session_id: str, hook_context) -> None:
    """会话结束时显示统计摘要"""
    summary = hook_context.summary()
    print(f"\n📊 会话摘要")
    print(f"  消息: 发送 {summary['messages']['sent']}, 接收 {summary['messages']['received']}")
    print(f"  工具: 调用 {summary['tools']['called']}, 成功 {summary['tools']['succeeded']}, 失败 {summary['tools']['failed']}")