#!/bin/bash
set -e

# Stop Shell Hook - 会话结束

INPUT_JSON=$(cat)

# 从session中提取session_id
SESSION_ID=$(echo "$INPUT_JSON" | grep -o '"id"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')
SHORT_ID=${SESSION_ID:0:8}

echo "{"decision": "allow", "message": "👋 会话结束于 $(date '+%H:%M:%S') (ID: $SHORT_ID)"}"