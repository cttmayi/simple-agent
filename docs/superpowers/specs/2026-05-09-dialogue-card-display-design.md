# 对话卡片显示设计

**日期:** 2026-05-09
**作者:** Claude
**状态:** 已批准

## 概述

重新设计Web日志分析器，以卡片形式显示对话，按日志文件组织。每个API调用显示为一个卡片，包含摘要视图和可展开的详细信息。

## 需求

1. **按日志文件组织** - 同一日志文件的对话分组显示
2. **卡片式显示** - 每个API调用（request/response/tool_execution）显示为一张卡片
3. **摘要视图** - 卡片显示关键信息概览
4. **可展开详情** - 点击卡片显示结构化的完整信息
5. **Usage显示** - Response卡片在摘要中显示token使用情况

## 设计

### 两级结构

**第一级：日志文件组**
- 显示日志文件名称和API调用总数
- 点击展开/收起该组下的所有卡片

**第二级：API调用卡片**
- 显示request、response、tool_execution的摘要
- 点击展开/收起详细信息视图

### 卡片摘要

每张卡片显示：
- **标题**: 模型名称 + 时间戳
- **Request摘要**: `[REQUEST]` 徽章 + 最后一条user消息预览
- **Response摘要**: `[RESPONSE]` 徽章 + 时间戳 + **usage信息** + tool数量
- **Tool摘要**: `[TOOL]` 徽章列表（如果有多个工具调用）

**Usage显示格式:**
```
📤 [RESPONSE] 18:16:05 | 1500 tokens (500 + 1000) | 2 tools
                        总计    prompt  completion
```

### 展开视图

展开后，每张卡片显示结构化区块：

**Request区块**
- 完整的messages数组
- 每条消息显示role和content
- 可折叠

**Response区块**
- 完整的content
- Usage明细（prompt + completion + total）
- Tool calls列表（名称+参数）
- 每个tool call可折叠显示详细参数

**Tool Execution区块**
- 工具名称和调用ID
- 完整的result对象
- JSON格式化显示
- 错误时红色高亮

### 交互

- 点击卡片头部：展开/收起整个卡片
- 点击区块头部：展开/收起单个区块
- 双击：快速展开/收起

## 数据流

1. `get_all_conversations()` 返回按日志文件分组的对话
2. 前端通过 `log_file` 字段分组
3. 每个组渲染一个会话头部和对应的卡片
4. 每张卡片默认渲染摘要视图
5. 点击后展开显示结构化区块

## 实施说明

- 复用现有的 `groupConversationsByLog()` 函数
- 修改 `renderConversations()` 使用卡片布局
- 添加新的 `renderCardSummary()` 和 `renderCardDetails()` 函数
- 添加卡片样式和动画的CSS
- 保持现有的消息去重逻辑