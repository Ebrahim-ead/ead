/* ============================================================
   bible-reader.js — বাংলা বাইবেলের নিজস্ব পাঠক-ইঞ্জিন
   ------------------------------------------------------------
   কেন আলাদা: grantho.js চারটি গ্রন্থ-পাতা (গীতা, ঋগ্বেদ, যজুর্বেদ,
   বাইবেল) শেয়ার করে। বাইবেলের আচরণ আলাদা করে গোছাতে গেলে ওই
   শেয়ারড ফাইলে হাত দিতে হতো — তাতে অন্য তিনটি গ্রন্থ ভাঙার ঝুঁকি।
   তাই বাইবেলের পথটুকু এখানে স্বাধীনভাবে রাখা হলো (English Bible-এর
   মতো ধাঁচ), আর grantho.js অপরিবর্তিত।

   ডেটা: assets/grantho/data/bible/
     index.json   — পুস্তকের তালিকা, testament, perChapter
     ch<N>.json   — এক পুস্তকের পাঠ (verses[], suktas[] = অধ্যায়-সীমা)
     en/ch<N>.json — ইংরেজি পাঠ (থাকলে), পদের নম্বর ধরে মেলানো

   নীতি: পাঠ কখনো বদলানো হয় না — কেবল দেখানো/লুকানো আর ক্রম।
   ============================================================ */
(function () {
  "use strict";

  var root = document.getElementById("grantho-reader");
  if (!root) return;

  var SLUG = root.dataset.granth || "bible";

  /* data-base না থাকলে পেজের নিজের ঠিকানা থেকে পথ বের করি। */
  function autoBase() {
    var dir = location.pathname.replace(/[^\/]*$/, "");
    var segs = dir.split("/").filter(Boolean).slice(1);
    return "../".repeat(segs.length) + "assets/grantho/data/" + SLUG + "/";
  }

  var BASE = root.dataset.base || autoBase();
  var KEY = "grantho." + SLUG + ".v1";
  var BN = "০১২৩৪৫৬৭৮৯";

  function bn(n) {
    return String(n).replace(/[0-9]/g, function (d) { return BN[+d]; });
  }
  function comma(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }
  function bnNum(n) {
    return bn(comma(n));
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  var listEl = document.getElementById("g-chapter-list");
  var bodyEl = document.getElementById("g-body");
  var titleEl = document.getElementById("g-ch-title");
  var metaEl = document.getElementById("g-ch-meta");
  var searchEl = document.getElementById("g-search");
  var hitsEl = document.getElementById("g-hits");
  var gridEl = document.getElementById("g-chapter-grid");
  var prevBtn = document.getElementById("g-prev");
  var nextBtn = document.getElementById("g-next");
  var bnNoteEl = document.getElementById("g-bn-note");
  var sideEl = document.getElementById("g-side");

  /* গীতা/বেদে «শ্লোক», বাইবেলে «পদ» — সবই index.json থেকে, হার্ডকোড নয়। */
  var VW = "পদ", GW = "অধ্যায়", CW = "পুস্তক";
  var state = { bn: true, q: "", onlyBn: false, lang: "both" };
  var index = null, chapter = null, chapterEn = null;
  var bookId = 0, chapterId = 0, scope = "book";
  var testFilter = "all";
  var paintToken = 0;
  var CHUNK = 150;

  var FILTERS = [["all", "সব"], ["old", "পুরাতন নিয়ম"], ["new", "নতুন নিয়ম"]];

  /* ---------- ছোট সহায়ক ---------- */
  function saved() {
    try { return JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { return {}; }
  }
  function save(patch) {
    try {
      var cur = saved();
      for (var k in patch) cur[k] = patch[k];
      localStorage.setItem(KEY, JSON.stringify(cur));
    } catch (e) { }
  }

  var cache = {};
  function loadJSON(url) {
    if (cache[url]) return Promise.resolve(cache[url]);
    return fetch(url, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(url + " → " + r.status);
      return r.json();
    }).then(function (d) { cache[url] = d; return d; });
  }

  /* ইংরেজি ডেটার আকার যাচাই — ভুল ফাইল হলে প্রতি পদে আবর্জনা বসত */
  function enMap(e) {
    return (e && e.verses && typeof e.verses === "object" && !Array.isArray(e.verses)) ? e.verses : {};
  }

  /* পুরাতন/নতুন নিয়ম — ডেটায় testament থাকলে সেটাই সত্য, নইলে ৩৯ পুস্তক পর্যন্ত পুরাতন */
  function bookTestament(c) {
    if (c.testament === "old" || c.testament === "new") return c.testament;
    return c.id <= 39 ? "old" : "new";
  }

  function chapterIds(bk) {
    var n = bk.grid && bk.grid.count ? +bk.grid.count : (+bk.suktaCount || 0);
    /* নিরাপত্তা-নেট: suktaCount শূন্য বা perChapter-এর চেয়ে কম হলে ডেটার
       perChapter-ই ভরসা — নইলে অধ্যায়-গ্রিড ফাঁকা দেখিয়ে পাঠ আটকে যায়
       (২০২৬-১১-১৬: ১৬টি পুস্তকে suktas ছিল না, তাই গ্রিডই আঁকা হতো না)। */
    if (bk.perChapter) {
      var maxCh = 0;
      for (var k in bk.perChapter) {
        var v = +k;
        if (v > maxCh) maxCh = v;
      }
      if (maxCh > n) n = maxCh;
    }
    var out = [];
    for (var i = 1; i <= n; i++) out.push(i);
    return out;
  }

  function bookById(id) {
    if (!index) return null;
    for (var i = 0; i < index.chapters.length; i++) if (index.chapters[i].id === id) return index.chapters[i];
    return null;
  }
  function bkOf() { return bookById(bookId) || {}; }

  /* অধ্যায়টি ডেটায় সত্যিই আছে কি না — খালি ঘর ও নেভিগেশনের জন্য */
  function hasChapter(bk, id) {
    if (!bk) return false;
    var miss = (bk.grid && bk.grid.missing) || bk.missing || [];
    for (var i = 0; i < miss.length; i++) if (+miss[i] === +id) return false;
    var pc = bk.perChapter;
    if (pc && typeof pc === "object") return Object.prototype.hasOwnProperty.call(pc, String(id));
    return true;
  }

  /* ---------- পুস্তক-তালিকা ---------- */
  function renderBooks() {
    var box = document.getElementById("g-book-list");
    if (!box || !index) return;
    box.innerHTML = index.chapters.map(function (c) {
      var on = c.id === bookId;
      var meta = bn(c.count) + " " + VW;
      if (c.suktaCount) meta += " · " + bn(c.suktaCount) + " " + GW;
      if (c.prefaceCount) meta += " · অনুক্রমণিকা";

      /* অসম্পূর্ণ পুস্তক চিহ্নিত — chaptersTotal-এর কম perChapter থাকলে */
      var haveCh = c.perChapter ? Object.keys(c.perChapter).length : 0;
      var fullCh = +c.chaptersTotal || 0;
      var partial = fullCh > haveCh;
      if (partial && haveCh) {
        meta = bn(c.count) + " " + VW + " · " + bn(haveCh) + "/" + bn(fullCh) + " " + GW;
      }
      var tag = c.en ? ' <span class="g-bk-en" lang="en" dir="ltr">' + esc(c.en) + "</span>" : "";
      var badge = partial ? ' <span class="g-bk-p" title="' +
        esc("অসম্পূর্ণ — " + bn(haveCh) + "/" + bn(fullCh) + " " + GW) + '">অসম্পূর্ণ</span>' : "";
      return '<button class="g-ch g-bk' + (on ? " on" : "") + '" type="button" data-ch="' + c.id + '"' +
        (on ? ' aria-current="true"' : "") + ">" +
        '<span class="num">' + bn(c.num || c.id) + "</span>" +
        '<span class="txt"><span class="nm">' + esc(c.bn) + tag + badge + "</span>" +
        '<span class="meta">' + meta + "</span></span></button>";
    }).join("");
    box.querySelectorAll("[data-ch]").forEach(function (b) {
      b.addEventListener("click", function () {
        showBookView(+b.dataset.ch);
        try {
          if (window.matchMedia && window.matchMedia("(max-width: 980px)").matches) {
            setFolded(true, false);
          }
        } catch (e) {}
      });
    });
  }

  /* ---------- পুরাতন/নতুন নিয়ম — ছাঁকনি ও গ্রুপ-শিরোনাম ---------- */
  function renderTestaments() {
    var tb = document.getElementById("g-testament");
    var box = document.getElementById("g-book-list");
    if (!tb || !box || !index) return;
    var has = index.chapters.some(function (c) { return c.testament === "old" || c.testament === "new"; });
    if (!has) {
      tb.hidden = true;
      box.querySelectorAll(".g-tgroup").forEach(function (e) { e.remove(); });
      return;
    }
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
        h.innerHTML = "<span>" + lbl + '</span><i>' + bn(groups[t].length) + " " + CW + "</i>";
        box.insertBefore(h, first);
      });
    } else {
      index.chapters.forEach(function (c) {
        var b = box.querySelector('[data-ch="' + c.id + '"]');
        var keep = bookTestament(c) === testFilter;
        if (b) b.hidden = !keep;
      });
    }
  }

  /* ---------- তালিকার ভাঁজ (মোবাইল) ---------- */
  function syncFold() {
    var btn = document.getElementById("g-side-toggle");
    if (!sideEl || !btn) return;
    var folded = sideEl.classList.contains("folded");
    btn.setAttribute("aria-expanded", folded ? "false" : "true");
    var now = document.getElementById("g-side-now");
    if (now) {
      var bk = bkOf();
      var cur = bk.bn || "";
      now.textContent = cur;
      now.hidden = !(folded && cur);
    }
  }
  function setFolded(on, remember) {
    if (!sideEl) return;
    sideEl.classList.toggle("folded", !!on);
    syncFold();
    if (remember) save({ fold: !!on });
  }
  function bindFold() {
    var btn = document.getElementById("g-side-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      setFolded(!sideEl.classList.contains("folded"), true);
    });
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
      /* খালি ঘরও দেখাই (আলাদা রঙে) — নইলে পাঠক ভাবেন অধ্যায়টাই নেই */
      return '<button class="g-cg' + (on ? " on" : "") + (have ? "" : " off") +
        '" type="button" data-c="' + i + '"' + (on ? ' aria-current="true"' : "") +
        (have ? "" : ' aria-label="' + bn(i) + ' — পাঠ নেই" title="উৎসে পাওয়া যায়নি"') + ">" +
        "<span>" + prefix + bn(i) + "</span></button>";
    }).join("");
    gridEl.querySelectorAll("[data-c]").forEach(function (b) {
      b.addEventListener("click", function () { openChapter(+b.dataset.c); });
    });
  }

  /* ---------- শিরোনাম ---------- */
  function syncHead() {
    if (state.q && state.q.length >= 2) return;
    var bk = bkOf();
    if (!bk.bn) return;
    if (scope === "chapter" && chapter && chapter.id === bookId) {
      if (titleEl) titleEl.textContent = bk.bn + " · " + GW + " " + bn(chapterId) + " ";
      var ent = bk.perChapter ? bk.perChapter[String(chapterId)] : null;
      if (metaEl) metaEl.textContent = ent ? bn(ent) + " " + VW : "";
    } else {
      /* পুস্তক-দৃশ্য: শিরোনামে পুস্তকের নাম, মেটায় অধ্যায় ও পদ-সংখ্যা।
         মোট পদ পুস্তক-ভিত্তিক (perChapter সমষ্টি), অধ্যায়-সংখ্যা গ্রিড থেকে। */
      var tot = bk.perChapter
        ? Object.keys(bk.perChapter).reduce(function (a, k) { return a + (+bk.perChapter[k] || 0); }, 0)
        : (+bk.count || 0);
      if (titleEl) titleEl.textContent = bk.bn + " · " + CW + " ";
      if (metaEl) metaEl.textContent = bn(chapterIds(bk).length) + " " + GW + " · " + bn(tot) + " " + VW;
    }
  }

  /* ইংরেজি কভারেজের নোট — ডেটার aligned/skipped থেকে */
  function enNote() {
    var el = document.getElementById("g-en-note");
    if (!el) return;
    var bk = bkOf();
    var al = bk.aligned == null ? null : +bk.aligned;
    var sk = bk.skipped == null ? null : +bk.skipped;
    if (al == null) { el.hidden = true; return; }
    var txt;
    if (al === 0) txt = "এই পুস্তকে ইংরেজি পাঠ এখনো যোগ করা যায়নি — কেবল বাংলা দেখানো হচ্ছে।";
    else if (sk) txt = "এই পুস্তকের " + bn(al) + "টি অধ্যায়ে ইংরেজি পাঠ মিলেছে; " + bn(sk) +
      "টিতে মেলেনি (দুই সংস্করণের পদ-বিন্যাস আলাদা) — সেখানে কেবল বাংলা।";
    else { el.hidden = true; el.textContent = ""; return; }
    el.hidden = false;
    el.innerHTML = "<b>ইংরেজি পাঠ।</b> " + esc(txt);
  }

  function refreshCrumb() {
    var cr = document.getElementById("g-crumb2");
    if (!cr) return;
    var bk = bookById(bookId);
    if (!bk || scope !== "chapter") { cr.hidden = true; return; }
    cr.hidden = false;
    cr.innerHTML = '<button type="button" class="g-crumb-b" data-go="books">' + esc(bk.bn) +
      "</button><span>›</span><b>" + GW + " " + bn(chapterId) + "</b>";
    var b0 = cr.querySelector("[data-go]");
    if (b0) b0.addEventListener("click", function () { showBookView(bookId); });
  }

  var searchRendered = false;
  function clearSearch(keepInput) {
    searchRendered = false;
    if (!keepInput) {
      state.q = "";
      if (searchEl) searchEl.value = "";
    }
    if (hitsEl) hitsEl.textContent = "";
  }

  /* ---------- দৃশ্য: পুস্তক (অধ্যায়-গ্রিড) ---------- */
  function showBookView(id, keepInput) {
    bookId = id;
    scope = "book"; chapter = null; chapterEn = null; chapterId = 0;
    paintToken++;
    clearSearch(keepInput);
    if (bodyEl) bodyEl.innerHTML = '<p class="g-empty g-pick">উপরের তালিকা থেকে একটি অধ্যায় বেছে নিন — পদগুলো নিচে দেখা যাবে।</p>';
    syncHead();
    if (bnNoteEl) bnNoteEl.hidden = true;
    if (langBox) langBox.hidden = true;
    renderChapterGrid();
    refreshCrumb();
    enNote();
    setPrevNext();
    syncFold();
    renderBooks();
    renderTestaments();
    save({ book: id });
  }

  /* ---------- আগের/পরের ---------- */
  function setPrevNext() {
    if (!index) return;
    var bs = index.chapters, i = -1;
    for (var k = 0; k < bs.length; k++) if (bs[k].id === bookId) i = k;
    var bk = i >= 0 ? bs[i] : null;
    var nch = bk ? chapterIds(bk).length : 0;
    var atCh = scope === "chapter";
    var nxt = chapterId + 1;
    while (bk && nxt <= nch && !hasChapter(bk, nxt)) nxt++;
    var prv = chapterId - 1;
    while (bk && prv >= 1 && !hasChapter(bk, prv)) prv--;
    var pTxt = "‹ আগের", nTxt = "পরের ›";
    if (atCh && prv >= 1) pTxt = "‹ " + GW + " " + bn(prv);
    else if (i > 0) pTxt = "‹ " + bs[i - 1].bn;
    if (atCh && nxt <= nch) nTxt = GW + " " + bn(nxt) + " ›";
    else if (i >= 0 && i < bs.length - 1) nTxt = bs[i + 1].bn + " ›";
    var canPrev = (atCh && prv >= 1) || i > 0;
    var canNext = (atCh && nxt <= nch) || (i >= 0 && i < bs.length - 1);
    if (prevBtn) { prevBtn.disabled = !canPrev; prevBtn.textContent = canPrev ? pTxt : "‹ আগের"; }
    if (nextBtn) { nextBtn.disabled = !canNext; nextBtn.textContent = canNext ? nTxt : "পরের ›"; }
  }

  function step(d) {
    if (!index) return;
    var bs = index.chapters, pos = -1;
    for (var k = 0; k < bs.length; k++) if (bs[k].id === bookId) pos = k;
    if (pos < 0) return;
    var bk = bs[pos], nch = chapterIds(bk).length;
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
  }

  /* ---------- পদ ---------- */
  function verseHTML(v) {
    var q = state.q ? state.q.toLowerCase() : "";
    var en = enMap(chapterEn)[String(v.n)] || "";
    var hit = q && ((v.bn || "").toLowerCase().indexOf(q) > -1 ||
                    en.toLowerCase().indexOf(q) > -1);
    var shown = (typeof v.vn === "number") ? v.vn : v.n;
    var out = '<article class="g-v' + (hit ? " hit" : "") + '" id="v' + v.n + '">';
    out += (v.noNum ? '<div class="g-v-num g-v-nonum" aria-hidden="true"></div>'
                    : '<div class="g-v-num" aria-hidden="true">' + bn(shown) + "</div>") +
           '<div class="g-v-body">';
    if (v.hd) out += '<p class="g-v-hd">' + esc(v.hd) + "</p>";
    if (v.spk) out += '<p class="g-v-spk">' + esc(v.spk) + "</p>";
    if (state.bn && v.bn && state.lang !== "en") {
      out += '<p class="g-v-bn">' + esc(v.bn).replace(/\n+/g, '</p><p class="g-v-bn">') + "</p>";
    }
    /* উৎসে পদ-নম্বর আছে কিন্তু পাঠ নেই — লুকিয়ে না রেখে স্পষ্ট নোট */
    if (v.srcEmpty && state.lang !== "en") {
      out += '<p class="g-v-empty">এই পদ-নম্বরটি উৎসে আছে, কিন্তু উৎস-পাতায় এর পাঠ দেওয়া হয়নি।</p>';
    }
    if (en && state.lang !== "bn") {
      out += '<p class="g-v-en" lang="en">' + esc(en) + "</p>";
    }
    out += "</div></article>";
    return out;
  }

  /* সার্চ পুরো বাইবেল জুড়ে — একবার সব পুস্তক এনে মিলিয়ে রাখি */
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
          .catch(function () { });
      }));
    }).then(function () { return allLoaded; });
  }

  function searchHTML(q) {
    var low = q.toLowerCase(), rows = [], total = 0;
    allLoaded.forEach(function (c) {
      var enm = enMap(enByCh[c.id]);
      var hit = c.verses.filter(function (v) {
        return (v.bn || "").toLowerCase().indexOf(low) > -1 ||
               ((enm[String(v.n)] || "").toLowerCase().indexOf(low) > -1);
      });
      if (!hit.length) return;
      total += hit.length;
      rows.push('<p class="g-hit-head">' + esc(c.bn) + " · " + bn(hit.length) + "টি</p>");
      rows.push(hit.map(function (v) {
        var out = '<article class="g-v hit" id="v' + c.id + '-' + v.n + '">';
        out += '<div class="g-v-num">' + bn(v.vn || v.n) + '</div><div class="g-v-body">';
        if (v.spk) out += '<p class="g-v-spk">' + esc(v.spk) + "</p>";
        if (v.bn) out += '<p class="g-v-bn">' + esc(v.bn) + "</p>";
        if (enm[String(v.n)]) out += '<p class="g-v-en" lang="en">' + esc(enm[String(v.n)]) + "</p>";
        return out + "</div></article>";
      }).join(""));
    });
    return { html: rows.join("") || '<p class="g-empty">কিছু মেলেনি। অন্য শব্দে চেষ্টা করুন।</p>', total: total };
  }

  function renderVerses() {
    /* পুস্তক-দৃশ্যে (কোনো অধ্যায় খোলা নেই) সার্চ তবুও চলবে — নইলে পাঠক
       তালিকায় থেমে সার্চ লিখে কিছুই পান না। সার্চ মুছে ফেললে পুস্তক-দৃশ্য ফিরবে। */
    if (!chapter && !(state.q && state.q.length >= 2)) {
      if (searchRendered && scope === "book" && bookId) showBookView(bookId, true);
      return;
    }

    /* খোঁজার অবস্থায় থাকলে পুরো বাইবেলের ফলাফল */
    if (state.q && state.q.length >= 2) {
      var qSnap = state.q;
      searchRendered = true;
      if (bnNoteEl) bnNoteEl.hidden = true;
      bodyEl.innerHTML = window.EadSkeleton
        ? window.EadSkeleton.readerSkeleton({ cards: 3, head: false, label: "খোঁজা হচ্ছে…" })
        : '<p class="g-loading">খোঁজা হচ্ছে…</p>';
      loadAll().then(function () {
        if (state.q !== qSnap) return;
        var r = searchHTML(qSnap);
        bodyEl.innerHTML = r.html;
        if (titleEl) titleEl.textContent = "খোঁজা: " + qSnap;
        if (metaEl) metaEl.textContent = bn(r.total) + "টি " + VW;
        if (hitsEl) hitsEl.textContent = r.total ? bn(r.total) + "টি " + VW + " পাওয়া গেছে" : "কিছু মেলেনি";
      });
      return;
    }
    searchRendered = false;

    var all = chapter.verses;
    if (state.onlyBn) all = all.filter(function (v) { return v.bn; });

    /* বাংলা অনুবাদের কভারেজ — একবার, প্রতি পদে নয় */
    if (bnNoteEl) {
      var withBn = chapter.verses.filter(function (v) { return v.bn; }).length;
      var total = chapter.verses.length;
      if (!state.bn) {
        bnNoteEl.hidden = true;
      } else if (withBn === 0) {
        bnNoteEl.hidden = false;
        bnNoteEl.innerHTML = "এই অধ্যায়ের <b>" + bn(total) + "টি " + VW + "</b>-এর বাংলা অনুবাদ এখনো যোগ করা যায়নি।";
      } else if (withBn < total) {
        bnNoteEl.hidden = false;
        bnNoteEl.innerHTML = "বাংলা অনুবাদ পাওয়া গেছে <b>" + bn(withBn) + "/" + bn(total) + "</b>টিতে।";
      } else {
        bnNoteEl.hidden = true;
      }
    }

    /* একবারে এক অধ্যায় — শিরোনাম + কেবল তার পদ */
    var parts = [];
    var pick = null;
    if (chapter.suktas) {
      chapter.suktas.forEach(function (x) { if (+x.id === +chapterId) pick = x; });
    }
    if (pick) {
      var inR = all.filter(function (v) { return v.n >= pick.from && v.n <= pick.to; });
      parts.push('<h3 class="g-sukta-h g-chap-h" id="sukta' + pick.id + '">' +
        '<span class="g-sukta-n">' + GW + " " + bn(pick.id) + "</span>" +
        '<span class="g-sukta-m">' + VW + " " +
        bn(pick.vfrom || pick.from) + "–" + bn(pick.vto || pick.to) +
        (pick.shloka ? " · " + bn(pick.shloka) + " শ্লোক" : "") + "</span></h3>");
      inR.forEach(function (v) { parts.push(verseHTML(v)); });
      if (!inR.length) {
        parts.push('<p class="g-empty g-miss"><b>' + GW + " " + bn(pick.id) +
          "</b> এই অধ্যায়ের পাঠ উৎসে পাওয়া যায়নি — অনুমান করে কিছু বসানো হয় না।</p>");
      }
    } else {
      /* উৎসে অধ্যায়টিই নেই — সত্য কথাটাই বলি, অনুমান করে কিছু বসাই না */
      var bk0 = bkOf();
      parts.push('<p class="g-empty g-miss"><b>' + GW + " " + bn(chapterId) +
        "</b> এই অধ্যায়ের পাঠ উৎসে পাওয়া যায়নি" +
        (bk0.bn ? " (" + esc(bk0.bn) + ")" : "") +
        " — অনুমান করে কিছু বসানো হয় না। পাশের অধ্যায় থেকে পড়া চালিয়ে যেতে পারেন।</p>");
    }

    /* উৎসের ভূমিকা — পাঠ নয়, তাই আলাদা ভাঁজ-ব্লকে */
    var front = "";
    if (!state.q && (chapter.preface || chapter.heading)) {
      var sumTxt = chapter.heading ? esc(chapter.heading).replace(/\n+/g, " · ") : "অনুক্রমণিকা";
      front = '<details class="g-front"><summary>' + sumTxt +
        ' <span class="g-front-tag">উৎসের ভূমিকা-অনুবাদ · পাঠের বাইরে</span></summary>' +
        String(chapter.preface || "").split(/\n\n+/).filter(function (x) { return x.trim(); })
          .map(function (par) {
            return '<p class="g-front-t">' + esc(par).replace(/\n+/g, '</p><p class="g-front-t">') + "</p>";
          }).join("") +
        "</details>";
    }

    /* ভাষা-টগল কেবল তখনই, যখন এই অধ্যায়ে সত্যিই ইংরেজি পাঠ আছে */
    var hasEn = Object.keys(enMap(chapterEn)).length > 0;
    if (langBox) langBox.hidden = !hasEn;
    if (!hasEn && state.lang === "en") { state.lang = "both"; syncLang(); }

    /* ব্যাচে ব্যাচে আঁকা — বড় অধ্যায়ে ব্রাউজার ঝুলে যায়; token মিলিয়ে
       অন্য অধ্যায় খুললে পুরোনো ব্যাচ থেমে যায় (দুই অধ্যায় মেশে না) */
    var token = ++paintToken;
    bodyEl.innerHTML = front;
    var at = 0;
    (function draw() {
      if (token !== paintToken || !bodyEl.isConnected) return;
      var slice = parts.slice(at, at + CHUNK);
      bodyEl.insertAdjacentHTML("beforeend", slice.join("") ||
        (at === 0 ? '<p class="g-empty">কিছু পাওয়া যায়নি।</p>' : ""));
      at += CHUNK;
      if (at < parts.length) setTimeout(draw, 0);
    })();
    if (hitsEl) hitsEl.textContent = "";
    syncHead();
  }

  /* ---------- অধ্যায় খোলা ---------- */
  function openChapter(id) {
    if (!id || isNaN(+id)) return;
    id = +id;
    chapterId = id;
    scope = "chapter";
    paintToken++;
    clearSearch();
    save({ last: id, lastbook: bookId, scope: "chapter" });
    renderChapterGrid();
    refreshCrumb();
    syncFold();
    setPrevNext();
    bodyEl.innerHTML = window.EadSkeleton
      ? window.EadSkeleton.readerSkeleton({ cards: 4, head: false, label: "লোড হচ্ছে…" })
      : '<p class="g-loading">লোড হচ্ছে…</p>';
    Promise.all([
      loadJSON(BASE + "ch" + bookId + ".json"),
      loadJSON(BASE + "en/ch" + bookId + ".json").catch(function () { return null; })
    ]).then(function (r) {
      if (chapterId !== id || bookId !== r[0].id) return;
      chapter = r[0]; chapterEn = r[1];
      syncHead(); refreshCrumb(); enNote(); syncFold();
      renderVerses();
      try { window.scrollTo({ top: (gridEl || root).offsetTop - 90, behavior: "smooth" }); } catch (e) { }
      var h = location.hash;
      if (h && /^#v?\d+$/.test(h)) {
        var el = document.getElementById("v" + h.replace("#v", "").replace("#", ""));
        if (el) el.scrollIntoView({ block: "center" });
      }
    }).catch(function () {
      bodyEl.innerHTML = '<p class="g-empty">অধ্যায়টি লোড করা গেল না। পুনরায় চেষ্টা করুন।</p>';
    });
  }

  /* ---------- ভাষা-নিয়ন্ত্রণ ---------- */
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
  function bind() {
    if (searchEl) {
      searchEl.addEventListener("input", function () {
        state.q = searchEl.value.trim();
        renderVerses();
      });
    }
    var bnBtn = document.getElementById("g-bn-btn");
    if (bnBtn) bnBtn.addEventListener("click", function () {
      state.bn = !state.bn; bnBtn.classList.toggle("on", state.bn);
      bnBtn.setAttribute("aria-pressed", state.bn ? "true" : "false");
      save({ bn: state.bn }); renderVerses();
    });
    var onlyBnEl = document.getElementById("g-only-bn");
    if (onlyBnEl) onlyBnEl.addEventListener("change", function () {
      state.onlyBn = onlyBnEl.checked; save({ onlyBn: state.onlyBn }); renderVerses();
    });
    if (prevBtn) prevBtn.addEventListener("click", function () { step(-1); });
    if (nextBtn) nextBtn.addEventListener("click", function () { step(1); });
    if (listEl) listEl.addEventListener("keydown", function (e) {
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

  function syncStickTop() {
    if (!root) return;
    var narrow = false;
    try { narrow = window.matchMedia && window.matchMedia("(max-width: 980px)").matches; } catch (e) {}
    if (narrow) { root.style.removeProperty("--g-stick-top"); return; }
    var header = document.querySelector("header.top");
    var bar = root.querySelector(".g-toolbar");
    var hh = header ? header.getBoundingClientRect().height : 70;
    var bh = bar ? bar.getBoundingClientRect().height : 62;
    root.style.setProperty("--g-stick-top", Math.max(150, Math.ceil(hh + bh + 16)) + "px");
  }

  /* ---------- শুরু ---------- */
  var st = saved();
  if (typeof st.bn === "boolean") state.bn = st.bn;
  if (typeof st.onlyBn === "boolean") state.onlyBn = st.onlyBn;
  if (st.lang === "both" || st.lang === "bn" || st.lang === "en") state.lang = st.lang;
  var bnBtn0 = document.getElementById("g-bn-btn");
  if (bnBtn0) { bnBtn0.classList.toggle("on", state.bn); bnBtn0.setAttribute("aria-pressed", state.bn ? "true" : "false"); }
  var onlyBn0 = document.getElementById("g-only-bn");
  if (onlyBn0) onlyBn0.checked = state.onlyBn;

  loadJSON(BASE + "index.json").then(function (d) {
    index = d;
    if (d.verseWord) VW = d.verseWord;
    if (d.groupWord) GW = d.groupWord;
    if (d.chword) CW = d.chword;
    /* সব পুস্তকে বাংলা থাকলে এই ছাঁকনি অকেজো — লুকিয়ে রাখি */
    if (onlyBn0 && d.total && d.withBn === d.total) {
      var lab = onlyBn0.closest ? onlyBn0.closest("label") : onlyBn0.parentNode;
      if (lab) lab.hidden = true;
    }
    buildLangBox();
    bind();
    bindFold();
    syncStickTop();
    window.addEventListener("resize", function () {
      syncStickTop();
      var narrowNow = false;
      try { narrowNow = window.matchMedia && window.matchMedia("(max-width: 980px)").matches; } catch (e) {}
      if (!narrowNow) setFolded(false, false);
    });
    if (window.ResizeObserver) {
      var bBar = root.querySelector(".g-toolbar");
      if (bBar) new ResizeObserver(syncStickTop).observe(bBar);
    }
    /* ফোনে ডিফল্ট ভাঁজ, ডেস্কটপে খোলা; পাঠক নিজে বদলালে ফোনের অবস্থা মনে থাকে */
    var narrow = false;
    try { narrow = window.matchMedia && window.matchMedia("(max-width: 980px)").matches; } catch (e) { }
    if (narrow) setFolded(typeof st.fold === "boolean" ? st.fold : true, false);
    else setFolded(false, false);

    var m = (location.hash || "").match(/^#ch(\d+)$/) || (location.hash || "").match(/^#b(\d+)c(\d+)$/);
    var startBook = null, startCh = null;
    if (location.hash && /^#b\d+c\d+$/.test(location.hash)) {
      var mm = location.hash.match(/^#b(\d+)c(\d+)$/);
      startBook = +mm[1]; startCh = +mm[2];
    } else if (m) {
      startBook = +m[1];   /* পুরোনো লিংক #ch12 = পুস্তক-নম্বর */
    }

    renderBooks();
    renderTestaments();
    if (startBook != null && bookById(startBook)) {
      if (startCh != null) { showBookView(startBook); openChapter(startCh); }
      else showBookView(startBook);
    } else if (st.book && bookById(st.book)) {
      if (st.last && st.lastbook === st.book && st.scope === "chapter") {
        showBookView(st.book);
        openChapter(st.last);
      } else {
        showBookView(st.book);
      }
    } else if (index.chapters[0]) {
      showBookView(index.chapters[0].id);
    }
    setPrevNext();
  }).catch(function () {
    if (bodyEl) bodyEl.innerHTML = '<p class="g-empty">সূচি লোড করা গেল না।</p>';
  });
})();
