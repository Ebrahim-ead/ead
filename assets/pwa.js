/* ============================================================
   pwa.js — Service Worker ও অফলাইন-অবস্থা
   ------------------------------------------------------------
   · sw.js রেজিস্ট্রার করে (শুধু HTTPS / localhost-এ)
   · নতুন সংস্করণ এলে «রিফ্রেশ» নোটিশ দেখায়
   · অফলাইনে গেলে ছোট নোটিশ দেখায়
   · কোনো ফিচার না মিললে চুপচাপ বাদ যায় — কিছু ভাঙে না

   ⚠ ইনস্টল-সিস্টেম নেই। ব্যবহারকারীর নির্দেশে («অ্যাপ ইনস্টল সিস্টেম
   বাদ দাও») ইনস্টলের প্রম্পট, ব্যানার, iOS-নির্দেশনা ও হিরোর
   «অ্যাপ ইনস্টল করুন» বোতাম — সব সরানো হয়েছে।
   ============================================================ */
(function () {
  'use strict';

  /* ---- ১. Service Worker ---- */
  function registerSW() {
    if (!('serviceWorker' in navigator)) return;
    // file:// বা HTTP (localhost ছাড়া) — SW কাজ করে না
    if (location.protocol !== 'https:' && location.hostname !== 'localhost'
        && location.hostname !== '127.0.0.1') return;

    navigator.serviceWorker.register('/ead/sw.js', { scope: '/ead/' })
      .then(function (reg) {
        // নতুন সংস্করণ এলে জানাই
        reg.addEventListener('updatefound', function () {
          var w = reg.installing;
          if (!w) return;
          w.addEventListener('statechange', function () {
            if (w.state === 'installed' && navigator.serviceWorker.controller) {
              showUpdateBar();
            }
          });
        });
      })
      .catch(function () { /* চুপচাপ — SW না পেলেও সাইট চলবে */ });
  }

  /* ---- নোটিশ-অ্যানিমেশন ----
     ঢোকার অ্যানিমেশন: rAF-এ ভরসা করি না — ব্যাকগ্রাউন্ড ট্যাবে rAF স্থগিত
     থাকতে পারে, তখন নোটিশ চিরকাল লুকানো থেকে যায়। void offsetWidth দিয়ে
     লেআউট বাধ্য করি, যেন transform-ট্রানজিশন সত্যিই চলে। */
  function open(el) {
    if (!el) return;
    void el.offsetWidth;
    el.classList.add('is-open');
  }

  /* ---- ৩. আপডেট-নোটিশ ---- */
  function showUpdateBar() {
    var bar = document.createElement('div');
    bar.className = 'pwa-banner pwa-update';
    bar.setAttribute('role', 'status');
    bar.innerHTML = '<div class="pwa-body"><b>নতুন সংস্করণ এসেছে</b>'
      + '<span class="pwa-note">আপডেট নিলে নতুন লেখা ও উন্নতি পাবেন।</span></div>';

    var act = document.createElement('div');
    act.className = 'pwa-actions';
    var go = document.createElement('button');
    go.type = 'button';
    go.className = 'pwa-btn primary';
    go.textContent = 'রিফ্রেশ';
    go.addEventListener('click', function () {
      if (navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' });
      }
      location.reload();
    });
    act.appendChild(go);
    bar.appendChild(act);
    document.body.appendChild(bar);
    open(bar);
  }

  /* ---- ৪. অফলাইন-নোটিশ ---- */
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
    var n = offNote; offNote = null;
    n.classList.remove('is-open');
    setTimeout(function () { if (n.parentNode) n.parentNode.removeChild(n); }, 300);
  }

  window.addEventListener('offline', showOffline);
  window.addEventListener('online', hideOffline);


  /* ---- ৫. ফিরে এলে যেখানে ছিলেন --------------------------------------------------
     ইনস্টল করা অ্যাপে প্রতিবার শূন্য থেকে শুরু হলে «অ্যাপ» মনে হয় না।
     পৃষ্ঠা ছাড়ার আগে scroll-স্থিতি মনে রাখি, ফিরে এলে ফিরিয়ে দিই।
     কেবল ইনস্টল-মোডে — ব্রাউজার-ট্যাবে ব্রাউজারের নিজের behavior-ই ভালো। */
  var SCROLL_KEY = 'ead:scroll:';

  /* ইনস্টল-মোডে চলছি কি না — শুধু স্ক্রল-রিস্টোরের জন্য (ইনস্টল-ব্যানার
     সরানো হলেও অ্যাপ-মোডে ফিরে এলে জায়গা মনে রাখার সুবিধা অটুট) */
  function isApp() {
    if (window.navigator.standalone === true) return true;   // iOS হোম-স্ক্রিন
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
    // ছবি/ফন্ট আসার পর উচ্চতা বদলায় — দুই ধাপে ফিরিয়ে দিই
    var go = function () {
      try { window.scrollTo(0, y); } catch (e) {}
    };
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
    window.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden') saveScroll();
    });
    restoreScroll();
    window.addEventListener('load', restoreScroll);
  }


  /* ---- চালু ---- */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  function boot() {
    registerSW();
    if (!navigator.onLine) showOffline();
  }
})();
