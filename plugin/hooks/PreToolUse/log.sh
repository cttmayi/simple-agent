#!/bin/bash
set -e

# PreToolUse Shell Hook - 记录工具调用

INPUT_JSON=$(cat)

# 提取工具名称 (使用 tool 而不是 tool_name)
TOOL=$(echo "$INPUT_JSON" | grep -o '"tool"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')

LOG_FILE=".simple-agent/tools.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tool called: $TOOL" >> "$LOG_FILE"

cat <<EOF
{"decision": "allow"}
EOF