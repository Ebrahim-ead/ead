(function () {
  'use strict';
  var updateBar = null;
  function registerSW() {
    if (!('serviceWorker' in navigator)) return;
    if (location.protocol !== 'https:' && location.hostname !== 'localhost' &&
        location.hostname !== '127.0.0.1') return;
    navigator.serviceWorker.register('/ead/sw.js', { scope: '/ead/' })
      .then(function (reg) {
        if (!reg) return;
        if (reg.waiting && navigator.serviceWorker.controller) {
          showUpdateBar(reg);
        }
        reg.addEventListener('updatefound', function () {
          var w = reg.installing;
          if (!w) return;
          w.addEventListener('statechange', function () {
            if (w.state === 'installed' && navigator.serviceWorker.controller) {
              showUpdateBar(reg);
            }
          });
        });
      })
      .catch(function () {});
  }
  function open(el) { if (!el) return; void el.offsetWidth; el.classList.add('is-open'); }
  function closeUpdateBar() {
    if (!updateBar) return;
    var el = updateBar;
    updateBar = null;
    el.classList.remove('is-open');
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 250);
  }
  function showUpdateBar(reg) {
    if (updateBar) return;
    var bar = document.createElement('div');
    bar.className = 'pwa-update-bar';
    bar.setAttribute('role', 'status');
    bar.innerHTML = '<div class="pwa-update-body"><b>নতুন সংস্করণ এসেছে</b>' +
      '<span class="pwa-update-note">আপডেট নিলে নতুন লেখা ও উন্নতি পাবেন।</span></div>';
    var act = document.createElement('div');
    act.className = 'pwa-update-actions';
    var go = document.createElement('button');
    go.type = 'button';
    go.className = 'pwa-update-btn';
    go.textContent = 'রিফ্রেশ';
    go.addEventListener('click', function () {
      go.disabled = true;
      var target = (reg && reg.waiting) || navigator.serviceWorker.waiting;
      var reloaded = false;
      function reloadNow() {
        if (reloaded) return;
        reloaded = true;
        location.reload();
      }
      if (target && navigator.serviceWorker.addEventListener) {
        navigator.serviceWorker.addEventListener('controllerchange', reloadNow);
        target.postMessage({ type: 'SKIP_WAITING' });
        setTimeout(reloadNow, 1200);
      } else {
        reloadNow();
      }
    });
    var closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'pwa-update-close';
    closeBtn.setAttribute('aria-label', 'বিজ্ঞপ্তি বন্ধ করুন');
    closeBtn.textContent = '✕';
    closeBtn.addEventListener('click', closeUpdateBar);
    act.appendChild(go);
    act.appendChild(closeBtn);
    bar.appendChild(act);
    updateBar = bar;
    document.body.appendChild(bar);
    open(bar);
  }
  var offNote = null;
  function showOffline() {
    if (offNote) return;
    offNote = document.createElement('div');
    offNote.className = 'pwa-offline';
    offNote.setAttribute('role', 'status');
    offNote.innerHTML = '<b>ইন্টারনেট নেই</b> — আগে পড়া পাতাগুলো এখনো পড়া যাবে।';
    document.body.appendChild(offNote);
    open(offNote);
  }
  function hideOffline() {
    if (!offNote) return;
    var n = offNote;
    offNote = null;
    n.classList.remove('is-open');
    setTimeout(function () { if (n.parentNode) n.parentNode.removeChild(n); }, 300);
  }
  window.addEventListener('offline', showOffline);
  window.addEventListener('online', hideOffline);
  var SCROLL_KEY = 'ead:scroll:';
  function isApp() {
    if (window.navigator.standalone === true) return true;
    if (!window.matchMedia) return false;
    return ['standalone', 'minimal-ui', 'fullscreen'].some(function (m) {
      try { return window.matchMedia('(display-mode: ' + m + ')').matches; } catch (e) { return false; }
    });
  }
  function restoreScroll() {
    if (!isApp()) return;
    var key = SCROLL_KEY + location.pathname + location.search;
    var y = 0;
    try { y = +(sessionStorage.getItem(key) || 0); } catch (e) { return; }
    if (!y || y < 40) return;
    var go = function () { try { window.scrollTo(0, y); } catch (e) {} };
    go();
    setTimeout(go, 120);
    if (window.requestAnimationFrame) requestAnimationFrame(function () { setTimeout(go, 60); });
  }
  function saveScroll() {
    if (!isApp()) return;
    var key = SCROLL_KEY + location.pathname + location.search;
    try { sessionStorage.setItem(key, String(window.pageYOffset || 0)); } catch (e) {}
  }
  if (isApp()) {
    window.addEventListener('pagehide', saveScroll);
    window.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') saveScroll(); });
    restoreScroll();
    window.addEventListener('load', restoreScroll);
  }
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', boot); } else { boot(); }
  function boot() { registerSW(); if (!navigator.onLine) showOffline(); }
})();
