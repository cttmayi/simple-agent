#!/bin/bash
# 记录会话开始 - session_start Shell Hook 示例

LOG_FILE=".simple-agent/session.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Session started" >> "$LOG_FILE"
