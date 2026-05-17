#!/bin/bash
set -e

# UserPromptSubmit Shell Hook - 记录用户发送的消息

INPUT_JSON=$(cat)

# 从payload中提取userPrompt
USER_PROMPT=$(echo "$INPUT_JSON" | grep -o '"userPrompt"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')

LOG_FILE=".simple-agent/messages.log"
mkdir -p "$(dirname "$LOG_FILE")"

# 记录到日志
echo "[$(date '+%Y-%m-%d %H:%M:%S')] User: $USER_PROMPT" >> "$LOG_FILE"

cat <<EOF
{"decision": "allow"}
EOF