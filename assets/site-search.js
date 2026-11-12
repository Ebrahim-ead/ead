/* ============================================================
   site-search.js — পুরো সাইট-জুড়ে সার্চ
   ------------------------------------------------------------
   · সূচি আসে assets/search-index.js থেকে (window.SITE_SEARCH)
     — কোনো fetch নেই, তাই file:// থেকেও কাজ করে।
   · মোডাল ডায়ালগ; Ctrl/⌘+K বা «/» চাপে খোলে।
   · ফল: পাতা, কুরআনের সূরা, হাদিসের কিতাব, ধর্মীয় গ্রন্থ।
   · তীর-কী ↑↓, Enter, Esc কাজ করে; ফোকাস-ট্র্যাপ আছে।
   · সূচি লোড না হলে বোতামটি নিজেই লুকিয়ে যায় — কিছু ভাঙে না।
   ============================================================ */
(function () {
  'use strict';

  var data = window.SITE_SEARCH;
  var triggers = document.querySelectorAll('[data-search-open]');
  if (!data || !data.length || !triggers.length) return;

  /* ── বাংলা অক্ষর স্বাভাবিক করা (সার্চ-মিলের জন্য) ──
     একই শব্দের একাধিক বানান মিলবে: ি/ী, ু/ূ, য়/য, নুকতা, ৎ — সব সমান। */
  var FOLD = {
    '\u09c0': '\u09bf', // ী → ি
    '\u09c2': '\u09c1', // ূ → ু
    '\u09bc': '',        // ় নুকতা
    '\u09df': '\u09af', // য় → য
    '\u09ce': '\u09a4', // ৎ → ত
    '\u200c': '', '\u200d': ''
  };
  function norm(s) {
    s = (s || '').toString();
    if (s.normalize) s = s.normalize('NFC');
    s = s.toLowerCase();
    return s.replace(/[\u09c0\u09c2\u09bc\u09df\u09ce\u200c\u200d]/g, function (c) {
      return FOLD[c] !== undefined ? FOLD[c] : c;
    });
  }
  /* www → সাইটের সব এন্ট্রি; সংখ্যা বাংলাতেও লেখা যায় */
  var BN_DIGITS = { '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4', '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9' };
  function asciiDigits(s) {
    return s.replace(/[০-৯]/g, function (d) { return BN_DIGITS[d]; });
  }

  var TYPE_LABEL = {
    page: 'পাতা',
    quran: 'কুরআন',
    hadith: 'হাদিস',
    grantho: 'গ্রন্থ'
  };

  /* ── মোডাল কাঠামো ── */
  var root = document.createElement('div');
  root.className = 'ss';
  root.hidden = true;
  root.innerHTML =
    '<div class="ss-backdrop" data-search-close></div>' +
    '<div class="ss-panel" role="dialog" aria-modal="true" aria-labelledby="ss-title" tabindex="-1">' +
      '<h2 id="ss-title" class="ss-sr">সাইট-সার্চ</h2>' +
      '<div class="ss-bar">' +
        '<span class="ss-icon" aria-hidden="true">' +
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">' +
            '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/>' +
          '</svg>' +
        '</span>' +
        '<input class="ss-input" type="search" id="ss-input" placeholder="কিছু খুঁজুন — সূরা, হাদিস, প্রবন্ধ, বই…" ' +
          'autocomplete="off" spellcheck="false" aria-controls="ss-results" aria-describedby="ss-count">' +
        '<button class="ss-esc" type="button" data-search-close aria-label="সার্চ বন্ধ করুন">Esc</button>' +
      '</div>' +
      '<p class="ss-count" id="ss-count" role="status" aria-live="polite"></p>' +
      '<ul class="ss-results" id="ss-results" role="listbox" aria-label="সার্চ-ফল"></ul>' +
      '<p class="ss-foot">' +
        '<kbd>↑</kbd><kbd>↓</kbd> চালনা · <kbd>Enter</kbd> খুলুন · <kbd>Esc</kbd> বন্ধ' +
      '</p>' +
    '</div>';
  document.body.appendChild(root);

  var panel = root.querySelector('.ss-panel');
  var input = root.querySelector('.ss-input');
  var list = root.querySelector('.ss-results');
  var count = root.querySelector('.ss-count');
  var lastFocus = null;
  var active = -1;
  var shown = [];

  function clearResults() {
    list.textContent = '';
    count.textContent = '';
    active = -1;
    shown = [];
  }

  function highlight(text, q) {
    /* ফলাফলের শিরোনামে মিল-করা অংশ <mark> করি — HTML-ইনজেকশন এড়াতে টেক্সট-নোডে */
    var frag = document.createDocumentFragment();
    if (!q) { frag.appendChild(document.createTextNode(text)); return frag; }
    var hay = norm(text);
    var nq = norm(q);
    var i = hay.indexOf(nq);
    if (i === -1) { frag.appendChild(document.createTextNode(text)); return frag; }
    frag.appendChild(document.createTextNode(text.slice(0, i)));
    var mk = document.createElement('mark');
    mk.textContent = text.slice(i, i + nq.length);
    frag.appendChild(mk);
    frag.appendChild(document.createTextNode(text.slice(i + nq.length)));
    return frag;
  }

  function render(results, q) {
    clearResults();
    shown = results;
    if (!q) {
      count.textContent = 'যা মনে আসে লিখুন — বাংলা বা ইংরেজি।';
      var hint = ['সূরা ইয়াসিন', 'বুখারী', 'কুরআন', 'প্রবন্ধ', 'বাইবেল'];
      var ul = document.createElement('li');
      ul.className = 'ss-hintwrap';
      var chips = document.createElement('div');
      chips.className = 'ss-chips';
      hint.forEach(function (h) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'ss-chip';
        b.textContent = h;
        b.addEventListener('click', function () { input.value = h; input.dispatchEvent(new Event('input')); input.focus(); });
        chips.appendChild(b);
      });
      ul.appendChild(chips);
      list.appendChild(ul);
      return;
    }
    if (!results.length) {
      count.textContent = '«' + q + '» — কিছু পাওয়া যায়নি।';
      var nf = document.createElement('li');
      nf.className = 'ss-empty';
      nf.textContent = 'অন্য শব্দে চেষ্টা করুন, অথবা দেখুন: পৃষ্ঠা-তালিকা, বিষয়সমূহ।';
      list.appendChild(nf);
      return;
    }
    count.textContent = results.length + 'টি ফল';
    results.forEach(function (r, i) {
      var li = document.createElement('li');
      li.className = 'ss-result';
      li.id = 'ss-opt-' + i;
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', 'false');
      li.dataset.href = r.u;

      var a = document.createElement('a');
      a.href = r.u;
      a.className = 'ss-link';

      var top = document.createElement('span');
      top.className = 'ss-top';
      var tag = document.createElement('span');
      tag.className = 'ss-tag ss-tag-' + r.t;
      tag.textContent = TYPE_LABEL[r.t] || 'পাতা';
      top.appendChild(tag);
      a.appendChild(top);

      var nm = document.createElement('span');
      nm.className = 'ss-name';
      nm.appendChild(highlight(r.n, q));
      a.appendChild(nm);

      if (r.d) {
        var dd = document.createElement('span');
        dd.className = 'ss-desc';
        dd.textContent = r.d;
        a.appendChild(dd);
      }

      li.appendChild(a);
      // মাউস-হোভারে সক্রিয় ফল বদলাই
      li.addEventListener('mouseenter', function () { setActive(i); });
      list.appendChild(li);
    });
  }

  function setActive(i) {
    var items = list.querySelectorAll('.ss-result');
    if (!items.length) { active = -1; return; }
    if (i < 0) i = items.length - 1;
    if (i >= items.length) i = 0;
    items.forEach(function (el, k) {
      var on = k === i;
      el.classList.toggle('is-active', on);
      el.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    input.setAttribute('aria-activedescendant', items[i].id);
    active = i;
    var el = items[i];
    if (el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
  }

  /* ── স্কোরিং: শিরোনাম-মিল > বর্ণনা > কীওয়ার্ড ── */
  function search(q) {
    var nq = norm(q);
    if (!nq) return [];
    var out = [];
    for (var i = 0; i < data.length; i++) {
      var r = data[i];
      var name = norm(r.n);
      var desc = norm(r.d || '');
      var key = r.k || '';
      var score = 0;
      if (name === nq) score = 100;
      else if (name.indexOf(nq) === 0) score = 80;
      else if (name.indexOf(nq) > -1) score = 60;
      else if (desc.indexOf(nq) > -1) score = 35;
      else if (key && key.indexOf(nq) > -1) score = 20;
      if (!score) continue;
      // পাতা ও কুরআনকে অল্প অগ্রাধিকার
      if (r.t === 'page') score += 6;
      if (r.t === 'quran') score += 3;
      out.push({ r: r, s: score });
    }
    out.sort(function (a, b) { return b.s - a.s; });
    return out.slice(0, 24).map(function (x) { return x.r; });
  }

  var debounce = 0;
  function onInput() {
    var q = input.value.trim();
    clearTimeout(debounce);
    debounce = setTimeout(function () {
      render(search(asciiDigits(q)), q);
    }, 90);
  }

  function open() {
    if (!root.hidden) return;
    lastFocus = document.activeElement;
    root.hidden = false;
    document.documentElement.classList.add('ss-open');
    input.value = '';
    render([], '');
    // ইনপুটে ফোকাস দিই (মোবাইলে কিবোর্ড খুলবে)
    setTimeout(function () { input.focus(); }, 20);
  }

  function close() {
    if (root.hidden) return;
    root.hidden = true;
    document.documentElement.classList.remove('ss-open');
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  /* ── ঘটনা ── */
  Array.prototype.forEach.call(triggers, function (t) {
    t.addEventListener('click', function (e) { e.preventDefault(); open(); });
  });

  root.addEventListener('click', function (e) {
    if (e.target.closest('[data-search-close]')) close();
  });

  input.addEventListener('input', onInput);

  input.addEventListener('keydown', function (e) {
    var items = list.querySelectorAll('.ss-result');
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(active + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(active - 1); }
    else if (e.key === 'Enter') {
      var el = active > -1 ? items[active] : null;
      if (!el) el = items[0];
      if (el && el.dataset.href) { e.preventDefault(); location.href = el.dataset.href; }
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !root.hidden) { close(); return; }
    // Ctrl/⌘+K — যেকোনো পাতা থেকে
    if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      if (root.hidden) open(); else close();
      return;
    }
    // «/» — কোনো ইনপুটে টাইপ না করলে
    if (e.key === '/' && root.hidden) {
      var t = e.target;
      var tag = t && t.tagName ? t.tagName.toUpperCase() : '';
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (t && t.isContentEditable)) return;
      e.preventDefault();
      open();
      return;
    }
    // ফোকাস-ট্র্যাপ
    if (e.key === 'Tab' && !root.hidden) {
      var f = panel.querySelectorAll('input, button, a[href]');
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });
})();
