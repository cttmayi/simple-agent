#!/bin/bash
# 记录工具调用 - tool_call_before Shell Hook 示例

LOG_FILE=".simple-agent/tools.log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Tool called" >> "$LOG_FILE"
