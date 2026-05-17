#!/usr/bin/env python3
"""会话结束时显示摘要 - 官方 stdin/stdout JSON 协议"""

import sys
import json

# 读取 stdin
input_json = sys.stdin.read()
data = json.loads(input_json)

# 解析字段
session_id = data.get("payload", {}).get("session_id", "unknown")

# 构建会话摘要消息（从日志文件读取统计信息）
import os
tools_log = ".simple-agent/tools.log"
messages_log = ".simple-agent/messages.log"

tools_called = 0
if os.path.exists(tools_log):
    with open(tools_log) as f:
        tools_called = len(f.readlines())

messages_sent = 0
if os.path.exists(messages_log):
    with open(messages_log) as f:
        messages_sent = len(f.readlines())

# 输出JSON
result = {
    "decision": "allow",
    "message": f"\n📊 会话摘要: 消息 {messages_sent}, 工具调用 {tools_called}"
}

print(json.dumps(result, ensure_ascii=False))