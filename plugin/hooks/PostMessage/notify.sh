#!/bin/bash
set -e

# 收到AI响应通知

INPUT_JSON=$(cat)

# 提取content
CONTENT=$(echo "$INPUT_JSON" | grep -o '"content"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')
CONTENT=${CONTENT:0:30}

echo "{\"decision\": \"allow\", \"message\": \"📥 收到 AI 响应: $CONTENT...\"}"