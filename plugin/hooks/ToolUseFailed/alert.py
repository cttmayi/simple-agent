#!/usr/bin/env python3
"""工具调用失败时记录错误 - 官方 stdin/stdout JSON 协议"""

import sys
import json

# 读取 stdin
input_json = sys.stdin.read()
data = json.loads(input_json)

# 解析字段
payload = data.get("payload", {})
tool_name = payload.get("tool_name", "unknown")
error = payload.get("error", "unknown error")

# 记录到日志文件
import os
LOG_FILE = ".simple-agent/errors.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

with open(LOG_FILE, "a") as f:
    from datetime import datetime
    f.write(f"[{datetime.now()}] Tool {tool_name} failed: {error[:100]}\n")

# 输出JSON
result = {
    "decision": "allow",
    "message": f"⚠️ 工具失败: {tool_name}"
}

print(json.dumps(result, ensure_ascii=False))