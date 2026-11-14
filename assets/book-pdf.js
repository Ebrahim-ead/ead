/* book-pdf.js — বইয়ের PDF সবার ডিভাইসে খোলার নিশ্চয়তা।
 *
 * ⚠ যে সমস্যাটা এটি সারায় (২০২৬-১১-১০, ব্যবহারকারীর রিপোর্ট):
 *   «ফোন ব্যবহার করে ওয়েবসাইটে বইয়ের PDF গুলো দেখা যায় না।»
 *
 * কারণ: পাতায় PDF <iframe>-এ এমবেড করা ছিল। ডেস্কটপে তা চলে, কিন্তু
 *   • iOS Safari (iPhone/iPad): iframe-এ PDF-এর শুধু *প্রথম পৃষ্ঠা* দেখায়,
 *     বাকিটা দেখতে হলে আলাদা করে খুলতে হয়;
 *   • Android Chrome: বহু সংস্করণে iframe-ভেতরে PDF রেন্ডারই হয় না —
 *     ফাঁকা সাদা জায়গা থাকে (নিম্ন-শক্তির ডিভাইসে বিশেষত);
 *   • Samsung Internet / Firefox mobile: প্রায়ই ডাউনলোডে পাঠিয়ে দেয়।
 *   অর্থাৎ ওই «অনলাইনে পড়ুন» বোতাম ফোনে চাপলে কিছুই দেখা যেত না।
 *
 * সমাধান: ব্লকটি কেবল *সত্যিই* PDF দেখাতে পারে এমন পরিবেশে খুলি
 *   (navigator.pdfViewerEnabled + ডেস্কটপ-প্রস্থ)। নইলে PDF নতুন ট্যাবে
 *   খোলার বড় বোতাম + ডাউনলোড দেখাই — ফোনের নিজের PDF রিডারেই তা চলবে,
 *   যা সব iOS/Android-এ কাজ করে। কোনো ফিচার হারায় না, বরং পথ পরিষ্কার।
 *
 * নীতি: ইনলাইন-হ্যান্ডলার/অতিরিক্ত নির্ভরতা নেই; প্রতিটি বই-ব্লক আলাদা
 *   `[data-book-viewer]` ধারক দিয়ে চিহ্নিত, সাথে `[data-book-fallback]` প্যানেল।
 */
(function () {
  'use strict';

  /** এই ব্রাউজার কি iframe-এর ভেতরে PDF রেন্ডার করতে পারে? */
  function canInlinePdf() {
    // ১) সরাসরি জিজ্ঞাসা — Chrome/Edge/Safari আধুনিক সংস্করণে আছে
    if (typeof navigator !== 'undefined' && 'pdfViewerEnabled' in navigator) {
      if (!navigator.pdfViewerEnabled) return false;
    }
    // ২) মোবাইল/টাচ — ওখানে ইনলাইন রেন্ডার অবিশ্বাস্য, তাই ফলব্যাকই ভালো
    var ua = (navigator && navigator.userAgent) || '';
    if (/iPhone|iPad|iPod|Android|Mobile|SamsungBrowser|Opera Mini/i.test(ua)) return false;
    // ৩) ছোট স্ক্রিন (ফোন) — PDF-পৃষ্ঠা পড়াই কষ্টকর
    if (typeof window.matchMedia === 'function' &&
        window.matchMedia('(max-width: 760px)').matches) return false;
    // ৪) টাচ-প্রধান ডিভাইস
    if (typeof navigator !== 'undefined' && navigator.maxTouchPoints > 1 &&
        typeof window.matchMedia === 'function' &&
        !window.matchMedia('(pointer: fine)').matches) return false;
    return true;
  }

  var INLINE_OK = canInlinePdf();

  /** একটি বই-ব্লকে সিদ্ধান্ত প্রয়োগ করি। */
  function setup(box) {
    var frame = box.querySelector('iframe');
    // ফলব্যাক-প্যানেল ভিউয়ারের ভেতরে বা ঠিক পরে — দুই জায়গাতেই খুঁজি
    var fallback = box.querySelector('[data-book-fallback]') ||
                   (box.nextElementSibling && box.nextElementSibling.matches('[data-book-fallback]')
                     ? box.nextElementSibling : null) ||
                   document.querySelector('[data-book-fallback]');
    var openLink = (fallback && fallback.querySelector('[data-book-open]')) ||
                   document.querySelector('[data-book-open]');
    var url = box.getAttribute('data-book-src') || (openLink && openLink.getAttribute('href')) || '';

    if (!frame || !fallback || !url) return;

    if (INLINE_OK) {
      // ডেস্কটপ: আগের মতোই ইনলাইন ভিউয়ার
      frame.setAttribute('src', url);
      fallback.hidden = true;
    } else {
      // ফোন: ভিউয়ার লুকিয়ে PDF খোলার স্পষ্ট পথ দেখাই
      frame.removeAttribute('src');      // অকারণে ৯–১৪ MB নামবে না
      fallback.hidden = false;
      box.classList.add('is-fallback');
      // iOS/Android-এর নিজের রিডারে খুললে সব পৃষ্ঠা ঠিকঠাক চলে
      if (openLink) openLink.setAttribute('href', url);
    }
  }

  function run() {
    var boxes = document.querySelectorAll('[data-book-viewer]');
    for (var i = 0; i < boxes.length; i++) setup(boxes[i]);
  }


  /* ============================================================
     ডাউনলোড-অগ্রগতি
     ------------------------------------------------------------
     বইয়ের PDF ৯–১৫ MB। ধীর সংযোগে ব্রাউজার চুপচাপ নামায় — ব্যবহারকারী
     ভাবেন «কিছুই হচ্ছে না» এবং বাতিল করে দেন। এখন চাপলে সাথে সাথে
     «ডাউনলোড হচ্ছে… ৪২%» দেখাই, শেষ হলে বোতাম আবার স্বাভাবিক।

     কৌশল: fetch + ReadableStream দিয়ে নিজে নামাই, অগ্রগতি দেখাই, তারপর
     Blob → <a download>. stream/Blob না থাকলে (পুরোনো ব্রাউজার) সাধারণ
     লিঙ্ক-ডাউনলোডই চলে — কিছু ভাঙে না। abort হলে অর্ধেক ফাইল নষ্ট হয় না।
     ============================================================ */
  function humanSize(b) {
    if (!b) return '';
    return b >= 1048576 ? (b / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(b / 1024)) + ' KB';
  }

  function makeBar(btn) {
    var bar = btn.querySelector('[data-dl-bar]');
    if (bar) return bar;
    bar = document.createElement('span');
    bar.className = 'dl-bar';
    bar.setAttribute('data-dl-bar', '');
    bar.setAttribute('aria-hidden', 'true');
    bar.innerHTML = '<i></i>';
    var tx = btn.querySelector('.tx') || btn;
    tx.appendChild(bar);
    return bar;
  }

  function label(btn, main, sub) {
    var b = btn.querySelector('.tx b') || btn.querySelector('b');
    var s = btn.querySelector('.tx small') || btn.querySelector('small');
    if (b) b.textContent = main;
    if (s && sub !== undefined) s.textContent = sub;
  }

  /* প্রতিটি বোতামের নিজস্ব মূল লেখা — একটার লেখা অন্যের ওপর নয় */
  function originalOf(btn) {
    if (!btn.__dlOrig) {
      var b = btn.querySelector('.tx b') || btn.querySelector('b');
      var s = btn.querySelector('.tx small') || btn.querySelector('small');
      btn.__dlOrig = {
        main: (b && b.textContent) || 'ডাউনলোড',
        sub: (s && s.textContent) || ''
      };
    }
    return btn.__dlOrig;
  }

  function download(btn, url) {
    var orig = originalOf(btn);

    /* একই সময়ে দুবার চাপলে দ্বিতীয়টা উপেক্ষা করি */
    if (btn.dataset.dlBusy === '1') return;
    btn.dataset.dlBusy = '1';
    btn.setAttribute('aria-busy', 'true');
    var bar = makeBar(btn);
    bar.classList.add('on');
    btn.classList.add('is-downloading');

    var ctrl = typeof AbortController === 'function' ? new AbortController() : null;
    var done = false;
    var fail = function () {
      if (done) return;
      done = true;
      btn.dataset.dlBusy = '';
      btn.removeAttribute('aria-busy');
      bar.classList.remove('on');
      btn.classList.remove('is-downloading');
      label(btn, orig.main, orig.sub);
      /* ব্যর্থ হলে ব্রাউজারের নিজের পথই খুলে দিই — ব্যবহারকারী আটকে থাকেন না */
      var a = document.createElement('a');
      a.href = url; a.download = ''; a.rel = 'noopener';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
    };

    var canStream = typeof fetch === 'function' &&
                    typeof Response === 'function' &&
                    window.Response && 'body' in Response.prototype &&
                    typeof Blob === 'function' && typeof URL !== 'undefined' && URL.createObjectURL;

    if (!canStream) { fail(); return; }

    fetch(url, { credentials: 'same-origin', signal: ctrl ? ctrl.signal : undefined })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        var total = +(res.headers.get('Content-Length') || 0);
        label(btn, 'ডাউনলোড হচ্ছে…', total ? humanSize(total) : '');
        var reader = res.body && res.body.getReader ? res.body.getReader() : null;
        if (!reader) return res.blob();      /* stream নেই — একবারে নামুক */

        var chunks = [], got = 0;
        return (function pump() {
          return reader.read().then(function (r) {
            if (r.done) return new Blob(chunks, { type: 'application/pdf' });
            chunks.push(r.value);
            got += r.value.length;
            var pct = total ? Math.min(100, Math.round(got / total * 100)) : null;
            var i = bar.querySelector('i');
            if (i) i.style.width = pct !== null ? pct + '%' : '';
            /* % জানা থাকলে সেটাই, নইলে কত MB নামল */
            label(btn, pct !== null ? 'ডাউনলোড হচ্ছে… ' + pct + '%' : 'ডাউনলোড হচ্ছে…',
                      pct !== null ? humanSize(got) + ' / ' + humanSize(total) : humanSize(got));
            return pump();
          });
        })();
      })
      .then(function (blob) {
        if (done) return;
        var obj = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = obj;
        a.download = (url.split('/').pop() || 'book.pdf');
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        setTimeout(function () { URL.revokeObjectURL(obj); }, 60000);
        done = true;
        btn.dataset.dlBusy = '';
        btn.removeAttribute('aria-busy');
        bar.classList.remove('on');
        btn.classList.remove('is-downloading');
        label(btn, 'ডাউনলোড হয়েছে ✓', orig.sub);
        setTimeout(function () { label(btn, orig.main, orig.sub); }, 4000);
      })
      .catch(fail);
  }

  function wireDownloads() {
    var links = document.querySelectorAll('a[download][href$=".pdf"], a[download][href*=".pdf?"]');
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      if (a.dataset.dlWired === '1') continue;
      a.dataset.dlWired = '1';
      a.addEventListener('click', function (e) {
        /* Ctrl/Cmd/Shift-চাপ বা মাঝের বোতাম → ব্রাউজারের স্বাভাবিক আচরণ */
        if (e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || e.button !== 0) return;
        var url = this.getAttribute('href');
        if (!url) return;
        e.preventDefault();
        download(this, url);
      });
    }
  }

  // ⚠ jsdom/পরীক্ষায় readyState কখনো 'complete' নাও হতে পারে — তাই সরাসরিই
  //   চালাই, আর DOMContentLoaded-এ আবার (run() idempotent: দুবার চললে ক্ষতি নেই)।
  run();
  wireDownloads();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  }

  // পরীক্ষার জন্য প্রকাশ (tools/test_pdf.mjs ব্যবহার করে)
  window.__bookPdf = { canInlinePdf: canInlinePdf, inlineOk: INLINE_OK,
                       wireDownloads: wireDownloads, download: download };
})();
