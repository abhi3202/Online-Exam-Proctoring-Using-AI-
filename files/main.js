/**
 * ProctorDesk — Application Entry Point
 * main.js
 *
 * Auto-detects the current page from <body data-page="...">
 * and bootstraps the correct page controller.
 *
 * Usage in HTML:
 *   <body data-page="dashboard">  → loads dashboard.js
 *   <body data-page="exam">       → loads exam.js
 *   <body data-page="profile">    → loads profile.js
 *
 * Also registers global shared behaviours available on all pages.
 */

/* ============================================================
   PAGE DETECTION & LAZY LOAD
   ============================================================ */

const PAGE = document.body.dataset.page ?? '';

(async () => {
  switch (PAGE) {
    case 'dashboard':
      await import('./dashboard.js');
      break;
    case 'exam':
      await import('./exam.js');
      break;
    case 'profile':
      await import('./profile.js');
      break;
    default:
      console.warn(`[ProctorDesk] Unknown page: "${PAGE}". No page controller loaded.`);
  }
})();

/* ============================================================
   GLOBAL SHARED BEHAVIOURS (run on every page)
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initTooltips();
  initGlobalKeyboard();
  announceLiveRegion();
});

/* ============================================================
   THEME (light / dark)
   ============================================================ */

function initThemeToggle() {
  const btn = document.getElementById('btn-theme');
  if (!btn) return;

  // Restore saved preference
  const saved = localStorage.getItem('pd-theme');
  if (saved === 'dark')  document.documentElement.setAttribute('data-theme', 'dark');
  if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');

  btn.addEventListener('click', () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const next   = isDark ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('pd-theme', next);
    btn.setAttribute('aria-label', `Switch to ${isDark ? 'dark' : 'light'} mode`);
  });
}

/* ============================================================
   SIMPLE TOOLTIP SYSTEM
   Attach data-tooltip="…" to any element.
   ============================================================ */

function initTooltips() {
  let tip = null;

  document.addEventListener('mouseover', (e) => {
    const el  = e.target.closest('[data-tooltip]');
    if (!el) return;
    const msg = el.dataset.tooltip;
    if (!msg) return;

    tip = document.createElement('div');
    tip.textContent = msg;
    Object.assign(tip.style, {
      position:     'fixed',
      background:   'var(--color-background-primary)',
      border:       '0.5px solid var(--color-border-secondary)',
      borderRadius: 'var(--border-radius-md)',
      padding:      '5px 10px',
      fontSize:     '12px',
      color:        'var(--color-text-primary)',
      pointerEvents:'none',
      zIndex:       '800',
      whiteSpace:   'nowrap',
      opacity:      '0',
      transition:   'opacity 0.15s ease',
    });
    document.body.appendChild(tip);

    const rect = el.getBoundingClientRect();
    tip.style.left = `${rect.left + rect.width / 2 - tip.offsetWidth / 2}px`;
    tip.style.top  = `${rect.bottom + 6}px`;

    requestAnimationFrame(() => { tip.style.opacity = '1'; });
  });

  document.addEventListener('mouseout', (e) => {
    if (tip && !e.target.closest('[data-tooltip]')) {
      tip.remove();
      tip = null;
    }
  });
}

/* ============================================================
   GLOBAL KEYBOARD SHORTCUTS
   ============================================================ */

function initGlobalKeyboard() {
  document.addEventListener('keydown', (e) => {
    // Escape: close any open modals/overlays
    if (e.key === 'Escape') {
      const overlay = document.querySelector('[data-overlay]');
      if (overlay) overlay.remove();
    }

    // Cmd/Ctrl + K: focus search bar
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      const search = document.querySelector('.search-bar input');
      if (search) search.focus();
    }
  });
}

/* ============================================================
   ARIA LIVE REGION (for screen-reader announcements)
   ============================================================ */

function announceLiveRegion() {
  if (document.getElementById('live-region')) return;

  const region = document.createElement('div');
  region.id = 'live-region';
  region.setAttribute('aria-live', 'polite');
  region.setAttribute('aria-atomic', 'true');
  Object.assign(region.style, {
    position: 'absolute',
    width:    '1px',
    height:   '1px',
    overflow: 'hidden',
    clip:     'rect(0,0,0,0)',
    whiteSpace: 'nowrap',
  });
  document.body.appendChild(region);
}

/**
 * Announce a message to screen readers.
 * @param {string} message
 */
export function announce(message) {
  const region = document.getElementById('live-region');
  if (!region) return;
  region.textContent = '';
  requestAnimationFrame(() => { region.textContent = message; });
}

/* ============================================================
   HTML USAGE GUIDE (not executed — documentation only)
   ============================================================

  DASHBOARD:
  ----------
  <html>
    <head>
      <link rel="stylesheet" href="css/variables.css">
      <link rel="stylesheet" href="css/base.css">
      <link rel="stylesheet" href="css/components.css">
      <link rel="stylesheet" href="css/pages.css">
    </head>
    <body data-page="dashboard">
      <!-- markup here -->
      <script type="module" src="js/main.js"></script>
    </body>
  </html>

  EXAM PAGE:
  ----------
  <body data-page="exam">
    <!-- countdown timer: <span id="exam-timer"> -->
    <!-- answer options:  <div class="answer-options">
                            <div class="answer-option" data-option="A"> ... </div>
                         </div> -->
    <!-- next button:     <button id="btn-next"> -->
    <!-- prev button:     <button id="btn-prev"> -->
    <!-- skip button:     <button id="btn-skip"> -->
    <!-- clear button:    <button id="btn-clear"> -->
    <!-- submit button:   <button id="btn-submit"> -->
    <!-- q palette:       <div class="q-palette">
                            <div class="q-cell" data-index="0">1</div>
                         </div> -->
    <!-- section tabs:    <button class="section-tab" data-section="A">Sec A</button> -->
    <!-- progress fill:   <div id="progress-fill" class="progress-bar__fill"> -->
    <!-- stats:           <span id="stat-answered">, #stat-skipped, #stat-remaining, #stat-pct -->
    <!-- section bars:    <div id="sec-bar-A" class="progress-bar__fill">, #sec-count-A etc. -->
  </body>

  PROFILE PAGE:
  -------------
  <body data-page="profile">
    <!-- stat cards:    <span id="stat-incidents">, #stat-progress, #stat-answered, #stat-time -->
    <!-- action btns:  <button id="btn-download">, #btn-warn, #btn-terminate -->
    <!-- incident log: <div id="incident-log"> -->
    <!-- notes input:  <textarea id="proctor-note-input"> -->
    <!-- notes btn:    <button id="btn-add-note"> -->
    <!-- notes list:   <div id="notes-list"> -->
    <!-- palette:      .q-cell with data-index -->
    <!-- snaps:        .profile-snap (click to lightbox) -->
    <!-- progress:     <div id="progress-fill" class="progress-bar__fill"> -->
    <!-- palette stats: #palette-answered, #palette-skipped, #palette-remaining, #palette-time -->
  </body>

  ============================================================ */
