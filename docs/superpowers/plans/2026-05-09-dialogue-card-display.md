# 对话卡片显示实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 重新设计Web日志分析器，以两级卡片结构显示对话（日志文件组 + API调用卡片）

**架构:** 保持现有的Flask后端，完全重构analyzer.html的前端显示逻辑。使用JavaScript实现卡片渲染和交互。

**技术栈:** HTML, CSS (内联), JavaScript (原生), Flask (后端)

---

## 文件结构

**修改的文件:**
- `simple_agent/web/analyzer.html` - 包含所有前端代码（HTML、CSS、JavaScript）

## 任务分解

### Task 1: 添加卡片样式CSS

**文件:**
- Modify: `simple_agent/web/analyzer.html` (在 `<style>` 标签内)

- [ ] **Step 1: 在 `.conversation-body.active` 样式后添加卡片相关样式**

```css
/* 卡片摘要样式 */
.card-summary {
    padding: 15px 20px;
    cursor: pointer;
    border-left: 4px solid #667eea;
    transition: background 0.2s;
}

.card-summary:hover {
    background: #1a253a;
}

.card-summary-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.card-summary-title {
    font-weight: bold;
    font-size: 1.1em;
    color: #eaeaea;
}

.card-summary-meta {
    color: #888;
    font-size: 0.85em;
}

.card-summary-section {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
    font-size: 0.9em;
}

.card-summary-section:last-child {
    margin-bottom: 0;
}

/* 卡片详情样式 */
.card-details {
    display: none;
    padding: 0 20px 20px 20px;
    border-top: 1px solid #333;
}

.card-details.active {
    display: block;
}

/* 详情区块样式 */
.detail-section {
    margin-top: 15px;
    background: #0f1f2e;
    border-radius: 6px;
    overflow: hidden;
}

.detail-section-header {
    background: #1a2a3a;
    padding: 10px 15px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: bold;
    font-size: 0.9em;
}

.detail-section-header:hover {
    background: #253545;
}

.detail-section-content {
    display: none;
    padding: 15px;
}

.detail-section-content.active {
    display: block;
}

/* Usage显示样式 */
.usage-display {
    background: #0a0a1a;
    padding: 8px 12px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.85em;
    color: #667eea;
}

/* 卡片容器样式 */
.api-call-card {
    background: #16213e;
    border-radius: 8px;
    margin-bottom: 15px;
    border: 1px solid #333;
    overflow: hidden;
}

.api-call-card:last-child {
    margin-bottom: 0;
}
```

- [ ] **Step 2: 提交样式更改**

```bash
git add simple_agent/web/analyzer.html
git commit -m "style: add card display CSS styles

- Add card summary and details styles
- Add detail section styles with collapsible headers
- Add usage display styling

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: 添加卡片渲染辅助函数

**文件:**
- Modify: `simple_agent/web/analyzer.html` (在 `<script>` 标签内)

- [ ] **Step 1: 在 `escapeHtml` 函数后添加卡片渲染辅助函数**

```javascript
// 渲染卡片摘要
function renderCardSummary(conv) {
    const request = conv.request;
    const response = conv.response;
    const toolExecutions = conv.tool_executions || [];

    // 获取最后一条user消息
    let userMessage = '';
    if (request.messages) {
        const userMsgs = request.messages.filter(m => m.role === 'user');
        if (userMsgs.length > 0) {
            const lastUserMsg = userMsgs[userMsgs.length - 1].content || '';
            userMessage = lastUserMsg.length > 50 ? lastUserMsg.substring(0, 50) + '...' : lastUserMsg;
        }
    }

    // 获取response内容预览和usage
    let responsePreview = '';
    let usageDisplay = '';
    let toolCount = 0;

    if (response) {
        const content = response.content || '';
        responsePreview = content.length > 50 ? content.substring(0, 50) + '...' : content;

        // Usage显示
        const usage = response.usage || {};
        const totalTokens = usage.total_tokens || 0;
        const promptTokens = usage.prompt_tokens || 0;
        const completionTokens = usage.completion_tokens || 0;

        if (totalTokens > 0) {
            usageDisplay = `<span class="usage-display">| ${totalTokens} tokens (${promptTokens} + ${completionTokens})</span>`;
        }

        toolCount = (response.tool_calls || []).length;
    }

    // Tool摘要
    let toolSummary = '';
    if (toolExecutions.length > 0) {
        const toolBadges = toolExecutions.map(te => {
            const status = te.result?.success ? 'OK' : 'ERR';
            return `<span class="badge ${te.result?.success ? 'response' : 'error'}">🔧 ${escapeHtml(te.tool_name)} (${status})</span>`;
        }).join(' ');
        toolSummary = `<div class="card-summary-section">${toolBadges}</div>`;
    }

    return `
        <div class="card-summary" onclick="toggleCard(this)">
            <div class="card-summary-header">
                <span class="card-summary-title">📄 API Call: ${escapeHtml(request.model || 'unknown')}</span>
                <span class="card-summary-meta">${new Date(request.timestamp).toLocaleString()}</span>
            </div>
            ${userMessage ? `
                <div class="card-summary-section">
                    <span class="badge request">📄 [REQUEST]</span>
                    <span style="color: #aaa;">${escapeHtml(userMessage)}</span>
                </div>
            ` : ''}
            ${response ? `
                <div class="card-summary-section">
                    <span class="badge response">📤 [RESPONSE]</span>
                    <span style="color: #aaa;">${escapeHtml(responsePreview)}</span>
                    ${usageDisplay}
                    ${toolCount > 0 ? `<span class="badge tool">| ${toolCount} tools</span>` : ''}
                </div>
            ` : ''}
            ${toolSummary}
        </div>
    `;
}

// 渲染卡片详情
function renderCardDetails(conv) {
    const request = conv.request;
    const response = conv.response;
    const toolExecutions = conv.tool_executions || [];

    let sections = '';

    // Request区块
    if (request && request.messages) {
        sections += `
            <div class="detail-section">
                <div class="detail-section-header" onclick="toggleSection(this)">
                    <span>📄 Request</span>
                    <span>▼</span>
                </div>
                <div class="detail-section-content active">
                    ${request.messages.map(msg => `
                        <div class="message ${msg.role}">
                            <div class="message-header">
                                <span class="message-role">${msg.role}</span>
                            </div>
                            <div class="message-content">${escapeHtml(msg.content || '(no content)')}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Response区块
    if (response) {
        const toolCalls = response.tool_calls || [];
        const usage = response.usage || {};

        sections += `
            <div class="detail-section">
                <div class="detail-section-header" onclick="toggleSection(this)">
                    <span>📤 Response</span>
                    <span>▼</span>
                </div>
                <div class="detail-section-content active">
                    ${response.content ? `
                        <div style="margin-bottom: 15px;">
                            <div style="color: #888; font-size: 0.85em; margin-bottom: 5px;">Content:</div>
                            <div class="message-content">${escapeHtml(response.content)}</div>
                        </div>
                    ` : ''}

                    <div style="margin-bottom: 15px;">
                        <div style="color: #888; font-size: 0.85em; margin-bottom: 5px;">Usage:</div>
                        <div class="usage-display">
                            ${usage.total_tokens || 0} total (${usage.prompt_tokens || 0} prompt + ${usage.completion_tokens || 0} completion)
                        </div>
                    </div>

                    ${toolCalls.length > 0 ? `
                        <div style="margin-bottom: 15px;">
                            <div style="color: #888; font-size: 0.85em; margin-bottom: 5px;">Tool Calls (${toolCalls.length}):</div>
                            ${toolCalls.map((tc, i) => `
                                <div class="detail-section" style="margin-top: 10px;">
                                    <div class="detail-section-header" onclick="toggleSection(this)">
                                        <span>→ ${escapeHtml(tc.function.name)}</span>
                                        <span>▼</span>
                                    </div>
                                    <div class="detail-section-content">
                                        <div class="tool-arguments">${renderArguments(tc.function.arguments)}</div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    // Tool Execution区块
    if (toolExecutions.length > 0) {
        sections += `
            <div class="detail-section">
                <div class="detail-section-header" onclick="toggleSection(this)">
                    <span>🔧 Tool Executions (${toolExecutions.length})</span>
                    <span>▼</span>
                </div>
                <div class="detail-section-content active">
                    ${toolExecutions.map(te => `
                        <div class="message tool">
                            <div class="message-header">
                                <span class="message-role">← ${escapeHtml(te.tool_name)}</span>
                                <span class="badge ${te.result?.success ? 'response' : 'error'}">
                                    ${te.result?.success ? 'OK' : 'Error'}
                                </span>
                            </div>
                            <div class="tool-result ${te.result?.success ? 'success' : 'error'}">
                                ${te.result?.error || renderResultContent(te.result || {})}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    return `<div class="card-details">${sections}</div>`;
}

// 切换卡片展开/收起
function toggleCard(element) {
    const card = element.parentElement;
    const details = card.querySelector('.card-details');
    details.classList.toggle('active');
}

// 切换详情区块展开/收起
function toggleSection(element) {
    const content = element.nextElementSibling;
    content.classList.toggle('active');
    const arrow = element.querySelector('span:last-child');
    arrow.textContent = content.classList.contains('active') ? '▼' : '▶';
}
```

- [ ] **Step 2: 提交辅助函数**

```bash
git add simple_agent/web/analyzer.html
git commit -m "feat: add card rendering helper functions

- Add renderCardSummary for card summary display
- Add renderCardDetails for detailed view
- Add toggleCard and toggleSection functions
- Include usage display with token breakdown

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: 修改renderConversations使用卡片布局

**文件:**
- Modify: `simple_agent/web/analyzer.html` (替换现有的 `renderConversations` 函数)

- [ ] **Step 1: 替换 `renderConversations` 函数**

```javascript
function renderConversations(conversations) {
    const container = document.getElementById('conversations-container');
    const emptyState = document.getElementById('empty-state');

    if (conversations.length === 0) {
        container.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';

    const groups = groupConversationsByLog(conversations);
    let globalIndex = 0;

    container.innerHTML = groups.map((group, groupIndex) => {
        const idx = globalIndex++;
        const cardsHtml = group.conversations.map((conv, convIndex) => `
            <div class="api-call-card">
                ${renderCardSummary(conv)}
                ${renderCardDetails(conv)}
            </div>
        `).join('');

        return `
            <div class="session-group">
                <div class="session-header" onclick="toggleSession(${idx})">
                    <div class="info">
                        <div class="log-file">📁 ${escapeHtml(group.log_file)}</div>
                        <div style="margin-top: 5px; color: #888; font-size: 0.9em;">
                            ${group.conversations.length} API call${group.conversations.length > 1 ? 's' : ''}
                        </div>
                    </div>
                    <div class="conv-count">${group.conversations.length}</div>
                </div>
                <div class="session-body" id="session-${idx}">
                    ${cardsHtml}
                </div>
            </div>
        `;
    }).join('');
}
```

- [ ] **Step 2: 删除不再需要的函数**

```javascript
// 删除这些函数（在Task 2中已被新函数替代）:
// - buildDialogue
// - renderDialogue
// - renderAssistantMessage
// - renderToolMessage
// - isDuplicateMessage
```

- [ ] **Step 3: 提交更改**

```bash
git add simple_agent/web/analyzer.html
git commit -m "refactor: use card layout for conversations

- Replace renderConversations with card-based layout
- Each conversation now renders as a card with summary and details
- Remove obsolete dialogue rendering functions

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: 测试并验证功能

**文件:**
- No file changes (manual testing)

- [ ] **Step 1: 重启Web服务器**

```bash
lsof -ti:5001 | xargs kill -9 2>/dev/null
.venv/bin/python -m simple_agent.web.server --port 5001
```

- [ ] **Step 2: 在浏览器中打开 http://localhost:5001**

- [ ] **Step 3: 验证卡片摘要显示**
  - 检查每个日志文件组显示正确
  - 检查每张卡片显示模型名称和时间戳
  - 检查Request摘要显示最后一条user消息
  - 检查Response摘要显示usage信息（格式：| 1500 tokens (500 + 1000)）
  - 检查Tool摘要显示工具名称和状态

- [ ] **Step 4: 验证卡片展开功能**
  - 点击卡片摘要，验证详情展开
  - 检查Request区块显示完整messages
  - 检查Response区块显示content、usage和tool_calls
  - 检查Tool Execution区块显示所有工具执行结果
  - 再次点击卡片摘要，验证详情收起

- [ ] **Step 5: 验证详情区块折叠功能**
  - 点击区块标题，验证区块折叠/展开
  - 检查箭头图标正确切换（▼/▶）

- [ ] **Step 6: 验证双击功能（可选）**
  - 测试双击卡片头部是否快速展开/收起

- [ ] **Step 7: 如有问题，修复并重新测试**

- [ ] **Step 8: 提交最终版本**

```bash
git add simple_agent/web/analyzer.html
git commit -m "fix: adjust card display based on testing

- [Description of any fixes made]

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## 自我审查

**Spec覆盖检查:**
- ✅ 按日志文件组织 (Task 3)
- ✅ 卡片式显示 (Task 1, 2, 3)
- ✅ 摘要视图 (Task 2 - renderCardSummary)
- ✅ 可展开详情 (Task 2 - renderCardDetails, toggleCard, toggleSection)
- ✅ Usage显示 (Task 2 - usage display format)

**占位符扫描:**
- ✅ 没有TBD/TODO
- ✅ 没有模糊的指令如"添加错误处理"
- ✅ 所有步骤都有完整的代码

**类型一致性:**
- ✅ 函数名一致 (toggleCard, toggleSection, renderCardSummary, renderCardDetails)
- ✅ CSS类名一致 (card-summary, card-details, detail-section等)
