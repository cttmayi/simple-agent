#!/bin/bash
set -e

# SessionStart Shell Hook - 记录到日志

INPUT_JSON=$(cat)

# 从session中提取session_id
SESSION_ID=$(echo "$INPUT_JSON" | grep -o '"id"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')

LOG_FILE=".simple-agent/session.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Session started: $SESSION_ID" >> "$LOG_FILE"

# 放行
echo '{"decision": "allow"}'