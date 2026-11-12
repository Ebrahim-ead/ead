/* ============================================================
   site-search.js — পুরো সাইট-জুড়ে সার্চ
   ------------------------------------------------------------
   · সূচি আসে assets/search-index.js থেকে (window.SITE_SEARCH)
     — কোনো fetch নেই, তাই file:// থেকেও কাজ করে।
   · মোডাল ডায়ালগ; Ctrl/⌘+K বা «/» চাপে খোলে।
   · ফল: পাতা, কুরআনের সূরা, **কুরআনের আয়াত**, হাদিসের কিতাব, ধর্মীয় গ্রন্থ।
   · আয়াতের সূচি (۲.১ MB) আলাদা ফাইলে — সার্চে টাইপ করলে তবেই নামে।
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
    grantho: 'গ্রন্থ',
    ayah: 'আয়াত'
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
        if (r.t === 'ayah' && typeof r._i === 'number' && r._i > 40) {
          // মিল-শব্দের আশপাশ দেখাই — লেখার শুরু নয়
          dd.appendChild(document.createTextNode('…' + r.d.slice(r._i - 40)));
        } else if (r.t === 'ayah') {
          dd.appendChild(highlight(r.d, q));
        } else {
          dd.textContent = r.d;
        }
        a.appendChild(dd);
      }

      if (r.t === 'ayah') {
        var go = document.createElement('span');
        go.className = 'ss-ayah-go';
        go.textContent = 'আয়াত খুলুন →';
        a.appendChild(go);
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

  /* ── কুরআনের আয়াত: আলাদা ফাইল, চাহিদা-ভিত্তিক লোড ──
     মূল সূচি ১৮০ KB — হালকা। আয়াত ২.১ MB, তাই প্রথম টাইপে নামে।
     fetch ব্যর্থ হলে (file://) <script> ট্যাগে চেষ্টা করি। */
  var ayahs = null;          // [[সূরা, আয়াত, লেখা, ফোল্ড-করা লেখা], …]
  var ayahState = 'idle';    // idle | loading | ready | failed
  var ayahWaiters = [];

  function readyAyahs(list) {
    ayahs = list || [];
    ayahState = ayahs.length ? 'ready' : 'failed';
    // কী-লেখা আগেই ফোল্ড করে রাখি — প্রতি কী-স্ট্রোকে norm() নয়
    for (var i = 0; i < ayahs.length; i++) ayahs[i][3] = norm(ayahs[i][2]);
    var w = ayahWaiters; ayahWaiters = [];
    for (var k = 0; k < w.length; k++) { try { w[k](); } catch (e) {} }
  }

  function loadAyahs(cb) {
    if (ayahState === 'ready' || ayahState === 'failed') { cb(); return; }
    ayahWaiters.push(cb);
    if (ayahState === 'loading') return;
    ayahState = 'loading';

    var src = 'assets/search-ayahs.js';
    var done = false;
    function finish(list) { if (done) return; done = true; readyAyahs(list); }

    if (window.fetch && location.protocol !== 'file:') {
      fetch(src).then(function (r) { return r.text(); }).then(function (txt) {
        // ফাইলটি «window.SITE_AYAHS=[…];» — JSON অংশটুকু কেটে নিই
        var a = txt.indexOf('['), b = txt.lastIndexOf(']');
        finish(a > -1 && b > a ? JSON.parse(txt.slice(a, b + 1)) : []);
      }).catch(function () { scriptFallback(); });
    } else {
      scriptFallback();
    }

    function scriptFallback() {
      var el = document.createElement('script');
      el.onload = function () { finish(window.SITE_AYAHS || []); };
      el.onerror = function () { finish(null); };
      el.src = src;
      document.head.appendChild(el);
    }
  }

  /* ── প্রতিশব্দ: কুরআনে যে শব্দ নেই, মানুষ যা খোঁজে ──
     যেমন কুরআনে «নামাজ» নয় «সালাত»; «রোজা» নয় «সিয়াম»।
     ব্যবহারকারী একটি লিখলে অন্যটাও খুঁজি। */
  var SYNONYMS = {
    'নামাজ': ['সালাত', 'নামায'],
    'নামায': ['সালাত', 'নামাজ'],
    'সালাত': ['নামাজ'],
    'রোজা': ['সিয়াম', 'সাওম'],
    'রোযা': ['সিয়াম', 'সাওম'],
    'সিয়াম': ['রোজা'],
    'যাকাত': ['জাকাত'],
    'জাকাত': ['যাকাত'],
    'হজ': ['হজ্জ'],
    'ওযু': ['উযু', 'অযু'],
    'গোসল': ['গুসল'],
    'জান্নাত': ['জন্নাত'],
    'জাহান্নাম': ['দোযখ', 'দোজখ'],
    'দোযখ': ['জাহান্নাম'],
    'ফেরেশতা': ['মালাক', 'ফেরেশ্তা'],
    'শয়তান': ['শাইতান', 'ইবলিস'],
    'ইবলিস': ['শয়তান'],
    'তাওবা': ['তওবা'],
    'তওবা': ['তাওবা'],
    'ঈমান': ['ইমান'],
    'ইমান': ['ঈমান'],
    'কিয়ামত': ['কিয়ামত', 'ক্বিয়ামত'],
    'আখিরাত': ['আখেরাত'],
    'আখেরাত': ['আখিরাত'],
    'পাপ': ['গুনাহ', 'পাপ'],
    'গুনাহ': ['পাপ'],
    'ক্ষমা': ['মাগফিরাত'],
    'ধৈর্য': ['সবর'],
    'সবর': ['ধৈর্য'],
    'কৃতজ্ঞতা': ['শোকর'],
    'শোকর': ['কৃতজ্ঞতা'],
    'পরকাল': ['আখিরাত'],
    'আল্লাহ': ['আল্লাহ্'],
    'নবী': ['নবি', 'রাসুল'],
    'রাসুল': ['রাসূল', 'নবী'],
    'কিতাব': ['গ্রন্থ'],
    'দান': ['সদকা'],
    'সদকা': ['দান'],
  };

  /* প্রশ্নকে একাধিক কী-তে ভাঙি */
  function expand(q) {
    var out = [q];
    var extra = SYNONYMS[q];
    if (extra) out = out.concat(extra);
    return out;
  }

  /* আয়াত-ফল: পুরো লেখায় মিল খুঁজি, ফল-সংখ্যা সীমিত রাখি */
  var ayahCache = {};       // প্রশ্ন → ফল (বারবার একই খোঁজে দ্রুত)
  function searchAyahs(nq, limit) {
    if (!ayahs) return [];
    if (ayahCache[nq]) return ayahCache[nq].slice(0, limit);
    var keys = expand(nq).map(norm).filter(function (k, i, arr) { return k && arr.indexOf(k) === i; });
    if (!keys.length) return [];
    var hits = [], seen = {};
    for (var k = 0; k < keys.length; k++) {
      var nk = keys[k];
      for (var i = 0; i < ayahs.length; i++) {
        var a = ayahs[i];
        var at = a[3] || '';
        var idx = at.indexOf(nk);
        if (idx === -1) continue;
        var id = a[0] + ':' + a[1];
        if (seen[id]) continue;
        seen[id] = 1;
        hits.push({ a: a, i: idx });
        if (hits.length >= limit * 6) break;
      }
    }
    ayahCache[nq] = hits;
    return hits.slice(0, limit);
  }

  /* ── স্কোরিং: শিরোনাম-মিল > বর্ণনা > কীওয়ার্ড ── */
  function search(q) {
    var nq = norm(q);
    if (!nq) return [];
    var out = [];
    for (var i = 0; i < data.length; i++) {
      var r = data[i];
      if (!r._n) { r._n = norm(r.n); r._d = norm(r.d || ''); }   // একবারই গুনি
      var name = r._n;
      var desc = r._d;
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
    var top = out.slice(0, 24).map(function (x) { return x.r; });

    /* আয়াত — শুধু ৩+ অক্ষরের খোঁজে (ছোট শব্দে সব মিলে যেত)।
       পুরো তালিকা না ভরিয়ে নিচে জুড়ে দিই: আগে পাতা/সূরা/বই, পরে আয়াত। */
    if (nq.length >= 3) {
      var ah = searchAyahs(nq, 40);
      if (ah.length) {
        // আয়াত সব শেষে — আগে সাধারণ ফল, পরে আয়াত
        ah.slice(0, 14).forEach(function (h) {
          var a = h.a;
          top.push({
            t: 'ayah',
            u: 'quran.html#' + a[0] + ':' + a[1],
            n: 'আয়াত ' + a[1] + ' · সূরা ' + (suraName(a[0]) || a[0]),
            d: a[2],
            _i: h.i,
            _q: nq
          });
        });
      }
    }
    return top;
  }

  /* সূরার নাম — URL থেকে (#সূরা:আয়াত), তাই ক্রম-অনুমান লাগে না */
  var suraNames = null;
  function suraName(n) {
    if (!suraNames) {
      suraNames = {};
      for (var i = 0; i < data.length; i++) {
        var r = data[i];
        if (r.t !== 'quran') continue;
        var m = /#(\d+)$/.exec(r.u);
        if (!m) continue;
        suraNames[+m[1]] = r.n.replace(/^সূরা\s+/, '');
      }
    }
    return suraNames[n];
  }

  var debounce = 0;
  var lastQuery = '';
  function onInput() {
    var q = input.value.trim();
    lastQuery = q;
    if (q.length >= 3 && ayahState !== 'ready') {
      count.textContent = (ayahState === 'loading' ? 'আয়াত খোঁজা হচ্ছে…' : 'আয়াত-সূচি আনা হচ্ছে…');
      loadAyahs(function () {
        if (input.value.trim() !== q) return;   // এর মধ্যে টাইপ বদলেছে
        render(search(asciiDigits(q)), q);
      });
    }
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
    // নীরবে আয়াত-সূচি নামিয়ে রাখি — প্রথম খোঁজেই প্রস্তুত
    setTimeout(function () { loadAyahs(function () {}); }, 300);
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
