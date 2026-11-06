/* ============================================================
   grantho.js — হিন্দু ধর্মগ্রন্থের পড়ার ইঞ্জিন
   ------------------------------------------------------------
   একবারে একটা অধ্যায় লোড হয়: assets/grantho/data/<granth>/ch<N>.json
   প্রতিটি শ্লোকে সংস্কৃত (দেবনাগরী) + বাংলা অনুবাদ + বক্তা।

   নীতি: পাঠ কখনো বদলানো হয় না। শুধু দেখানো/লুকানো আর ক্রম।
   একই ইঞ্জিন পরে বেদ, উপনিষদ, পুরাণের পাতাতেও চলবে — শুধু
   ডেটা ফোল্ডার আলাদা হবে (data-granth অ্যাট্রিবিউট)।
   ============================================================ */
(function () {
  "use strict";

  var root = document.getElementById("grantho-reader");
  if (!root) return;

  var SLUG = root.dataset.granth || "gita";
  /* data-base না থাকলে পেজের নিজের ঠিকানা থেকে পথ বের করি।
     এখানে পেজ যেমনই থাকুক, ঠিক সংখ্যক ../ বসিয়ে সাইটের মূল ফোল্ডারে
     পৌঁছাব। রেপো-রুট /ead/ নিজেও একটা সাব-পাথ, তাই শেষ সেগমেন্টটা
     ('ead') বাদ দিই — বাকি প্রতিটি ফোল্ডারের জন্য একটা ../।
       /ead/grantho/hindu/gita.html → ["ead","grantho","hindu"] → ২টি ../
       /ead/grantho/islam.html      → ["ead","grantho"]          → ১টি ../
       /ead/hadith.html             → ["ead"]                     → ০টি ../ */
  function autoBase() {
    var dir = location.pathname.replace(/[^\/]*$/, "");
    var segs = dir.split("/").filter(Boolean).slice(1);
    return "../".repeat(segs.length) + "assets/grantho/data/" + SLUG + "/";
  }

  var BASE = root.dataset.base || autoBase();
  var KEY = "grantho." + SLUG + ".v1";

  var listEl   = document.getElementById("g-chapter-list");
  var bodyEl   = document.getElementById("g-body");
  var titleEl  = document.getElementById("g-ch-title");
  var metaEl   = document.getElementById("g-ch-meta");
  var totalEl  = document.getElementById("g-total");
  var searchEl = document.getElementById("g-search");
  var onlyBnEl = document.getElementById("g-only-bn");

  var index = null, chapter = null, chapterId = null;
  var gridEl   = document.getElementById("g-chapter-grid");
  var prevBtn  = document.getElementById("g-prev");
  var nextBtn  = document.getElementById("g-next");
  /* grouped = গ্রন্থে পুস্তক>অধ্যায়>পদ স্তর আছে কি না (বাইবেল) */
  var grouped = false, bookId = 0, testFilter = "all";
  var bnNoteEl = document.getElementById("g-bn-note");
  /* গীতা/পুরাণে «শ্লোক», বেদ-উপনিষদে «মন্ত্র», বাইবেলে «পদ» — index.json-এর
     verseWord থেকে। একইভাবে গ্রুপ-শব্দ (ঋগ্বেদে «সূক্ত», বাইবেলে «অধ্যায়») ও
     অধ্যায়-শব্দ (বাইবেলে «পুস্তক») ডেটা থেকেই নেওয়া হয়, হার্ডকোড নয়। */
  var VW = "শ্লোক", GW = "সূক্ত", CW = "অধ্যায়";
  var state = { bn: true, sk: true, q: "", onlyBn: false, lang: "both" };
  /* ইংরেজি অনুবাদ (বাইবেল): অধ্যায়ভিত্তিক আলাদা ফাইল en/chN.json — বাংলা পাঠের
     ফাইলে হাত দেওয়া হয় না, তাই দুই উৎস স্বাধীনভাবে নামে ও হালনাগাদ হয়। */
  var chapterEn = null;
  /* ইংরেজি ডেটার আকার যাচাই: verses অবশ্যই অবজেক্ট (n→পাঠ); ভুল ফাইল লোড
     হলে (যেমন পদ-তালিকার অ্যারে) যেন প্রতি পদে আবর্জনা না বসে। */
  function enMap(e) {
    return (e && e.verses && typeof e.verses === "object" && !Array.isArray(e.verses)) ? e.verses : {};
  }
  var cache = {};

  /* ---------- সহায়ক ---------- */
  var BN_DIGITS = "০১২৩৪৫৬৭৮৯";
  function bn(n) {
    return String(n).replace(/[0-9]/g, function (d) { return BN_DIGITS[+d]; });
  }
  function bnNum(n) {
    return bn(String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",")).replace(/,/g, ",");
  }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function saved() {
    try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; }
  }
  function save(patch) {
    try {
      var s = saved();
      for (var k in patch) s[k] = patch[k];
      localStorage.setItem(KEY, JSON.stringify(s));
    } catch (e) {}
  }

  function loadJSON(url) {
    if (cache[url]) return Promise.resolve(cache[url]);
    return fetch(url, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(url + " → " + r.status);
      return r.json();
    }).then(function (d) { cache[url] = d; return d; });
  }

  /* ---------- দৃষ্টি-স্তর (drill-down) ----------
     তিন স্তর: পুস্তক-তালিকা → অধ্যায়-গ্রিড → পদ।
     বাইবেলের মতো গ্রুপযুক্ত গ্রন্থে (index-এ testament + suktas) বই খুললে
     আগে শুধু অধ্যায়গুলো দেখাই, অধ্যায়ে ক্লিক করলে নিচে তার পদ।
     অন্য গ্রন্থে (গীতা/বেদ) আগের মতোই: খণ্ড-তালিকা, ক্লিকেই পাঠ। */
  var scope = "book";        // book | chapter
  var FILTERS = [["all", "সব"], ["old", "পুরাতন নিয়ম"], ["new", "নতুন নিয়ম"]];

  function bookTestament(c) {
    /* ডেটায় testament থাকলে সেটাই সত্য; না থাকলে বাইবেল-ক্রমের ৩৯ পুস্তক
       পর্যন্ত পুরাতন — এটাই প্রচলিত ভাগ (অনুমান নয়, ক্যানন)। */
    if (c.testament === "old" || c.testament === "new") return c.testament;
    return c.id <= 39 ? "old" : "new";
  }

  function chapterIds(c) {
    /* অধ্যায়-নম্বরগুলো ডেটার ভেতর থেকেই: grid.prefix (ফাঁকা অধ্যায় থাকলে
       উৎস-ক্রম ধরে নাম) নয়তো ১..suktaCount। শিরোনামে ডেটার suktaCount। */
    var n = c.grid && c.grid.count ? +c.grid.count : (+c.suktaCount || 0);
    var out = [];
    for (var i = 1; i <= n; i++) out.push(i);
    return out;
  }

  /* একক-স্তরের তালিকা (গীতা/বেদ): নম্বর + নাম + পদ-গণনা — আগের আচরণ অটুট */
  function renderChapters() {
    if (!listEl || !index) return;
    listEl.innerHTML = index.chapters.map(function (c) {
      var on = c.id === chapterId;
      var meta = bn(c.count) + " " + VW;
      if (c.suktaCount) meta += " · " + bn(c.suktaCount) + " " + GW;
      else if (c.from && c.to && c.count > 1) meta += " · " + bn(c.from) + " – " + bn(c.to) + " নং";
      if (c.prefaceCount) meta += " · অনুক্রমণিকা";
      return '<button class="g-ch' + (on ? " on" : "") + '" type="button" data-ch="' + c.id + '"' +
        (on ? ' aria-current="true"' : "") + '>' +
        '<span class="num">' + bn(c.id) + '</span>' +
        '<span class="txt"><span class="nm">' + esc(c.bn) + '</span>' +
        '<span class="meta">' + meta + '</span></span></button>';
    }).join("");
    listEl.querySelectorAll("[data-ch]").forEach(function (b) {
      b.addEventListener("click", function () { openChapter(+b.dataset.ch); });
    });
    if (totalEl) totalEl.textContent = bnNum(index.total) + " " + VW + " · " + bn(index.chapters.length) + " " + CW;
  }

  function renderBooks() {
    var box = document.getElementById("g-book-list");
    if (!box || !index) return;
    box.innerHTML = index.chapters.map(function (c) {
      var on = c.id === bookId;
      var meta = bn(c.count) + " " + VW;
      if (c.suktaCount) meta += " · " + bn(c.suktaCount) + " " + GW;
      if (c.prefaceCount) meta += " · অনুক্রমণিকা";
      var tag = c._en ? ' <span class="g-bk-en">' + esc(c._en) + "</span>" : "";
      return '<button class="g-ch g-bk' + (on ? " on" : "") + '" type="button" data-ch="' + c.id + '"' +
        (on ? ' aria-current="true"' : "") + '>' +
        '<span class="num">' + bn(c.num || c.id) + '</span>' +
        '<span class="txt"><span class="nm">' + esc(c.bn) + tag + '</span>' +
        '<span class="meta">' + meta + "</span></span></button>";
    }).join("");
    box.querySelectorAll("[data-ch]").forEach(function (b) {
      b.addEventListener("click", function () {
        var id = +b.dataset.ch;
        /* গ্রুপযুক্ত গ্রন্থে পুস্তক ≠ অধ্যায়: বইয়ে ক্লিক = অধ্যায়-তালিকা খোলা।
           একক-স্তরের গ্রন্থে (গীতা/বেদ) আগের মতোই সরাসরি পাঠ। */
        if (grouped) showBookView(id);
        else openChapter(id);
      });
    });
  }

  /* পুরাতন/নতুন নিয়ম — পুস্তক-তালিকার উপরে ছাঁকনি ও গ্রুপ-শিরোনাম */
  function renderTestaments() {
    var tb = document.getElementById("g-testament");
    var box = document.getElementById("g-book-list");
    if (!tb || !box || !index) return;
    var has = index.chapters.some(function (c) { return c.testament === "old" || c.testament === "new"; });
    if (!has) { tb.hidden = true; box.querySelectorAll(".g-tgroup").forEach(function (e) { e.remove(); }); return; }
    tb.hidden = false;
    if (!tb.children.length) {
      tb.innerHTML = FILTERS.map(function (f) {
        return '<button type="button" class="g-tbtn" data-t="' + f[0] + '">' + f[1] + "</button>";
      }).join("");
      tb.querySelectorAll("[data-t]").forEach(function (b) {
        b.addEventListener("click", function () { testFilter = b.dataset.t; syncTestaments(); });
      });
    }
    syncTestaments();
  }

  function syncTestaments() {
    var tb = document.getElementById("g-testament"), box = document.getElementById("g-book-list");
    if (!tb || !box || !index) return;
    tb.querySelectorAll("[data-t]").forEach(function (b) {
      var on = b.dataset.t === testFilter;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    /* গ্রুপ-শিরোনাম: তালিকায় বইগুলোর ক্রমেই বসাই, তাই ছাঁকনি বদলালেও ক্রম অটুট */
    var groups = { old: [], new: [] };
    box.querySelectorAll(".g-ch").forEach(function (b) { b.hidden = false; });
    box.querySelectorAll(".g-tgroup").forEach(function (e) { e.remove(); });
    if (testFilter === "all") {
      index.chapters.forEach(function (c) {
        var t = bookTestament(c);
        (groups[t] = groups[t] || []).push(c.id);
      });
      ["old", "new"].forEach(function (t) {
        if (!groups[t] || !groups[t].length) return;
        var first = box.querySelector('[data-ch="' + groups[t][0] + '"]');
        if (!first) return;
        var h = document.createElement("div");
        h.className = "g-tgroup";
        var lbl = t === "old" ? "পুরাতন নিয়ম" : "নতুন নিয়ম";
        h.innerHTML = '<span>' + lbl + '</span><i>' + bn(groups[t].length) + " " + CW + "</i>";
        box.insertBefore(h, first);
      });
    } else {
      var n = 0;
      index.chapters.forEach(function (c) {
        var b = box.querySelector('[data-ch="' + c.id + '"]');
        var keep = bookTestament(c) === testFilter;
        if (b) b.hidden = !keep;
        if (keep) n++;
      });
      if (!n && totalEl) totalEl.textContent = "কিছু নেই";
    }
  }

  /* ---------- অধ্যায়-গ্রিড ---------- */
  function renderChapterGrid() {
    if (!gridEl || !index) return;
    var bk = bookById(bookId);
    if (!bk) { gridEl.innerHTML = ""; return; }
    var ids = chapterIds(bk);
    var prefix = (bk.grid && bk.grid.prefix) || "";
    gridEl.innerHTML = ids.map(function (i) {
      var on = scope === "chapter" && i === chapterId;
      var have = hasChapter(bk, i);
      /* ফাঁকা ঘরগুলোও দেখাই (কিন্তু আলাদা রঙে) — তালিকা থেকে সংখ্যা হারালে
         পাঠক ভাবতেন অধ্যায়টাই নেই; এখন স্পষ্ট বোঝা যায় «পাঠ নেই»। */
      return '<button class="g-cg' + (on ? " on" : "") + (have ? "" : " off") +
        '" type="button" data-c="' + i + '"' + (on ? ' aria-current="true"' : "") +
        (have ? "" : ' aria-label="' + bn(i) + ' — পাঠ নেই" title="উৎসে পাওয়া যায়নি"') + ">" +
        "<span>" + prefix + bn(i) + "</span></button>";
    }).join("");
    gridEl.querySelectorAll("[data-c]").forEach(function (b) {
      b.addEventListener("click", function () { openChapter(+b.dataset.c); });
    });
  }

  /* শিরোনাম/মেটা: গ্রুপযুক্ত গ্রন্থে «পুস্তক · অধ্যায় N» — খোঁজা শেষে
     আবার এটাই ফিরে আসে (আগে «খোঁজা: …» আটকে থাকত)। */
  function syncHead() {
    if (!grouped) return;
    if (state.q && state.q.length >= 2) return;
    var bk = bkOf();
    if (!bk.bn) return;
    var miss = (bk.grid && bk.grid.missing) || bk.missing || [];
    if (scope === "chapter" && chapter && chapter.id === bookId) {
      if (titleEl) titleEl.textContent = bk.bn + " · " + GW + " " + bn(chapterId);
      var gm = (chapter.suktas || []).filter(function (x) { return x.id === chapterId; })[0] || null;
      /* উৎসে না-থাকা অধ্যায়ে «০ পদ» লেখা বিভ্রান্তিকর — সত্য কথাটাই লিখি */
      if (metaEl) metaEl.textContent = gm ? bn(gm.verse || 0) + " " + VW : "উৎসে পাওয়া যায়নি";
    } else {
      if (titleEl) titleEl.textContent = bk.bn;
      var mtxt = bn(bk.count || 0) + " " + VW + " · " + bn(bk.suktaCount || 0) + " " + GW;
      if (miss.length) mtxt += " · " + bn(miss.length) + "টি উৎসে নেই";
      if (metaEl) metaEl.textContent = mtxt;
    }
  }

  function bkOf() {
    return bookById(bookId) || {};
  }

  /* অধ্যায়টি ডেটায় সত্যিই আছে কি না — গ্রিডের ফাঁকা ঘর ও নেভিগেশনের জন্য।
     missing-তালিকা থাকলে সেটাই; না থাকলে ফাঁকা ঘর নিজেই প্রমাণ। */
  function hasChapter(bk, id) {
    if (!bk) return false;
    var miss = (bk.grid && bk.grid.missing) || bk.missing || [];
    for (var i = 0; i < miss.length; i++) if (+miss[i] === +id) return false;
    return true;
  }

  function bookById(id) {
    if (!index) return null;
    for (var i = 0; i < index.chapters.length; i++) if (index.chapters[i].id === id) return index.chapters[i];
    return null;
  }

  /* ইংরেজি কভারেজের নোট — নীরবে উধাও না হয়ে সংখ্যাটা বলা হয়:
     বইয়ের কত অধ্যায়ে ইংরেজি আছে তার হিসাব ডেটার `aligned` থেকে। */
  function enNote() {
    var el = document.getElementById("g-en-note");
    if (!el) return;
    var bk = bkOf();
    var al = bk.aligned == null ? null : +bk.aligned;
    var sk = bk.skipped == null ? null : +bk.skipped;
    if (!grouped || al == null) { el.hidden = true; return; }
    var txt;
    if (al === 0) txt = "এই পুস্তকে ইংরেজি পাঠ এখনো যোগ করা যায়নি — কেবল বাংলা দেখানো হচ্ছে।";
    else if (sk) txt = "এই পুস্তকের " + bn(al) + "টি অধ্যায়ে ইংরেজি পাঠ মিলেছে; " + bn(sk) +
      "টিতে মেলেনি (দুই সংস্করণের পদ-বিন্যাস আলাদা) — সেখানে কেবল বাংলা।";
    else { el.hidden = true; el.textContent = ""; return; }   // কিছু বলার নেই → দেখাই না
    el.hidden = false;
    el.innerHTML = '<b>ইংরেজি পাঠ।</b> ' + esc(txt);
  }

  function refreshCrumb() {
    var cr = document.getElementById("g-crumb2");
    if (!cr) return;
    var bk = bookById(bookId);
    if (!bk || !grouped || scope !== "chapter") { cr.hidden = true; return; }
    var lbl = GW + " " + bn(chapterId);
    cr.hidden = false;
    cr.innerHTML = '<button type="button" class="g-crumb-b" data-go="books">' + esc(bk.bn) +
      "</button><span>›</span><b>" + lbl + "</b>";
    var b0 = cr.querySelector("[data-go]");
    if (b0) b0.addEventListener("click", function () { showBookView(bookId); });
  }

  /* বইয়ের দৃশ্য: উপরে অধ্যায়-গ্রিড, ক্লিক না হওয়া পর্যন্ত নিচে পাঠ নেই */
  function showBookView(id) {
    bookId = id;
    scope = "book"; chapter = null; chapterEn = null; chapterId = 0;
    paintToken++;
    if (bodyEl) bodyEl.innerHTML = '<p class="g-empty g-pick">উপরের তালিকা থেকে একটি অধ্যায় বেছে নিন — পদগুলো নিচে দেখা যাবে।</p>';
    syncHead();
    if (bnNoteEl) bnNoteEl.hidden = true;
    if (langBox) langBox.hidden = true;
    if (searchEl) { var note = document.getElementById("g-hits"); if (note) note.textContent = ""; }
    renderChapterGrid();
    refreshCrumb();
    enNote();
    setPrevNext();
    save({ book: id });
  }

  /* বাটনের লেখাতেই গন্তব্য: পাঠক অন্ধভাবে চাপেন না (আর সূচির ফাঁকা পুস্তকও
     বাদ পড়ে, কারণ ক্রম index.chapters থেকেই আসে)। */
  function setPrevNext() {
    if (!index) return;
    var bs = index.chapters, i = -1;
    for (var k = 0; k < bs.length; k++) if (bs[k].id === bookId) i = k;
    if (!grouped) {
      if (prevBtn) { prevBtn.disabled = !(i > 0); prevBtn.textContent = "‹ আগের"; }
      if (nextBtn) { nextBtn.disabled = !(i >= 0 && i < bs.length - 1); nextBtn.textContent = "পরের ›"; }
      return;
    }
    var bk = i >= 0 ? bs[i] : null;
    var nch = bk ? chapterIds(bk).length : 0;
    var atCh = scope === "chapter";
    var nxt = chapterId + 1;
    while (bk && nxt <= nch && !hasChapter(bk, nxt)) nxt++;
    var prv = chapterId - 1;
    while (bk && prv >= 1 && !hasChapter(bk, prv)) prv--;
    var pTxt = "‹ আগের", nTxt = "পরের ›";
    if (atCh && prv >= 1) pTxt = "‹ " + GW + " " + bn(prv);
    else if (i > 0) pTxt = "‹ " + esc(bs[i - 1].bn);
    if (atCh && nxt <= nch) nTxt = GW + " " + bn(nxt) + " ›";
    else if (i >= 0 && i < bs.length - 1) nTxt = esc(bs[i + 1].bn) + " ›";
    var canPrev = (atCh && prv >= 1) || i > 0;
    var canNext = (atCh && nxt <= nch) || (i >= 0 && i < bs.length - 1);
    if (prevBtn) { prevBtn.disabled = !canPrev; prevBtn.textContent = canPrev ? pTxt : "‹ আগের"; }
    if (nextBtn) { nextBtn.disabled = !canNext; nextBtn.textContent = canNext ? nTxt : "পরের ›"; }
  }

  /* ---------- শ্লোক ---------- */
  /* ---------- শ্লোক ---------- */
  /* সূক্ত/অংশ: chapter.suktas থাকলে «সূক্ত ১২» ধরে সাজাই, আর cuts-এ যে
     মন্ত্রের ভেতরে কয়েকটি শ্লোক জোড়া ছিল সেগুলো আলাদা পঙক্তি-কার্ড হয়। */
  var cuts = {};       // মন্ত্র-নং → [অংশ…]
  var inSukta = {};    // মন্ত্র-নং → সূক্ত-নং

  function useLayout() {
    cuts = {}; inSukta = {};
    if (!chapter || !chapter.suktas) return false;
    chapter.suktas.forEach(function (s) {
      for (var n = s.from; n <= s.to; n++) inSukta[n] = s.id;
      if (s.cuts) for (var k in s.cuts) cuts[k] = s.cuts[k];
    });
    return true;
  }

  function verseHTML(v) {
    var q = state.q ? state.q.toLowerCase() : "";
    var en = enMap(chapterEn)[String(v.n)] || "";
    var hit = q && ((v.sk || "").toLowerCase().indexOf(q) > -1 ||
                    (v.bn || "").toLowerCase().indexOf(q) > -1 ||
                    en.toLowerCase().indexOf(q) > -1);
    var la = (typeof v.n === "number") ? v.n : 0;
    var sk = (v.sk || "").replace(/\n+/g, "<br>");
    var parts = state.bn ? (cuts[la] || null) : null;
    /* বাইবেলে পদ-নম্বর প্রতি অধ্যায়ে ১ থেকে শুরু, তাই প্রদর্শনের জন্য আলাদা
       `vn`; `n` পুস্তকের ভেতরে অনন্য ক্রম (অ্যাংকর ও গ্রুপ-সীমার জন্য)। */
    var shown = (typeof v.vn === "number") ? v.vn : v.n;
    var out = '<article class="g-v' + (hit ? " hit" : "") + '" id="v' + v.n + '">';
    out += '<div class="g-v-num" aria-hidden="true">' + bn(shown) + '</div><div class="g-v-body">';
    if (v.hd) out += '<p class="g-v-hd">' + esc(v.hd) + '</p>';
    if (v.spk && state.sk) out += '<p class="g-v-spk">' + esc(v.spk) + '</p>';
    if (state.sk && sk) out += '<p class="g-v-sk" lang="sa">' + sk + '</p>';
    if (parts) {
      out += '<div class="g-v-padas">';
      out += parts.map(function (x, i) {
        return '<p class="g-v-bn g-v-pada"><span class="g-pada-n">' +
          bn(i + 1) + '</span>' + esc(x) + '</p>';
      }).join("");
      out += '</div>';
    } else if (state.bn && v.bn && state.lang !== "en") {
      out += '<p class="g-v-bn">' + esc(v.bn).replace(/\n+/g, "</p><p class=\"g-v-bn\">") + '</p>';
    }
    /* উৎসে পদ-নম্বর ছাপা কিন্তু পাঠ নেই (ebanglalibrary-র কিছু পাতায় এমন আছে,
       যেমন আদিপুস্তক ৩৬:৭-৮) — লুকিয়ে না রেখে স্পষ্ট নোট দেখাই। */
    if (v.srcEmpty && state.lang !== "en") {
      out += '<p class="g-v-empty">এই পদ-নম্বরটি উৎসে আছে, কিন্তু উৎস-পাতায় এর পাঠ দেওয়া হয়নি।</p>';
    }
    if (en && state.lang !== "bn") {
      out += '<p class="g-v-en" lang="en">' + esc(en) + '</p>';
    }
    /* উৎস-কৃতিত্ব গ্রন্থের শুরুতে একবারই — প্রতি মন্ত্রে পুনরাবৃত্তি নয় */
    out += '</div></article>';
    return out;
  }

  /* সার্চ পুরো গ্রন্থ জুড়ে — একবার সব অধ্যায় এনে মিলিয়ে রাখি */
  var allLoaded = null, enByCh = {};
  function loadAll() {
    if (allLoaded) return Promise.resolve(allLoaded);
    return Promise.all(index.chapters.map(function (c) {
      return loadJSON(BASE + "ch" + c.id + ".json");
    })).then(function (list) {
      allLoaded = list;
      return Promise.all(list.map(function (c, i) {
        return loadJSON(BASE + "en/ch" + index.chapters[i].id + ".json")
          .then(function (e) { enByCh[index.chapters[i].id] = e; })
          .catch(function () {});
      }));
    }).then(function () { return allLoaded; });
  }

  function searchHTML(q) {
    var low = q.toLowerCase(), rows = [], total = 0;
    allLoaded.forEach(function (c) {
      var enm = enMap(enByCh[c.id]);
      var hit = c.verses.filter(function (v) {
        return (v.sk || "").toLowerCase().indexOf(low) > -1 ||
               (v.bn || "").toLowerCase().indexOf(low) > -1 ||
               ((enm[String(v.n)] || "").toLowerCase().indexOf(low) > -1);
      });
      if (!hit.length) return;
      total += hit.length;
      rows.push('<p class="g-hit-head">' + esc(c.bn) + " · " + bn(hit.length) + "টি</p>");
      rows.push(hit.map(function (v) {
        var out = '<article class="g-v hit" id="v' + c.id + '-' + v.n + '">';
        out += '<div class="g-v-num">' + bn(v.n) + '</div><div class="g-v-body">';
        if (v.spk) out += '<p class="g-v-spk">' + esc(v.spk) + '</p>';
        if (v.sk) out += '<p class="g-v-sk" lang="sa">' + esc(v.sk).replace(/\n+/g, "<br>") + '</p>';
        if (v.bn) out += '<p class="g-v-bn">' + esc(v.bn) + '</p>';
        if (enm[String(v.n)]) out += '<p class="g-v-en" lang="en">' + esc(enm[String(v.n)]) + '</p>';
        return out + "</div></article>";
      }).join(""));
    });
    return { html: rows.join("") || '<p class="g-empty">কিছু মেলেনি। অন্য শব্দে চেষ্টা করুন।</p>', total: total };
  }

  /* ---------- পুরো অধ্যায় এক পৃষ্ঠায় ----------
     «আগের/পরের পৃষ্ঠা» পেজার-ব্যবস্থাটি সরানো হয়েছে (পাঠকের দাবি): প্রতিটি
     অধ্যায়ের সম্পূর্ণ পাঠ এখন একটানা এক পৃষ্ঠায়। বড় অধ্যায়ে (ঋগ্বেদ ১০ম:
     ১,৭২৯ কার্ড) একবারে সব কার্ড বসালে ব্রাউজার ঝুলে যায়, তাই হাদিস-পাঠকের
     মতো CHUNK ব্যাচে আঁকা হয় — চোখে এক পৃষ্ঠাই, সংখ্যা ও ক্রম অটুট। */
  var CHUNK = 150;
  var paintToken = 0;

  function renderVerses() {
    if (!chapter) return;

    /* খোঁজার অবস্থায় থাকলে পুরো গ্রন্থের ফলাফল দেখাই */
    if (state.q && state.q.length >= 2) {
      if (bnNoteEl) bnNoteEl.hidden = true;
      bodyEl.innerHTML = '<p class="g-loading">খোঁজা হচ্ছে…</p>';
      loadAll().then(function () {
        var r = searchHTML(state.q);
        bodyEl.innerHTML = r.html;
        if (titleEl) titleEl.textContent = "খোঁজা: " + state.q;
        if (metaEl) metaEl.textContent = bn(r.total) + "টি " + VW;
        var note = document.getElementById("g-hits");
        if (note) note.textContent = r.total ? bn(r.total) + "টি " + VW + " পাওয়া গেছে" : "কিছু মেলেনি";
      });
      return;
    }

    var all = chapter.verses;
    if (state.onlyBn) all = all.filter(function (v) { return v.bn; });

    /* বাংলা অনুবাদের কভারেজ — প্রতি মন্ত্রে পুনরাবৃত্তি না করে একবার */
    if (bnNoteEl) {
      var withBn = chapter.verses.filter(function (v) { return v.bn; }).length;
      var total = chapter.verses.length;
      if (!state.bn) {
        bnNoteEl.hidden = true;
      } else if (withBn === 0) {
        bnNoteEl.hidden = false;
        bnNoteEl.innerHTML = "এই অধ্যায়ের <b>" + bn(total) + "টি " + VW + "</b>-এর বাংলা অনুবাদ এখনো যোগ করা যায়নি — সংস্কৃত মূল পাঠই এখানে প্রামাণ্য।";
      } else if (withBn < total) {
        bnNoteEl.hidden = false;
        bnNoteEl.innerHTML = "বাংলা অনুবাদ পাওয়া গেছে <b>" + bn(withBn) + "/" + bn(total) + "</b>টিতে।";
      } else {
        bnNoteEl.hidden = true;
      }
    }
    var hasS = useLayout();
    var parts = [], curS = null, sMeta = {};
    /* গ্রুপযুক্ত গ্রন্থ (বাইবেল): একবারে এক অধ্যায় — শিরোনাম + কেবল তার পদ।
       গ্রুপ-ভিত্তিক ক্রম ভাঙা থাকলে (উৎসে অধ্যায়-নম্বর এলোমেলো) কিছুই বাদ
       যায় না, পুরো বই-ই দেখানো হয়: পাঠ হারানো কখনোই গ্রহণযোগ্য নয়। */
    if (grouped && hasS) {
      var pick = null;
      chapter.suktas.forEach(function (x) { if (x.id === chapterId) pick = x; });
      if (!pick) {
        /* উৎসে অধ্যায়টিই নেই (যেমন যাত্রা ১১, সামসঙ্গীত ১৬+) — পুরো বই
           ঢেলে দিলে পাঠক বিভ্রান্ত হবেন (দেখাবে «অধ্যায় ১২» অথচ পদ ১..)।
           তাই সত্য কথাটাই বলা হয়, অনুমান করে কিছু বসানো হয় না। */
        var bk0 = bkOf();
        parts.push('<p class="g-empty g-miss"><b>' + GW + " " + bn(chapterId) +
          "</b> এই অধ্যায়ের পাঠ উৎসে পাওয়া যায়নি" +
          (bk0.bn ? " (" + esc(bk0.bn) + ")" : "") +
          " — অনুমান করে কিছু বসানো হয় না। পাশের অধ্যায় থেকে পড়া চালিয়ে যেতে পারেন।</p>");
      }
      if (pick) {
        all = all.filter(function (v) { return v.n >= pick.from && v.n <= pick.to; });
        parts.push('<h3 class="g-sukta-h g-chap-h" id="sukta' + pick.id + '">' +
          '<span class="g-sukta-n">' + GW + " " + bn(pick.id) + '</span>' +
          '<span class="g-sukta-m">' + VW + " " +
          bn(pick.vfrom || 1) + "–" + bn(pick.vto || pick.verse) + "</span></h3>");
        all.forEach(function (v) { parts.push(verseHTML(v)); });
      }
    }
    if (!parts.length && hasS) {
      chapter.suktas.forEach(function (x) { sMeta[x.id] = x; });
      all.forEach(function (v) {
        var sid = inSukta[v.n];
        if (sid && sid !== curS) {
          curS = sid;
          var sm = sMeta[sid] || {};
          parts.push('<h3 class="g-sukta-h" id="sukta' + sid + '">' +
            '<span class="g-sukta-n">' + GW + ' ' + bn(sid) + '</span>' +
            '<span class="g-sukta-m">' + VW + " " + bn(sm.vfrom || sm.from) + "–" +
            bn(sm.vto || sm.to) +
            (sm.shloka ? " · " + bn(sm.shloka) + " শ্লোক" : "") + '</span></h3>');
        }
        parts.push(verseHTML(v));
      });
    } else if (!parts.length) {
      parts = all.map(verseHTML);
    }
    /* উৎসের অনুক্রমণিকা/ভূমিকা-অনুবাদ মন্ত্র নয় — তাই আলাদা ব্লকে, কল্যাপ্স করা
       অবস্থায় (পাঠ অটুট থাকে, কিন্তু মন্ত্র-তালিকা পরিষ্কার থাকে)। */
    var front = "";
    if (!state.q && (chapter.preface || chapter.heading)) {
      var sumTxt = chapter.heading ? esc(chapter.heading).replace(/\n+/g, " · ") : "অনুক্রমণিকা";
      front = '<details class="g-front"><summary>' + sumTxt +
        ' <span class="g-front-tag">উৎসের ভূমিকা-অনুবাদ · মন্ত্র-গণনার বাইরে</span></summary>' +
        String(chapter.preface || "").split(/\n\n+/).filter(function (x) { return x.trim(); })
          .map(function (par) {
            return '<p class="g-front-t">' + esc(par).replace(/\n+/g, "</p><p class=\"g-front-t\">") + "</p>";
          }).join("") +
        "</details>";
    }
    if (titleEl && !grouped) titleEl.textContent = chapter.bn;
    if (metaEl && !grouped) {
      var mm = bn(chapter.count) + " " + VW;
      if (hasS) mm += " · " + bn(chapter.suktaCount || 0) + " " + GW;
      if (chapter.preface || chapter.heading) mm += " · অনুক্রমণিকা সহ";
      var enCount = Object.keys(enMap(chapterEn)).length;
      if (enCount) {
        mm += " · ইংরেজি " + bn(enCount) + " পদে";
      }
      metaEl.textContent = mm;
    }
    /* ভাষা-টগল কেবল তখনই, যখন এই অধ্যায়ে সত্যিই ইংরেজি পাঠ আছে — ফাইল
       থাকলেই দেখালে ফাঁকা টগল পেয়ে পাঠক বিভ্রান্ত হতেন। */
    var hasEn = Object.keys(enMap(chapterEn)).length > 0;
    if (langBox) langBox.hidden = !hasEn;
    if (!hasEn && state.lang === "en") { state.lang = "both"; syncLang(); }
    /* প্রথমে ভূমিকা-ব্লক, তারপর পাঠ ব্যাচে ব্যাচে — অন্য অধ্যায় খুললে পুরোনো
       ব্যাচ থেমে যায় (paintToken), তাই দুই অধ্যায়ের পাঠ কখনো মেশে না। */
    var token = ++paintToken;
    bodyEl.innerHTML = front;
    var at = 0;
    (function step() {
      if (token !== paintToken || !bodyEl.isConnected) return;
      var slice = parts.slice(at, at + CHUNK);
      bodyEl.insertAdjacentHTML("beforeend", slice.join("") ||
        (at === 0 ? '<p class="g-empty">কিছু পাওয়া যায়নি।</p>' : ""));
      at += CHUNK;
      if (at < parts.length) setTimeout(step, 0);
    })();
    if (searchEl) {
      var note = document.getElementById("g-hits");
      if (note) note.textContent = "";
    }
    syncHead();
  }

  /* ---------- অধ্যায় খোলা ---------- */
  function openChapter(id) {
    if (!id || isNaN(+id)) return;
    id = +id;
    chapterId = id;
    if (grouped) scope = "chapter";
    paintToken++;
    save({ last: id, lastbook: bookId, scope: grouped ? "chapter" : "book" });
    if (grouped) {
      renderChapterGrid();
      refreshCrumb();
    } else {
      renderChapters();
    }
    setPrevNext();
    bodyEl.innerHTML = '<p class="g-loading">লোড হচ্ছে…</p>';
    /* ফাইলের নাম: গ্রুপযুক্ত গ্রন্থে ফাইল = পুস্তক (ch<book>.json), গ্রুপ = অধ্যায়।
       একক-স্তরে ফাইলই অধ্যায় — আগের আচরণ অটুট। */
    var fileId = grouped ? bookId : id;
    Promise.all([
      loadJSON(BASE + "ch" + fileId + ".json"),
      loadJSON(BASE + "en/ch" + fileId + ".json").catch(function () { return null; })
    ]).then(function (r) {
      if (chapterId !== id || (grouped && bookId !== fileId)) return;
      chapter = r[0]; chapterEn = r[1];
      if (grouped) { syncHead(); refreshCrumb(); enNote(); }
      renderVerses();
      try { window.scrollTo({ top: (gridEl || root).offsetTop - 90, behavior: "smooth" }); } catch (e) {}
      var h = location.hash;
      if (h && /^#v?\d+$/.test(h)) {
        var el = document.getElementById("v" + h.replace("#v", "").replace("#", ""));
        if (el) el.scrollIntoView({ block: "center" });
      }
    }).catch(function () {
      bodyEl.innerHTML = '<p class="g-empty">অধ্যায়টি লোড করা গেল না। পুনরায় চেষ্টা করুন।</p>';
    });
  }

  /* ---------- ভাষা-নিয়ন্ত্রণ ----------
     টেমপ্লেটে হাত না দিয়ে রানটাইমে বসাই, যাতে সব পাতা (পুরোনো-নতুন) পায়;
     ইংরেজি ডেটা না থাকলে বাক্সটি লুকানো থাকে। */
  var langBox = null;
  function buildLangBox() {
    var anchor = document.getElementById("g-bn-btn");
    if (!anchor || !anchor.parentNode) return;
    langBox = document.createElement("div");
    langBox.className = "g-lang";
    langBox.setAttribute("role", "group");
    langBox.setAttribute("aria-label", "পাঠের ভাষা");
    [["both", "বাংলা+ইংরেজি"], ["bn", "শুধু বাংলা"], ["en", "শুধু ইংরেজি"]].forEach(function (x) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "g-lang-btn"; b.setAttribute("data-lang", x[0]);
      b.textContent = x[1];
      b.addEventListener("click", function () {
        state.lang = x[0]; save({ lang: state.lang }); syncLang(); renderVerses();
      });
      langBox.appendChild(b);
    });
    anchor.parentNode.insertBefore(langBox, anchor.nextSibling);
    langBox.hidden = true;
    syncLang();
  }
  function syncLang() {
    if (!langBox) return;
    var bs = langBox.querySelectorAll(".g-lang-btn");
    for (var i = 0; i < bs.length; i++) {
      var on = bs[i].getAttribute("data-lang") === state.lang;
      bs[i].classList.toggle("on", on);
      bs[i].setAttribute("aria-pressed", on ? "true" : "false");
    }
  }

  /* ---------- নিয়ন্ত্রণ ---------- */
  function step(d) {
    if (!index) return;
    var bs = index.chapters, pos = -1;
    for (var k = 0; k < bs.length; k++) if (bs[k].id === bookId) pos = k;
    if (pos < 0) return;
    if (grouped) {
      var bk = bs[pos], nch = chapterIds(bk).length;
      /* পরের/আগের *যে অধ্যায়ে পাঠ আছে* সেটাতেই নিই — ফাঁকা ঘরে থেমে গেলে
         পাঠক আটকে যেতেন («কিছু নেই» পেয়ে আর এগোনো যায় না)। */
      var nxt = chapterId + 1;
      while (nxt <= nch && !hasChapter(bk, nxt)) nxt++;
      if (d > 0 && nxt <= nch) return openChapter(nxt);
      var prv = chapterId - 1;
      while (prv >= 1 && !hasChapter(bk, prv)) prv--;
      if (d < 0 && prv >= 1) return openChapter(prv);
      if (d > 0 && pos < bs.length - 1) { showBookView(bs[pos + 1].id); return openChapter(1); }
      if (d < 0 && pos > 0) {
        var prevBk = bs[pos - 1], last = chapterIds(prevBk).length;
        while (last > 1 && !hasChapter(prevBk, last)) last--;
        showBookView(prevBk.id);
        return openChapter(last || 1);
      }
      return;
    }
    var t = pos + d;
    if (t < 0 || t >= bs.length) return;
    openChapter(bs[t].id);
  }

  function bind() {
    if (searchEl) {
      searchEl.addEventListener("input", function () {
        state.q = searchEl.value.trim();
        renderVerses();
      });
    }
    var skBtn = document.getElementById("g-sk-btn"), bnBtn = document.getElementById("g-bn-btn");
    if (skBtn) skBtn.addEventListener("click", function () {
      state.sk = !state.sk; skBtn.classList.toggle("on", state.sk);
      skBtn.setAttribute("aria-pressed", state.sk ? "true" : "false");
      save({ sk: state.sk }); renderVerses();
    });
    if (bnBtn) bnBtn.addEventListener("click", function () {
      state.bn = !state.bn; bnBtn.classList.toggle("on", state.bn);
      bnBtn.setAttribute("aria-pressed", state.bn ? "true" : "false");
      save({ bn: state.bn }); renderVerses();
    });
    if (onlyBnEl) onlyBnEl.addEventListener("change", function () {
      state.onlyBn = onlyBnEl.checked; save({ onlyBn: state.onlyBn }); renderVerses();
    });
    /* আগে/পরের: সূচির আসল ক্রম ধরে (ফাঁকা পুস্তক ১৪/১৬/২৪/৪৮ পার হয়ে যায়),
       আর গ্রুপযুক্ত গ্রন্থে আগে অধ্যায়, শেষ হলে পরের পুস্তক। */
    if (prevBtn) prevBtn.addEventListener("click", function () { step(-1); });
    if (nextBtn) nextBtn.addEventListener("click", function () { step(1); });
    listEl && listEl.addEventListener("keydown", function (e) {
      var b = e.target.closest && e.target.closest("[data-ch]");
      if (!b) return;
      if (e.key === "ArrowDown" || e.key === "ArrowRight") {
        var n = b.nextElementSibling;
        while (n && !n.matches("[data-ch]")) n = n.nextElementSibling;
        if (n) { n.focus(); e.preventDefault(); }
      } else if (e.key === "ArrowUp" || e.key === "ArrowLeft") {
        var p = b.previousElementSibling;
        while (p && !p.matches("[data-ch]")) p = p.previousElementSibling;
        if (p) { p.focus(); e.preventDefault(); }
      }
    });
  }

  /* ---------- শুরু ---------- */
  var st = saved();
  if (typeof st.sk === "boolean") state.sk = st.sk;
  if (typeof st.bn === "boolean") state.bn = st.bn;
  if (typeof st.onlyBn === "boolean") state.onlyBn = st.onlyBn;
  if (st.lang === "both" || st.lang === "bn" || st.lang === "en") state.lang = st.lang;
  var skBtn0 = document.getElementById("g-sk-btn"), bnBtn0 = document.getElementById("g-bn-btn");
  if (skBtn0) { skBtn0.classList.toggle("on", state.sk); skBtn0.setAttribute("aria-pressed", state.sk ? "true" : "false"); }
  if (bnBtn0) { bnBtn0.classList.toggle("on", state.bn); bnBtn0.setAttribute("aria-pressed", state.bn ? "true" : "false"); }
  if (onlyBnEl) onlyBnEl.checked = state.onlyBn;

  loadJSON(BASE + "index.json").then(function (d) {
    index = d;
    if (d.verseWord) VW = d.verseWord;
    if (d.groupWord) GW = d.groupWord;
    if (d.chword) CW = d.chword;
    /* সব খণ্ডেই বাংলা থাকলে এই ছাঁকনি অকেজো — অথচ বোতামটি থেকে গেলে মনে হয়
       কিছু বাদ পড়ছে। তাই তখন লুকিয়ে রাখি (সংস্কৃত-টগলের মতোই)। */
    if (onlyBnEl && d.total && d.withBn === d.total) {
      var lab = onlyBnEl.closest ? onlyBnEl.closest("label") : onlyBnEl.parentNode;
      if (lab) lab.hidden = true;
    }
    /* গ্রুপযুক্ত গ্রন্থ চেনা: পুস্তকে testament/সূক্ত-গণনা আছে (বাইবেল) */
    grouped = d.chapters.some(function (c) { return c.testament === "old" || c.testament === "new"; }) &&
              d.chapters.some(function (c) { return (+c.suktaCount || 0) > 0; });
    buildLangBox();
    bind();
    var m = (location.hash || "").match(/^#ch(\d+)$/) || (location.hash || "").match(/^#b(\d+)c(\d+)$/);
    var startBook = null, startCh = null;
    if (location.hash && /^#b\d+c\d+$/.test(location.hash)) {
      var mm = location.hash.match(/^#b(\d+)c(\d+)$/);
      startBook = +mm[1]; startCh = +mm[2];
    } else if (m && grouped) {
      /* পুরোনো লিংক #ch12 — গ্রুপযুক্ত গ্রন্থে ওটা পুস্তক-নম্বরই ছিল */
      startBook = +m[1];
    }
    if (grouped) {
      renderBooks();
      renderTestaments();
      if (startBook != null && bookById(startBook)) {
        if (startCh != null) {
          showBookView(startBook);
          openChapter(startCh);
        } else {
          showBookView(startBook);      // বই খুললে আগে অধ্যায়-তালিকা
        }
      } else if (st.book && bookById(st.book)) {
        /* গতবার যেখানে ছিলেন: অধ্যায়-স্তরে থাকলে সেখানেই, নইলে বইয়ের তালিকায় */
        if (st.last && st.lastbook === st.book && st.scope === "chapter") {
          showBookView(st.book);
          openChapter(st.last);
        } else {
          showBookView(st.book);
        }
      } else {
        index.chapters[0] && showBookView(index.chapters[0].id);
      }
      setPrevNext();
      return;
    }
    var start = 1;
    if (m) start = +m[1];
    else if (st.last && d.chapters.some(function (c) { return c.id === st.last; })) start = st.last;
    if (!d.chapters.some(function (c) { return c.id === start; })) start = 1;
    renderChapters();
    openChapter(start);
  }).catch(function () {
    bodyEl.innerHTML = '<p class="g-empty">সূচি লোড করা গেল না।</p>';
  });
})();
