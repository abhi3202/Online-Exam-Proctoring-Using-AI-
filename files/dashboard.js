/**
 * ProctorDesk — Dashboard Page Controller
 * dashboard.js
 *
 * Controls:
 *  - Topbar elapsed clock
 *  - Countdown timer (time remaining)
 *  - Sidebar navigation active state
 *  - Candidate list filter buttons
 *  - Incident alert actions (warn / dismiss / terminate)
 *  - Camera grid layout switcher
 *  - Alert auto-pulse for new incidents
 */

import {
  $, $$, on, delegate, setActive,
  formatTime, ElapsedClock, CountdownTimer, bus
} from './utils.js';

/* ============================================================
   INIT
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initSidebar();
  initCandidateFilters();
  initCameraGrid();
  initAlertActions();
  initCandidateRows();
  initSearchBar();
});

/* ============================================================
   TOPBAR CLOCK (elapsed) + COUNTDOWN
   ============================================================ */

function initClock() {
  const clockEl     = $('#clock-elapsed');
  const countdownEl = $('#clock-remaining');

  // Elapsed clock — counts up from a fixed start offset (demo: 5924s in)
  if (clockEl) {
    const elapsed = new ElapsedClock({
      start: 5924,
      onTick: (s) => { clockEl.textContent = formatTime(s); }
    });
    elapsed.start();
  }

  // Countdown — 3-hour exam, 1h 38m remaining at page load
  if (countdownEl) {
    const countdown = new CountdownTimer({
      seconds: 4924,
      warnAt:  600,
      onTick:  (s) => { countdownEl.textContent = formatTime(s); },
      onWarn:  ()  => { countdownEl.classList.add('timer-value--warning'); },
      onExpire: ()  => { showToast('Exam time has ended.', 'danger'); }
    });
    countdown.start();
  }
}

/* ============================================================
   SIDEBAR NAVIGATION
   ============================================================ */

function initSidebar() {
  const items = $$('.nav-item');
  delegate(document.querySelector('.app-sidebar'), '.nav-item', 'click', function () {
    setActive(items, this, 'nav-item--active');
  });
}

/* ============================================================
   CANDIDATE FILTER BUTTONS
   ============================================================ */

function initCandidateFilters() {
  const filters = $$('.filter-btn');
  if (!filters.length) return;

  filters.forEach(btn => {
    on(btn, 'click', () => {
      setActive(filters, btn, 'filter-btn--active');
      const mode = btn.dataset.filter ?? 'all';
      filterCandidates(mode);
    });
  });
}

function filterCandidates(mode) {
  const rows = $$('.candidate-row');
  rows.forEach(row => {
    const risk = row.dataset.risk ?? 'clear';
    const show = mode === 'all'
      || (mode === 'flagged'  && ['warning','critical'].includes(risk))
      || (mode === 'critical' && risk === 'critical')
      || (mode === 'offline'  && risk === 'offline');
    row.style.display = show ? '' : 'none';
    // Also hide its separator
    const sep = row.nextElementSibling;
    if (sep?.classList.contains('row-sep')) sep.style.display = show ? '' : 'none';
  });
}

/* ============================================================
   SEARCH BAR
   ============================================================ */

function initSearchBar() {
  const input = $('.search-bar input');
  if (!input) return;

  import('./utils.js').then(({ debounce }) => {
    on(input, 'input', debounce((e) => {
      const query = e.target.value.toLowerCase().trim();
      $$('.candidate-row').forEach(row => {
        const name = row.querySelector('.candidate-name')?.textContent.toLowerCase() ?? '';
        const meta = row.querySelector('.candidate-meta')?.textContent.toLowerCase() ?? '';
        const match = !query || name.includes(query) || meta.includes(query);
        row.style.display = match ? '' : 'none';
      });
    }, 200));
  });
}

/* ============================================================
   CAMERA GRID LAYOUT SWITCHER
   ============================================================ */

function initCameraGrid() {
  const layoutBtns = $$('.cam-layout-btn');
  const grid       = $('.cam-grid');
  if (!grid || !layoutBtns.length) return;

  layoutBtns.forEach(btn => {
    on(btn, 'click', () => {
      setActive(layoutBtns, btn, 'filter-btn--active');
      const layout = btn.dataset.layout;
      grid.className = `cam-grid cam-grid--${layout}`;
    });
  });
}

/* ============================================================
   INCIDENT ALERT ACTIONS
   ============================================================ */

function initAlertActions() {
  const panel = $('.alerts-panel, .card[data-panel="alerts"]');
  if (!panel) return;

  delegate(panel, '[data-action]', 'click', function (e, btn) {
    e.stopPropagation();
    const action      = btn.dataset.action;
    const alertItem   = btn.closest('.alert-item');
    const candidateId = alertItem?.dataset.candidate;

    switch (action) {
      case 'dismiss':
        dismissAlert(alertItem);
        break;
      case 'warn':
        sendWarning(candidateId, alertItem);
        break;
      case 'terminate':
        confirmTerminate(candidateId, alertItem);
        break;
      case 'clear-all':
        $$('.alert-item').forEach(dismissAlert);
        break;
    }
  });
}

function dismissAlert(alertItem) {
  if (!alertItem) return;
  alertItem.style.opacity = '0';
  alertItem.style.transition = 'opacity 0.2s ease';
  setTimeout(() => alertItem.remove(), 200);
  updateAlertCount();
}

function sendWarning(candidateId, alertItem) {
  showToast(`Warning sent to candidate ${candidateId ?? ''}`, 'warning');
  dismissAlert(alertItem);
  bus.emit('warning:sent', { candidateId });
}

function confirmTerminate(candidateId, alertItem) {
  const confirmed = window.confirm(
    `Terminate exam session for candidate ${candidateId ?? 'this candidate'}?\nThis action cannot be undone.`
  );
  if (confirmed) {
    showToast(`Session terminated for ${candidateId ?? 'candidate'}`, 'danger');
    dismissAlert(alertItem);
    bus.emit('session:terminated', { candidateId });
    markCandidateOffline(candidateId);
  }
}

function updateAlertCount() {
  const countEl = $('#alert-count');
  if (!countEl) return;
  const remaining = $$('.alert-item').length;
  countEl.textContent = remaining;
  if (remaining === 0) countEl.style.display = 'none';
}

function markCandidateOffline(candidateId) {
  const row = $(`.candidate-row[data-id="${candidateId}"]`);
  if (!row) return;
  const badge = row.querySelector('.risk-badge');
  if (badge) {
    badge.className = 'risk-badge risk-badge--offline';
    badge.textContent = 'Offline';
  }
  row.classList.remove('candidate-row--critical');
  row.dataset.risk = 'offline';
}

/* ============================================================
   CANDIDATE ROW CLICK — navigate to profile
   ============================================================ */

function initCandidateRows() {
  delegate(document.body, '.candidate-row', 'click', function (e, row) {
    const id = row.dataset.id;
    if (id) {
      // In a real SPA: router.push(`/candidates/${id}`)
      // For demo: just emit an event
      bus.emit('candidate:selected', { id });
    }
  });
}

/* ============================================================
   TOAST NOTIFICATION
   ============================================================ */

function showToast(message, type = 'info') {
  let container = $('#toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    Object.assign(container.style, {
      position: 'fixed',
      bottom:   '24px',
      right:    '24px',
      display:  'flex',
      flexDirection: 'column',
      gap: '8px',
      zIndex: '999',
    });
    document.body.appendChild(container);
  }

  const colorMap = {
    info:    { bg: 'var(--blue-50)',   color: 'var(--blue-800)',  border: 'var(--color-border-info)' },
    success: { bg: 'var(--green-50)',  color: 'var(--green-800)', border: 'var(--color-border-success)' },
    warning: { bg: 'var(--amber-50)',  color: 'var(--amber-800)', border: 'var(--color-border-warning)' },
    danger:  { bg: 'var(--red-50)',    color: 'var(--red-800)',   border: 'var(--color-border-danger)' },
  };

  const { bg, color, border } = colorMap[type] ?? colorMap.info;

  const toast = document.createElement('div');
  toast.textContent = message;
  Object.assign(toast.style, {
    background:   bg,
    color:        color,
    border:       `0.5px solid ${border}`,
    borderRadius: 'var(--border-radius-md)',
    padding:      '10px 16px',
    fontSize:     '13px',
    maxWidth:     '300px',
    opacity:      '0',
    transition:   'opacity 0.2s ease',
    boxShadow:    'none',
  });

  container.appendChild(toast);
  requestAnimationFrame(() => { toast.style.opacity = '1'; });

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 200);
  }, 3500);
}

// Expose for non-module usage in HTML onclick attributes
window.ProctorDeskDashboard = { showToast, filterCandidates };
