#!/usr/bin/env python3
"""UserPromptSubmit Hook - 注入代码开发指导到 LLM"""

import sys
import json

# 读取 stdin
input_json = sys.stdin.read()
data = json.loads(input_json)

# 解析 payload
payload = data.get("payload", {})
user_prompt = payload.get("userPrompt", "")

# 检查是否需要注入（例如，用户提到了"代码"或"Python"）
keywords = ["代码", "Python", "函数", "类", "bug", "调试", "实现", "写一个", "帮我写"]
need_injection = any(keyword in user_prompt for keyword in keywords)

if need_injection:
    # 注入系统提示词
    additional_context = """## 代码开发指导原则

请遵循以下原则回答用户关于代码的问题：

1. **代码质量**
   - 使用有意义的变量名和函数名
   - 添加必要的注释和文档字符串
   - 遵循 PEP 8 代码风格规范

2. **最佳实践**
   - 使用 try-except 处理可能的异常
   - 避免硬编码魔法数字，使用常量
   - 优先使用列表推导式和生成器表达式

3. **调试建议**
   - 建议使用 print() 或 logging 模块调试
   - 推荐使用 pytest 进行单元测试
   - 解释问题时提供完整的错误堆栈

请根据以上原则提供代码建议。
"""

    output = {
        "additionalContext": additional_context
    }
    print(json.dumps(output, ensure_ascii=False))
else:
    # 不需要注入，只返回 allow
    print(json.dumps({"decision": "allow"}))