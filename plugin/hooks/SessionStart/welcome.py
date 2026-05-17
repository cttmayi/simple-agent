#!/usr/bin/env python3
"""会话开始时显示欢迎消息 - 官方 stdin/stdout JSON 协议"""

import sys
import json

# 读取 stdin
input_json = sys.stdin.read()
data = json.loads(input_json)

# 解析字段
session_id = data.get("payload", {}).get("session_id", "unknown")
short_id = session_id[:8] if len(session_id) > 8 else session_id

# 输出 JSON
result = {
    "decision": "allow",
    "message": f"🚀 会话已启动! ID: {short_id}"
}

print(json.dumps(result, ensure_ascii=False))