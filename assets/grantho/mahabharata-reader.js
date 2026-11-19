/* ============================================================
   mahabharata-reader.js — মহাভারতের ১৮ পর্ব ও ৩ সংস্করণের পাঠক
   ------------------------------------------------------------
   সংস্করণ:
     · bn — বাংলা গদ্য অনুবাদ (কালীপ্রসন্ন সিংহ · ২,০৮৮ অধ্যায় · ৩,৭৬৫ উপাখ্যান)
     · en — ইংরেজি অনুবাদ (Kisari Mohan Ganguli · ২,১০৮ পরিচ্ছেদ)
     · sa — সংস্কৃত মূল পাঠ (দেবনাগরী · ২,৩১৫ অধ্যায় · ৯৬,৮১২ শ্লোক)

   নীতি: প্রতিটি সংস্করণের অধ্যায়-বিন্যাস তার নিজস্ব ঐতিহ্য অনুযায়ী অটুট
   রাখা হয় — অনুমান করে অধ্যায় জোড়া হয় না বা ঘাটতি গোপন করা হয় না।
   একবারে কেবল ৫০ অধ্যায়ের সংশ্লিষ্ট খণ্ডটি লোড হয়।
   ============================================================ */
(function () {
  "use strict";

  var root = document.getElementById("grantho-reader");
  if (!root) return;

  var SLUG = root.dataset.granth || "mahabharata";
  function autoBase() {
    var dir = location.pathname.replace(/[^\/]*$/, "");
    var segs = dir.split("/").filter(Boolean).slice(1);
    return "../".repeat(segs.length) + "assets/grantho/data/" + SLUG + "/";
  }
  var BASE = root.dataset.base || autoBase();
  var KEY = "grantho." + SLUG + ".v1";
  var BN_DIGITS = "০১২৩৪৫৬৭৮৯";

  function bn(n) {
    return String(n).replace(/[0-9]/g, function (d) { return BN_DIGITS[+d]; });
  }
  function bnNum(n) {
    return bn(String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","));
  }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }
  function saved() {
    try { return JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { return {}; }
  }
  function save(patch) {
    try {
      var s = saved();
      for (var k in patch) s[k] = patch[k];
      localStorage.setItem(KEY, JSON.stringify(s));
    } catch (e) {}
  }

  var cache = {};
  function loadJSON(url) {
    if (cache[url]) return Promise.resolve(cache[url]);
    return fetch(url, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(url + " -> " + r.status);
      return r.json();
    }).then(function (d) { cache[url] = d; return d; });
  }

  var bookListEl = document.getElementById("g-book-list");
  var bodyEl     = document.getElementById("g-body");
  var titleEl    = document.getElementById("g-ch-title");
  var metaEl     = document.getElementById("g-ch-meta");
  var gridEl     = document.getElementById("g-chapter-grid");
  var prevBtn    = document.getElementById("g-prev");
  var nextBtn    = document.getElementById("g-next");
  var searchEl   = document.getElementById("g-search");
  var hitsEl     = document.getElementById("g-hits");
  var edBox      = document.getElementById("g-mbh-ed");
  var noteEl     = document.getElementById("g-en-note");
  var crumbEl    = document.getElementById("g-crumb2");

  var EDITIONS = [
    ["bn", "বাংলা (কালীপ্রসন্ন)"],
    ["en", "English (Ganguli)"],
    ["sa", "সংস্কৃত (মূল)"]
  ];

  var index = null;
  var parvaId = 1;
  var chapterId = 1;
  var scope = "book";   // "book" | "chapter"
  var edition = "bn";   // "bn" | "en" | "sa"
  var query = "";
  var loadToken = 0;

  function parvaById(id) {
    if (!index || !index.parvas) return null;
    for (var i = 0; i < index.parvas.length; i++) {
      if (index.parvas[i].id === id) return index.parvas[i];
    }
    return null;
  }

  function edMeta(pv, ed) {
    return (pv && pv.editions && pv.editions[ed || edition]) || null;
  }

  /* বর্তমান পর্ব ও সংস্করণের সব বৈধ অধ্যায়-নম্বর */
  function allChapterIds(pv, ed) {
    var em = edMeta(pv, ed);
    if (!em || !em.chunks) return [];
    var out = [];
    for (var i = 0; i < em.chunks.length; i++) {
      var ids = em.chunks[i].ids || [];
      for (var j = 0; j < ids.length; j++) out.push(ids[j]);
    }
    return out;
  }

  /* গ্রিডের সব ঘর (বাংলায় অনুপস্থিত ঘরগুলোও আলাদা রঙে দেখানোর জন্য) */
  function gridCells(pv, ed) {
    var ids = allChapterIds(pv, ed);
    if (!ids.length) return [];
    if ((ed || edition) !== "bn") {
      return ids.map(function (id) { return { id: id, have: true }; });
    }
    var em = edMeta(pv, "bn");
    var maxCh = (em && em.maxCh) || ids[ids.length - 1];
    var present = {};
    for (var i = 0; i < ids.length; i++) present[ids[i]] = true;
    var cells = [];
    for (var n = 1; n <= maxCh; n++) {
      cells.push({ id: n, have: !!present[n] });
    }
    return cells;
  }

  function chunkForChapter(pv, ed, ch) {
    var em = edMeta(pv, ed);
    if (!em || !em.chunks) return null;
    for (var i = 0; i < em.chunks.length; i++) {
      var ck = em.chunks[i];
      if (ck.ids && ck.ids.indexOf(ch) > -1) return ck;
    }
    return null;
  }

  /* ---------- মোবাইল ভাঁজ ও স্টিকি পজিশন ---------- */
  function syncFold() {
    var side = document.getElementById("g-side");
    var btn = document.getElementById("g-side-toggle");
    if (!side || !btn) return;
    var folded = side.classList.contains("folded");
    btn.setAttribute("aria-expanded", folded ? "false" : "true");
    var now = document.getElementById("g-side-now");
    if (now) {
      var pv = parvaById(parvaId) || {};
      var cur = pv.bn || "";
      now.textContent = cur;
      now.hidden = !(folded && cur);
    }
  }

  function setFolded(on, remember) {
    var side = document.getElementById("g-side");
    if (!side) return;
    side.classList.toggle("folded", !!on);
    syncFold();
    if (remember) save({ fold: !!on });
  }

  function syncStickTop() {
    var narrow = false;
    try { narrow = window.matchMedia && window.matchMedia("(max-width: 980px)").matches; } catch (e) {}
    if (narrow) { root.style.removeProperty("--g-stick-top"); return; }
    var header = document.querySelector("header.top");
    var bar = root.querySelector(".g-toolbar");
    var hh = header ? header.getBoundingClientRect().height : 70;
    var bh = bar ? bar.getBoundingClientRect().height : 62;
    root.style.setProperty("--g-stick-top", Math.max(150, Math.ceil(hh + bh + 16)) + "px");
  }

  /* ---------- সংস্করণ সুইচার ---------- */
  function buildEditions() {
    if (!edBox) return;
    edBox.innerHTML = EDITIONS.map(function (x) {
      return '<button type="button" class="g-mbh-ed-btn" data-ed="' + x[0] + '">' + esc(x[1]) + '</button>';
    }).join("");
    edBox.querySelectorAll("[data-ed]").forEach(function (b) {
      b.addEventListener("click", function () {
        switchEdition(b.dataset.ed);
      });
    });
    syncEditions();
  }

  function syncEditions() {
    if (!edBox) return;
    edBox.querySelectorAll("[data-ed]").forEach(function (b) {
      var on = b.getAttribute("data-ed") === edition;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (searchEl) {
      var ph = edition === "bn" ? "এই পর্বে খুঁজুন (বাংলা)"
             : edition === "en" ? "এই পর্বে খুঁজুন (English)"
             : "এই পর্বে খুঁজুন (संस्कृतम्)";
      searchEl.setAttribute("placeholder", ph);
    }
  }

  function switchEdition(ed) {
    if (ed !== "bn" && ed !== "en" && ed !== "sa") return;
    if (ed === edition) return;
    edition = ed;
    save({ ed: edition });
    syncEditions();
    renderParvas();
    var pv = parvaById(parvaId);
    if (!pv) return;
    if (scope === "chapter") {
      var ids = allChapterIds(pv, edition);
      var target = ids.indexOf(chapterId) > -1 ? chapterId : (ids[0] || 1);
      openChapter(target);
    } else {
      showParvaView(parvaId);
    }
  }

  /* ---------- ১৮ পর্বের বাম-তালিকা ---------- */
  function renderParvas() {
    if (!bookListEl || !index) return;
    bookListEl.hidden = false;
    bookListEl.innerHTML = index.parvas.map(function (pv) {
      var on = pv.id === parvaId;
      var em = edMeta(pv, edition);
      var meta = "";
      if (edition === "bn") {
        meta = bnNum(em.chCount) + " অধ্যায় · " + bnNum(em.upaCount) + " উপাখ্যান";
      } else if (edition === "en") {
        meta = bnNum(em.chCount) + " পরিচ্ছেদ";
      } else {
        meta = bnNum(em.chCount) + " অধ্যায় · " + bnNum(em.shlokaCount) + " শ্লোক";
      }
      var tag = pv.en ? ' <span class="g-bk-en" lang="en" dir="ltr">' + esc(pv.en) + '</span>' : "";
      var badge = (edition === "bn" && em && em.note && pv.id === 9)
        ? ' <span class="g-bk-p" title="শল্যপর্বের ডিজিটাল বাংলা পাঠ ৪৫ অধ্যায় পর্যন্ত">৪৫/' + bn(em.chCount) + '</span>'
        : "";
      return '<button class="g-ch g-bk' + (on ? " on" : "") + '" type="button" data-ch="' + pv.id + '"' +
        (on ? ' aria-current="true"' : "") + '>' +
        '<span class="num">' + bn(pv.id) + '</span>' +
        '<span class="txt"><span class="nm">' + esc(pv.bn) + tag + badge + '</span>' +
        '<span class="meta">' + meta + '</span></span></button>';
    }).join("");
    bookListEl.querySelectorAll("[data-ch]").forEach(function (b) {
      b.addEventListener("click", function () {
        showParvaView(+b.dataset.ch);
        try {
          if (window.matchMedia && window.matchMedia("(max-width: 980px)").matches) {
            setFolded(true, false);
          }
        } catch (e) {}
      });
    });
  }

  /* ---------- অধ্যায়-গ্রিড ---------- */
  function renderGrid() {
    if (!gridEl) return;
    var pv = parvaById(parvaId);
    if (!pv) { gridEl.innerHTML = ""; return; }
    var cells = gridCells(pv, edition);
    var em = edMeta(pv, edition);
    var titles = (em && em.titles) || {};
    gridEl.innerHTML = cells.map(function (c) {
      var on = scope === "chapter" && c.id === chapterId;
      var lbl = c.id === 0 ? "ভূমিকা" : bn(c.id);
      var tip = !c.have
        ? "ডিজিটাল বাংলা উৎসে অনুপস্থিত"
        : (titles[String(c.id)] || ((edition === "en" ? "পরিচ্ছেদ " : "অধ্যায় ") + bn(c.id)));
      return '<button class="g-cg' + (on ? " on" : "") + (c.have ? "" : " off") +
        '" type="button" data-c="' + c.id + '"' + (on ? ' aria-current="true"' : "") +
        ' title="' + esc(tip) + '" aria-label="' + esc(tip) + '">' +
        '<span>' + esc(lbl) + '</span></button>';
    }).join("");
    gridEl.querySelectorAll("[data-c]").forEach(function (b) {
      b.addEventListener("click", function () {
        openChapter(+b.dataset.c);
      });
    });
  }

  function renderNote() {
    if (!noteEl) return;
    var pv = parvaById(parvaId);
    var em = edMeta(pv, edition);
    if (em && em.note) {
      noteEl.hidden = false;
      noteEl.innerHTML = '<b>উৎস-তথ্য।</b> ' + esc(em.note) +
        '<div class="g-en-note-act">' +
        '<button type="button" data-sw="en">English (Ganguli)-তে পড়ুন</button>' +
        '<button type="button" data-sw="sa">সংস্কৃত মূলে পড়ুন</button>' +
        '</div>';
      noteEl.querySelectorAll("[data-sw]").forEach(function (btn) {
        btn.addEventListener("click", function () { switchEdition(btn.dataset.sw); });
      });
    } else {
      noteEl.hidden = true;
      noteEl.textContent = "";
    }
  }

  function syncHead(chObj) {
    if (query.length >= 2) return;
    var pv = parvaById(parvaId) || {};
    var em = edMeta(pv, edition) || {};
    if (scope === "chapter" && chObj) {
      var unit = edition === "en" ? "পরিচ্ছেদ" : "অধ্যায়";
      var headLbl = chObj.c === 0 ? "ভূমিকা" : (unit + " " + bn(chObj.c));
      if (titleEl) {
        titleEl.textContent = pv.bn + " · " + headLbl + " ";
        if (pv.en) {
          var s = document.createElement("span");
          s.className = "g-head-en"; s.lang = "en"; s.dir = "ltr"; s.textContent = pv.en;
          titleEl.appendChild(s);
        }
      }
      if (metaEl) {
        if (edition === "bn") {
          metaEl.textContent = (chObj.t ? chObj.t + " · " : "") + bn(chObj.u.length) + " উপাখ্যান";
        } else if (edition === "en") {
          metaEl.textContent = (chObj.t || ("Section " + chObj.c)) + " · " + bn(chObj.p.length) + " অনুচ্ছেদ";
        } else {
          metaEl.textContent = (chObj.t ? chObj.t + " · " : "") + bn(chObj.v.length) + " শ্লোক";
        }
      }
    } else {
      if (titleEl) {
        titleEl.textContent = pv.bn + " ";
        if (pv.en) {
          var s2 = document.createElement("span");
          s2.className = "g-head-en"; s2.lang = "en"; s2.dir = "ltr"; s2.textContent = pv.en;
          titleEl.appendChild(s2);
        }
      }
      if (metaEl) {
        if (edition === "bn") {
          metaEl.textContent = bnNum(em.chCount) + " অধ্যায় · " + bnNum(em.upaCount) + " উপাখ্যান (কালীপ্রসন্ন সিংহ)";
        } else if (edition === "en") {
          metaEl.textContent = bnNum(em.chCount) + " পরিচ্ছেদ (Kisari Mohan Ganguli)";
        } else {
          metaEl.textContent = bnNum(em.chCount) + " অধ্যায় · " + bnNum(em.shlokaCount) + " শ্লোক (সংস্কৃত মূল)";
        }
      }
    }
  }

  function refreshCrumb() {
    if (!crumbEl) return;
    var pv = parvaById(parvaId);
    if (!pv || scope !== "chapter") { crumbEl.hidden = true; return; }
    var unit = edition === "en" ? "পরিচ্ছেদ" : "অধ্যায়";
    var lbl = chapterId === 0 ? "ভূমিকা" : (unit + " " + bn(chapterId));
    crumbEl.hidden = false;
    crumbEl.innerHTML = '<button type="button" class="g-crumb-b" data-go="parva">' + esc(pv.bn) +
      '</button><span>›</span><b>' + esc(lbl) + '</b>';
    var b = crumbEl.querySelector("[data-go]");
    if (b) b.addEventListener("click", function () { showParvaView(parvaId); });
  }

  function setPrevNext() {
    if (!index) return;
    var pv = parvaById(parvaId);
    var ids = allChapterIds(pv, edition);
    var pos = -1;
    for (var i = 0; i < index.parvas.length; i++) {
      if (index.parvas[i].id === parvaId) { pos = i; break; }
    }
    var unit = edition === "en" ? "পরিচ্ছেদ" : "অধ্যায়";
    var idx = scope === "chapter" ? ids.indexOf(chapterId) : -1;
    var canPrev = (scope === "chapter" && idx > 0) || pos > 0;
    var canNext = (scope === "chapter" && idx >= 0 && idx < ids.length - 1) || (pos >= 0 && pos < index.parvas.length - 1);
    var pTxt = "‹ আগের", nTxt = "পরের ›";
    if (scope === "chapter" && idx > 0) {
      var pid = ids[idx - 1];
      pTxt = "‹ " + (pid === 0 ? "ভূমিকা" : unit + " " + bn(pid));
    } else if (pos > 0) {
      pTxt = "‹ " + index.parvas[pos - 1].bn;
    }
    if (scope === "chapter" && idx >= 0 && idx < ids.length - 1) {
      var nid = ids[idx + 1];
      nTxt = (nid === 0 ? "ভূমিকা" : unit + " " + bn(nid)) + " ›";
    } else if (pos >= 0 && pos < index.parvas.length - 1) {
      nTxt = index.parvas[pos + 1].bn + " ›";
    }
    if (prevBtn) { prevBtn.disabled = !canPrev; prevBtn.textContent = canPrev ? pTxt : "‹ আগের"; }
    if (nextBtn) { nextBtn.disabled = !canNext; nextBtn.textContent = canNext ? nTxt : "পরের ›"; }
  }

  /* ---------- রেন্ডারিং ---------- */
  function renderChapterContent(chObj) {
    if (!bodyEl) return;
    var unit = edition === "en" ? "পরিচ্ছেদ" : "অধ্যায়";
    var headTitle = (chObj.c === 0 ? "Translator's Preface" : (unit + " " + bn(chObj.c))) +
      (chObj.t ? " · " + chObj.t : "");
    var out = '<h3 class="g-sukta-h g-chap-h"><span class="g-sukta-n">' + esc(headTitle) + '</span>' +
      '<span class="g-sukta-m">' +
      (edition === "bn" ? bn(chObj.u.length) + " উপাখ্যান"
       : edition === "en" ? bn(chObj.p.length) + " অনুচ্ছেদ"
       : bn(chObj.v.length) + " শ্লোক") +
      '</span></h3>';

    if (edition === "bn") {
      out += chObj.u.map(function (u) {
        var blk = '<article class="g-mbh-upa">';
        if (u.b) blk += '<h4 class="g-mbh-upa-b">' + esc(u.b) + '</h4>';
        blk += u.p.map(function (p) {
          return '<p class="g-mbh-p">' + esc(p).replace(/\n+/g, "<br>") + '</p>';
        }).join("");
        blk += '</article>';
        return blk;
      }).join("");
      bodyEl.innerHTML = out;
      return;
    }

    if (edition === "en") {
      var prose = '<section class="g-prose-en" lang="en" dir="ltr">';
      prose += '<h4 class="g-prose-en-h">' + esc(chObj.t || ("Section " + chObj.c)) + '</h4>';
      if (chObj.s) prose += '<p class="g-prose-en-sub">' + esc(chObj.s) + '</p>';
      if (chObj.n) prose += '<div class="g-en-note"><b>Editorial Note:</b> ' + esc(chObj.n) + '</div>';
      prose += chObj.p.map(function (p) {
        return '<p class="g-prose-p">' + esc(p) + '</p>';
      }).join("");
      if (chObj.fn && chObj.fn.length) {
        prose += '<div class="g-prose-fn"><h4>Footnotes</h4>' +
          chObj.fn.map(function (fn) { return '<p>' + esc(fn) + '</p>'; }).join("") +
          '</div>';
      }
      prose += '</section>';
      bodyEl.innerHTML = out + prose;
      return;
    }

    /* সংস্কৃত (sa) */
    var cards = chObj.v.map(function (v) {
      return '<article class="g-v" id="v' + v.vn + '">' +
        '<div class="g-v-num" aria-hidden="true">' + bn(v.vn) + '</div>' +
        '<div class="g-v-body">' +
        (v.spk ? '<p class="g-v-spk">' + esc(v.spk) + '</p>' : "") +
        '<p class="g-v-sk" lang="sa">' + esc(v.sk).replace(/\n+/g, "<br>") + '</p>' +
        '</div></article>';
    });
    var token = ++loadToken;
    bodyEl.innerHTML = out;
    var at = 0, STEP = 150;
    (function paint() {
      if (token !== loadToken || !bodyEl.isConnected) return;
      bodyEl.insertAdjacentHTML("beforeend", cards.slice(at, at + STEP).join(""));
      at += STEP;
      if (at < cards.length) setTimeout(paint, 0);
    })();
  }

  /* ---------- পর্বের দৃশ্য ও অধ্যায় খোলা ---------- */
  function showParvaView(id) {
    parvaId = id;
    scope = "book";
    chapterId = 0;
    loadToken++;
    save({ parva: id, scope: "book", ed: edition });
    renderParvas();
    renderGrid();
    renderNote();
    refreshCrumb();
    syncHead(null);
    setPrevNext();
    syncFold();
    if (bodyEl && query.length < 2) {
      bodyEl.innerHTML = '<p class="g-empty g-pick">উপরের গ্রিড থেকে একটি ' +
        (edition === "en" ? "পরিচ্ছেদ" : "অধ্যায়") + ' বেছে নিন — সম্পূর্ণ পাঠ নিচে খুলবে।</p>';
    }
  }

  function openChapter(id) {
    var pv = parvaById(parvaId);
    if (!pv) return;
    chapterId = +id;
    scope = "chapter";
    var tok = ++loadToken;
    save({ parva: parvaId, ch: chapterId, scope: "chapter", ed: edition });
    renderParvas();
    renderGrid();
    renderNote();
    refreshCrumb();
    setPrevNext();
    syncFold();

    var ck = chunkForChapter(pv, edition, chapterId);
    if (!ck) {
      syncHead(null);
      if (titleEl) {
        titleEl.textContent = pv.bn + " · অধ্যায় " + bn(chapterId);
      }
      if (metaEl) metaEl.textContent = "ডিজিটাল বাংলা উৎসে অনুপস্থিত";
      bodyEl.innerHTML = '<p class="g-empty g-miss"><b>অধ্যায় ' + bn(chapterId) +
        '</b> (' + esc(pv.bn) + ') ডিজিটাল বাংলা উৎসে (কালীপ্রসন্ন সিংহ) অনুপস্থিত — ' +
        'অনুমান করে কিছু বসানো হয় না। উপরের <b>English (Ganguli)</b> বা <b>সংস্কৃত (মূল)</b> ' +
        'সংস্করণে এই অংশের পূর্ণ পাঠ পড়তে পারেন।</p>';
      return;
    }

    if (bodyEl) {
      bodyEl.innerHTML = window.EadSkeleton
        ? window.EadSkeleton.readerSkeleton({ cards: 4, head: false, label: "লোড হচ্ছে…" })
        : '<p class="g-loading">লোড হচ্ছে…</p>';
    }
    loadJSON(BASE + ck.f).then(function (data) {
      if (tok !== loadToken) return;
      var chObj = null;
      for (var i = 0; i < data.chs.length; i++) {
        if (+data.chs[i].c === +chapterId) { chObj = data.chs[i]; break; }
      }
      if (!chObj) {
        bodyEl.innerHTML = '<p class="g-empty">অধ্যায়টি পাওয়া যায়নি।</p>';
        return;
      }
      syncHead(chObj);
      renderChapterContent(chObj);
      try { window.scrollTo({ top: (gridEl || root).offsetTop - 90, behavior: "smooth" }); } catch (e) {}
    }).catch(function () {
      if (tok === loadToken && bodyEl) {
        bodyEl.innerHTML = '<p class="g-empty">অধ্যায়টি লোড করা গেল না। পুনরায় চেষ্টা করুন।</p>';
      }
    });
  }

  /* ---------- বর্তমান পর্বে সার্চ ---------- */
  function clip(txt, low) {
    if (!txt || txt.length <= 360) return txt || "";
    var i = txt.toLowerCase().indexOf(low);
    if (i < 0) return txt.slice(0, 280) + "…";
    var a = Math.max(0, i - 110), b = Math.min(txt.length, i + 230);
    return (a > 0 ? "…" : "") + txt.slice(a, b) + (b < txt.length ? "…" : "");
  }

  function runSearch() {
    var pv = parvaById(parvaId);
    var em = edMeta(pv, edition);
    if (!pv || !em || !bodyEl) return;
    var tok = ++loadToken;
    var q = query;
    var low = q.toLowerCase();
    bodyEl.innerHTML = window.EadSkeleton
      ? window.EadSkeleton.readerSkeleton({ cards: 3, head: false, label: "খোঁজা হচ্ছে…" })
      : '<p class="g-loading">খোঁজা হচ্ছে…</p>';
    Promise.all(em.chunks.map(function (ck) { return loadJSON(BASE + ck.f); })).then(function (lists) {
      if (tok !== loadToken) return;
      var rows = [], total = 0;
      lists.forEach(function (chunkData) {
        (chunkData.chs || []).forEach(function (ch) {
          var matches = [];
          if (edition === "bn") {
            (ch.u || []).forEach(function (u) {
              var allT = (u.b ? u.b + " — " : "") + (u.p || []).join(" ");
              if (allT.toLowerCase().indexOf(low) > -1) matches.push(clip(allT, low));
            });
          } else if (edition === "en") {
            (ch.p || []).forEach(function (p) {
              if (p.toLowerCase().indexOf(low) > -1) matches.push(clip(p, low));
            });
          } else {
            (ch.v || []).forEach(function (v) {
              if ((v.sk || "").toLowerCase().indexOf(low) > -1 || (v.spk || "").toLowerCase().indexOf(low) > -1) {
                matches.push((v.spk ? v.spk + ": " : "") + clip(v.sk, low));
              }
            });
          }
          if (!matches.length) return;
          total += matches.length;
          rows.push('<p class="g-hit-head">' + esc(pv.bn) + ' · ' +
            (ch.c === 0 ? "ভূমিকা" : "অধ্যায় " + bn(ch.c)) +
            ' · ' + bn(matches.length) + 'টি <button type="button" class="g-crumb-b" data-jump="' + ch.c + '">খুলুন →</button></p>');
          matches.slice(0, 6).forEach(function (txt) {
            rows.push('<article class="g-v hit"><div class="g-v-num">' + bn(ch.c) +
              '</div><div class="g-v-body"><p class="' + (edition === "sa" ? "g-v-sk" : edition === "en" ? "g-v-en" : "g-v-bn") +
              '"' + (edition === "en" ? ' lang="en" dir="ltr"' : "") + '>' + esc(txt) + '</p></div></article>');
          });
        });
      });
      bodyEl.innerHTML = rows.join("") || '<p class="g-empty">এই পর্বে কিছু মেলেনি। অন্য শব্দে বা অন্য সংস্করণে চেষ্টা করুন।</p>';
      bodyEl.querySelectorAll("[data-jump]").forEach(function (b) {
        b.addEventListener("click", function () {
          query = "";
          if (searchEl) searchEl.value = "";
          if (hitsEl) hitsEl.textContent = "";
          openChapter(+b.dataset.jump);
        });
      });
      if (titleEl) titleEl.textContent = pv.bn + " · খোঁজা: " + q;
      if (metaEl) metaEl.textContent = bn(total) + "টি মিল";
      if (hitsEl) hitsEl.textContent = total ? bn(total) + "টি মিল পাওয়া গেছে" : "কিছু মেলেনি";
    });
  }

  function step(d) {
    if (!index) return;
    var pv = parvaById(parvaId);
    var ids = allChapterIds(pv, edition);
    var pos = -1;
    for (var i = 0; i < index.parvas.length; i++) {
      if (index.parvas[i].id === parvaId) { pos = i; break; }
    }
    if (scope === "chapter") {
      var idx = ids.indexOf(chapterId);
      if (d > 0 && idx >= 0 && idx < ids.length - 1) return openChapter(ids[idx + 1]);
      if (d < 0 && idx > 0) return openChapter(ids[idx - 1]);
    }
    if (d > 0 && pos >= 0 && pos < index.parvas.length - 1) {
      var np = index.parvas[pos + 1];
      showParvaView(np.id);
      var nIds = allChapterIds(np, edition);
      return openChapter(nIds[0] || 1);
    }
    if (d < 0 && pos > 0) {
      var pp = index.parvas[pos - 1];
      showParvaView(pp.id);
      var pIds = allChapterIds(pp, edition);
      return openChapter(pIds[pIds.length - 1] || 1);
    }
  }

  function bind() {
    var sideToggle = document.getElementById("g-side-toggle");
    if (sideToggle) {
      sideToggle.addEventListener("click", function () {
        var side = document.getElementById("g-side");
        if (side) setFolded(!side.classList.contains("folded"), true);
      });
    }
    if (prevBtn) prevBtn.addEventListener("click", function () { step(-1); });
    if (nextBtn) nextBtn.addEventListener("click", function () { step(1); });
    var timer = 0;
    if (searchEl) {
      searchEl.addEventListener("input", function () {
        query = searchEl.value.trim();
        clearTimeout(timer);
        if (query.length >= 2) {
          timer = setTimeout(runSearch, 180);
        } else {
          if (hitsEl) hitsEl.textContent = "";
          if (scope === "chapter") openChapter(chapterId);
          else showParvaView(parvaId);
        }
      });
    }
  }

  /* ---------- শুরু ---------- */
  loadJSON(BASE + "index.json").then(function (d) {
    index = d;
    var st = saved();
    if (st.ed === "bn" || st.ed === "en" || st.ed === "sa") edition = st.ed;
    var h = location.hash || "";
    var hmEd = h.match(/ed=(bn|en|sa)/);
    if (hmEd) edition = hmEd[1];

    buildEditions();
    bind();
    syncStickTop();
    window.addEventListener("resize", function () {
      syncStickTop();
      var narrowNow = false;
      try { narrowNow = window.matchMedia && window.matchMedia("(max-width: 980px)").matches; } catch (e) {}
      if (!narrowNow) setFolded(false, false);
    });
    if (window.ResizeObserver) {
      var gBar = root.querySelector(".g-toolbar");
      if (gBar) new ResizeObserver(syncStickTop).observe(gBar);
    }
    var narrow = false;
    try { narrow = window.matchMedia && window.matchMedia("(max-width: 980px)").matches; } catch (e) {}
    if (narrow) setFolded(typeof st.fold === "boolean" ? st.fold : true, false);
    else setFolded(false, false);

    var mPC = h.match(/^#p(\d+)c(\d+)/);
    var mP  = h.match(/^#ch(\d+)/) || h.match(/^#p(\d+)$/);
    if (mPC && parvaById(+mPC[1])) {
      showParvaView(+mPC[1]);
      openChapter(+mPC[2]);
    } else if (mP && parvaById(+mP[1])) {
      showParvaView(+mP[1]);
    } else if (st.parva && parvaById(st.parva)) {
      showParvaView(st.parva);
      if (st.scope === "chapter" && st.ch != null) openChapter(st.ch);
    } else {
      showParvaView(1);
    }
  }).catch(function () {
    if (bodyEl) bodyEl.innerHTML = '<p class="g-empty">মহাভারতের সূচি লোড করা গেল না।</p>';
  });
})();
