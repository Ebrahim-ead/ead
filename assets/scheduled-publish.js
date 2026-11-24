/* ============================================================
   scheduled-publish.js — নির্ধারিত সময়ে প্রবন্ধ প্রকাশ নিয়ন্ত্রণ
   ------------------------------------------------------------
   <meta name="ead:publish-at" content="ISO-8601"> পড়ে।
   নির্ধারিত সময়ের আগে মূল প্রবন্ধ লুকানো থাকে ও অপেক্ষা-বার্তা
   দেখায়; সময় পূর্ণ হওয়া মাত্র (রিফ্রেশ ছাড়াই) পাতা উন্মুক্ত হয়।
   ============================================================ */
(function () {
  'use strict';

  var doc = document;
  var meta = doc.querySelector('meta[name="ead:publish-at"]');
  if (!meta) return;

  var raw = (meta.getAttribute('content') || '').trim();
  var publishAt = Date.parse(raw);
  if (!isFinite(publishAt)) return;

  var BN = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'];
  function bn(n, pad2) {
    var s = String(n);
    if (pad2 && s.length < 2) s = '0' + s;
    return s.replace(/[0-9]/g, function (d) { return BN[+d]; });
  }

  var unlocked = false;
  var timer = 0;

  function unlock() {
    if (unlocked) return;
    unlocked = true;
    if (timer) { clearInterval(timer); timer = 0; }

    doc.documentElement.classList.add('is-published');

    var pubTitle = doc.documentElement.getAttribute('data-pub-title');
    if (pubTitle) {
      doc.title = pubTitle;
      doc.documentElement.removeAttribute('data-pub-title');
    }

    var gates = doc.querySelectorAll('[data-scheduled-gate]');
    for (var i = 0; i < gates.length; i++) {
      gates[i].hidden = true;
      gates[i].setAttribute('hidden', '');
    }

    var contents = doc.querySelectorAll('[data-scheduled-content]');
    for (var j = 0; j < contents.length; j++) {
      contents[j].hidden = false;
      contents[j].removeAttribute('hidden');
    }

    if (typeof window.__reveal === 'function') {
      try { window.__reveal(); } catch (e) {}
    }
    try {
      if (typeof Event === 'function') {
        window.dispatchEvent(new Event('resize'));
        window.dispatchEvent(new Event('scroll'));
      }
    } catch (e) {}
  }

  function formatRemaining(ms) {
    var totalSec = Math.max(0, Math.ceil(ms / 1000));
    var days = Math.floor(totalSec / 86400);
    var hours = Math.floor((totalSec % 86400) / 3600);
    var mins = Math.floor((totalSec % 3600) / 60);
    var secs = totalSec % 60;
    var parts = [];
    if (days > 0) parts.push(bn(days, false) + ' দিন');
    parts.push(bn(hours, true) + ' ঘণ্টা');
    parts.push(bn(mins, true) + ' মিনিট');
    parts.push(bn(secs, true) + ' সেকেন্ড');
    return 'বাকি সময়: ' + parts.join(' ');
  }

  function updateCountdown() {
    var diff = publishAt - Date.now();
    if (diff <= 0) {
      unlock();
      return;
    }
    var el = doc.getElementById('sched-countdown');
    if (el) el.textContent = formatRemaining(diff);
  }

  if (Date.now() >= publishAt) {
    unlock();
  } else {
    doc.documentElement.classList.remove('is-published');
    updateCountdown();
    timer = setInterval(updateCountdown, 1000);
  }
})();
