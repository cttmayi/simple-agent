#!/bin/bash
# 记录发送的消息 - message_sent Shell Hook 示例

LOG_FILE=".simple-agent/messages.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Message sent" >> "$LOG_FILE"
