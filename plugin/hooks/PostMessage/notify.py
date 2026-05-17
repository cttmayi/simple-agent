#!/usr/bin/env python3
"""PostMessage Hook - 收到AI响应时记录 - 官方 stdin/stdout JSON 协议"""

import sys
import json

# 读取 stdin
input_json = sys.stdin.read()
data = json.loads(input_json)

# 解析字段
payload = data.get("payload", {})
role = payload.get("role", "unknown")
user_prompt = payload.get("userPrompt", "")

# 输出JSON
result = {
    "decision": "allow",
    "message": f"📥 收到 {role} 响应"
}

print(json.dumps(result, ensure_ascii=False))