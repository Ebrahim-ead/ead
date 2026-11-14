/* ============================================================
   pwa.js — Service Worker, ইনস্টল-বাটন ও অফলাইন-অবস্থা
   ------------------------------------------------------------
   · sw.js রেজিস্টার করে (শুধু HTTPS / localhost-এ)
   · Android/Chrome-এ «ইনস্টল করুন» বাটন দেখায়
   · iOS-এ বাটন নেই — তাই নির্দেশনা দেখায়
   · ইনস্টল হয়ে গেলে বাটন চিরতরে লুকিয়ে যায়
   · অফলাইনে গেলে ছোট নোটিশ দেখায়
   · কোনো ফিচার না মিললে চুপচাপ বাদ যায় — কিছু ভাঙে না
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

  /* ---- ২. ইনস্টল-প্রম্পট ---- */
  var deferredPrompt = null;

  function isStandalone() {
    return (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches)
      || window.navigator.standalone === true;
  }

  function isIOS() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent)
      || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  }

  function isAndroid() {
    return /Android/i.test(navigator.userAgent);
  }

  /* একবার বন্ধ করলে ৩০ দিন আর দেখাব না */
  var DISMISS_KEY = 'ead:install-dismissed';

  function dismissed() {
    try {
      var t = localStorage.getItem(DISMISS_KEY);
      if (!t) return false;
      return Date.now() - (+t) < 30 * 24 * 60 * 60 * 1000;
    } catch (e) { return false; }
  }

  function dismiss() {
    try { localStorage.setItem(DISMISS_KEY, String(Date.now())); } catch (e) {}
    hideBanner();
  }

  var banner = null;

  function buildBanner(mode) {
    if (banner) return banner;
    banner = document.createElement('div');
    banner.className = 'pwa-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'অ্যাপ ইনস্টল');

    var icon = document.createElement('img');
    icon.src = '/ead/assets/img/icon-192.png';
    icon.alt = '';
    icon.width = 44;
    icon.height = 44;
    icon.decoding = 'async';
    banner.appendChild(icon);

    var body = document.createElement('div');
    body.className = 'pwa-body';

    var title = document.createElement('b');
    title.textContent = 'অ্যাপ হিসেবে ইনস্টল করুন';
    body.appendChild(title);

    var note = document.createElement('span');
    note.className = 'pwa-note';
    note.innerHTML = mode === 'ios'
      ? 'Safari-তে <b>শেয়ার</b> ▸ <b>«হোম স্ক্রিনে যোগ করুন»</b> চাপুন — ইন্টারনেট ছাড়াই পড়তে পারবেন।'
      : 'হোম স্ক্রিনে আইকন আসবে — দ্রুত খুলবে, অফলাইনেও চলবে।';
    body.appendChild(note);

    banner.appendChild(body);

    var actions = document.createElement('div');
    actions.className = 'pwa-actions';

    if (mode !== 'ios') {
      var install = document.createElement('button');
      install.type = 'button';
      install.className = 'pwa-btn primary';
      install.textContent = 'ইনস্টল';
      install.addEventListener('click', doInstall);
      actions.appendChild(install);
    }

    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'pwa-btn ghost';
    close.textContent = 'পরে';
    close.setAttribute('aria-label', 'ব্যানার বন্ধ করুন');
    close.addEventListener('click', dismiss);
    actions.appendChild(close);

    banner.appendChild(actions);
    document.body.appendChild(banner);

    return banner;
  }

  // ঢোকার অ্যানিমেশন: rAF-এ ভরসা করি না — ব্যাকগ্রাউন্ড ট্যাবে rAF স্থগিত
  // থাকতে পারে, তখন ব্যানার চিরকাল লুকানো থেকে যায়। void offsetWidth দিয়ে
  // লেআউট বাধ্য করি, যেন transform-ট্রানজিশন সত্যিই চলে।
  function open(el) {
    if (!el) return;
    void el.offsetWidth;
    el.classList.add('is-open');
  }

  function showBanner(mode) {
    if (isStandalone() || dismissed()) return;
    buildBanner(mode);
    open(banner);
  }

  function hideBanner() {
    if (!banner) return;
    banner.classList.remove('is-open');
    var b = banner;
    banner = null;
    setTimeout(function () { if (b.parentNode) b.parentNode.removeChild(b); }, 320);
  }

  function doInstall() {
    if (!deferredPrompt) { hideBanner(); return; }
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then(function (choice) {
      if (choice.outcome === 'accepted') hideBanner();
      deferredPrompt = null;
    }).catch(function () { deferredPrompt = null; });
  }

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();          // নিজের বাটন দেখাব
    deferredPrompt = e;
    // প্রথম আসার ৩ সেকেন্ড পর দেখাই — সাথে সাথে নয়
    setTimeout(function () {
      if (!isStandalone() && !dismissed()) showBanner('android');
    }, 3000);
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    hideBanner();
    try { localStorage.setItem(DISMISS_KEY, String(Date.now() + 365 * 24 * 3600 * 1000)); } catch (e) {}
  });

  /* iOS-এ beforeinstallprompt নেই — তাই আলাদা নির্দেশনা */
  function maybeIOSHint() {
    if (!isIOS() || isStandalone() || dismissed()) return;
    // Safari কিনা দেখি
    var ua = navigator.userAgent;
    var isSafari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua);
    if (!isSafari) return;
    // ১০ সেকেন্ড পর, একবার
    setTimeout(function () { showBanner('ios'); }, 10000);
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

  /* ---- চালু ---- */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  function boot() {
    registerSW();
    if (!navigator.onLine) showOffline();
    maybeIOSHint();
  }
})();
