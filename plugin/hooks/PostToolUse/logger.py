#!/usr/bin/env python3
"""记录工具调用结果 - 官方 stdin/stdout JSON 协议"""

import sys
import json

# 读取 stdin
input_json = sys.stdin.read()
data = json.loads(input_json)

# 解析字段
payload = data.get("payload", {})
tool_name = payload.get("tool_name", "unknown")
result = payload.get("result", {})
success = result.get("success", True)

# 输出日志
LOG_FILE = ".simple-agent/tools.log"
import os
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

with open(LOG_FILE, "a") as f:
    from datetime import datetime
    status = "✓" if success else "✗"
    f.write(f"[{datetime.now()}] Tool: {tool_name} {status}\n")

# 放行
output = {"decision": "allow"}
print(json.dumps(output, ensure_ascii=False))