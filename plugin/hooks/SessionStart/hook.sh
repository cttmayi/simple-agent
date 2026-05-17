#!/bin/bash
set -e

# 会话开始 Shell Hook - 记录到日志

INPUT_JSON=$(cat)
SESSION_ID=$(echo "$INPUT_JSON" | grep -o '"session_id"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')

LOG_FILE=".simple-agent/session.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Session started: $SESSION_ID" >> "$LOG_FILE"

# 放行
echo '{"decision": "allow"}'