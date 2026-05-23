// Simple Agent Web Chat - frontend logic

const $ = (id) => document.getElementById(id);
const messagesEl = $('messages');
const inputBox = $('input-box');
const sendBtn = $('send-btn');
const inputForm = $('input-form');

// Configure marked + highlight.js (safe fallback if hljs CDN fails)
marked.setOptions({
  breaks: true,
  gfm: true,
  highlight: (code, lang) => {
    if (typeof hljs !== 'undefined' && lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value;
    }
    if (typeof hljs !== 'undefined') {
      return hljs.highlightAuto(code).value;
    }
    return code;
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
  if (typeof hljs !== 'undefined') {
    div.querySelectorAll('pre code').forEach((b) => hljs.highlightElement(b));
  }
  return div;
}

function appendError(message) {
  const div = document.createElement('div');
  div.className = 'bubble error';
  div.innerHTML = `<div class="role">error</div><div class="content">${escapeHtml(message)}</div>`;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendToolLoading(event) {
  const card = document.createElement('div');
  card.className = 'tool-card loading';
  const argsStr = formatArgs(event.arguments);
  card.innerHTML = `
    <div class="tool-header">
      <span>${escapeHtml(event.tool_name)} ${escapeHtml(argsStr)}</span>
      <span class="status spinner">⚙</span>
    </div>
  `;
  card.dataset.callId = event.call_id;
  messagesEl.appendChild(card);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return card;
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
    case 'tool_start':
      appendToolLoading(ev);
      break;
    case 'tool_end': {
      // Update the existing loading card in-place
      const card = document.querySelector(`.tool-card.loading[data-call-id="${ev.call_id}"]`);
      if (card) {
        card.classList.remove('loading');
        const statusClass = ev.success ? 'ok' : 'fail';
        const statusIcon = ev.success ? '✓' : '✗';
        const statusEl = card.querySelector('.status');
        statusEl.className = `status ${statusClass}`;
        statusEl.textContent = statusIcon;
        const body = document.createElement('div');
        body.className = 'tool-body';
        body.innerHTML = `<pre>${escapeHtml(JSON.stringify(ev.result, null, 2))}</pre>`;
        card.appendChild(body);
        card.querySelector('.tool-header').addEventListener('click', () => {
          card.classList.toggle('expanded');
        });
      }
      break;
    }
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
    // Step 1: POST to start the turn
    const resp = await fetch('/api/turn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input }),
    });

    if (!resp.ok) {
      const err = await resp.json();
      appendError(`Error: ${err.error || resp.statusText}`);
      return;
    }

    const respData = await resp.json();
    const turn_id = respData.turn_id;

    // Step 2: Poll for events
    let after = 0;
    while (true) {
      const pollResp = await fetch(`/api/turn/events/${turn_id}?after=${after}`);
      const data = await pollResp.json();
      for (const event of data.events) {
        renderEvent(event);
      }
      after = data.next_after;
      if (data.done) break;
    }

    // Clean up server state
    fetch(`/api/turn/events/${turn_id}`, { method: 'DELETE' });
    refreshSidebar();
  } catch (e) {
    console.error('[sendTurn] error:', e);
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

async function refreshSidebar() {
  try {
    const resp = await fetch('/api/sidebar');
    const data = await resp.json();
    renderTodoList(data.todos || []);
    renderSimpleList('loaded-skills-list', data.loaded_skills || [], (s) => s);
    renderSimpleList(
      'available-skills-list',
      data.available_skills || [],
      (s) => `<strong>${escapeHtml(s.name)}</strong>: ${escapeHtml(s.description || '')}`,
      true,
    );
    renderSimpleList(
      'available-agents-list',
      data.available_agents || [],
      (a) => `<strong>${escapeHtml(a.name)}</strong>: ${escapeHtml(a.description || '')}`,
      true,
    );
  } catch (e) {
    console.warn('refreshSidebar failed', e);
  }
}

function renderTodoList(todos) {
  const ul = $('todo-list');
  if (!todos.length) {
    ul.innerHTML = '<li class="empty">无</li>';
    return;
  }
  ul.innerHTML = '';
  for (const t of todos) {
    const li = document.createElement('li');
    const status = t.status || 'pending';
    const icon = { completed: '✓', in_progress: '⚙', pending: '◯', blocked: '🚫' }[status] || '◯';
    li.innerHTML = `<span class="todo-status todo-${status}">${icon}</span> ${escapeHtml(t.subject || '')}`;
    ul.appendChild(li);
  }
}

function renderSimpleList(elId, items, render, isHtml = false) {
  const ul = $(elId);
  if (!items.length) {
    ul.innerHTML = '<li class="empty">无</li>';
    return;
  }
  ul.innerHTML = '';
  for (const item of items) {
    const li = document.createElement('li');
    const content = render(item);
    if (isHtml) li.innerHTML = content;
    else li.textContent = content;
    ul.appendChild(li);
  }
}

// Resume dialog
const resumeBtn = $('resume-btn');
const resumeDialog = $('resume-dialog');
const logFileList = $('log-file-list');
const resumeCancel = $('resume-cancel');

resumeBtn.addEventListener('click', async () => {
  try {
    const resp = await fetch('/api/logs');
    const data = await resp.json();
    logFileList.innerHTML = '';
    if (!data.logs || !data.logs.length) {
      logFileList.innerHTML = '<li class="empty">无可用日志</li>';
    } else {
      for (const log of data.logs) {
        const li = document.createElement('li');
        li.textContent = log.name;
        li.addEventListener('click', () => doResume(log.path));
        logFileList.appendChild(li);
      }
    }
    resumeDialog.classList.remove('hidden');
  } catch (e) {
    appendError(`Load logs failed: ${e.message || e}`);
  }
});

resumeCancel.addEventListener('click', () => {
  resumeDialog.classList.add('hidden');
});

async function doResume(logPath) {
  resumeDialog.classList.add('hidden');
  try {
    const resp = await fetch('/api/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ log_file: logPath }),
    });
    if (!resp.ok) {
      const err = await resp.json();
      appendError(`Resume failed: ${err.error}`);
      return;
    }
    await loadSession();
    await refreshSidebar();
  } catch (e) {
    appendError(`Resume failed: ${e.message || e}`);
  }
}

// Boot
loadSession();
refreshSidebar();
