#!/bin/bash
set -e

# 记录用户发送的消息

LOG_FILE=".simple-agent/messages.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Message sent" >> "$LOG_FILE"

echo '{"decision": "allow"}'