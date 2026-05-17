#!/bin/bash
set -e

# ======================
# 官方标准 Hook 示例 (Bash)
# 1. 从 stdin 读取完整 JSON
# 2. 解析字段
# 3. 业务逻辑
# 4. 输出标准 JSON（只能输出这个！）
# ======================

INPUT_JSON=$(cat)

# 解析字段（使用 jq，如果没有 jq 可以用 grep/sed）
EVENT=$(echo "$INPUT_JSON" | grep -o '"event"[^,]*' | cut -d'"' -f4)
TOOL=$(echo "$INPUT_JSON" | grep -o '"tool"[^,}]*' | cut -d'"' -f4)

# ======================
# 业务逻辑
# ======================
if [ "$TOOL" = "Bash" ] && echo "$INPUT_JSON" | grep -q "rm -rf"; then
  # 拦截：输出标准 JSON
  cat <<EOF
{
  "decision": "block",
  "message": "❌ Hook 拦截：禁止使用 rm -rf 命令"
}
EOF
else
  # 放行
  cat <<EOF
{
  "decision": "allow"
}
EOF
fi