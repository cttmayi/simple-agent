// Simple Agent Web Chat - frontend logic

const $ = (id) => document.getElementById(id);
const messagesEl = $('messages');
const inputBox = $('input-box');
const sendBtn = $('send-btn');
const inputForm = $('input-form');

// Configure marked + highlight.js
marked.setOptions({
  breaks: true,
  gfm: true,
  highlight: (code, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value;
    }
    return hljs.highlightAuto(code).value;
  },
});

function renderMarkdown(content) {
  return marked.parse(content || '');
}

function appendBubble(role, content, klass) {
  const div = document.createElement('div');
  div.className = `bubble ${klass || role}`;
  div.innerHTML = `
    <div class="role">${role}</div>
    <div class="content">${renderMarkdown(content)}</div>
  `;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  div.querySelectorAll('pre code').forEach((b) => hljs.highlightElement(b));
  return div;
}

function appendError(message) {
  const div = document.createElement('div');
  div.className = 'bubble error';
  div.innerHTML = `<div class="role">error</div><div class="content">${escapeHtml(message)}</div>`;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendToolCard(event) {
  const card = document.createElement('div');
  card.className = 'tool-card';
  const statusClass = event.success ? 'ok' : 'fail';
  const statusIcon = event.success ? '✓' : '✗';
  const argsStr = formatArgs(event.arguments);
  card.innerHTML = `
    <div class="tool-header">
      <span>${escapeHtml(event.tool_name)} ${escapeHtml(argsStr)}</span>
      <span class="status ${statusClass}">${statusIcon}</span>
    </div>
    <div class="tool-body">
      <pre>${escapeHtml(JSON.stringify(event.result, null, 2))}</pre>
    </div>
  `;
  card.querySelector('.tool-header').addEventListener('click', () => {
    card.classList.toggle('expanded');
  });
  messagesEl.appendChild(card);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function formatArgs(args) {
  if (!args || typeof args !== 'object') return '';
  const parts = [];
  for (const [k, v] of Object.entries(args)) {
    if (parts.length >= 3) { parts.push('…'); break; }
    let s = typeof v === 'string' ? v : JSON.stringify(v);
    if (s.length > 30) s = s.slice(0, 29) + '…';
    parts.push(`${k}=${s}`);
  }
  return parts.length ? `[${parts.join(', ')}]` : '';
}

function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function renderEvent(ev) {
  switch (ev.type) {
    case 'message':
      appendBubble(ev.role, ev.content);
      break;
    case 'error':
      appendError(ev.message);
      break;
    case 'tool_end':
      appendToolCard(ev);
      break;
    case 'tool_start':
    case 'turn_start':
    case 'turn_end':
    case 'status':
      break;
    default:
      console.warn('Unknown event type', ev);
  }
}

async function loadSession() {
  const resp = await fetch('/api/session');
  const data = await resp.json();
  $('session-id').textContent = (data.session_id || '—').slice(0, 8) + '…';
  $('model-name').textContent = data.model || '—';
  messagesEl.innerHTML = '';
  for (const msg of data.messages || []) {
    if (msg.role === 'tool') continue;
    appendBubble(msg.role, msg.content || '');
  }
}

async function sendTurn(input) {
  appendBubble('user', input);
  inputBox.value = '';
  sendBtn.disabled = true;
  sendBtn.innerHTML = '发送 <span class="loading"></span>';

  try {
    const resp = await fetch('/api/turn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input }),
    });
    const data = await resp.json();
    for (const ev of (data.events || [])) renderEvent(ev);
    refreshSidebar();
  } catch (e) {
    appendError(`Request failed: ${e.message || e}`);
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = '发送';
  }
}

inputForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = inputBox.value.trim();
  if (!text) return;
  sendTurn(text);
});

inputBox.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    inputForm.requestSubmit();
  }
});

function refreshSidebar() {}

loadSession();
