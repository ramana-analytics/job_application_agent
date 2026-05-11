/* ResumeOps script.js v2 */
const API = '';
let state = { resumes:[], jobs:[], applicationFiles:[], copilotRuns:[], selectedResumeId:null, selectedJobId:null, jobFilter:'', selectedResumeSemanticText:'', selectedResumeIsLatex:false, latexPdfVisible:true };
const LATEX_SPLIT_STORAGE_KEY = 'resumeops.latexSplitPct';
const RIGHT_PANE_WIDTH_STORAGE_KEY = 'resumeops.rightPaneWidthPx';
const LATEX_PDF_VISIBLE_STORAGE_KEY = 'resumeops.latexPdfVisible';
const COPILOT_RUNS_STORAGE_KEY = 'resumeops.copilotRuns';
const LATEX_EDITOR_FONT_SIZE_STORAGE_KEY = 'resumeops.latexEditorFontSize';

async function apiFetch(path, opts={}) {
  const r = await fetch(API+path, opts);
  if (!r.ok) { const e = await r.json().catch(()=>({error:r.statusText})); throw new Error(e.error||r.statusText); }
  return r.json();
}
async function apiJSON(path, method, body) {
  return apiFetch(path, { method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) });
}
const qs  = sel => document.querySelector(sel);
const qsa = sel => [...document.querySelectorAll(sel)];

function applyLatexSplit(splitPct) {
  const pct = Math.max(35, Math.min(75, Number(splitPct) || 56));
  document.documentElement.style.setProperty('--latex-split', `${pct}%`);
  try { localStorage.setItem(LATEX_SPLIT_STORAGE_KEY, String(pct)); } catch (_) {}
}

function applyLatexEditorFontSize(px, persist = true) {
  const clamped = Math.max(10, Math.min(22, Number(px) || 12.5));
  const rounded = Math.round(clamped * 10) / 10;
  document.documentElement.style.setProperty('--latex-font-size', `${rounded}px`);
  const label = qs('#latexFontSizeLabel');
  if (label) label.textContent = `${rounded}px`;
  if (persist) {
    try { localStorage.setItem(LATEX_EDITOR_FONT_SIZE_STORAGE_KEY, String(rounded)); } catch (_) {}
  }
}

function initLatexEditorFontSize() {
  let size = 12.5;
  try {
    const saved = Number(localStorage.getItem(LATEX_EDITOR_FONT_SIZE_STORAGE_KEY));
    if (!Number.isNaN(saved)) size = saved;
  } catch (_) {}
  applyLatexEditorFontSize(size, false);
}

function initLatexDivider() {
  const divider = qs('#latexDivider');
  const wrap = qs('#resumeEditorWrap');
  if (!divider || !wrap) return;

  const stored = (() => {
    try { return Number(localStorage.getItem(LATEX_SPLIT_STORAGE_KEY)); }
    catch (_) { return NaN; }
  })();
  if (!Number.isNaN(stored)) applyLatexSplit(stored);

  let dragging = false;

  const onMove = (clientX) => {
    const rect = wrap.getBoundingClientRect();
    if (!rect.width) return;
    const pct = ((clientX - rect.left) / rect.width) * 100;
    applyLatexSplit(pct);
  };

  divider.addEventListener('mousedown', (e) => {
    if (!state.selectedResumeIsLatex) return;
    dragging = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    onMove(e.clientX);
  });

  window.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    onMove(e.clientX);
  });

  window.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  });
}

function setLatexPdfVisibility(visible, persist = true) {
  state.latexPdfVisible = !!visible;
  const wrap = qs('#resumeEditorWrap');
  const btn = qs('#btnToggleLatexPdf');
  if (wrap) wrap.classList.toggle('latex-pdf-hidden', state.selectedResumeIsLatex && !state.latexPdfVisible);
  if (btn) btn.textContent = state.latexPdfVisible ? 'Hide PDF' : 'Show PDF';
  if (persist) {
    try { localStorage.setItem(LATEX_PDF_VISIBLE_STORAGE_KEY, state.latexPdfVisible ? '1' : '0'); } catch (_) {}
  }
}

function applyRightPaneWidth(px) {
  const clamped = Math.max(220, Math.min(620, Number(px) || 300));
  document.documentElement.style.setProperty('--panel-w-right', `${Math.round(clamped)}px`);
  try { localStorage.setItem(RIGHT_PANE_WIDTH_STORAGE_KEY, String(Math.round(clamped))); } catch (_) {}
}

function initRightPaneResizers() {
  const dividers = [qs('#resumesPaneDivider'), qs('#jobsPaneDivider')].filter(Boolean);
  if (!dividers.length) return;

  const stored = (() => {
    try { return Number(localStorage.getItem(RIGHT_PANE_WIDTH_STORAGE_KEY)); }
    catch (_) { return NaN; }
  })();
  if (!Number.isNaN(stored)) applyRightPaneWidth(stored);

  let dragging = false;
  let activeDivider = null;

  const onMove = (clientX) => {
    if (!activeDivider) return;
    const section = activeDivider.closest('.tab-content');
    if (!section) return;
    const rect = section.getBoundingClientRect();
    const width = rect.right - clientX;
    applyRightPaneWidth(width);
  };

  dividers.forEach(divider => {
    divider.addEventListener('mousedown', (e) => {
      dragging = true;
      activeDivider = divider;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      onMove(e.clientX);
    });
  });

  window.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    onMove(e.clientX);
  });

  window.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;
    activeDivider = null;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  });
}

function escapeHtml(s='') {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function highlightLatexLine(line='') {
  const escaped = escapeHtml(line);
  const tokens = [];
  const stash = (input, regex, cls) => input.replace(regex, (m) => {
    const key = `@@TOK${tokens.length}@@`;
    tokens.push(`<span class="${cls}">${m}</span>`);
    return key;
  });

  let core = escaped;
  // Process comments separately to avoid coloring inside comments.
  let comment = '';
  for (let i = 0; i < core.length; i++) {
    if (core[i] === '%' && (i === 0 || core[i - 1] !== '\\')) {
      comment = core.slice(i);
      core = core.slice(0, i);
      break;
    }
  }

  core = stash(core, /\\(begin|end)\{[^\n\}]*\}/g, 'lx-env');
  core = stash(core, /\$[^$\n]*\$/g, 'lx-math');
  core = stash(core, /\\[a-zA-Z@]+\*?/g, 'lx-cmd');
  core = stash(core, /\[[^\]\n]*\]/g, 'lx-opt');
  core = stash(core, /[\{\}]/g, 'lx-brace');

  core = core.replace(/@@TOK(\d+)@@/g, (_, n) => tokens[Number(n)] || '');
  if (comment) core += `<span class="lx-cmt">${comment}</span>`;
  return core;
}

function updateLatexPreview() {
  const preview = qs('#latexPreview');
  if (!preview) return;
  const text = qs('#resumeTextarea').value || '';
  preview.innerHTML = text.split('\n').map(highlightLatexLine).join('\n');
}

function formatLatexSource(sourceText = '', indentSize = 2) {
  const unit = ' '.repeat(Math.max(2, Math.min(8, Number(indentSize) || 2)));
  const lines = String(sourceText).replace(/\r\n?/g, '\n').split('\n');
  const formatted = [];
  let envDepth = 0;
  let previousBlank = false;

  for (const rawLine of lines) {
    let line = rawLine.replace(/\t/g, '  ').replace(/\s+$/g, '');
    const trimmed = line.trim();

    if (!trimmed) {
      if (!previousBlank) {
        formatted.push('');
        previousBlank = true;
      }
      continue;
    }

    previousBlank = false;

    if (/^\\end\{[^}]+\}/.test(trimmed)) {
      envDepth = Math.max(0, envDepth - 1);
    }

    const indent = unit.repeat(envDepth);
    formatted.push(indent + trimmed);

    const opens = (trimmed.match(/\\begin\{[^}]+\}/g) || []).length;
    const closes = (trimmed.match(/\\end\{[^}]+\}/g) || []).length;
    const delta = opens - closes;
    if (delta > 0) envDepth += delta;
  }

  while (formatted.length && formatted[formatted.length - 1] === '') formatted.pop();
  return formatted.join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/\n(\\section\*?\{)/g, '\n\n$1')
    .replace(/\n(\\subsection\*?\{)/g, '\n\n$1')
    .replace(/\n(\\item)/g, '\n$1');
}

function getLatestPdfForSelectedResume() {
  if (!state.selectedResumeId) return null;
  return (state.applicationFiles || []).find(f =>
    f.resume_id === state.selectedResumeId &&
    (f.format || '').toLowerCase() === 'pdf'
  ) || null;
}

function refreshLatexPdfEmbed(downloadUrl = '') {
  const frame = qs('#latexPdfFrame');
  if (!frame) return;
  const url = downloadUrl || (() => {
    const latest = getLatestPdfForSelectedResume();
    return latest ? `/api/application-files/${latest.id}/preview` : '';
  })();

  if (!url) {
    frame.removeAttribute('src');
    frame.srcdoc = '<html><body style="margin:0;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;background:#fff;color:#444;display:flex;align-items:center;justify-content:center;height:100%">Compile LaTeX to preview PDF here.</body></html>';
    return;
  }
  frame.removeAttribute('srcdoc');
  const sep = url.includes('?') ? '&' : '?';
  frame.src = `${url}${sep}t=${Date.now()}`;
}

function showModal(spinning=true, msg='') {
  qs('#modalOverlay').style.display = 'flex';
  qs('#modalSpinner').style.display = spinning ? 'block' : 'none';
  qs('#modalMessage').style.display = msg ? 'block' : 'none';
  qs('#modalMessage').textContent   = msg;
  qs('#modalClose').style.display   = msg ? 'inline-block' : 'none';
}
function hideModal() { qs('#modalOverlay').style.display = 'none'; }

function setStatus(msg, cls='') {
  const b = qs('#statusBadge');
  b.textContent = '● ' + msg;
  b.className = 'status-badge ' + cls;
}

function scoreColor(s) { return s >= 75 ? '' : s >= 50 ? 'warn' : 'bad'; }
function statusPill(s) { return `<span class="status-pill s-${s}">${s}</span>`; }

const cliLogs = [];

function saveCopilotRuns() {
  try { localStorage.setItem(COPILOT_RUNS_STORAGE_KEY, JSON.stringify(state.copilotRuns.slice(0, 40))); } catch (_) {}
}

function loadCopilotRunsFromStorage() {
  try {
    const raw = localStorage.getItem(COPILOT_RUNS_STORAGE_KEY);
    state.copilotRuns = raw ? JSON.parse(raw) : [];
  } catch (_) {
    state.copilotRuns = [];
  }
}

function renderCopilotRuns() {
  const list = qs('#cpHistoryList');
  if (!list) return;
  if (!state.copilotRuns.length) {
    list.innerHTML = '<div class="cli-log-empty">No prompt runs yet.</div>';
    return;
  }

  list.innerHTML = state.copilotRuns.map((run, idx) => {
    const ts = run.ts || '';
    const model = run.model || 'auto';
    const prompt = escapeHtml(run.prompt || '');
    const result = escapeHtml(run.result || '');
    return `<div class="cli-log-entry" data-run-idx="${idx}">
      <div class="cli-log-header">
        <span class="cli-log-ts">${ts}</span>
        <span class="cli-log-task">prompt</span>
        <span class="cli-log-ts">model: ${model}</span>
      </div>
      <div class="block-title" style="margin:0">Prompt</div>
      <pre class="cli-log-output">${prompt}</pre>
      <div class="block-title" style="margin:0">Result</div>
      <pre class="cli-log-output">${result || '(no output)'}</pre>
      <div class="action-row mt-sm">
        <button class="btn btn-sm" data-action="reuse-run-prompt" data-run-idx="${idx}">Reuse Prompt</button>
        <button class="btn btn-sm" data-action="use-run-result" data-run-idx="${idx}">Use Result as Prompt</button>
      </div>
    </div>`;
  }).join('');
}

function buildCopilotHistoryContext() {
  if (!state.copilotRuns.length) return '';
  const recent = state.copilotRuns.slice(0, 5);
  const blocks = recent.map((r, i) => {
    const p = (r.prompt || '').slice(0, 1200);
    const out = (r.result || '').slice(0, 1600);
    return `Run ${i + 1}\nPrompt:\n${p}\n\nResult:\n${out}`;
  });
  return `Use the following recent prompt/result history as additional context:\n\n${blocks.join('\n\n---\n\n')}`;
}

function updateCliStatus(meta = {}) {
  const ts      = new Date().toLocaleTimeString();
  const task    = meta.task    || 'copilot';
  const command = meta.command || '-';
  const model   = meta.model   || 'auto';
  const success = !!meta.success;
  const output  = (meta.output || meta.error || 'No output').trim();

  cliLogs.unshift({ ts, task, command, model, success, output });

  const list = qs('#cliLogList');
  if (!list) return;

  const entry = document.createElement('div');
  entry.className = 'cli-log-entry';
  entry.innerHTML =
    `<div class="cli-log-header">` +
      `<span class="cli-log-ts">${ts}</span>` +
      `<span class="cli-log-task">${task}</span>` +
      `<span class="cli-log-ts">model: ${model}</span>` +
      `<span class="cli-log-result" style="color:${success ? 'var(--green)' : 'var(--red)'}">` +
        `${success ? '✓ success' : '✗ failed'}` +
      `</span>` +
    `</div>` +
    `<code class="cli-log-cmd">${command}</code>` +
    `<pre class="cli-log-output">${output.slice(0, 6000)}</pre>`;

  list.prepend(entry);
}

/* ── TABS ─────────────────────────────────────────────────────── */
qsa('.tab-btn').forEach(btn => btn.addEventListener('click', () => {
  qsa('.tab-btn').forEach(b => b.classList.remove('active'));
  qsa('.tab-content').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  qs('#tab-' + btn.dataset.tab).classList.add('active');
  if (btn.dataset.tab === 'jobs')    loadJobStats();
  if (btn.dataset.tab === 'applications') loadApplicationFiles();
}));

function formatDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

async function loadApplicationFiles() {
  try {
    state.applicationFiles = await apiFetch('/api/application-files');
    renderApplicationFiles();
    if (state.selectedResumeIsLatex) refreshLatexPdfEmbed();
  } catch (err) {
    const box = qs('#applicationFilesList');
    if (box) box.innerHTML = `<div class="cli-log-empty">Failed to load files: ${err.message}</div>`;
  }
}

function renderApplicationFiles() {
  const box = qs('#applicationFilesList');
  if (!box) return;
  if (!state.applicationFiles.length) {
    box.innerHTML = '<div class="cli-log-empty">No generated DOCX/PDF files yet.</div>';
    return;
  }

  box.innerHTML = state.applicationFiles.map(f => {
    const jobLabel = f.job_title ? `${f.job_title}${f.company ? ' · ' + f.company : ''}` : 'No linked job';
    return `<div class="cli-log-entry">
      <div class="cli-log-header">
        <span class="cli-log-task">${(f.format || '').toUpperCase()} file</span>
        <span class="cli-log-ts">${formatDateTime(f.created_at)}</span>
      </div>
      <div class="item-name">${f.resume_filename || 'Resume export'}</div>
      <div class="item-meta">${jobLabel}</div>
      <code class="cli-log-cmd">${f.file_name || ''}</code>
      <div class="action-row mt-sm">
        <button class="btn btn-sm btn-accent" data-action="download-application-file" data-id="${f.id}">Download</button>
        <button class="btn btn-sm btn-danger" data-action="delete-application-file" data-id="${f.id}">Delete</button>
      </div>
    </div>`;
  }).join('');
}

/* ── THEME ────────────────────────────────────────────────────── */
qs('#themeToggle').addEventListener('click', () => {
  const h = document.documentElement, dark = h.getAttribute('data-theme') === 'dark';
  h.setAttribute('data-theme', dark ? 'light' : 'dark');
  qs('#themeToggle').textContent = dark ? '\u{1F319}' : '\u2600\uFE0F';
});
qs('#modalClose').addEventListener('click', hideModal);

/* ── GLOBAL COPILOT WINDOW ───────────────────────────────────── */
function setCopilotWindowOpen(open) {
  qs('#copilotWindow').style.display = open ? 'block' : 'none';
  qs('#copilotWindowToggle').textContent = open ? '✕ Close Copilot' : '🤖 Copilot';
}

qs('#copilotWindowToggle').addEventListener('click', () => {
  const isOpen = qs('#copilotWindow').style.display !== 'none';
  setCopilotWindowOpen(!isOpen);
});

qs('#btnCloseCopilotWindow').addEventListener('click', () => setCopilotWindowOpen(false));

qs('#btnRunCopilotPrompt').addEventListener('click', async () => {
  const prompt = qs('#copilotPrompt').value.trim();
  const model = qs('#copilotModel').value.trim();
  if (!prompt) {
    setStatus('Enter a Copilot prompt first', '');
    return;
  }

  setStatus('Running Copilot prompt…', 'busy');
  qs('#copilotResult').value = 'Running...';
  try {
    const r = await apiJSON('/api/copilot/prompt', 'POST', { prompt, model });
    qs('#copilotResult').value = r.result || r.cli_status?.error || 'No output';
    updateCliStatus(r.cli_status || {
      task: 'prompt_window',
      success: false,
      error: 'No CLI metadata returned',
      model: model || 'auto',
    });
    setStatus('Copilot prompt complete', 'ok');
  } catch (err) {
    qs('#copilotResult').value = 'Error: ' + err.message;
    setStatus('Copilot prompt failed', '');
  }
});

qs('#btnRunCopilotTabPrompt').addEventListener('click', async () => {
  const prompt = qs('#cpPromptInput').value.trim();
  const model = qs('#cpModel').value.trim();
  const useHistory = !!qs('#cpUseHistory').checked;
  if (!prompt) {
    setStatus('Enter a prompt first', '');
    return;
  }

  setStatus('Running Copilot prompt…', 'busy');
  const historyContext = useHistory ? buildCopilotHistoryContext() : '';
  const mergedPrompt = historyContext ? `${historyContext}\n\nCurrent prompt:\n${prompt}` : prompt;
  try {
    const r = await apiJSON('/api/copilot/prompt', 'POST', { prompt: mergedPrompt, model });
    const result = r.result || r.cli_status?.error || '';
    state.copilotRuns.unshift({
      ts: new Date().toLocaleString(),
      model: model || 'auto',
      prompt,
      result,
      usedHistory: useHistory,
    });
    state.copilotRuns = state.copilotRuns.slice(0, 40);
    saveCopilotRuns();
    renderCopilotRuns();
    updateCliStatus(r.cli_status || {
      task: 'prompt_tab',
      success: false,
      error: 'No CLI metadata returned',
      model: model || 'auto',
    });
    setStatus('Prompt run complete', 'ok');
  } catch (err) {
    state.copilotRuns.unshift({
      ts: new Date().toLocaleString(),
      model: model || 'auto',
      prompt,
      result: 'Error: ' + err.message,
      usedHistory: useHistory,
    });
    state.copilotRuns = state.copilotRuns.slice(0, 40);
    saveCopilotRuns();
    renderCopilotRuns();
    setStatus('Prompt failed', '');
  }
});

qs('#cpHistoryList').addEventListener('click', (e) => {
  const btn = e.target.closest('button[data-action]');
  if (!btn) return;
  const idx = Number(btn.dataset.runIdx);
  const run = state.copilotRuns[idx];
  if (!run) return;
  if (btn.dataset.action === 'reuse-run-prompt') {
    qs('#cpPromptInput').value = run.prompt || '';
    return;
  }
  if (btn.dataset.action === 'use-run-result') {
    qs('#cpPromptInput').value = run.result || '';
  }
});

/* ══════════════════════ RESUMES ════════════════════════════════ */
async function loadResumes() {
  const arch = qs('#showArchived').checked;
  state.resumes = await apiFetch('/api/resumes?include_archived=' + arch);
  renderResumeList();
  populateJobResumeSelect();
}

function renderResumeList() {
  const f    = qs('#resumeSearch').value.toLowerCase();
  const list = qs('#resumeList');
  const items = state.resumes.filter(r =>
    r.filename.toLowerCase().includes(f) || (r.tags||[]).some(t => t.toLowerCase().includes(f))
  );
  if (!items.length) { list.innerHTML = '<li class="empty-msg">No resumes found</li>'; return; }
  list.innerHTML = items.map(r => {
    const ats  = r.ats_analysis?.ats_score;
    const athHtml = ats != null
      ? `<span class="item-ats" style="color:${ats>=75?'var(--green)':ats>=50?'var(--yellow)':'var(--red)'}">${ats}</span>` : '';
    return `<li class="resume-item${r.id===state.selectedResumeId?' selected':''}" data-id="${r.id}">
      <div class="item-name">${r.filename}${r.archived?' \uD83D\uDCE6':''}</div>
      <div class="item-meta">${(r.tags||[]).join(', ')||'No tags'}${r.version>1?' \u00B7 v'+r.version:''}</div>${athHtml}</li>`;
  }).join('');
  qsa('#resumeList .resume-item').forEach(li => li.addEventListener('click', () => selectResume(li.dataset.id)));
}

function selectResume(id) {
  state.selectedResumeId = id;
  renderResumeList();
  const r = state.resumes.find(x => x.id === id);
  if (!r) return;
  state.selectedResumeSemanticText = r.plain_text || r.text || '';
  state.selectedResumeIsLatex = r.source_format === 'latex' || (r.file_path || '').toLowerCase().endsWith('.tex');
  qs('#resumeEmptyState').style.display  = 'none';
  qs('#resumeTextarea').style.display    = 'flex';
  qs('#resumeTextarea').value            = r.text || '';
  qs('#resumeHeader').style.display      = 'flex';
  qs('#resumeFilename').textContent      = r.filename + ((r.source_format === 'latex' || (r.file_path || '').toLowerCase().endsWith('.tex')) ? ' (LaTeX)' : '');
  qs('#resumeVersion').textContent       = 'v' + r.version;
  qs('#resumeTags').innerHTML            = (r.tags||[]).map(t => `<span class="tag-item">${t}</span>`).join('');
  qs('#atsBar').style.display            = 'flex';
  const isLatex = state.selectedResumeIsLatex;
  const compileBtn = qs('#btnCompileLatexPdf');
  const togglePdfBtn = qs('#btnToggleLatexPdf');
  const exportDrop = qs('#btnExportDrop');
  const originalBtn = qs('#btnDownloadOriginalResume');
  const updatedBtn = qs('#btnDownloadUpdatedResume');
    const latexEditorControls = qs('#latexEditorControls');
  const latexPreview = qs('#latexPreview');
  const latexDivider = qs('#latexDivider');
  const latexPdfFrame = qs('#latexPdfFrame');
  const editorWrap = qs('#resumeEditorWrap');
  if (editorWrap) editorWrap.classList.toggle('latex-mode', isLatex);
  if (editorWrap) editorWrap.classList.toggle('latex-pdf-hidden', isLatex && !state.latexPdfVisible);
  if (latexPreview) latexPreview.style.display = isLatex ? 'block' : 'none';
  if (latexDivider) latexDivider.style.display = (isLatex && state.latexPdfVisible) ? 'block' : 'none';
  if (latexPdfFrame) latexPdfFrame.style.display = (isLatex && state.latexPdfVisible) ? 'block' : 'none';
  if (compileBtn) compileBtn.style.display = isLatex ? 'inline-block' : 'none';
    if (latexEditorControls) latexEditorControls.style.display = isLatex ? 'inline-flex' : 'none';
  if (togglePdfBtn) {
    togglePdfBtn.style.display = isLatex ? 'inline-block' : 'none';
    togglePdfBtn.textContent = state.latexPdfVisible ? 'Hide PDF' : 'Show PDF';
  }
  if (exportDrop) exportDrop.parentElement.style.display = isLatex ? 'none' : 'inline-block';
  if (originalBtn) originalBtn.style.display = isLatex ? 'inline-block' : 'none';
  if (updatedBtn) updatedBtn.style.display = isLatex ? 'inline-block' : 'none';
  if (isLatex) {
    updateLatexPreview();
    if (state.latexPdfVisible) refreshLatexPdfEmbed();
  }
  const ats = r.ats_analysis;
  if (ats?.ats_score != null) {
    qs('#atsFill').style.width   = ats.ats_score + '%';
    qs('#atsFill').className     = 'ats-fill ' + scoreColor(ats.ats_score);
    qs('#atsScore').textContent  = ats.ats_score + '%';
    renderAtsDetails(ats);
  } else {
    qs('#atsFill').style.width  = '0%';
    qs('#atsScore').textContent = '\u2014';
    qs('#atsDetailBlock').innerHTML = '<div class="block-title">ATS Analysis</div>'
      + '<div class="ats-score-big">\u2014</div>'
      + '<p style="font-size:11px;color:var(--text2);text-align:center">Click \u201CCheck ATS\u201D to analyze</p>';
  }
}

function renderAtsDetails(ats) {
  if (!ats) return;
  const c = ats.ats_score >= 75 ? 'var(--green)' : ats.ats_score >= 50 ? 'var(--yellow)' : 'var(--red)';
  const issues = (ats.issues||[]).map(i => {
    const sev  = i.severity || 'low';
    const hi   = sev === 'critical' || sev === 'high';
    const med  = sev === 'warning'  || sev === 'medium';
    const cls  = hi ? 'issue-critical' : med ? 'issue-warning' : 'issue-ok';
    const icon = hi ? '\u2717' : med ? '!' : '\u2713';
    return `<div class="issue-item ${cls}"><span class="issue-icon">${icon}</span><span>${i.message}</span></div>`;
  }).join('');
  const kw = ats.keyword_analysis || {};
  const matched = (kw.matched_keywords||[]).map(k => `<span class="kw-tag">${k}</span>`).join('');
  const missing = (kw.missing_keywords||[]).map(k => `<span class="kw-tag">${k}</span>`).join('');
  qs('#atsDetailBlock').innerHTML =
    `<div class="block-title">ATS Analysis</div>
     <div class="ats-score-big" style="color:${c}">${ats.ats_score}%</div>
     <div class="issue-list">${issues}</div>
     ${matched ? '<div class="block-title mt">Matched Keywords</div><div class="kw-row">'+matched+'</div>' : ''}
     ${missing ? '<div class="block-title mt">Missing Keywords</div><div class="kw-row kw-missing">'+missing+'</div>' : ''}`;
}

qs('#resumeSearch').addEventListener('input', renderResumeList);
qs('#showArchived').addEventListener('change', loadResumes);
qs('#resumeTextarea').addEventListener('input', () => {
  if (state.selectedResumeIsLatex) updateLatexPreview();
});
qs('#resumeTextarea').addEventListener('scroll', () => {
  if (!state.selectedResumeIsLatex) return;
  const ta = qs('#resumeTextarea');
  const pv = qs('#latexPreview');
  if (!ta || !pv) return;
  pv.scrollTop = ta.scrollTop;
  pv.scrollLeft = ta.scrollLeft;
});

/* — Upload ——————————————————————————————————————————————————— */
qs('#resumeFileInput').addEventListener('change', async e => {
  const file = e.target.files[0]; if (!file) return;
  setStatus('Uploading\u2026', 'busy'); showModal(true);
  try {
    const fd = new FormData(); fd.append('file', file);
    const r    = await fetch('/api/resumes/upload', { method:'POST', body:fd });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Upload failed');
    await loadResumes(); hideModal(); setStatus('Uploaded', 'ok');
    if (data.id) selectResume(data.id);
  } catch(err) { showModal(false, 'Upload failed: ' + err.message); setStatus('Error',''); }
  e.target.value = '';
});

/* — Save text ———————————————————————————————————————————————— */
qs('#btnSaveText').addEventListener('click', async () => {
  if (!state.selectedResumeId) return;
  setStatus('Saving\u2026', 'busy');
  try {
    await apiJSON('/api/resumes/'+state.selectedResumeId+'/text', 'PATCH', { text: qs('#resumeTextarea').value });
    if (state.selectedResumeIsLatex) {
      const compileResult = await apiJSON('/api/resumes/' + state.selectedResumeId + '/compile-pdf', 'POST', {
        job_id: state.selectedJobId || '',
        source_text: qs('#resumeTextarea').value,
      });
      await loadApplicationFiles();
      if (state.latexPdfVisible) refreshLatexPdfEmbed(compileResult.preview_url || compileResult.download_url || '');
    }
    await loadResumes(); selectResume(state.selectedResumeId); setStatus('Saved','ok');
  } catch(err) {
    showModal(false, err.message || 'Save/compile failed');
    setStatus('Error: '+err.message, '');
  }
});

/* — Archive / Delete ————————————————————————————————————————— */
qs('#btnArchiveResume').addEventListener('click', async () => {
  if (!state.selectedResumeId) return;
  const r = state.resumes.find(x => x.id === state.selectedResumeId);
  const archived = !r?.archived;
  await apiJSON('/api/resumes/'+state.selectedResumeId+'/archive', 'PATCH', { archived });
  await loadResumes();
  if (!archived) { selectResume(state.selectedResumeId); }
  else { state.selectedResumeId = null; clearResumeView(); }
});

qs('#btnDeleteResume').addEventListener('click', async () => {
  if (!state.selectedResumeId || !confirm('Delete this resume?')) return;
  await apiFetch('/api/resumes/'+state.selectedResumeId, { method:'DELETE' });
  state.selectedResumeId = null; await loadResumes(); clearResumeView();
});

function clearResumeView() {
  qs('#resumeHeader').style.display     = 'none';
  qs('#resumeEmptyState').style.display = 'flex';
  qs('#resumeTextarea').style.display   = 'none';
  qs('#atsBar').style.display           = 'none';
  qs('#latexPreview').style.display     = 'none';
  qs('#latexDivider').style.display     = 'none';
  qs('#latexPdfFrame').style.display    = 'none';
  qs('#latexPdfFrame').removeAttribute('src');
  qs('#latexPdfFrame').removeAttribute('srcdoc');
  qs('#resumeEditorWrap').classList.remove('latex-mode');
  state.selectedResumeIsLatex = false;
}

/* — Check ATS ———————————————————————————————————————————————— */
qs('#btnCheckAts').addEventListener('click', async () => {
  if (!state.selectedResumeId) return;
  const job = state.jobs.find(j => j.id === state.selectedJobId);
  showModal(true); setStatus('Analyzing ATS\u2026', 'busy');
  try {
    const ats = await apiJSON('/api/ats/check', 'POST', {
      resume_text: state.selectedResumeSemanticText || qs('#resumeTextarea').value,
      job_description: job?.description || ''
    });
    qs('#atsFill').style.width  = ats.ats_score + '%';
    qs('#atsFill').className    = 'ats-fill ' + scoreColor(ats.ats_score);
    qs('#atsScore').textContent = ats.ats_score + '%';
    renderAtsDetails(ats); hideModal(); setStatus('ATS checked','ok');
  } catch(err) { showModal(false, 'ATS check failed: '+err.message); setStatus('Error',''); }
});

async function downloadResumeFile(kind) {
  const response = await fetch('/api/resumes/' + state.selectedResumeId + '/file?kind=' + encodeURIComponent(kind));
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || body.error || response.statusText);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = '';
  link.click();
  URL.revokeObjectURL(url);
}

qs('#btnDownloadOriginalResume').addEventListener('click', async () => {
  if (!state.selectedResumeId) return;
  try {
    await downloadResumeFile('original');
    setStatus('Original LaTeX downloaded', 'ok');
  } catch (err) {
    setStatus('Download failed: ' + err.message, '');
  }
});

qs('#btnDownloadUpdatedResume').addEventListener('click', async () => {
  if (!state.selectedResumeId) return;
  try {
    await downloadResumeFile('updated');
    setStatus('Updated LaTeX downloaded', 'ok');
  } catch (err) {
    setStatus('Download failed: ' + err.message, '');
  }
});

qs('#btnCompileLatexPdf').addEventListener('click', async () => {
  if (!state.selectedResumeId) return;
  showModal(true);
  setStatus('Compiling LaTeX…', 'busy');
  try {
    const r = await apiJSON('/api/resumes/' + state.selectedResumeId + '/compile-pdf', 'POST', {
      job_id: state.selectedJobId || '',
      source_text: qs('#resumeTextarea').value,
    });
    await loadApplicationFiles();
    hideModal();
    setStatus('Compiled PDF ready', 'ok');
    if (state.latexPdfVisible && (r.preview_url || r.download_url)) {
      refreshLatexPdfEmbed(r.preview_url || r.download_url);
    }
  } catch (err) {
    showModal(false, err.message || 'LaTeX compilation failed');
    setStatus('Compile failed', '');
  }
});

qs('#btnToggleLatexPdf').addEventListener('click', () => {
  if (!state.selectedResumeIsLatex) return;
  setLatexPdfVisibility(!state.latexPdfVisible);
  const latexDivider = qs('#latexDivider');
  const latexPdfFrame = qs('#latexPdfFrame');
  if (latexDivider) latexDivider.style.display = state.latexPdfVisible ? 'block' : 'none';
  if (latexPdfFrame) latexPdfFrame.style.display = state.latexPdfVisible ? 'block' : 'none';
  if (state.latexPdfVisible) refreshLatexPdfEmbed();
});

qs('#btnLatexFontIncrease').addEventListener('click', () => {
  if (!state.selectedResumeIsLatex) return;
  const current = getComputedStyle(document.documentElement).getPropertyValue('--latex-font-size').trim();
  const parsed = Number(current.replace('px', ''));
  applyLatexEditorFontSize((Number.isNaN(parsed) ? 12.5 : parsed) + 0.5);
});

qs('#btnLatexFontDecrease').addEventListener('click', () => {
  if (!state.selectedResumeIsLatex) return;
  const current = getComputedStyle(document.documentElement).getPropertyValue('--latex-font-size').trim();
  const parsed = Number(current.replace('px', ''));
  applyLatexEditorFontSize((Number.isNaN(parsed) ? 12.5 : parsed) - 0.5);
});

qs('#btnFormatLatex').addEventListener('click', () => {
  if (!state.selectedResumeIsLatex) return;
  const ta = qs('#resumeTextarea');
  if (!ta) return;
  const before = ta.value || '';
  const after = formatLatexSource(before);
  ta.value = after;
  updateLatexPreview();
  setStatus(before === after ? 'LaTeX already formatted' : 'LaTeX formatted', 'ok');
});
  qs('#latexEditorControls').style.display = 'none';

/* — Export ——————————————————————————————————————————————————— */
qs('#btnExportDrop').addEventListener('click', e => {
  e.stopPropagation(); qs('#btnExportDrop').parentElement.classList.toggle('open');
});
document.addEventListener('click', () => qsa('.dropdown.open').forEach(d => d.classList.remove('open')));
qsa('#exportMenu button').forEach(btn => btn.addEventListener('click', async () => {
  if (!state.selectedResumeId) return;
  const fmt = btn.dataset.fmt;
  qs('#btnExportDrop').parentElement.classList.remove('open');
  setStatus('Exporting\u2026', 'busy');
  try {
    const r = await fetch('/api/resumes/'+state.selectedResumeId+'/export', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({fmt, job_id: state.selectedJobId || ''})
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({ error: r.statusText }));
      throw new Error(e.error || e.detail || r.statusText);
    }
    const blob = await r.blob();
    const url  = URL.createObjectURL(blob);
    const a    = Object.assign(document.createElement('a'), { href:url, download:'resume.'+fmt });
    a.click(); URL.revokeObjectURL(url);
    await loadApplicationFiles();
    setStatus('Exported','ok');
  } catch(err) { setStatus('Export failed: '+err.message,''); }
}));

function getResumeLabel(resumeId) {
  const resume = state.resumes.find(r => r.id === resumeId);
  return resume ? resume.filename : '';
}

function populateJobResumeSelect() {
  const select = qs('#jobResumeSelect');
  if (!select) return;
  select.innerHTML = '<option value="">— select resume —</option>' +
    state.resumes.map(r => `<option value="${r.id}">${r.filename}</option>`).join('');
}

/* ══════════════════════ JOBS ═══════════════════════════════════ */
async function loadJobs() {
  state.jobs = await apiFetch('/api/jobs');
  renderJobList();
  populateJobResumeSelect();
  await loadJobStats();
}

function renderJobList() {
  const f    = qs('#jobSearch').value.toLowerCase();
  const sf   = state.jobFilter;
  const list = qs('#jobList');
  const items = state.jobs.filter(j => {
    const ms = !sf || j.status === sf;
    const mt = !f || (j.job_title||'').toLowerCase().includes(f) || (j.company||'').toLowerCase().includes(f);
    return ms && mt;
  });
  if (!items.length) { list.innerHTML = '<li class="empty-msg">No jobs match</li>'; return; }
  list.innerHTML = items.map(j => {
    const m = j.job_match_percentage != null ? ` \u00B7 ${j.job_match_percentage}%` : '';
    return `<li class="job-item${j.id===state.selectedJobId?' selected':''}" data-id="${j.id}">
      <div class="item-name">${j.job_title||'Unnamed'}</div>
      <div class="item-meta">${j.company||'\u2014'}${m} \u00B7 ${statusPill(j.status||'saved')}</div></li>`;
  }).join('');
  qsa('#jobList .job-item').forEach(li => li.addEventListener('click', () => selectJob(li.dataset.id)));
}

function selectJob(id) {
  state.selectedJobId = id; renderJobList();
  const j = state.jobs.find(x => x.id === id); if (!j) return;
  qs('#jobEmptyState').style.display    = 'none';
  qs('#jobDetailContent').style.display = 'block';
  qs('#jobDetailTitle').textContent     = j.job_title || '\u2014';
  qs('#jobDetailCompany').textContent   = j.company || '';
  qs('#jobStatusSelect').value          = j.status || 'saved';
  qs('#jLocation').textContent     = (j.locations||[]).join(', ') || '\u2014';
  qs('#jType').textContent         = j.job_type || '\u2014';
  qs('#jSponsorship').textContent  = j.sponsorship_required || '\u2014';
  qs('#jSalary').textContent       = j.salary_range || '\u2014';
  qs('#jBand').textContent         = j.band_level || '\u2014';
  qs('#jExp').textContent          = j.experience_requirements || '\u2014';
  qs('#jApplied').textContent      = j.applied_date || '\u2014';
  qs('#jDeadline').textContent     = j.deadline || '\u2014';
  const url = j.job_url || '';
  qs('#jUrl').innerHTML = url ? `<a href="${url}" target="_blank" style="color:var(--accent)">Open \u2197</a>` : '\u2014';
  qs('#jobResumeSelect').value = j.resume_id || '';
  const resumeLabel = j.resume_id ? getResumeLabel(j.resume_id) : '';
  qs('#jResumeUsedText').innerHTML = j.resume_id
    ? `Selected resume: <a href="#" id="jobResumeInlineLink" style="color:var(--accent);text-decoration:underline">${resumeLabel || 'Open resume'}</a>`
    : 'No resume selected yet';
  qs('#jMyInfoArea').value = j.my_info || '';
  qs('#jRecommendationsArea').value = j.resume_recommendations || '';
  qs('#btnApplyRecommendations').style.display = (j.resume_recommendations || '').trim() ? 'inline-block' : 'none';
  qs('#jobCoverLetterArea').value = j.cover_letter || '';
  // Summary tab — show stored summary or placeholder
  const storedSummary = j.copilot_summary || '';
  if (storedSummary) {
    qs('#jSummaryText').textContent = storedSummary;
    qs('#jSummaryText').style.display = 'block';
    qs('#jSummaryPlaceholder').style.display = 'none';
  } else {
    qs('#jSummaryText').style.display = 'none';
    qs('#jSummaryPlaceholder').style.display = 'block';
  }
  qsa('.sub-tab').forEach(t => t.classList.remove('active'));
  qsa('.sub-block').forEach(b => b.classList.remove('active'));
  qs('.sub-tab[data-block="jSummary"]').classList.add('active');
  qs('#jSummary').classList.add('active');

  const openResume = () => {
    if (!j.resume_id) return;
    qs('.tab-btn[data-tab="resumes"]').click();
    selectResume(j.resume_id);
  };

  const inlineLink = qs('#jobResumeInlineLink');
  if (inlineLink) inlineLink.onclick = e => { e.preventDefault(); openResume(); };
}

qs('#jobSearch').addEventListener('input', renderJobList);
qsa('.filter-chip').forEach(chip => chip.addEventListener('click', () => {
  qsa('.filter-chip').forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  state.jobFilter = chip.dataset.status;
  renderJobList();
}));

qsa('.sub-tab').forEach(tab => tab.addEventListener('click', () => {
  qsa('.sub-tab').forEach(t => t.classList.remove('active'));
  qsa('.sub-block').forEach(b => b.classList.remove('active'));
  tab.classList.add('active');
  qs('#' + tab.dataset.block).classList.add('active');
}));

qs('#btnSaveJobResume').addEventListener('click', async () => {
  if (!state.selectedJobId) return;
  const resumeId = qs('#jobResumeSelect').value || '';
  await apiJSON('/api/jobs/' + state.selectedJobId, 'PATCH', { resume_id: resumeId });
  await loadJobs();
  selectJob(state.selectedJobId);
  setStatus(resumeId ? 'Resume saved' : 'Resume cleared', 'ok');
});

qs('#btnOpenJobResume').addEventListener('click', () => {
  if (!state.selectedJobId) return;
  const j = state.jobs.find(x => x.id === state.selectedJobId);
  if (!j?.resume_id) {
    setStatus('Select and save a resume first', '');
    return;
  }
  qs('.tab-btn[data-tab="resumes"]').click();
  selectResume(j.resume_id);
});

qs('#btnGenerateRecommendations').addEventListener('click', async () => {
  if (!state.selectedJobId) return;
  const resumeId = qs('#jobResumeSelect').value || state.selectedResumeId || '';
  if (!resumeId) { setStatus('Select a resume first', ''); return; }
  showModal(true); setStatus('Generating recommendations…', 'busy');
  try {
    const r = await apiJSON('/api/jobs/' + state.selectedJobId + '/recommendations', 'POST', { resume_id: resumeId });
    qs('#jRecommendationsArea').value = r.recommendations || '';
    qs('#btnApplyRecommendations').style.display = (r.recommendations || '').trim() ? 'inline-block' : 'none';
    updateCliStatus(r.cli_status || { task: 'resume_recommendations', success: false, error: 'No CLI metadata returned' });
    hideModal(); setStatus('Recommendations ready', 'ok');
  } catch (err) { showModal(false, 'Recommendations failed: ' + err.message); setStatus('Error', ''); }
});

qs('#btnApplyRecommendations').addEventListener('click', async () => {
  if (!state.selectedJobId) return;
  const resumeId = qs('#jobResumeSelect').value || state.selectedResumeId || '';
  const recommendations = qs('#jRecommendationsArea').value.trim();
  if (!resumeId) { setStatus('Select a resume first', ''); return; }
  if (!recommendations) { setStatus('Generate recommendations first', ''); return; }
  showModal(true); setStatus('Applying recommendations to a new resume…', 'busy');
  try {
    const r = await apiJSON('/api/jobs/' + state.selectedJobId + '/recommendations/apply', 'POST', {
      resume_id: resumeId,
      recommendations,
    });
    const newResumeId = r.resume?.id || '';
    await loadResumes();
    if (newResumeId) {
      qs('.tab-btn[data-tab="resumes"]').click();
      selectResume(newResumeId);
      setStatus('New tailored resume opened', 'ok');
    } else {
      setStatus('Tailored resume created', 'ok');
    }
    updateCliStatus(r.cli_status || { task: 'apply_resume_recommendations', success: false, error: 'No CLI metadata returned' });
    hideModal();
  } catch (err) {
    showModal(false, 'Apply recommendations failed: ' + err.message);
    setStatus('Error', '');
  }
});

qs('#btnGenerateCoverLetter').addEventListener('click', async () => {
  if (!state.selectedJobId) return;
  const resumeId = qs('#jobResumeSelect').value || state.selectedResumeId || '';
  if (!resumeId) { setStatus('Select a resume first', ''); return; }
  showModal(true); setStatus('Generating cover letter…', 'busy');
  try {
    const r = await apiJSON('/api/cover-letter', 'POST', { job_id: state.selectedJobId, resume_id: resumeId });
    qs('#jobCoverLetterArea').value = r.cover_letter || '';
    updateCliStatus(r.cli_status || { task: 'cover_letter', success: false, error: 'No CLI metadata returned' });
    hideModal(); setStatus('Cover letter ready', 'ok');
  } catch (err) { showModal(false, 'Cover letter failed: ' + err.message); setStatus('Error', ''); }
});

qs('#btnSaveCoverLetter').addEventListener('click', async () => {
  if (!state.selectedJobId) return;
  await apiJSON('/api/jobs/' + state.selectedJobId, 'PATCH', { cover_letter: qs('#jobCoverLetterArea').value });
  await loadJobs();
  selectJob(state.selectedJobId);
  setStatus('Cover letter saved', 'ok');
});

/* — Copilot Fill Job ———————————————————————————————————————— */
qs('#btnCopilotFillJob').addEventListener('click', async () => {
  if (!state.selectedJobId) return;
  showModal(true); setStatus('Copilot analyzing job…', 'busy');
  try {
    const resumeId = qs('#jobResumeSelect').value || state.selectedResumeId || '';
    const myInfo = qs('#jMyInfoArea').value.trim();
    const r = await apiFetch(
      '/api/jobs/' + state.selectedJobId + '/copilot-fill' + (myInfo ? '?my_info=1' : ''),
      { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ my_info: myInfo, resume_id: resumeId }) }
    );
    const f = r.fields || {};
    const myInfoParts = [];
    if (f.summary) myInfoParts.push(`Summary: ${f.summary}`);
    if (f.job_title) myInfoParts.push(`Title: ${f.job_title}`);
    if (f.company) myInfoParts.push(`Company: ${f.company}`);
    if (f.locations?.length) myInfoParts.push(`Locations: ${f.locations.join(', ')}`);
    if (f.job_type) myInfoParts.push(`Job Type: ${f.job_type}`);
    if (f.sponsorship_required) myInfoParts.push(`Sponsorship: ${f.sponsorship_required}`);
    if (f.salary_range) myInfoParts.push(`Salary: ${f.salary_range}`);
    if (f.band_level) myInfoParts.push(`Band: ${f.band_level}`);
    if (f.experience_requirements) myInfoParts.push(`Experience: ${f.experience_requirements}`);
    if (f.deadline) myInfoParts.push(`Deadline: ${f.deadline}`);
    if (myInfo) myInfoParts.push(`User Notes:\n${myInfo}`);
    const mergedMyInfo = myInfoParts.join('\n\n');

    // Update meta grid live
    if (f.locations?.length)           qs('#jLocation').textContent     = f.locations.join(', ');
    if (f.job_type)                     qs('#jType').textContent         = f.job_type;
    if (f.sponsorship_required)         qs('#jSponsorship').textContent  = f.sponsorship_required;
    if (f.salary_range)                 qs('#jSalary').textContent       = f.salary_range;
    if (f.band_level)                   qs('#jBand').textContent         = f.band_level;
    if (f.experience_requirements)      qs('#jExp').textContent          = f.experience_requirements;
    if (f.deadline)                     qs('#jDeadline').textContent     = f.deadline;
    if (f.job_title)                    qs('#jobDetailTitle').textContent = f.job_title;
    if (f.company)                      qs('#jobDetailCompany').textContent = f.company;

    // Show summary and save all extracted info into My Info
    if (f.summary) {
      qs('#jSummaryText').textContent    = f.summary;
      qs('#jSummaryText').style.display  = 'block';
      qs('#jSummaryPlaceholder').style.display = 'none';
    }

    if (mergedMyInfo.trim()) {
      qs('#jMyInfoArea').value = mergedMyInfo;
      await apiJSON('/api/jobs/' + state.selectedJobId, 'PATCH', {
        copilot_summary: f.summary || '',
        my_info: mergedMyInfo,
      });
    }

    updateCliStatus(r.cli_status);
    await loadJobs();
    hideModal(); setStatus('Job filled by Copilot', 'ok');
  } catch(err) { showModal(false, 'Copilot fill failed: ' + err.message); setStatus('Error',''); }
});


qs('#btnSaveJobStatus').addEventListener('click', async () => {
  if (!state.selectedJobId) return;
  try {
    await apiJSON('/api/jobs/'+state.selectedJobId+'/status','PATCH',{ status: qs('#jobStatusSelect').value });
    await loadJobs(); selectJob(state.selectedJobId); setStatus('Status updated','ok');
  } catch(err) { setStatus('Error: '+err.message,''); }
});

qs('#btnDeleteJob').addEventListener('click', async () => {
  if (!state.selectedJobId || !confirm('Delete this job?')) return;
  await apiFetch('/api/jobs/'+state.selectedJobId, { method:'DELETE' });
  state.selectedJobId = null;
  qs('#jobEmptyState').style.display    = 'flex';
  qs('#jobDetailContent').style.display = 'none';
  await loadJobs();
});

qs('#btnSaveMyInfo').addEventListener('click', async () => {
  if (!state.selectedJobId) return;
  await apiJSON('/api/jobs/'+state.selectedJobId, 'PATCH', { my_info: qs('#jMyInfoArea').value });
  await loadJobs();
  selectJob(state.selectedJobId);
  setStatus('My Info saved','ok');
});

/* — Add Job form ————————————————————————————————————————————— */
qs('#btnAddJob').addEventListener('click', () => {
  qs('#addJobBlock').style.display = 'block';
  qs('#btnAddJob').style.display   = 'none';
});
qs('#btnCancelAddJob').addEventListener('click', () => {
  qs('#addJobBlock').style.display = 'none';
  qs('#btnAddJob').style.display   = 'inline-block';
});

qs('#btnSubmitJob').addEventListener('click', async () => {
  const desc = qs('#newJobDesc').value.trim();
  if (!desc) { alert('Paste a job description first'); return; }
  const payload = {
    job_title: '',
    company: '',
    job_url: qs('#newJobUrl').value.trim(),
    description: desc,
  };
  showModal(true);
  try {
    const j = await apiJSON('/api/jobs','POST', payload);
    await loadJobs();
    qs('#addJobBlock').style.display = 'none';
    qs('#btnAddJob').style.display   = 'inline-block';
    ['newJobUrl','newJobDesc']
      .forEach(id => qs('#'+id).value = '');
    hideModal(); selectJob(j.id); setStatus('Job added','ok');
  } catch(err) {
    showModal(false,'Failed: '+err.message);
    setStatus('Error','');
  }
});

/* — Stats ——————————————————————————————————————————————————— */
async function loadJobStats() {
  try {
    const s = await apiFetch('/api/jobs/stats');
    const by = s.by_status || {};
    const getCount = (key) => {
      if (typeof s[key] === 'number') return s[key];
      if (typeof by[key] === 'number') return by[key];
      return 0;
    };
    qs('#statsGrid').innerHTML = [
      ['Total', s.total || 0], ['Applied', getCount('applied')],
      ['Interview', getCount('interview')], ['Offers', getCount('offer')],
      ['Rejected', getCount('rejected')], ['Saved', getCount('saved')],
    ].map(([l,n]) => `<div class="stat-card"><div class="stat-num">${n}</div><div class="stat-lbl">${l}</div></div>`).join('');
  } catch(_) {}
}

/* ══════════════════════ PROFILE ════════════════════════════════ */



/* ══════════════════════ INIT ═══════════════════════════════════ */
qs('#btnClearPromptHistory').addEventListener('click', () => {
  state.copilotRuns = [];
  saveCopilotRuns();
  renderCopilotRuns();
  setStatus('Prompt history cleared', 'ok');
});

qs('#btnRefreshApplicationFiles').addEventListener('click', loadApplicationFiles);

qs('#applicationFilesList').addEventListener('click', async (e) => {
  const target = e.target.closest('button[data-action]');
  if (!target) return;
  const id = target.dataset.id;
  if (!id) return;

  const action = target.dataset.action;
  if (action === 'download-application-file') {
    try {
      const r = await fetch('/api/application-files/' + id + '/download');
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body.error || body.detail || r.statusText);
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = '';
      a.click();
      URL.revokeObjectURL(url);
      setStatus('File downloaded', 'ok');
    } catch (err) {
      setStatus('Download failed: ' + err.message, '');
    }
    return;
  }

  if (action === 'delete-application-file') {
    if (!confirm('Delete this generated file?')) return;
    try {
      await apiFetch('/api/application-files/' + id, { method: 'DELETE' });
      await loadApplicationFiles();
      setStatus('File deleted', 'ok');
    } catch (err) {
      setStatus('Delete failed: ' + err.message, '');
    }
  }
});

async function init() {
  setStatus('Loading\u2026','busy');
    initLatexEditorFontSize();
  loadCopilotRunsFromStorage();
  renderCopilotRuns();
  try {
    const saved = localStorage.getItem(LATEX_PDF_VISIBLE_STORAGE_KEY);
    if (saved === '0') state.latexPdfVisible = false;
    if (saved === '1') state.latexPdfVisible = true;
  } catch (_) {}
  initLatexDivider();
  initRightPaneResizers();
  try { await Promise.all([loadResumes(), loadJobs(), loadApplicationFiles()]); setStatus('Ready','ok'); }
  catch(err) { setStatus('Error loading data',''); console.error(err); }
}
init();
