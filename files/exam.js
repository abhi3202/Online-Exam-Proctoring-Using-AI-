/**
 * ProctorDesk — Exam Page Controller (Student View)
 * exam.js
 *
 * Controls:
 *  - Countdown timer display + warning state
 *  - Answer option selection
 *  - Question palette state (answered / skipped / current / unvisited)
 *  - Section tab switching (palette filter)
 *  - Previous / Save & Next navigation
 *  - Mark for review + clear response
 *  - Submit exam confirmation dialog
 *  - Anti-cheating detection hooks (tab visibility, fullscreen exit)
 */

import {
  $, $$, on, delegate, setActive,
  formatTime, CountdownTimer, bus
} from './utils.js';

/* ============================================================
   EXAM STATE
   ============================================================ */

const TOTAL_QUESTIONS = 30;
const EXAM_DURATION_S = 3 * 60 * 60; // 3 hours in seconds

// Q state: 'unvisited' | 'answered' | 'skipped' | 'review'
const questionState = Array.from({ length: TOTAL_QUESTIONS }, (_, i) => ({
  id:       i + 1,
  state:    'unvisited',
  answer:   null,  // 'A' | 'B' | 'C' | 'D' | null
  section:  i < 10 ? 'A' : i < 20 ? 'B' : i < 25 ? 'C' : 'D',
  timeSpent: 0,    // seconds
}));

// Pre-fill demo state matching the design
questionState[0].state = 'answered'; questionState[0].answer = 'B';
questionState[1].state = 'answered'; questionState[1].answer = 'C';
questionState[2].state = 'answered'; questionState[2].answer = 'A';
questionState[3].state = 'answered'; questionState[3].answer = 'D';
questionState[4].state = 'skipped';
questionState[5].state = 'answered'; questionState[5].answer = 'A';
questionState[6].state = 'answered'; questionState[6].answer = 'B';
questionState[7].state = 'answered'; questionState[7].answer = 'C';
questionState[8].state = 'skipped';
questionState[9].state = 'answered'; questionState[9].answer = 'B'; // Q10 — current

let currentQuestion = 9; // 0-indexed, Q10
let activeSection   = 'A';

/* ============================================================
   INIT
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  initTimer();
  initAnswerOptions();
  initNavButtons();
  initPalette();
  initSectionTabs();
  initSubmit();
  initAntiCheating();
  refreshPalette();
  refreshStats();
});

/* ============================================================
   COUNTDOWN TIMER
   ============================================================ */

function initTimer() {
  const timerEl = $('#exam-timer');
  if (!timerEl) return;

  const timer = new CountdownTimer({
    seconds:  4924,
    warnAt:   600,
    onTick:   (s) => { timerEl.textContent = formatTime(s); },
    onWarn:   ()  => {
      timerEl.classList.add('timer-value--warning');
      showWarning('Less than 10 minutes remaining. Please review your answers.');
    },
    onExpire: ()  => {
      showWarning('Time is up! Your exam is being submitted automatically.');
      setTimeout(submitExam, 3000);
    },
  });

  timer.start();

  // Track time per question
  setInterval(() => {
    questionState[currentQuestion].timeSpent++;
  }, 1000);
}

/* ============================================================
   ANSWER OPTION SELECTION
   ============================================================ */

function initAnswerOptions() {
  const optionsContainer = $('.answer-options');
  if (!optionsContainer) return;

  delegate(optionsContainer, '.answer-option', 'click', function (e, opt) {
    const selected = opt.dataset.option; // 'A' | 'B' | 'C' | 'D'
    selectAnswer(selected, opt);
  });
}

function selectAnswer(option, clickedEl) {
  // Deselect all
  $$('.answer-option').forEach(el => el.classList.remove('answer-option--selected'));
  $$('.answer-option .answer-option__key').forEach(k => {
    k.style.background  = '';
    k.style.color       = '';
    k.style.borderColor = '';
  });

  // Select clicked
  if (clickedEl) {
    clickedEl.classList.add('answer-option--selected');
    const key = clickedEl.querySelector('.answer-option__key');
    if (key) {
      key.style.background  = 'var(--blue-400)';
      key.style.color       = '#fff';
      key.style.borderColor = 'transparent';
    }
  }

  // Persist to state
  questionState[currentQuestion].answer = option;
  if (questionState[currentQuestion].state !== 'review') {
    questionState[currentQuestion].state = 'answered';
  }

  refreshPalette();
  refreshStats();
}

/* ============================================================
   NAVIGATION BUTTONS (Prev / Next / Skip / Clear)
   ============================================================ */

function initNavButtons() {
  const btnNext = $('#btn-next');
  const btnPrev = $('#btn-prev');
  const btnSkip = $('#btn-skip');
  const btnClear = $('#btn-clear');

  on(btnNext,  'click', () => saveAndNext());
  on(btnPrev,  'click', () => goTo(currentQuestion - 1));
  on(btnSkip,  'click', () => markForReview());
  on(btnClear, 'click', () => clearResponse());
}

function saveAndNext() {
  // If unanswered, mark skipped
  if (!questionState[currentQuestion].answer) {
    questionState[currentQuestion].state = 'skipped';
  }
  if (currentQuestion < TOTAL_QUESTIONS - 1) {
    goTo(currentQuestion + 1);
  } else {
    // Last question — prompt submit
    showSubmitDialog();
  }
}

function goTo(index) {
  if (index < 0 || index >= TOTAL_QUESTIONS) return;

  currentQuestion = index;

  // Mark as visited if unvisited
  if (questionState[index].state === 'unvisited') {
    questionState[index].state = 'unvisited'; // stays until answered
  }

  refreshQuestion();
  refreshPalette();
  refreshStats();
  updateNavButtons();
}

function markForReview() {
  questionState[currentQuestion].state = 'review';
  questionState[currentQuestion].answer = null;
  goTo(currentQuestion + 1 < TOTAL_QUESTIONS ? currentQuestion + 1 : currentQuestion);
}

function clearResponse() {
  questionState[currentQuestion].answer = null;
  questionState[currentQuestion].state  = 'unvisited';

  $$('.answer-option').forEach(el => el.classList.remove('answer-option--selected'));
  $$('.answer-option__key').forEach(k => {
    k.style.background  = '';
    k.style.color       = '';
    k.style.borderColor = '';
  });

  refreshPalette();
  refreshStats();
}

function updateNavButtons() {
  const btnPrev = $('#btn-prev');
  const btnNext = $('#btn-next');
  if (btnPrev) btnPrev.disabled = currentQuestion === 0;
  if (btnNext) btnNext.textContent = currentQuestion === TOTAL_QUESTIONS - 1
    ? 'Submit exam' : 'Save & next →';
}

/* ============================================================
   REFRESH QUESTION DISPLAY
   ============================================================ */

function refreshQuestion() {
  const qNum = currentQuestion + 1;

  // Update question number
  const numEl = $('.question-card__num');
  if (numEl) numEl.textContent = `Question ${qNum} of ${TOTAL_QUESTIONS} · Section ${questionState[currentQuestion].section}`;

  // Restore selected answer in UI
  const savedAnswer = questionState[currentQuestion].answer;
  $$('.answer-option').forEach(opt => {
    const isSelected = opt.dataset.option === savedAnswer;
    opt.classList.toggle('answer-option--selected', isSelected);
    const key = opt.querySelector('.answer-option__key');
    if (key) {
      key.style.background  = isSelected ? 'var(--blue-400)' : '';
      key.style.color       = isSelected ? '#fff' : '';
      key.style.borderColor = isSelected ? 'transparent' : '';
    }
  });

  updateNavButtons();
}

/* ============================================================
   QUESTION PALETTE
   ============================================================ */

function initPalette() {
  const palette = $('.q-palette');
  if (!palette) return;

  delegate(palette, '.q-cell', 'click', function (e, cell) {
    const idx = parseInt(cell.dataset.index, 10);
    if (!isNaN(idx)) goTo(idx);
  });
}

function refreshPalette() {
  const cells = $$('.q-cell');
  cells.forEach((cell, idx) => {
    const section = questionState[idx]?.section;

    // Section filter
    if (activeSection !== 'all' && section !== activeSection) {
      cell.style.visibility = 'hidden';
    } else {
      cell.style.visibility = '';
    }

    const state = idx === currentQuestion ? 'current' : questionState[idx]?.state;

    cell.className = 'q-cell';
    switch (state) {
      case 'current':   cell.classList.add('q-cell--current');   break;
      case 'answered':  cell.classList.add('q-cell--answered');  break;
      case 'skipped':   cell.classList.add('q-cell--skipped');   break;
      case 'review':    cell.classList.add('q-cell--skipped');   break;
      default:          cell.classList.add('q-cell--unvisited'); break;
    }
  });
}

/* ============================================================
   SECTION TABS
   ============================================================ */

function initSectionTabs() {
  const tabs = $$('.section-tab');
  tabs.forEach(tab => {
    on(tab, 'click', () => {
      setActive(tabs, tab, 'section-tab--active');
      activeSection = tab.dataset.section ?? 'all';
      refreshPalette();
    });
  });
}

/* ============================================================
   STATS SIDEBAR REFRESH
   ============================================================ */

function refreshStats() {
  const answered  = questionState.filter(q => q.state === 'answered').length;
  const skipped   = questionState.filter(q => q.state === 'skipped').length;
  const remaining = TOTAL_QUESTIONS - answered - skipped;
  const pct       = Math.round((answered / TOTAL_QUESTIONS) * 100);

  const setEl = (id, val) => { const el = $(`#${id}`); if (el) el.textContent = val; };

  setEl('stat-answered',  answered);
  setEl('stat-skipped',   skipped);
  setEl('stat-remaining', remaining);
  setEl('stat-pct',       `${pct}%`);

  const fillEl = $('#progress-fill');
  if (fillEl) fillEl.style.width = `${pct}%`;

  // Section breakdown bars
  ['A','B','C','D'].forEach(sec => {
    const secQs  = questionState.filter(q => q.section === sec);
    const done   = secQs.filter(q => q.state === 'answered').length;
    const barEl  = $(`#sec-bar-${sec}`);
    const cntEl  = $(`#sec-count-${sec}`);
    if (barEl) barEl.style.width = `${Math.round((done / secQs.length) * 100)}%`;
    if (cntEl) cntEl.textContent = `${done}/${secQs.length}`;
  });
}

/* ============================================================
   SUBMIT EXAM
   ============================================================ */

function initSubmit() {
  const submitBtn = $('#btn-submit');
  if (submitBtn) on(submitBtn, 'click', showSubmitDialog);
}

function showSubmitDialog() {
  const answered  = questionState.filter(q => q.state === 'answered').length;
  const unanswered = TOTAL_QUESTIONS - answered;
  const msg = unanswered > 0
    ? `You have ${unanswered} unanswered question(s).\nAre you sure you want to submit?`
    : 'Are you sure you want to submit your exam?';

  if (window.confirm(msg)) submitExam();
}

function submitExam() {
  // In a real app: POST to server, redirect to confirmation page
  const overlay = document.createElement('div');
  overlay.innerHTML = `
    <div style="position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:999">
      <div style="background:var(--color-background-primary);border-radius:var(--border-radius-lg);padding:32px;text-align:center;max-width:320px;">
        <div style="font-size:16px;font-weight:500;color:var(--color-text-primary);margin-bottom:8px">Exam submitted</div>
        <div style="font-size:13px;color:var(--color-text-secondary)">Your responses have been recorded. You may close this window.</div>
      </div>
    </div>`;
  document.body.appendChild(overlay);
}

/* ============================================================
   ANTI-CHEATING DETECTION
   ============================================================ */

function initAntiCheating() {
  let tabSwitchCount = 0;

  // Tab visibility change
  on(document, 'visibilitychange', () => {
    if (document.hidden) {
      tabSwitchCount++;
      bus.emit('cheat:tab-switch', { count: tabSwitchCount, question: currentQuestion + 1 });

      if (tabSwitchCount === 1) {
        showWarning('Tab switch detected. Please return to the exam window.');
      } else if (tabSwitchCount === 2) {
        showWarning('Second tab switch detected. A warning has been sent to your proctor.');
      } else {
        showWarning('Multiple tab switches detected. Your proctor has been notified.');
      }
    }
  });

  // Copy-paste prevention
  on(document, 'copy',  e => e.preventDefault());
  on(document, 'cut',   e => e.preventDefault());
  on(document, 'paste', e => e.preventDefault());

  // Right-click prevention
  on(document, 'contextmenu', e => e.preventDefault());

  // Fullscreen exit detection
  on(document, 'fullscreenchange', () => {
    if (!document.fullscreenElement) {
      showWarning('You have exited fullscreen mode. Please return to fullscreen.');
    }
  });
}

/* ============================================================
   INLINE WARNING BANNER
   ============================================================ */

function showWarning(message) {
  let bar = $('.warn-bar');
  if (!bar) {
    bar = document.createElement('div');
    bar.className = 'warn-bar';
    const examMain = $('.exam-main');
    if (examMain) examMain.prepend(bar);
  }
  bar.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style="flex-shrink:0">
      <path d="M8 2L14.5 13H1.5L8 2z" stroke="#854F0B" stroke-width="1.2" stroke-linejoin="round"/>
      <path d="M8 6v3M8 11v.5" stroke="#854F0B" stroke-width="1.2" stroke-linecap="round"/>
    </svg>
    ${message}
  `;
  bar.style.display = 'flex';

  clearTimeout(bar._timeout);
  bar._timeout = setTimeout(() => { bar.style.display = 'none'; }, 8000);
}

// Expose state for debugging
window.ExamState = { questionState, getCurrentQuestion: () => currentQuestion };
