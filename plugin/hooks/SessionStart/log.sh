#!/bin/bash
set -e

# 会话开始 Shell Hook - 显示欢迎消息

INPUT_JSON=$(cat)
SESSION_ID=$(echo "$INPUT_JSON" | grep -o '"session_id"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')

SHORT_ID=${SESSION_ID:0:8}

# 显示欢迎消息
echo "{\"decision\": \"allow\", \"message\": \"🚀 会话已启动! ID: $SHORT_ID\"}"