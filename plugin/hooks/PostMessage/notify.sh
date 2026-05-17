#!/bin/bash
set -e

# PostMessage Shell Hook - 收到AI响应通知

INPUT_JSON=$(cat)

# 从payload中提取userPrompt
USER_PROMPT=$(echo "$INPUT_JSON" | grep -o '"userPrompt"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')
USER_PROMPT=${USER_PROMPT:0:30}

echo "{"decision": "allow", "message": "📥 收到 AI 响应: $USER_PROMPT..."}"