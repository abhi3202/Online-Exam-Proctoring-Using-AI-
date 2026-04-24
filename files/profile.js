/**
 * ProctorDesk — Student Profile Page Controller (Proctor View)
 * profile.js
 *
 * Controls:
 *  - Breadcrumb navigation
 *  - Profile action buttons (warn / terminate / download)
 *  - Question palette clicks (highlight detail)
 *  - Incident log rendering
 *  - Proctor notes (add / list)
 *  - Camera snapshot expand (lightbox)
 *  - Device info table
 */

import { $, $$, on, delegate, formatTime, bus } from './utils.js';

/* ============================================================
   CANDIDATE DATA (demo — replace with API fetch)
   ============================================================ */

const candidate = {
  id:       'RK029',
  name:     'Rahul Kapoor',
  initials: 'RK',
  roll:     '2024-CS-029',
  course:   'B.Tech Computer Science',
  semester: '4',
  examName: 'Advanced Mathematics',
  risk:     'critical',
  browser:  'Chrome 124.0',
  os:       'Windows 11',
  screen:   '1920 × 1080',
  loginAt:  '12:58 PM',
  ip:       '103.24.xx.xx',
  location: 'Hyderabad, IN',
  progress: 41,
  answered: 9,
  skipped:  2,
  timeSpentS: 5820, // 1h 37m
  incidents: [
    { id: 1, type: 'critical', text: 'Second person detected in camera frame', time: '2:41 PM', source: 'AI detection' },
    { id: 2, type: 'critical', text: 'Tab switch detected (3rd occurrence) — session locked', time: '2:38 PM', source: 'System event' },
    { id: 3, type: 'warning',  text: 'Warning sent: tab switch (2nd time)', time: '2:31 PM', source: 'Proctor action' },
    { id: 4, type: 'warning',  text: 'Warning sent: tab switch (1st time)', time: '2:24 PM', source: 'Proctor action' },
    { id: 5, type: 'info',     text: 'Unusual eye movement pattern flagged', time: '2:10 PM', source: 'AI detection' },
    { id: 6, type: 'info',     text: 'Identity verified — exam started', time: '1:00 PM', source: 'System event' },
  ],
  notes: [],
};

/* ============================================================
   INIT
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  renderProfile();
  initActions();
  initPaletteClicks();
  initNotes();
  initSnapshotLightbox();
  initIncidentActions();
});

/* ============================================================
   RENDER PROFILE (populate dynamic fields)
   ============================================================ */

function renderProfile() {
  // Stat values
  setEl('#stat-incidents', candidate.incidents.filter(i => ['critical','warning'].includes(i.type)).length);
  setEl('#stat-progress',  `${candidate.progress}%`);
  setEl('#stat-answered',  candidate.answered);
  setEl('#stat-time',      formatTime(candidate.timeSpentS));

  // Progress fill
  const fill = $('#progress-fill');
  if (fill) fill.style.width = `${candidate.progress}%`;

  // Palette stats
  setEl('#palette-answered',  candidate.answered);
  setEl('#palette-skipped',   candidate.skipped);
  setEl('#palette-remaining', 30 - candidate.answered - candidate.skipped);
  setEl('#palette-time',      formatTime(candidate.timeSpentS));
}

function setEl(selector, value) {
  const el = $(selector);
  if (el) el.textContent = value;
}

/* ============================================================
   ACTION BUTTONS (topbar)
   ============================================================ */

function initActions() {
  on($('#btn-download'), 'click', downloadReport);
  on($('#btn-warn'),     'click', sendWarning);
  on($('#btn-terminate'),'click', terminateSession);
}

function downloadReport() {
  // In production: generate PDF and trigger download
  alert(`Downloading proctoring report for ${candidate.name} (${candidate.roll})…`);
}

function sendWarning() {
  const confirmed = window.confirm(`Send a formal warning to ${candidate.name}?`);
  if (!confirmed) return;

  addIncidentToLog({
    type: 'warning',
    text: 'Manual warning sent by proctor',
    time: currentTime(),
    source: 'Proctor action',
  });

  showToast(`Warning sent to ${candidate.name}`, 'warning');
  bus.emit('warning:sent', { candidateId: candidate.id });
}

function terminateSession() {
  const confirmed = window.confirm(
    `Terminate exam session for ${candidate.name} (${candidate.roll})?\nThis will immediately end their exam and cannot be undone.`
  );
  if (!confirmed) return;

  addIncidentToLog({
    type: 'critical',
    text: 'Session terminated by proctor',
    time: currentTime(),
    source: 'Proctor action',
  });

  // Update risk badge
  const badge = $('.risk-badge');
  if (badge) {
    badge.textContent = 'Terminated';
    badge.className   = 'risk-badge risk-badge--offline';
  }

  // Disable action buttons
  $$('#btn-warn, #btn-terminate').forEach(btn => {
    btn.disabled = true;
    btn.style.opacity = '0.4';
  });

  showToast(`Session terminated for ${candidate.name}`, 'danger');
  bus.emit('session:terminated', { candidateId: candidate.id });
}

/* ============================================================
   QUESTION PALETTE INTERACTION
   ============================================================ */

function initPaletteClicks() {
  delegate(document.body, '.q-cell', 'click', function (e, cell) {
    const idx = parseInt(cell.dataset.index, 10);
    if (isNaN(idx)) return;
    showQuestionDetail(idx + 1);
  });
}

function showQuestionDetail(qNum) {
  // Highlight the clicked cell
  $$('.q-cell').forEach((c, i) => {
    c.style.outline = (i === qNum - 1) ? `2px solid var(--blue-400)` : '';
  });
  // In production: open question detail panel or scroll to a Q detail card
  console.info(`Proctor viewing Q${qNum} for ${candidate.roll}`);
}

/* ============================================================
   PROCTOR NOTES
   ============================================================ */

function initNotes() {
  const textarea  = $('#proctor-note-input');
  const addBtn    = $('#btn-add-note');
  const notesList = $('#notes-list');

  if (!addBtn || !textarea) return;

  on(addBtn, 'click', () => {
    const text = textarea.value.trim();
    if (!text) return;

    const note = { text, time: currentTime(), id: Date.now() };
    candidate.notes.push(note);
    renderNote(note, notesList);
    textarea.value = '';

    addIncidentToLog({
      type: 'info',
      text: `Proctor note added: "${text.slice(0, 60)}${text.length > 60 ? '…' : ''}"`,
      time: note.time,
      source: 'Proctor note',
    });
  });

  // Allow Ctrl+Enter to submit
  on(textarea, 'keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) addBtn.click();
  });
}

function renderNote(note, container) {
  if (!container) return;
  const el = document.createElement('div');
  el.className = 'incident-row';
  el.dataset.noteId = note.id;
  el.innerHTML = `
    <span class="badge badge--neutral" style="font-size:10px;padding:1px 6px">Note</span>
    <span class="incident-row__text">${escapeHtml(note.text)}</span>
    <span class="incident-row__time">${note.time}</span>
  `;
  container.prepend(el);
}

/* ============================================================
   DYNAMIC INCIDENT LOG
   ============================================================ */

function initIncidentActions() {
  const log = $('#incident-log');
  if (!log) return;

  delegate(log, '[data-action]', 'click', function (e, btn) {
    e.stopPropagation();
    const action = btn.dataset.action;
    const row    = btn.closest('.incident-row, .alert-item');
    if (action === 'dismiss-incident' && row) {
      row.style.opacity = '0';
      row.style.transition = 'opacity 0.2s';
      setTimeout(() => row.remove(), 200);
    }
  });
}

function addIncidentToLog(incident) {
  const log = $('#incident-log');
  if (!log) return;

  const typeClasses = { critical: 'isev-c', warning: 'isev-w', info: 'isev-i' };
  const typeLabels  = { critical: 'Critical', warning: 'Warning', info: 'Info' };

  const el = document.createElement('div');
  el.className = 'incident-row';
  el.innerHTML = `
    <span class="alert-item__severity alert-item__severity--${incident.type}">
      ${typeLabels[incident.type] ?? 'Info'}
    </span>
    <span class="incident-row__text">${escapeHtml(incident.text)}</span>
    <span class="incident-row__time">${incident.time}</span>
  `;
  log.prepend(el);
}

/* ============================================================
   CAMERA SNAPSHOT LIGHTBOX
   ============================================================ */

function initSnapshotLightbox() {
  delegate(document.body, '.profile-snap', 'click', function (e, snap) {
    const label    = snap.querySelector('.cam-thumb__label, .snap-label')?.textContent ?? '';
    const flagged  = snap.classList.contains('profile-snap--flagged');

    showLightbox(label, flagged);
  });
}

function showLightbox(label, flagged) {
  const overlay = document.createElement('div');
  overlay.style.cssText = `
    position:fixed;inset:0;background:rgba(0,0,0,0.7);
    display:flex;align-items:center;justify-content:center;z-index:500;cursor:zoom-out;
  `;

  const box = document.createElement('div');
  box.style.cssText = `
    background:var(--color-background-secondary);
    border-radius:var(--border-radius-lg);
    border:${flagged ? '2px solid var(--red-400)' : '0.5px solid var(--color-border-tertiary)'};
    padding:24px;
    min-width:320px;
    text-align:center;
    color:var(--color-text-primary);
  `;
  box.innerHTML = `
    <div style="font-size:13px;font-weight:500;margin-bottom:8px">${escapeHtml(label)}</div>
    <div style="font-size:12px;color:var(--color-text-secondary)">
      ${flagged ? '<span style="color:var(--red-800)">Flagged frame</span>' : 'Clear frame'}
    </div>
    <div style="margin-top:16px;font-size:11px;color:var(--color-text-tertiary)">Click anywhere to close</div>
  `;

  overlay.appendChild(box);
  document.body.appendChild(overlay);
  on(overlay, 'click', () => overlay.remove());
}

/* ============================================================
   HELPERS
   ============================================================ */

function currentTime() {
  return new Date().toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' });
}

function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function showToast(message, type = 'info') {
  // Import and reuse dashboard's showToast or a standalone version
  let container = $('#toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    Object.assign(container.style, {
      position: 'fixed', bottom: '24px', right: '24px',
      display: 'flex', flexDirection: 'column', gap: '8px', zIndex: '999',
    });
    document.body.appendChild(container);
  }

  const colors = {
    info:    { bg: 'var(--blue-50)',   color: 'var(--blue-800)',  border: 'var(--color-border-info)' },
    warning: { bg: 'var(--amber-50)',  color: 'var(--amber-800)', border: 'var(--color-border-warning)' },
    danger:  { bg: 'var(--red-50)',    color: 'var(--red-800)',   border: 'var(--color-border-danger)' },
    success: { bg: 'var(--green-50)',  color: 'var(--green-800)', border: 'var(--color-border-success)' },
  };

  const { bg, color, border } = colors[type] ?? colors.info;
  const toast = document.createElement('div');
  toast.textContent = message;
  Object.assign(toast.style, {
    background: bg, color, border: `0.5px solid ${border}`,
    borderRadius: 'var(--border-radius-md)', padding: '10px 16px',
    fontSize: '13px', maxWidth: '300px', opacity: '0',
    transition: 'opacity 0.2s ease',
  });

  container.appendChild(toast);
  requestAnimationFrame(() => { toast.style.opacity = '1'; });
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 200);
  }, 3500);
}
