#!/usr/bin/env python3
"""UserPromptSubmit Hook - 记录用户发送的消息 - 官方 stdin/stdout JSON 协议"""

import sys
import json

# 读取 stdin
input_json = sys.stdin.read()
data = json.loads(input_json)

# 解析字段 - 使用 userPrompt
payload = data.get("payload", {})
user_prompt = payload.get("userPrompt", "")

# 记录到日志文件
import os
LOG_FILE = ".simple-agent/messages.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# 截取内容
short_content = user_prompt[:100] + "..." if len(user_prompt) > 100 else user_prompt

with open(LOG_FILE, "a") as f:
    from datetime import datetime
    f.write(f"[{datetime.now()}] user: {short_content}\n")

# 输出JSON
result = {
    "decision": "allow"
}

print(json.dumps(result, ensure_ascii=False))