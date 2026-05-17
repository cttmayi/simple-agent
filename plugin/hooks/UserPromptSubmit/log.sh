#!/bin/bash
set -e

# 显示消息发送日志

INPUT_JSON=$(cat)

# 从JSON中提取content（简单处理）
CONTENT=$(echo "$INPUT_JSON" | grep -o '"content"[^,}]*' | sed 's/.*: *"\([^"]*\)".*/\1/')
CONTENT=${CONTENT:0:50}  # 只显示前50个字符

echo "{\"decision\": \"allow\", \"message\": \"📤 发送消息: $CONTENT...\"}"