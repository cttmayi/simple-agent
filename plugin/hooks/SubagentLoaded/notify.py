#!/usr/bin/env python3
"""SubagentLoaded Hook - 记录 - 官方 stdin/stdout JSON 协议"""

import sys
import json

# 读取 stdin
input_json = sys.stdin.read()
data = json.loads(input_json)

# 解析字段 - 使用 agentName (驼峰命名)
payload = data.get("payload", {})
agent_name = payload.get("agentName", "unknown")

# 输出JSON
result = {
    "decision": "allow",
    "message": f"✓ Subagent 已加载: {agent_name}"
}

print(json.dumps(result, ensure_ascii=False))