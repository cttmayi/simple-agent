#!/bin/bash
set -e

# SessionStart Shell Hook - 显示欢迎消息

INPUT_JSON=$(cat)

# 从session中提取session_id
SESSION_ID=$(echo "$INPUT_JSON" | grep -o '"id"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')
SHORT_ID=${SESSION_ID:0:8}

# 显示欢迎消息
echo "{"decision": "allow", "message": "🚀 会话已启动! ID: $SHORT_ID"}"