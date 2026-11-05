/* ============================================================
   hadith.js — the reading engine for hadith.html
   ------------------------------------------------------------
   Loads one chapter at a time from assets/hadith/data/<book>/<n>.json,
   renders Arabic matn + English translation, and keeps the reader's
   place, bookmarks and display settings.

   Text is never altered: the only transformation is turning the
   narrator prefix and the hadith number into separate lines of UI.
   ============================================================ */
(function () {
  "use strict";

  var DATA = "assets/hadith/data/";
  var bnDigits = "০১২৩৪৫৬৭৮৯";
  var LS = {
    last: "hadith:last",
    bm: "hadith:bookmarks",
    set: "hadith:settings"
  };

  /* ---------------------------------------------------------- *
   * helpers
   * ---------------------------------------------------------- */
  function bn(n) {
    return String(n).replace(/[0-9]/g, function (d) { return bnDigits[+d]; });
  }
  /* ৩৪১৭৮ → ৩৪,১৭৮ (বাংলাদেশি হাজার-লক্ষের নিয়মে নয়, সাধারণ তিনে-তিনে) */
  function bnNum(n) {
    return bn(String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","));
  }
  /* ০-৯ → 0-9, so references typed in Bengali digits are understood */
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
  function norm(s) {
    return String(s || "").toLowerCase();
  }

  /* ---------------------------------------------------------- *
   * state
   * ---------------------------------------------------------- */
  var settings = Object.assign({
    arOn: true, bnOn: true,
    arSize: 25, bnSize: 17
  }, store(LS.set) || {});

  var index = null;          /* { books:[...], total } */
  var bookSlug = "bukhari";
  var chapterId = 1;
  var cache = {};            /* "book/chapter" → payload */
  var bookmarks = store(LS.bm) || [];
  var searchHits = [];       /* [{book, chapter, id, ar, en, n}] */

  var mainEl, listEl, totalEl, resultsEl, bmEl;

  /* ---------------------------------------------------------- *
   * book / chapter lookup
   * ---------------------------------------------------------- */
  function book() {
    if (!index) return null;
    for (var i = 0; i < index.books.length; i++) {
      if (index.books[i].slug === bookSlug) return index.books[i];
    }
    return null;
  }
  function chapter(id) {
    var b = book();
    if (!b) return null;
    for (var i = 0; i < b.chapters.length; i++) {
      if (b.chapters[i].id === id) return b.chapters[i];
    }
    return null;
  }
  function bookName(slug) {
    for (var i = 0; i < index.books.length; i++) {
      if (index.books[i].slug === slug) return index.books[i].bn;
    }
    return slug;
  }

  /* ---------------------------------------------------------- *
   * drawer (mobile book/chapter tree)
   * ---------------------------------------------------------- */
  var asideEl, backdropEl, drawerBtn;
  function isDrawer() { return document.documentElement.classList.contains("h-drawer"); }
  function openDrawer() {
    if (!isDrawer()) return;
    asideEl.classList.add("open");
    backdropEl.classList.add("on");
    if (drawerBtn) drawerBtn.setAttribute("aria-expanded", "true");
  }
  function closeDrawer() {
    if (!asideEl) return;
    asideEl.classList.remove("open");
    if (backdropEl) backdropEl.classList.remove("on");
    if (drawerBtn) drawerBtn.setAttribute("aria-expanded", "false");
  }
  function syncDrawerMode() {
    var narrow = window.matchMedia("(max-width:960px)").matches;
    document.documentElement.classList.toggle("h-drawer", narrow);
    if (!narrow) closeDrawer();
  }

  /* ---------------------------------------------------------- *
   * left column: six books + chapters of the open book
   * ---------------------------------------------------------- */
  function renderBooks() {
    var host = document.getElementById("h-books");
    if (!host) return;
    host.innerHTML = index.books.map(function (b) {
      return '<button class="h-book' + (b.slug === bookSlug ? " on" : "") + '" type="button" ' +
        'data-book="' + esc(b.slug) + '"' + (b.slug === bookSlug ? ' aria-current="true"' : "") + '>' +
        '<b>' + esc(b.bn) + '</b><small>' + bnNum(b.count) + ' হাদিস</small></button>';
    }).join("");
    host.querySelectorAll("[data-book]").forEach(function (btn) {
      btn.addEventListener("click", function () { loadBook(btn.dataset.book, 1); });
    });
  }

  function renderChapters() {
    var b = book();
    if (!b || !listEl) return;
    listEl.innerHTML = b.chapters.map(function (c) {
      var name = c.bn || c.en || "অধ্যায় " + bn(c.id);
      return '<button class="h-ch' + (c.id === chapterId ? " on" : "") + '" type="button" ' +
        'data-ch="' + c.id + '"' + (c.id === chapterId ? ' aria-current="true"' : "") + '>' +
        '<span class="num">' + bn(c.id) + '</span>' +
        '<span class="txt"><span class="bn">' + esc(name) + '</span>' +
        '<span class="meta">' + bn(c.count) + ' হাদিস</span>' +
        (c.from && c.to ? '<span class="meta h-range">' + bn(c.from) + ' – ' + bn(c.to) + ' নং</span>' : '') +
        '</span></button>';
    }).join("");
    listEl.querySelectorAll("[data-ch]").forEach(function (btn) {
      btn.addEventListener("click", function () { loadChapter(+btn.dataset.ch); });
    });
    if (totalEl) {
      totalEl.textContent = bnNum(b.count) + " হাদিস · " + bn(b.chapters.length) +
        " অধ্যায়" + (index.total ? " · সব কিতাবে " + bnNum(index.total) : "");
    }
  }

  function markActive() {
    if (!listEl) return;
    listEl.querySelectorAll(".h-ch").forEach(function (b) {
      var on = +b.dataset.ch === chapterId;
      b.classList.toggle("on", on);
      if (on) b.setAttribute("aria-current", "true");
      else b.removeAttribute("aria-current");
    });
  }

  /* ---------------------------------------------------------- *
   * filtering the chapter list
   * ---------------------------------------------------------- */
  function bindFilter() {
    var box = document.getElementById("h-filter");
    var none = document.getElementById("h-filter-none");
    if (!box) return;
    box.addEventListener("input", function () {
      var q = norm(box.value).trim();
      var shown = 0;
      listEl.querySelectorAll(".h-ch").forEach(function (b) {
        var c = chapter(+b.dataset.ch);
        var hay = norm((c.ar || "") + " " + (c.en || "") + " " + (c.bn || ""));
        var hit = !q || hay.indexOf(q) !== -1;
        b.hidden = !hit;
        if (hit) shown++;
      });
      if (none) none.hidden = !(q && !shown);
    });
  }

  /* ---------------------------------------------------------- *
   * load + render one chapter
   * ---------------------------------------------------------- */
  function loadBook(slug, ch) {
    bookSlug = slug;
    renderBooks();
    renderChapters();     // বই বদলালে নিশ্চিতভাবেই তালিকাও বদলাবে
    loadChapter(ch || 1);
  }

  function loadChapter(id, jumpTo, replace) {
    var b = book();
    if (!b) return;
    if (!chapter(id)) id = b.chapters[0].id;
    chapterId = id;
    markActive();
    closeDrawer();

    var hash = "#" + bookSlug + ":" + id + (jumpTo ? ":" + jumpTo : "");
    if (replace) history.replaceState(null, "", hash);
    else history.pushState(null, "", hash);

    var key = bookSlug + "/" + id;
    if (cache[key]) {
      if (jumpTo && mainEl.querySelector('[data-i="' + jumpTo + '"]')) { scrollToItem(jumpTo); return; }
      paint(id, cache[key], jumpTo);
      return;
    }

    mainEl.innerHTML = '<div class="h-empty">অধ্যায় লোড হচ্ছে…</div>';
    fetch(DATA + bookSlug + "/" + id + ".json")
      .then(function (r) { return r.json(); })
      .then(function (d) { cache[key] = d; paint(id, d, jumpTo); })
      .catch(function () {
        mainEl.innerHTML = '<div class="h-empty">এই অধ্যায়টি লোড করা যায়নি। ' +
          'ইন্টারনেট সংযোগ দেখে আবার চেষ্টা করুন।</div>';
      });
  }

  function paint(id, d) {
    var b = book();
    var c = chapter(id) || {};
    var name = c.bn || c.en || ("অধ্যায় " + bn(id));

    var head = '<div class="h-head"><div class="top">' +
      '<h2>' + esc(b.bn) + ' — ' + bn(id) + '. ' + esc(name) + '</h2>' +
      '<span class="ar-name">' + esc(b.ar || "") + '</span></div>' +
      '<div class="badges">' +
      '<span class="h-badge">' + bn(d.verses.length) + ' হাদিস</span>' +
      '<span class="h-badge plain">হাদিস ' + bn(c.from || 0) + '–' + bn(c.to || 0) + '</span>' +
      '</div></div>';

    mainEl.innerHTML = head + '<div class="h-items" id="h-items"></div>';
    paintItems(d.verses);

    var i = b.chapters.findIndex(function (x) { return x.id === id; });
    var prev = i > 0 ? b.chapters[i - 1] : null;
    var next = i > -1 && i < b.chapters.length - 1 ? b.chapters[i + 1] : null;
    var pager = '<div class="h-pager">' +
      (prev ? '<button class="h-btn" type="button" data-ch="' + prev.id + '">← ' +
        bn(prev.id) + '. ' + esc(prev.bn || prev.en) + '</button>' : "<span></span>") +
      (next ? '<button class="h-btn" type="button" data-ch="' + next.id + '">' +
        bn(next.id) + '. ' + esc(next.bn || next.en) + ' →</button>' : "<span></span>") +
      '</div>';

    var foot = document.createElement("div");
    foot.className = "h-chapter-foot";
    foot.innerHTML = pager;
    mainEl.appendChild(foot);
    foot.querySelectorAll("[data-ch]").forEach(function (btn) {
      btn.addEventListener("click", function () { loadChapter(+btn.dataset.ch); });
    });

    bindGradeFilter();
    applySettings();
    store(LS.last, { b: bookSlug, c: id });
  }

  /* ---------------------------------------------------------- *
   * এক অধ্যায়ের ভেতরে পৃষ্ঠা-পৃষ্ঠা করে আঁকা
   * ---------------------------------------------------------- */
  function itemHTML(v, k) {
    var ref = bookSlug + ":" + v.i;
    var has = bookmarks.indexOf(ref) !== -1;
    var g = v.g ? '<span class="h-grade ' + esc(v.gc || "other") + '">' + esc(v.g) + '</span>' : "";
    /* উৎসে দুটি ভিন্ন হাদিস একই নম্বরে এলে দ্বিতীয়টিকে "সংস্করণ" বলা হয় */
    var label = esc(book().short || book().bn) + ' ' + bn(v.i) +
      (v.dup ? ' <small style="opacity:.7">(সংস্করণ)</small>' : "");
    /* উৎসেই এই হাদিসের বাংলা দেওয়া নেই — ফাঁকা দেখানোর বদলে জানিয়ে দেওয়া */
    var noBn = !v.b || /^(অনুবাদ পাওয়া যায়নি।?|\(\.\.\.\)|—|-)$/.test(v.b);
    return '<div class="h-item' + (has ? " bm" : "") + '" id="h' + k + '" data-i="' + v.i + '">' +
      '<div class="h-item-top">' +
      '<span class="h-num">' + label + '</span>' +
      g +
      (v.n ? '<span class="h-narrator">' + esc(v.n) + '</span>' : "") +
      '<span class="h-item-tools">' +
      '<button class="h-icon' + (has ? " on" : "") + '" data-bm="' + ref + '" type="button" ' +
      'aria-label="বুকমার্ক" title="বুকমার্ক"><svg viewBox="0 0 24 24"><path d="M6 3h12v18l-6-4-6 4z"/></svg></button>' +
      '<button class="h-icon" data-copy="' + ref + '" type="button" aria-label="কপি" title="কপি">' +
      '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="12" height="12" rx="2"/>' +
      '<path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg></button>' +
      '</span></div>' +
      (v.a ? '<div class="h-ar">' + esc(v.a) + '</div>' : "") +
      '<div class="h-bn' + (noBn ? ' h-bn-missing' : '') + '">' +
        (noBn ? 'এই হাদিসের বাংলা অনুবাদ উৎসে দেওয়া নেই — উপরের আরবি পাঠটাই মূল।'
              : esc(v.b)) + '</div>' +
      (!v.a ? '<div class="h-ar-missing">এই হাদিসের আরবি পাঠ উৎসে দেওয়া নেই।</div>' : "") +
      (v.tah ? '<div class="h-tah"><b>তাহকীক:</b> ' + esc(v.tah) + '</div>' : "") +
      (v.no ? '<details class="h-note-d"><summary>ব্যাখ্যা ও সনদ</summary>' +
        '<div class="h-note-body">' + esc(v.no) + '</div></details>' : "") +
      '</div>';
  }

  /* পুরো অধ্যায় একসঙ্গে দেখানো হয় — কোনো পৃষ্ঠা/পেজার নেই। তবুও বড় অধ্যায়ে
     (নামায ৭৯২, আদাব ৪১৪) একবারে ৭০০+ কার্ড আঁকলে ব্রাউজার ঝুলে যায়, তাই
     ব্যাচে (CHUNK করে) আঁকা হয় — চোখে সবই এক পৃষ্ঠা, কিন্তু ব্রাউজার বাঁচে। */
  var CHUNK = 100;

  function paintItems(items) {
    var host = document.getElementById("h-items");
    if (!host) return;
    host.innerHTML = "";
    var at = 0;

    function step() {
      if (!host.isConnected) return;          /* এর মধ্যে অন্য অধ্যায় খোলা হয়েছে */
      var slice = items.slice(at, at + CHUNK);
      var html = slice.map(function (v, k) {
        return itemHTML(v, at + k);
      }).join("");
      host.insertAdjacentHTML("beforeend", html);
      at += CHUNK;
      if (at < items.length) {
        setTimeout(step, 0);
      } else {
        bindItemTools(host);
        applySettings();
      }
    }
    step();
  }

  function bindItemTools(host) {
    host.querySelectorAll("[data-bm]").forEach(function (btn) {
      btn.addEventListener("click", function () { toggleBookmark(btn); });
    });
    host.querySelectorAll("[data-copy]").forEach(function (btn) {
      btn.addEventListener("click", function () { copyItem(btn); });
    });
  }

  function scrollToItem(num, tries) {
    tries = tries || 0;
    var el = mainEl.querySelector('[data-i="' + num + '"]');
    if (!el) {
      /* বড় অধ্যায় ব্যাচে আঁকা হচ্ছে — কার্ডটি এখনো তৈরি হয়নি, এক মুহূর্ত পরে */
      if (tries < 40) setTimeout(function () { scrollToItem(num, tries + 1); }, 60);
      return;
    }
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    el.classList.add("hit");
    setTimeout(function () { el.classList.remove("hit"); }, 1800);
  }

  /* ---------------------------------------------------------- *
   * bookmarks
   * ---------------------------------------------------------- */
  function toggleBookmark(btn) {
    var ref = btn.dataset.bm;
    var at = bookmarks.indexOf(ref);
    if (at === -1) bookmarks.push(ref); else bookmarks.splice(at, 1);
    store(LS.bm, bookmarks);
    btn.classList.toggle("on", at === -1);
    var item = btn.closest(".h-item");
    if (item) item.classList.toggle("bm", at === -1);
    if (bmEl && !bmEl.hidden) renderBookmarks();
  }

  function renderBookmarks() {
    if (!bmEl) return;
    if (!bookmarks.length) {
      bmEl.innerHTML = '<div class="h-empty">এখনো কোনো হাদিস বুকমার্ক করা হয়নি। ' +
        'যে হাদিস ভালো লাগবে তার পাশের বুকমার্ক আইকনে চাপুন।</div>';
      return;
    }
    bmEl.innerHTML = bookmarks.map(function (ref) {
      var parts = ref.split(":");
      return '<button class="h-result" type="button" data-goto="' + esc(ref) + '">' +
        '<span class="rn">' + esc(bookName(parts[0])) + ' ' + bn(parts[1]) + '</span>' +
        '<span class="rt">হাদিস ' + bn(parts[1]) + '</span></button>';
    }).join("");
    bmEl.querySelectorAll("[data-goto]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var p = btn.dataset.goto.split(":");
        if (p[0] !== bookSlug) { bookSlug = p[0]; renderBooks(); }
        loadChapter(+p[1], +p[2] || null);
      });
    });
  }

  /* ---------------------------------------------------------- *
   * copy
   * ---------------------------------------------------------- */
  function copyItem(btn) {
    var item = btn.closest(".h-item");
    if (!item) return;
    var ar = item.querySelector(".h-ar"), bnEl = item.querySelector(".h-bn");
    var parts = [];
    if (bnEl) parts.push(bnEl.textContent.trim());
    if (ar) parts.push(ar.textContent.trim());
    var gr = item.querySelector(".h-grade");
    if (gr) parts.push("মান: " + gr.textContent.trim());
    var tah = item.querySelector(".h-tah");
    if (tah) parts.push(tah.textContent.trim());
    var text = parts.join("\n\n");
    var done = function () {
      var old = btn.title;
      btn.title = "কপি হয়েছে";
      setTimeout(function () { btn.title = old; }, 1400);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () {});
    } else {
      var ta = document.createElement("textarea");
      ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); done(); } catch (e) {}
      document.body.removeChild(ta);
    }
  }

  /* ---------------------------------------------------------- *
   * display settings
   * ---------------------------------------------------------- */
  function applySettings() {
    var root = document.documentElement;
    root.style.setProperty("--h-ar-size", settings.arSize + "px");
    root.style.setProperty("--h-bn-size", settings.bnSize + "px");
    document.querySelectorAll(".h-ar").forEach(function (el) {
      el.classList.toggle("h-hidden", !settings.arOn);
    });
    document.querySelectorAll(".h-bn").forEach(function (el) {
      el.classList.toggle("h-hidden", !settings.bnOn);
    });
    var tAr = document.getElementById("h-t-ar");
    var tBn = document.getElementById("h-t-bn");
    if (tAr) { tAr.classList.toggle("on", settings.arOn); tAr.setAttribute("aria-pressed", settings.arOn); }
    if (tBn) { tBn.classList.toggle("on", settings.bnOn); tBn.setAttribute("aria-pressed", settings.bnOn); }
    var sAr = document.getElementById("h-size-ar");
    var sBn = document.getElementById("h-size-bn");
    if (sAr) sAr.value = settings.arSize;
    if (sBn) sBn.value = settings.bnSize;
    store(LS.set, settings);
  }

  function bindControls() {
    var tAr = document.getElementById("h-t-ar");
    var tBn = document.getElementById("h-t-bn");
    if (tAr) tAr.addEventListener("click", function () { settings.arOn = !settings.arOn; applySettings(); });
    if (tBn) tBn.addEventListener("click", function () { settings.bnOn = !settings.bnOn; applySettings(); });

    [["h-size-ar", "arSize"], ["h-size-bn", "bnSize"]].forEach(function (cfg) {
      var el = document.getElementById(cfg[0]);
      if (!el) return;
      el.addEventListener("input", function () { settings[cfg[1]] = +el.value; applySettings(); });
    });
  }

  /* ---------------------------------------------------------- *
   * search across every book
   * ---------------------------------------------------------- */
  var searchBox, onlyThisBook = false, gradeFilter = "";

  /* গ্রেডের ছাঁকনি: শুধু দুর্বল বা শুধু জাল হাদিস দেখতে */
  function bindGradeFilter() {
    var sel = document.getElementById("h-grade");
    if (!sel) return;
    sel.addEventListener("change", function () {
      gradeFilter = sel.value;
      mainEl.querySelectorAll(".h-item").forEach(function (it) {
        var g = it.querySelector(".h-grade");
        var cls = g ? g.className.replace("h-grade ", "") : "";
        var show = !gradeFilter || cls === gradeFilter;
        it.hidden = !show;
      });
    });
  }

  function runSearch(q) {
    if (!resultsEl) return;
    var term = fromBengali(q).trim();
    var bengali = /[\u0980-\u09FF]/.test(q);

    if (!term) { resultsEl.hidden = true; resultsEl.innerHTML = ""; return; }

    /* a reference such as "বুখারী ১:৫" or "বুখারী ১" jumps straight there */
    var ref = term.match(/^\s*(বুখারী|মুসলিম|নাসাঈ|আবু\s*দাউদ|তিরমিজি|ইবনে\s*মাজাহ|মিশকাত(?:ুল\s*মাসাবি[হী])?|মিশকাত শরীফ)?\s*(\d{1,3})(?:\s*[:\s]\s*(\d{1,4}))?\s*$/);
    if (ref) {
      var slug = guessBook(ref[1]);
      var ch = +ref[2], had = ref[3] ? +ref[3] : null;
      if (slug && ch >= 1) {
        if (slug !== bookSlug) { bookSlug = slug; renderBooks(); }
        var c = chapter(ch);
        if (c) {
          loadChapter(ch, had && had >= c.from && had <= c.to ? had : null);
          resultsEl.hidden = true;
          return;
        }
      }
    }

    resultsEl.hidden = false;
    resultsEl.innerHTML = '<div class="h-empty">খোঁজা হচ্ছে… (প্রথম বারে ' +
      bnNum(index.total) + ' হাদিস সাজানো হয়, একবারই লাগে)</div>';

    whenIndexed().then(function (all) {
      var needle = q.trim().toLowerCase();
      var hits = [];
      for (var i = 0; i < all.length; i++) {
        var h = all[i];
        if (onlyThisBook && h.b !== bookSlug) continue;
        if ((h.e || "").toLowerCase().indexOf(needle) !== -1 ||
            (h.a || "").indexOf(q.trim()) !== -1 ||
            (h.g || "").indexOf(q.trim()) !== -1) hits.push(h);
        if (hits.length >= 60) break;
      }
      if (!hits.length) {
        resultsEl.innerHTML = '<div class="h-empty">এই শব্দে কোনো হাদিস পাওয়া যায়নি। ' +
          'অন্য শব্দ দিয়ে চেষ্টা করুন, অথবা “বুখারী ১:৫” এভাবে রেফারেন্স লিখুন।</div>';
        return;
      }
      if (q !== searchBox.value) return;   /* এর মধ্যে আরও টাইপ করা হয়েছে */
      resultsEl.innerHTML = hits.map(function (h) {
        return '<button class="h-result" type="button" data-goto="' + esc(h.b + ":" + h.c + ":" + h.i) + '">' +
          '<span class="rn">' + esc(bookName(h.b)) + ' ' + bn(h.i) +
            (h.g ? '<br><small style="font-weight:400;opacity:.75">' + esc(h.g) + '</small>' : '') + '</span>' +
          '<span class="rt">' + hl((h.e || "").slice(0, 220), q) + '</span></button>';
      }).join("");
      resultsEl.querySelectorAll("[data-goto]").forEach(function (btn) {
        btn.addEventListener("click", function () {
          var p = btn.dataset.goto.split(":");
          if (p[0] !== bookSlug) { bookSlug = p[0]; renderBooks(); }
          loadChapter(+p[1], +p[2]);
        });
      });
    });
  }

  function hl(text, q) {
    var t = esc(text);
    try {
      var safe = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return t.replace(new RegExp("(" + safe + ")", "gi"), "<mark>$1</mark>");
    } catch (e) { return t; }
  }

  function guessBook(name) {
    if (!name) return bookSlug;
    var t = name.replace(/\s+/g, " ").trim();
    if (/বুখারী/.test(t)) return "bukhari";
    if (/মুসলিম/.test(t)) return "muslim";
    if (/নাসাঈ/.test(t)) return "nasai";
    if (/আবু\s*দাউদ/.test(t)) return "abu-dawud";
    if (/তিরমিজি/.test(t)) return "tirmidhi";
    if (/ইবনে\s*মাজাহ/.test(t)) return "ibn-majah";
    if (/মিশকাত/.test(t)) return "mishkat";
    return bookSlug;
  }

  /* the search index is built once, lazily, from the six book files */
  var indexPromise = null;
  function whenIndexed() {
    if (indexPromise) return indexPromise;
    indexPromise = new Promise(function (resolve) {
      var out = [];
      var books = index.books;
      var i = 0;
      (function next() {
        if (i >= books.length) { searchHits = out; resolve(out); return; }
        var b = books[i++];
        var remaining = b.chapters.length;
        if (!remaining) { next(); return; }
        b.chapters.forEach(function (c) {
          fetch(DATA + b.slug + "/" + c.id + ".json")
            .then(function (r) { return r.json(); })
            .then(function (d) {
              d.verses.forEach(function (v) {
                out.push({ b: b.slug, c: c.id, i: v.i, a: v.a, e: v.b, n: v.n, g: v.g });
              });
            })
            .catch(function () {})
            .then(function () {
              if (--remaining === 0) next();
            });
        });
      })();
    });
    return indexPromise;
  }

  /* ---------------------------------------------------------- *
   * keyboard + history
   * ---------------------------------------------------------- */
  function bindKeys() {
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeDrawer();
      var t = e.target;
      if (t && t.matches && t.matches("input,textarea,select,[contenteditable]")) return;
      var b = book();
      if (!b) return;
      var i = b.chapters.findIndex(function (x) { return x.id === chapterId; });
      if (e.key === "ArrowRight" && i > -1 && i < b.chapters.length - 1) loadChapter(b.chapters[i + 1].id);
      if (e.key === "ArrowLeft" && i > 0) loadChapter(b.chapters[i - 1].id);
    });
  }

  function parseHash() {
    var h = decodeURIComponent(location.hash.replace(/^#/, ""));
    if (!h) return null;
    var p = h.split(":");
    if (p.length >= 2 && index.books.some(function (b) { return b.slug === p[0]; })) {
      return { book: p[0], ch: +fromBengali(p[1]), had: p[2] ? +fromBengali(p[2]) : null };
    }
    return null;
  }

  function routeFromHash(replace) {
    var r = parseHash();
    if (!r) {
      var last = store(LS.last);
      if (last && last.b) { bookSlug = last.b; }
      var b = book();
      loadChapter((r && r.ch) || (b && b.chapters[0].id) || 1, null, replace);
      return;
    }
    if (r.book !== bookSlug) { bookSlug = r.book; renderBooks(); }
    loadChapter(r.ch || 1, r.had, replace);
  }

  /* ---------------------------------------------------------- *
   * boot
   * ---------------------------------------------------------- */
  function init() {
    mainEl = document.getElementById("h-main");
    listEl = document.getElementById("h-chapter-list");
    totalEl = document.getElementById("h-total");
    resultsEl = document.getElementById("h-results");
    bmEl = document.getElementById("h-bm-list");
    asideEl = document.getElementById("h-aside");
    backdropEl = document.getElementById("h-backdrop");
    drawerBtn = document.getElementById("h-drawer-btn");

    syncDrawerMode();
    window.addEventListener("resize", syncDrawerMode);
    if (drawerBtn) {
      drawerBtn.addEventListener("click", function () {
        if (asideEl.classList.contains("open")) closeDrawer(); else openDrawer();
      });
    }
    if (backdropEl) backdropEl.addEventListener("click", closeDrawer);
    buildIcons();
    bindControls();
    bindKeys();

    fetch(DATA + "index.json")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        index = d;
        renderBooks();
        renderChapters();
        bindFilter();
        routeFromHash(true);
        wireSearch();
      })
      .catch(function () {
        if (mainEl) {
          mainEl.innerHTML = '<div class="h-empty">হাদিসের তালিকা লোড করা যায়নি। ' +
            'ইন্টারনেট সংযোগ দেখে আবার চেষ্টা করুন।</div>';
        }
      });
  }

  function wireSearch() {
    searchBox = document.getElementById("h-search");
    var onlyBtn = document.getElementById("h-search-all");
    if (onlyBtn) {
      onlyBtn.addEventListener("click", function () {
        onlyThisBook = !onlyThisBook;
        onlyBtn.classList.toggle("on", onlyThisBook);
        onlyBtn.setAttribute("aria-pressed", onlyThisBook);
        onlyBtn.textContent = onlyThisBook ? "শুধু এই কিতাব" : "সব কিতাব";
        if (searchBox && searchBox.value.trim()) runSearch(searchBox.value);
      });
    }
    if (!searchBox) return;
    var timer = null;
    searchBox.addEventListener("input", function () {
      clearTimeout(timer);
      var v = searchBox.value;
      timer = setTimeout(function () { runSearch(v); }, 260);
    });
    searchBox.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { searchBox.value = ""; runSearch(""); searchBox.blur(); }
    });
  }

  function buildIcons() {
    var bmBtn = document.getElementById("h-bm-btn");
    var panel = document.getElementById("h-bm-panel");
    if (bmBtn && panel && bmEl) {
      bmBtn.addEventListener("click", function () {
        var open = panel.hidden;
        panel.hidden = !open;
        bmBtn.setAttribute("aria-expanded", open);
        bmBtn.classList.toggle("on", open);
        if (open) renderBookmarks();
      });
    }
    var printBtn = document.getElementById("h-print");
    if (printBtn) printBtn.addEventListener("click", function () { window.print(); });
  }

  window.addEventListener("hashchange", function () { if (index) routeFromHash(false); });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
