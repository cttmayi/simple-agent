"""
官方标准 Hook 示例 (Python)

标准流程：
1. 从 stdin 读取 JSON
2. 解析事件和 payload
3. 业务逻辑判断
4. 输出标准 JSON（decision/message/updatedInput/additionalContext）

返回字段：
- decision: "allow" | "block" (必填)
- message: CLI 显示内容 (可选)
- updatedInput: 修改事件数据 (可选)
- additionalContext: 追加给 LLM 的内容 (可选)
"""
import sys
import json

# ======================
# 1. 读取 stdin（官方固定）
# ======================
input_json = sys.stdin.read()
data = json.loads(input_json)

# ======================
# 2. 解析字段
# ======================
event = data.get("event")
payload = data.get("payload", {})

# PreToolUse/PostToolUse: tool, parameters
# UserPromptSubmit: userPrompt
tool = payload.get("tool", "")
parameters = payload.get("parameters", {})
user_prompt = payload.get("userPrompt", "")

# ======================
# 3. 业务逻辑
# ======================
if event == "PreToolUse":
    # 示例：拦截危险的 Bash 命令
    if tool == "Bash":
        command = parameters.get("command", "")
        if "rm -rf" in command or "del /f /s /q" in command:
            result = {
                "decision": "block",
                "message": "❌ Hook 拦截：禁止使用破坏性删除命令"
            }
        else:
            result = {
                "decision": "allow",
                "message": f"✅ Bash 命令执行: {command[:50]}..."
            }
    else:
        result = {"decision": "allow"}

elif event == "UserPromptSubmit":
    # 示例：为 LLM 添加上下文
    if "error" in user_prompt.lower():
        result = {
            "decision": "allow",
            "additionalContext": "用户提到了错误，优先检查日志和错误信息。"
        }
    else:
        result = {"decision": "allow"}

else:
    result = {"decision": "allow"}

# ======================
# 4. 输出 JSON（必须只输出这个！）
# ======================
print(json.dumps(result, ensure_ascii=False))