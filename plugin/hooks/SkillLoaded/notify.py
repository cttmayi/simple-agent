#!/usr/bin/env python3
"""Skill 加载时记录 - 官方 stdin/stdout JSON 协议"""

import sys
import json

# 读取 stdin
input_json = sys.stdin.read()
data = json.loads(input_json)

# 解析字段
payload = data.get("payload", {})
skill_name = payload.get("skill_name", "unknown")

# 输出JSON
result = {
    "decision": "allow",
    "message": f"✓ Skill 已加载: {skill_name}"
}

print(json.dumps(result, ensure_ascii=False))