#!/bin/bash
set -e

# 会话结束清理

INPUT_JSON=$(cat)
SESSION_ID=$(echo "$INPUT_JSON" | grep -o '"session_id"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')
SHORT_ID=${SESSION_ID:0:8}  # 只取前8位

echo "{"decision": "allow", "message": "👋 会话结束于 $(date '+%H:%M:%S') (ID: $SHORT_ID)"}"