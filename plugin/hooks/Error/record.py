#!/usr/bin/env python3
"""记录运行时错误 - 官方 stdin/stdout JSON 协议"""

import sys
import json

# 读取 stdin
input_json = sys.stdin.read()
data = json.loads(input_json)

# 解析字段
payload = data.get("payload", {})
error_type = payload.get("error_type", "unknown")
error_message = payload.get("error_message", "")

# 记录到日志文件
import os
LOG_FILE = ".simple-agent/errors.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

with open(LOG_FILE, "a") as f:
    from datetime import datetime
    f.write(f"[{datetime.now()}] {error_type}: {error_message[:200]}\n")

# 输出JSON
result = {
    "decision": "allow",
    "message": f"❌ 错误: {error_type}"
}

print(json.dumps(result, ensure_ascii=False))