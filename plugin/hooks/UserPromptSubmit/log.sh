#!/bin/bash
set -e

# UserPromptSubmit Shell Hook - 显示消息发送日志

INPUT_JSON=$(cat)

# 从payload中提取userPrompt（而不是content）
USER_PROMPT=$(echo "$INPUT_JSON" | grep -o '"userPrompt"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')
USER_PROMPT=${USER_PROMPT:0:50}  # 只显示前50个字符

echo "{"decision": "allow", "message": "📤 发送消息: $USER_PROMPT..."}"