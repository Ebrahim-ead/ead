/* ============================================================
   quran.js — the reading engine for quran.html
   ------------------------------------------------------------
   Loads one sura at a time from assets/quran/data/suras/N.json,
   renders Arabic + Bengali + English (+ optional footnotes),
   and keeps the reader's place, bookmarks, and display settings.

   Layers can be toggled independently; text is never altered —
   the only transformation is rendering the publisher's own
   footnote markers as superscripts.
   ============================================================ */
(function () {
  "use strict";

  var DATA = "assets/quran/data/";
  var bnDigits = "০১২৩৪৫৬৭৮৯";
  var LS = {
    last: "quran:last",
    bm: "quran:bookmarks",
    set: "quran:settings"
  };

  /* ---------------------------------------------------------- *
   * helpers
   * ---------------------------------------------------------- */
  function bn(n) {
    return String(n).replace(/[0-9]/g, function (d) { return bnDigits[+d]; });
  }
  /* ০-৯ → 0-9, যাতে বাংলা অঙ্কে লেখা রেফারেন্সও পড়া যায় */
  function fromBengali(t) {
    return String(t).replace(/[০-৯]/g, function (d) {
      return String("০১২৩৪৫৬৭৮৯".indexOf(d));
    });
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function store(key, val) {
    try {
      if (val === undefined) {
        var raw = localStorage.getItem(key);
        return raw === null ? null : JSON.parse(raw);
      }
      localStorage.setItem(key, JSON.stringify(val));
    } catch (e) { /* private mode: carry on without persistence */ }
    return null;
  }
  /* [১] / [1] / [2,3] → superscript markers, nothing else touched */
  function marks(s) {
    return esc(s).replace(/\[([০-৯0-9]+(?:\s*,\s*[০-৯0-9]+)*)\]/g,
      '<span class="fnn">[$1]</span>');
  }

  /* ---------------------------------------------------------- *
   * state
   * ---------------------------------------------------------- */
  var settings = Object.assign({
    ar: true, bn: true, en: true, fn: false,
    arSize: 27, bnSize: 16.5, enSize: 14.5
  }, store(LS.set) || {});

  var bookmarks = store(LS.bm) || [];
  var index = null;
  var current = 0;
  var cache = {};
  var lastQuery = "";
  var fullRun = false;
  var lastQuery = "";
  var fullRun = false;

  /* ---------------------------------------------------------- *
   * elements
   * ---------------------------------------------------------- */
  var $ = function (sel) { return document.querySelector(sel); };
  var listEl, mainEl, searchEl, resultsEl, asideEl, backdropEl;

  /* ---------------------------------------------------------- *
   * boot
   * ---------------------------------------------------------- */
  function boot() {
    listEl = $("#q-sura-list");
    mainEl = $("#q-main");
    searchEl = $("#q-search");
    resultsEl = $("#q-results");
    asideEl = $("#q-aside");
    backdropEl = $("#q-backdrop");
    if (!listEl || !mainEl) return;

    /* Drawer mode is decided here, not left to a media query alone: on a
       laptop the sura list stays a plain column and can never float over
       the ayat. ?drawer=1 / ?drawer=0 force either layout for checking. */
    (function drawerMode() {
      var mq = window.matchMedia("(max-width: 960px)");
      var forced = /[?&]drawer=(0|1)/.exec(location.search);
      function sync() {
        var narrow = forced ? forced[1] === "1" : mq.matches;
        document.documentElement.classList.toggle("q-drawer", narrow);
        if (!narrow) closeDrawer();
      }
      sync();
      if (mq.addEventListener) mq.addEventListener("change", sync);
      else if (mq.addListener) mq.addListener(sync);
    })();

    applySettings();
    wireToolbar();

    fetch(DATA + "index.json")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        index = d;
        renderList();
        var fromHash = location.hash.match(/^#(\d+)(?::(\d+))?$/);
        var last = store(LS.last);
        var start = fromHash ? +fromHash[1] : (last && last.s ? last.s : 1);
        if (!(start >= 1 && start <= 114)) start = 1;
        loadSura(start, fromHash && fromHash[2] ? +fromHash[2] : null, true);
      })
      .catch(function () {
        mainEl.innerHTML = '<div class="q-empty">সূরার তালিকা লোড করা যায়নি। ' +
          'পাতাটি রিফ্রেশ করুন।</div>';
      });
  }

  /* ---------------------------------------------------------- *
   * sura list
   * ---------------------------------------------------------- */

  /* common ways people spell the suras, so a lookup does not depend on
     which transliteration the dataset happened to choose */
  var ALIAS = {
    1: ["fatiha", "fatihah", "fatima"], 2: ["baqara", "baqarah", "bakara"],
    3: ["imran"], 4: ["nisa", "nisaa"], 5: ["maida", "maidah"], 6: ["anam", "anaam"],
    7: ["araf", "aaraf"], 8: ["anfal"], 9: ["tawba", "tawbah", "tauba"],
    10: ["yunus", "younus"], 11: ["hud", "hood"], 12: ["yusuf", "yousuf"],
    13: ["rad", "raad"], 14: ["ibrahim"], 15: ["hijr"], 16: ["nahl"],
    17: ["isra"], 18: ["kahf", "kahaf"], 19: ["maryam", "mariam"],
    20: ["taha", "tahaa"], 21: ["anbiya", "ambiya"], 22: ["hajj", "haj"],
    23: ["muminun", "mominun"], 24: ["nur", "noor"], 25: ["furqan", "furkan"],
    26: ["shuara", "shuaraa"], 27: ["naml"], 28: ["qasas", "kasas"],
    29: ["ankabut", "ankaboot"], 30: ["rum", "room"], 31: ["luqman", "lokman"],
    32: ["sajda", "sajdah"], 33: ["ahzab", "ahzaab"], 34: ["saba", "sabaa"],
    35: ["fatir", "faatir"], 36: ["yasin", "yaseen", "yasin sharif"],
    37: ["saffat", "saaffaat"], 38: ["sad", "saad", "swad"], 39: ["zumar"],
    40: ["ghafir", "ghafur"], 41: ["fussilat", "ha mim"], 42: ["shura", "shoora"],
    43: ["zukhruf"], 44: ["dukhan", "dukhaan"], 45: ["jathiya", "jasiya"],
    46: ["ahqaf"], 47: ["muhammad"], 48: ["fath", "fatah"], 49: ["hujurat", "hujraat"],
    50: ["qaf", "kaaf"], 51: ["dhariyat", "zariyat"], 52: ["tur", "toor"],
    53: ["najm", "najam"], 54: ["qamar", "kamar"], 55: ["rahman", "rahmon"],
    56: ["waqia", "waqiah"], 57: ["hadid"], 58: ["mujadila", "mujadala"],
    59: ["hashr"], 60: ["mumtahina", "mumtahana"], 61: ["saff", "saf"],
    62: ["juma", "jumma"], 63: ["munafiqun", "munafiqoon"], 64: ["taghabun"],
    65: ["talaq", "talak"], 66: ["tahrim", "tahreem"], 67: ["mulk", "mulk sharif"],
    68: ["qalam", "kalam"], 69: ["haqqa", "haqqah"], 70: ["maarij", "marij"],
    71: ["nuh", "nooh"], 72: ["jinn", "jin"], 73: ["muzzammil", "mujammil"],
    74: ["muddassir", "mudassir"], 75: ["qiyama", "qiyamah"], 76: ["insan", "dahr"],
    77: ["mursalat"], 78: ["naba", "nabaah"], 79: ["naziat", "naziyat"],
    80: ["abasa", "abasa"], 81: ["takwir", "takweer"], 82: ["infitar", "infitaf"],
    83: ["mutaffifin", "mutaffifin"], 84: ["inshiqaq", "inshikak"],
    85: ["buruj", "burooj"], 86: ["tariq", "taariq"], 87: ["ala", "aalaa"],
    88: ["ghashiya", "ghashiyah"], 89: ["fajr"], 90: ["balad", "balad sharif"],
    91: ["shams", "shamsh"], 92: ["layl", "lail"], 93: ["duha", "zuha"],
    94: ["sharh", "inshirah"], 95: ["tin", "teen"], 96: ["alaq", "alak"],
    97: ["qadr", "kadar"], 98: ["bayyina", "bayyinah"], 99: ["zalzala", "zilzal"],
    100: ["adiyat", "adiyaat"], 101: ["qaria", "qariah"], 102: ["takathur", "takasur"],
    103: ["asr", "asar"], 104: ["humaza", "humazah"], 105: ["fil", "feel"],
    106: ["quraysh", "kuraish"], 107: ["maun", "maoon"], 108: ["kawthar", "kausar"],
    109: ["kafirun", "kafiroon"], 110: ["nasr", "nasr sharif"], 111: ["lahab", "masad"],
    112: ["ikhlas", "ekhlas"], 113: ["falaq", "falak"], 114: ["nas", "naas", "an-nas"]
  };

  /* let readers type loosely: "al-ikhlas" and "Al-Ikhlaas" are the same
     sura, and nobody wants to think about hyphens while looking one up */
  function squash(t) {
    return String(t).toLowerCase().replace(/[\s\-'’]/g, "");
  }
  function loose(t) {
    return squash(t).replace(/(.)\1+/g, "$1");
  }
  function matches(hay, hayLoose, q) {
    if (hay.indexOf(q) !== -1) return true;
    var lq = loose(q);
    return lq.length >= 4 && hayLoose.indexOf(lq) !== -1;
  }

  function suraButton(s) {
    var text = squash(s.bn + " " + s.translit + " " + s.name + " " +
      (ALIAS[s.n] || []).join(" "));
    return '<button class="q-sura" type="button" data-sura="' + s.n + '"' +
      (s.n === current ? ' aria-current="true"' : '') +
      ' data-hay="' + esc(text) + '" data-hay2="' + esc(loose(text)) + '">' +
      '<span class="num">' + bn(s.n) + '</span>' +
      '<span class="txt"><span class="bn">' + esc(s.bn) + '</span>' +
      '<span class="meta">' + esc(s.translit) + ' · ' + bn(s.count) + ' আয়াত · ' +
      (s.type === "makki" ? "মাক্কী" : "মাদানী") + '</span></span>' +
      '<span class="ar" aria-hidden="true">' + esc(s.name) + '</span>' +
      '</button>';
  }

  function renderList() {
    /* one straight 1–114 list: no grouping, just the order of the mushaf */
    listEl.innerHTML = index.suras.map(suraButton).join("");

    listEl.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-sura]");
      if (!btn) return;
      loadSura(+btn.dataset.sura);
      closeDrawer();
    });

    $("#q-total").textContent = bn(index.total) + " আয়াত · " + bn(114) + " সূরা";
    bindFilter();
  }

  /* 114 names are a lot: give the reader a box instead of a hunt */
  function bindFilter() {
    var box = document.getElementById("q-filter");
    if (!box) return;
    box.addEventListener("input", function () {
      var q = squash(box.value.trim());
      var shown = 0;
      [].forEach.call(listEl.querySelectorAll(".q-sura"), function (b) {
        var hit = !q || matches(b.dataset.hay, b.dataset.hay2 || "", q);
        b.hidden = !hit;
        if (hit) shown++;
      });
      var none = document.getElementById("q-filter-none");
      if (none) none.hidden = !(q && !shown);
    });
  }

  function markActive(n) {
    [].forEach.call(listEl.querySelectorAll(".q-sura"), function (b) {
      var on = +b.dataset.sura === n;
      b.classList.toggle("on", on);
      if (on) b.setAttribute("aria-current", "true");
      else b.removeAttribute("aria-current");
    });
  }

  /* ---------------------------------------------------------- *
   * load + render one sura
   * ---------------------------------------------------------- */
  function loadSura(n, jumpTo, replace) {
    if (!(n >= 1 && n <= 114)) return;
    current = n;
    markActive(n);
    closeDrawer();

    var meta = index.suras[n - 1];
    var hash = "#" + n + (jumpTo ? ":" + jumpTo : "");
    if (replace) history.replaceState(null, "", hash);
    else history.pushState(null, "", hash);

    if (cache[n]) {
      if (jumpTo && n === current && mainEl.querySelector("#v" + jumpTo)) {
        /* already rendered: just move to the ayah instead of repainting */
        scrollToVerse(jumpTo);
        return;
      }
      paint(n, meta, cache[n], jumpTo);
      return;
    }

    mainEl.innerHTML = '<div class="q-empty">সূরা লোড হচ্ছে…</div>';
    fetch(DATA + "suras/" + n + ".json")
      .then(function (r) { return r.json(); })
      .then(function (d) { cache[n] = d; paint(n, meta, d, jumpTo); })
      .catch(function () {
        mainEl.innerHTML = '<div class="q-empty">এই সূরাটি লোড করা যায়নি। ' +
          'ইন্টারনেট সংযোগ দেখে আবার চেষ্টা করুন।</div>';
      });
  }

  /* ডেটার প্রতিটি সূরার প্রথম আয়াতই বিসমিল্লাহ দিয়ে শুরু (সূরা ১ সহ),
     তাই আলাদা বাসমালা ব্লক ছাপালে একই কথা দুইবার দেখায়। সূরা ৯-এ নেই।
     ভবিষ্যতে বাসমালা আলাদা থাকা সংস্করণে এলে ব্লকটি নিজে থেকেই ফিরবে। */
  var BASMALA = /^\s*بِسْمِ/;
  function paint(n, meta, d, jumpTo) {
    var first = (d.verses && d.verses[0] && d.verses[0].ar) || "";
    var basmala = n !== 9 && !BASMALA.test(first);

    var head = '<div class="q-sura-head"><div class="top">' +
      '<h2>' + bn(n) + '. ' + esc(meta.bn) + '</h2>' +
      '<span class="ar-name">سورة ' + esc(meta.name) + '</span></div>' +
      '<div class="badges">' +
      '<span class="q-badge">' + esc(meta.translit) + '</span>' +
      '<span class="q-badge plain">' + (meta.type === "makki" ? "মাক্কী" : "মাদানী") + '</span>' +
      '<span class="q-badge plain">' + bn(meta.count) + ' আয়াত</span>' +
      '</div></div>';

    var verses = d.verses.map(function (v) {
      var id = n + ":" + v.a;
      var has = bookmarks.indexOf(id) !== -1;
      return '<div class="q-verse" id="v' + v.a + '" data-v="' + v.a + '">' +
        '<div class="q-verse-top">' +
        '<span class="q-ayah-num">' + bn(n) + ':' + bn(v.a) + '</span>' +
        '<span class="q-verse-tools">' +
        '<button class="q-icon' + (has ? " on" : "") + '" data-bm="' + id + '" type="button" ' +
        'aria-label="বুকমার্ক" title="বুকমার্ক"><svg viewBox="0 0 24 24"><path d="M6 3h12v18l-6-4-6 4z"/></svg></button>' +
        '<button class="q-icon" data-copy="' + id + '" type="button" aria-label="কপি" title="কপি">' +
        '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="12" height="12" rx="2"/>' +
        '<path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg></button>' +
        '</span></div>' +
        '<div class="q-ar">' + esc(v.ar) + '</div>' +
        '<div class="q-bn">' + marks(v.bn) + '</div>' +
        '<div class="q-en">' + marks(v.en) + '</div>' +
        (v.fn ? '<details class="q-fn"><summary>সংক্ষিপ্ত তাফসীর</summary>' +
          '<div class="q-fn-body">' + esc(v.fn) + '</div></details>' : '') +
        '</div>';
    }).join("");

    var pager = '<div class="q-pager">' +
      (n > 1 ? '<button class="q-btn" type="button" data-sura="' + (n - 1) + '">← ' +
        bn(n - 1) + '. ' + esc(index.suras[n - 2].bn) + '</button>' : "<span></span>") +
      (n < 114 ? '<button class="q-btn" type="button" data-sura="' + (n + 1) + '">' +
        bn(n + 1) + '. ' + esc(index.suras[n].bn) + ' →</button>' : "<span></span>") +
      '</div>';

    mainEl.innerHTML = head +
      (basmala ? '<div class="q-basmala">بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ</div>' : "") +
      '<div class="q-verses">' + verses + '</div>' + pager;

    mainEl.querySelectorAll("[data-sura]").forEach(function (b) {
      b.addEventListener("click", function () { loadSura(+b.dataset.sura); });
    });
    mainEl.querySelectorAll("[data-bm]").forEach(function (b) {
      b.addEventListener("click", function () { toggleBookmark(b); });
    });
    mainEl.querySelectorAll("[data-copy]").forEach(function (b) {
      b.addEventListener("click", function () { copyVerse(b); });
    });

    applySettings();
    store(LS.last, { s: n, v: 1 });
    if (jumpTo) scrollToVerse(jumpTo);
    else window.scrollTo({ top: mainEl.offsetTop - 120, behavior: "auto" });
  }

  function scrollToVerse(v) {
    var el = mainEl.querySelector('#v' + v);
    if (!el) return;
    el.scrollIntoView({ block: "center", behavior: "auto" });
    el.classList.add("hit");
    setTimeout(function () { el.classList.remove("hit"); }, 1700);
  }

  /* ---------------------------------------------------------- *
   * bookmarks + copy
   * ---------------------------------------------------------- */
  function toggleBookmark(btn) {
    var id = btn.dataset.bm;
    var i = bookmarks.indexOf(id);
    if (i === -1) bookmarks.push(id); else bookmarks.splice(i, 1);
    btn.classList.toggle("on", i === -1);
    store(LS.bm, bookmarks);
    renderBookmarks();
  }

  function copyVerse(btn) {
    var el = btn.closest(".q-verse");
    if (!el) return;
    var s = current + ":" + el.dataset.v;
    var text = [
      el.querySelector(".q-ar").textContent,
      el.querySelector(".q-bn").textContent,
      el.querySelector(".q-en").textContent,
      "— কুরআন " + s + " · অনুবাদ: ড. আবূ বকর মুহাম্মাদ যাকারিয়া (QuranEnc.com)"
    ].join("\n");
    var done = function () {
      btn.classList.add("on");
      setTimeout(function () { btn.classList.remove("on"); }, 1200);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, done);
    } else {
      var ta = document.createElement("textarea");
      ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); } catch (e) {}
      document.body.removeChild(ta); done();
    }
  }

  function renderBookmarks() {
    var box = $("#q-bm-list");
    if (!box) return;
    if (!bookmarks.length) {
      box.innerHTML = '<div class="q-empty">এখনো কোনো আয়াত বুকমার্ক করা হয়নি। ' +
        'যে আয়াত রাখতে চান, তার পাশের বুকমার্ক আইকনে চাপ দিন।</div>';
      return;
    }
    box.innerHTML = bookmarks.slice().reverse().map(function (id) {
      var p = id.split(":");
      var s = +p[0];
      var name = index ? index.suras[s - 1].bn : "";
      return '<button class="q-result" type="button" data-goto="' + id + '">' +
        '<span class="rn">' + bn(s) + ':' + bn(p[1]) + '</span>' +
        '<span class="rt">' + esc(name) + ' — ' + bn(s) + ' নং সূরা</span></button>';
    }).join("");
  }

  /* ---------------------------------------------------------- *
   * toolbar
   * ---------------------------------------------------------- */
  function wireToolbar() {
    /* layer toggles */
    [["#q-t-ar", "ar"], ["#q-t-bn", "bn"], ["#q-t-en", "en"], ["#q-t-fn", "fn"]].forEach(function (pair) {
      var el = $(pair[0]);
      if (!el) return;
      el.classList.toggle("on", !!settings[pair[1]]);
      el.setAttribute("aria-pressed", settings[pair[1]] ? "true" : "false");
      el.addEventListener("click", function () {
        settings[pair[1]] = !settings[pair[1]];
        el.classList.toggle("on", settings[pair[1]]);
        el.setAttribute("aria-pressed", settings[pair[1]] ? "true" : "false");
        store(LS.set, settings);
        applySettings();
      });
    });

    /* font sizes */
    [["#q-size-ar", "arSize", "--q-ar-size", 18, 44],
     ["#q-size-bn", "bnSize", "--q-bn-size", 13, 26],
     ["#q-size-en", "enSize", "--q-en-size", 12, 22]].forEach(function (cfg) {
      var el = $(cfg[0]);
      if (!el) return;
      el.value = settings[cfg[1]];
      el.addEventListener("input", function () {
        settings[cfg[1]] = +el.value;
        store(LS.set, settings);
        applySettings();
      });
    });

    /* search */
    var timer = null;
    if (searchEl) {
      searchEl.addEventListener("input", function () {
        clearTimeout(timer);
        timer = setTimeout(function () { doSearch(searchEl.value.trim()); }, 220);
      });
      searchEl.addEventListener("keydown", function (e) {
        if (e.key === "Escape") { searchEl.value = ""; doSearch(""); }
      });
    }

    /* bookmark panel */
    var bmBtn = $("#q-bm-btn"), bmPanel = $("#q-bm-panel");
    if (bmBtn && bmPanel) {
      bmBtn.addEventListener("click", function () {
        var open = bmPanel.hasAttribute("hidden");
        if (open) { bmPanel.removeAttribute("hidden"); renderBookmarks(); }
        else bmPanel.setAttribute("hidden", "");
        bmBtn.classList.toggle("on", open);
        bmBtn.setAttribute("aria-expanded", open ? "true" : "false");
      });
    }
    document.addEventListener("click", function (e) {
      var g = e.target.closest && e.target.closest("[data-goto]");
      if (!g) return;
      var p = g.dataset.goto.split(":");
      loadSura(+p[0], +p[1]);
      if (resultsEl) { resultsEl.setAttribute("hidden", ""); resultsEl.innerHTML = ""; }
      if (searchEl) searchEl.value = "";
      lastQuery = ""; fullRun = false;
      if (bmPanel) bmPanel.setAttribute("hidden", "");
      if (bmBtn) { bmBtn.classList.remove("on"); bmBtn.setAttribute("aria-expanded", "false"); }
    });

    /* mobile drawer */
    var dBtn = $("#q-drawer-btn");
    if (dBtn) dBtn.addEventListener("click", function () {
      asideEl.classList.add("open"); backdropEl.classList.add("on");
    });
    if (backdropEl) backdropEl.addEventListener("click", closeDrawer);

    /* print */
    var pBtn = $("#q-print");
    if (pBtn) pBtn.addEventListener("click", function () { window.print(); });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeDrawer();
      var t = e.target;
      if (t && t.matches && t.matches("input,textarea,select,[contenteditable]")) return;
      if (e.key === "ArrowRight" && current < 114) loadSura(current + 1);
      if (e.key === "ArrowLeft" && current > 1) loadSura(current - 1);
    });

    window.addEventListener("popstate", function () {
      var m = location.hash.match(/^#(\d+)(?::(\d+))?$/);
      if (m) loadSura(+m[1], m[2] ? +m[2] : null, true);
    });

    /* keep the reader's place */
    var saveTimer = null;
    window.addEventListener("scroll", function () {
      clearTimeout(saveTimer);
      saveTimer = setTimeout(function () {
        if (!current) return;
        var seen = 1;
        mainEl.querySelectorAll(".q-verse").forEach(function (v) {
          if (v.getBoundingClientRect().top < 140) seen = +v.dataset.v;
        });
        store(LS.last, { s: current, v: seen });
      }, 600);
    }, { passive: true });
  }

  function closeDrawer() {
    if (asideEl) asideEl.classList.remove("open");
    if (backdropEl) backdropEl.classList.remove("on");
  }

  /* ---------------------------------------------------------- *
   * display settings
   * ---------------------------------------------------------- */
  function applySettings() {
    var root = document.documentElement;
    root.style.setProperty("--q-ar-size", settings.arSize + "px");
    root.style.setProperty("--q-bn-size", settings.bnSize + "px");
    root.style.setProperty("--q-en-size", settings.enSize + "px");

    if (!mainEl) return;
    mainEl.querySelectorAll(".q-ar").forEach(function (e) { e.classList.toggle("q-hidden", !settings.ar); });
    mainEl.querySelectorAll(".q-bn").forEach(function (e) { e.classList.toggle("q-hidden", !settings.bn); });
    mainEl.querySelectorAll(".q-en").forEach(function (e) { e.classList.toggle("q-hidden", !settings.en); });
    mainEl.querySelectorAll(".q-fn").forEach(function (e) {
      e.classList.toggle("q-hidden", !settings.fn);
    });
  }

  /* ---------------------------------------------------------- *
   * search — Bengali, English, or an ayah reference
   * ---------------------------------------------------------- */
  function doSearch(q) {
    if (!resultsEl) return;
    if (!q) {
      lastQuery = ""; fullRun = false;
      resultsEl.setAttribute("hidden", ""); resultsEl.innerHTML = ""; return;
    }

    /* পাঠক বাংলা অঙ্কেই লিখবেন — ২:২৫৫ আর 2:255 দুটোই চেনা দরকার */
    var ref = fromBengali(q).match(/^\s*(\d{1,3})\s*[:\s]\s*(\d{1,3})\s*$/);
    if (ref && +ref[1] >= 1 && +ref[1] <= 114) {
      loadSura(+ref[1], +ref[2]);
      resultsEl.setAttribute("hidden", "");
      return;
    }

    /* sura by name */
    var nameHits = index.suras.filter(function (s) {
      return s.bn.indexOf(q) !== -1 || s.translit.toLowerCase().indexOf(q.toLowerCase()) !== -1;
    });
    if (nameHits.length === 1) { loadSura(nameHits[0].n); resultsEl.setAttribute("hidden", ""); return; }

    resultsEl.removeAttribute("hidden");
    var needle = q.toLowerCase();
    var hits = [];

    /* stage one: what is already in memory, so the first results are instant */
    Object.keys(cache).forEach(function (k) { scan(cache[k], needle, hits); });
    hits.sort(function (a, b) { return a.s - b.s || a.v - b.v; });
    renderHits(hits, needle, "partial");

    /* stage two: the reader asks for the whole Quran — only then do we
       pull the remaining sura files, eight at a time with a counter */
    lastQuery = needle;
  }

  function searchAll() {
    var needle = lastQuery;
    if (!needle || fullRun) return;
    fullRun = true;

    var hits = [];
    Object.keys(cache).forEach(function (k) { scan(cache[k], needle, hits); });

    var pending = [];
    for (var i = 1; i <= 114; i++) if (!cache[i]) pending.push(i);
    var total = pending.length;
    var batch = 8;

    (function step() {
      if (searchEl.value.trim().toLowerCase() !== needle) { fullRun = false; return; }
      if (!pending.length) {
        fullRun = false;
        hits.sort(function (a, b) { return a.s - b.s || a.v - b.v; });
        renderHits(hits, needle, "final");
        return;
      }
      var slice = pending.splice(0, batch);
      renderHits(hits, needle, "progress", total - pending.length, total);
      Promise.all(slice.map(function (n) {
        return fetch(DATA + "suras/" + n + ".json").then(function (r) { return r.json(); })
          .then(function (d) { cache[n] = d; return d; }).catch(function () { return null; });
      })).then(function (list) {
        if (searchEl.value.trim().toLowerCase() !== needle) { fullRun = false; return; }
        list.forEach(function (d) { if (d) scan(d, needle, hits); });
        step();
      });
    })();
  }

  function scan(sura, needle, hits) {
    sura.verses.forEach(function (v) {
      if (v.bn.toLowerCase().indexOf(needle) !== -1 ||
          v.en.toLowerCase().indexOf(needle) !== -1) {
        hits.push({ s: sura.n, v: v.a, bn: v.bn, en: v.en });
      }
    });
  }

  /* mode: "partial" = loaded suras only, "progress" = sweep running,
     "final" = the whole Quran was searched */
  function renderHits(hits, needle, mode, done, total) {
    var cap = 60;
    var head = "", foot = "";

    if (mode === "partial") {
      head = hits.length
        ? '<div class="q-empty" style="padding:4px 10px 8px">লোড করা ' + bn(Object.keys(cache).length) +
          'টি সূরায় ' + bn(hits.length) + 'টি আয়াতে পাওয়া গেছে</div>'
        : "";
      foot = '<div class="q-empty" style="padding:6px 10px 10px">' +
        '<button class="q-btn" type="button" id="q-search-all">সম্পূর্ণ কুরআনে খুঁজুন — ' +
        'সব সূরা লোড হবে, কিছুটা সময় লাগবে</button></div>';
    } else if (mode === "progress") {
      head = '<div class="q-empty" style="padding:4px 10px 8px">খোঁজা হচ্ছে… ' +
        bn(done) + ' / ' + bn(total) + ' সূরা · ' + bn(hits.length) + 'টি মিল</div>';
    } else {
      if (!hits.length) {
        resultsEl.innerHTML = '<div class="q-empty">কোনো আয়াত পাওয়া যায়নি — অন্য শব্দ দিয়ে চেষ্টা করুন, ' +
          'অথবা <b>২:২৫৫</b> এভাবে সূরা:আয়াত নম্বর লিখুন।</div>';
        return;
      }
      head = '<div class="q-empty" style="padding:4px 10px 8px">' +
        bn(hits.length) + 'টি আয়াতে পাওয়া গেছে (পুরো কুরআনে)</div>';
      if (hits.length > cap) {
        foot = '<div class="q-empty">প্রথম ' + bn(cap) + 'টি দেখানো হচ্ছে · আরও ' +
          bn(hits.length - cap) + 'টি আছে — শব্দটা আরেকটু নির্দিষ্ট করুন।</div>';
      }
    }

    var html = hits.slice(0, cap).map(function (h) {
      return '<button class="q-result" type="button" data-goto="' + h.s + ":" + h.v + '">' +
        '<span class="rn">' + bn(h.s) + ':' + bn(h.v) + '</span>' +
        '<span class="rt">' + hilite(h.bn, needle) + '</span></button>';
    }).join("");

    resultsEl.innerHTML = head + html + foot;
    var all = document.getElementById("q-search-all");
    if (all) all.addEventListener("click", searchAll);
  }

  function hilite(text, needle) {
    var i = text.toLowerCase().indexOf(needle);
    if (i === -1) return esc(text.slice(0, 180));
    var start = Math.max(0, i - 45);
    var piece = (start > 0 ? "…" : "") + text.slice(start, start + 190);
    var j = piece.toLowerCase().indexOf(needle);
    if (j === -1) return esc(piece);
    return esc(piece.slice(0, j)) + "<mark>" + esc(piece.substr(j, needle.length)) + "</mark>" +
      esc(piece.slice(j + needle.length));
  }

  /* ---------------------------------------------------------- */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
