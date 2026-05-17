#!/bin/bash
set -e

# 记录工具调用

INPUT_JSON=$(cat)

LOG_FILE=".simple-agent/tools.log"
mkdir -p "$(dirname "$LOG_FILE")"

# 提取工具名称
TOOL=$(echo "$INPUT_JSON" | grep -o '"tool_name"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tool called: $TOOL" >> "$LOG_FILE"

echo '{"decision": "allow"}'