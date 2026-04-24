/**
 * ProctorDesk — Core Utilities
 * utils.js
 *
 * Shared helpers used across all pages.
 * No dependencies — pure ES6+.
 */

'use strict';

/* ============================================================
   TIME & FORMATTING
   ============================================================ */

/**
 * Format seconds into HH:MM:SS string.
 * @param {number} totalSeconds
 * @returns {string} e.g. "01:22:04"
 */
export function formatTime(totalSeconds) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return [h, m, s].map(n => String(n).padStart(2, '0')).join(':');
}

/**
 * Format a Date to "h:mm AM/PM" local time string.
 * @param {Date} date
 * @returns {string} e.g. "2:41 PM"
 */
export function formatClock(date) {
  return date.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' });
}

/**
 * Return "X min ago" / "just now" relative string from a Date.
 * @param {Date} date
 * @returns {string}
 */
export function timeAgo(date) {
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  return `${Math.floor(diff / 3600)} hr ago`;
}

/* ============================================================
   DOM HELPERS
   ============================================================ */

/**
 * Shorthand querySelector.
 * @param {string} selector
 * @param {Element|Document} [root=document]
 * @returns {Element|null}
 */
export function $(selector, root = document) {
  return root.querySelector(selector);
}

/**
 * Shorthand querySelectorAll → Array.
 * @param {string} selector
 * @param {Element|Document} [root=document]
 * @returns {Element[]}
 */
export function $$(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

/**
 * Add event listener and return a cleanup function.
 * @param {EventTarget} target
 * @param {string} event
 * @param {Function} handler
 * @param {object} [options]
 * @returns {Function} cleanup
 */
export function on(target, event, handler, options) {
  target.addEventListener(event, handler, options);
  return () => target.removeEventListener(event, handler, options);
}

/**
 * Delegate event from a parent to matching children.
 * @param {Element} parent
 * @param {string} childSelector
 * @param {string} event
 * @param {Function} handler
 */
export function delegate(parent, childSelector, event, handler) {
  parent.addEventListener(event, (e) => {
    const target = e.target.closest(childSelector);
    if (target && parent.contains(target)) {
      handler.call(target, e, target);
    }
  });
}

/**
 * Toggle exclusive active class across sibling elements.
 * @param {Element[]} elements
 * @param {Element} active
 * @param {string} [cls='active']
 */
export function setActive(elements, active, cls = 'active') {
  elements.forEach(el => el.classList.toggle(cls, el === active));
}

/* ============================================================
   COUNTDOWN TIMER CLASS
   ============================================================ */

/**
 * CountdownTimer — drives live clocks and countdown displays.
 *
 * @example
 * const timer = new CountdownTimer({
 *   seconds: 4924,
 *   onTick: (remaining) => { el.textContent = formatTime(remaining); },
 *   onWarn: (remaining) => { el.classList.add('timer-value--warning'); },
 *   warnAt: 600,
 *   onExpire: () => { alert('Time is up!'); },
 * });
 * timer.start();
 */
export class CountdownTimer {
  /**
   * @param {object} options
   * @param {number}   options.seconds   Total seconds to count down from.
   * @param {Function} options.onTick    Called every second with remaining seconds.
   * @param {Function} [options.onWarn] Called once when remaining <= warnAt.
   * @param {number}   [options.warnAt=600] Seconds threshold for onWarn.
   * @param {Function} [options.onExpire] Called when timer reaches 0.
   */
  constructor({ seconds, onTick, onWarn, warnAt = 600, onExpire }) {
    this._remaining = seconds;
    this._onTick    = onTick;
    this._onWarn    = onWarn;
    this._warnAt    = warnAt;
    this._onExpire  = onExpire;
    this._warned    = false;
    this._interval  = null;
  }

  start() {
    if (this._interval) return;
    this._tick(); // immediate first tick
    this._interval = setInterval(() => this._tick(), 1000);
  }

  pause() {
    clearInterval(this._interval);
    this._interval = null;
  }

  reset(seconds) {
    this.pause();
    this._remaining = seconds;
    this._warned = false;
    this._tick();
  }

  get remaining() { return this._remaining; }

  _tick() {
    if (this._remaining <= 0) {
      this.pause();
      this._onTick?.(0);
      this._onExpire?.();
      return;
    }
    this._onTick?.(this._remaining);
    if (!this._warned && this._remaining <= this._warnAt) {
      this._warned = true;
      this._onWarn?.(this._remaining);
    }
    this._remaining--;
  }
}

/* ============================================================
   ELAPSED CLOCK CLASS
   ============================================================ */

/**
 * ElapsedClock — counts up from 0 (or a given start).
 *
 * @example
 * const clock = new ElapsedClock({
 *   start: 5924,
 *   onTick: (elapsed) => { el.textContent = formatTime(elapsed); },
 * });
 * clock.start();
 */
export class ElapsedClock {
  constructor({ start = 0, onTick }) {
    this._elapsed  = start;
    this._onTick   = onTick;
    this._interval = null;
  }

  start() {
    if (this._interval) return;
    this._onTick?.(this._elapsed);
    this._interval = setInterval(() => {
      this._elapsed++;
      this._onTick?.(this._elapsed);
    }, 1000);
  }

  stop() {
    clearInterval(this._interval);
    this._interval = null;
  }

  get elapsed() { return this._elapsed; }
}

/* ============================================================
   SIMPLE EVENT BUS
   ============================================================ */

/**
 * Lightweight pub/sub event bus for cross-component communication.
 *
 * @example
 * import { bus } from './utils.js';
 * bus.on('incident:new', handler);
 * bus.emit('incident:new', { candidateId: 'RK029', type: 'tab-switch' });
 */
class EventBus {
  constructor() { this._handlers = {}; }

  on(event, handler) {
    (this._handlers[event] ??= []).push(handler);
    return () => this.off(event, handler);
  }

  off(event, handler) {
    this._handlers[event] = (this._handlers[event] ?? []).filter(h => h !== handler);
  }

  emit(event, data) {
    (this._handlers[event] ?? []).forEach(h => h(data));
  }

  once(event, handler) {
    const wrapper = (data) => { handler(data); this.off(event, wrapper); };
    this.on(event, wrapper);
  }
}

export const bus = new EventBus();

/* ============================================================
   LOCAL STORAGE HELPERS
   ============================================================ */

/**
 * Safely get a JSON value from localStorage.
 * @param {string} key
 * @param {*} fallback
 * @returns {*}
 */
export function storageGet(key, fallback = null) {
  try {
    const val = localStorage.getItem(key);
    return val !== null ? JSON.parse(val) : fallback;
  } catch {
    return fallback;
  }
}

/**
 * Safely set a JSON value in localStorage.
 * @param {string} key
 * @param {*} value
 */
export function storageSet(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
}

/* ============================================================
   MISC
   ============================================================ */

/**
 * Clamp a number between min and max.
 */
export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

/**
 * Debounce a function.
 * @param {Function} fn
 * @param {number} delay
 * @returns {Function}
 */
export function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Generate a random integer between min and max (inclusive).
 */
export function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}
