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
  var bnNoteEl = document.getElementById("g-bn-note");
  /* গীতা/পুরাণে «শ্লোক», বেদ-উপনিষদে «মন্ত্র» — index.json-এর verseWord থেকে */
  var VW = "শ্লোক";
  var state = { bn: true, sk: true, q: "", onlyBn: false };
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

  /* ---------- অধ্যায়-তালিকা ---------- */
  function renderChapters() {
    if (!listEl || !index) return;
    listEl.innerHTML = index.chapters.map(function (c) {
      var on = c.id === chapterId;
      var meta = bn(c.count) + " " + VW;
      if (c.suktaCount) meta += " · " + bn(c.suktaCount) + " সূক্ত";
      else if (c.from && c.to && c.count > 1) meta += " · " + bn(c.from) + " – " + bn(c.to) + " নং";
      return '<button class="g-ch' + (on ? " on" : "") + '" type="button" data-ch="' + c.id + '"' +
        (on ? ' aria-current="true"' : "") + '>' +
        '<span class="num">' + bn(c.id) + '</span>' +
        '<span class="txt"><span class="nm">' + esc(c.bn) + '</span>' +
        '<span class="meta">' + meta + '</span></span></button>';
    }).join("");
    listEl.querySelectorAll("[data-ch]").forEach(function (b) {
      b.addEventListener("click", function () { openChapter(+b.dataset.ch); });
    });
    if (totalEl) totalEl.textContent = bnNum(index.total) + " " + VW + " · " + bn(index.chapters.length) + " অধ্যায়";
  }

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
    var hit = q && ((v.sk || "").toLowerCase().indexOf(q) > -1 || (v.bn || "").toLowerCase().indexOf(q) > -1);
    var la = (typeof v.n === "number") ? v.n : 0;
    var sk = (v.sk || "").replace(/\n+/g, "<br>");
    var parts = state.bn ? (cuts[la] || null) : null;
    var out = '<article class="g-v' + (hit ? " hit" : "") + '" id="v' + v.n + '">';
    out += '<div class="g-v-num" aria-hidden="true">' + bn(v.n) + '</div><div class="g-v-body">';
    if (v.spk && state.sk) out += '<p class="g-v-spk">' + esc(v.spk) + '</p>';
    if (state.sk && sk) out += '<p class="g-v-sk" lang="sa">' + sk + '</p>';
    if (parts) {
      out += '<div class="g-v-padas">';
      out += parts.map(function (x, i) {
        return '<p class="g-v-bn g-v-pada"><span class="g-pada-n">' +
          bn(i + 1) + '</span>' + esc(x) + '</p>';
      }).join("");
      out += '</div>';
    } else if (state.bn && v.bn) {
      out += '<p class="g-v-bn">' + esc(v.bn).replace(/\n+/g, "</p><p class=\"g-v-bn\">") + '</p>';
    }
    /* উৎস-কৃতিত্ব গ্রন্থের শুরুতে একবারই — প্রতি মন্ত্রে পুনরাবৃত্তি নয় */
    out += '</div></article>';
    return out;
  }

  /* সার্চ পুরো গ্রন্থ জুড়ে — একবার সব অধ্যায় এনে মিলিয়ে রাখি */
  var allLoaded = null;
  function loadAll() {
    if (allLoaded) return Promise.resolve(allLoaded);
    return Promise.all(index.chapters.map(function (c) {
      return loadJSON(BASE + "ch" + c.id + ".json");
    })).then(function (list) { allLoaded = list; return list; });
  }

  function searchHTML(q) {
    var low = q.toLowerCase(), rows = [], total = 0;
    allLoaded.forEach(function (c) {
      var hit = c.verses.filter(function (v) {
        return (v.sk || "").toLowerCase().indexOf(low) > -1 ||
               (v.bn || "").toLowerCase().indexOf(low) > -1;
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
        return out + "</div></article>";
      }).join(""));
    });
    return { html: rows.join("") || '<p class="g-empty">কিছু মেলেনি। অন্য শব্দে চেষ্টা করুন।</p>', total: total };
  }

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

    var list = chapter.verses;
    if (state.onlyBn) list = list.filter(function (v) { return v.bn; });

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
    var html = "", curS = null, sMeta = {};
    if (hasS) {
      chapter.suktas.forEach(function (x) { sMeta[x.id] = x; });
      list.forEach(function (v) {
        var sid = inSukta[v.n];
        if (sid && sid !== curS) {
          curS = sid;
          var sm = sMeta[sid] || {};
          html += '<h3 class="g-sukta-h" id="sukta' + sid + '">' +
            '<span class="g-sukta-n">সূক্ত ' + bn(sid) + '</span>' +
            '<span class="g-sukta-m">' + VW + " " + bn(sm.from) + "–" + bn(sm.to) +
            (sm.shloka ? " · " + bn(sm.shloka) + " শ্লোক" : "") + '</span></h3>';
        }
        html += verseHTML(v);
      });
    } else {
      html = list.map(verseHTML).join("");
    }
    bodyEl.innerHTML = html || '<p class="g-empty">কিছু পাওয়া যায়নি।</p>';
    if (titleEl) titleEl.textContent = chapter.bn;
    if (metaEl) {
      var mm = bn(chapter.count) + " " + VW;
      if (hasS) mm += " · " + bn(chapter.suktaCount || 0) + " সূক্ত";
      metaEl.textContent = mm;
    }
    var hits = bodyEl.querySelectorAll(".g-v.hit").length;
    if (searchEl) {
      var note = document.getElementById("g-hits");
      if (note) note.textContent = state.q ? (hits ? bn(hits) + "টি " + VW + " পাওয়া গেছে" : "কিছু মেলেনি") : "";
    }
  }

  /* ---------- অধ্যায় খোলা ---------- */
  function openChapter(id) {
    chapterId = id;
    save({ last: id });
    renderChapters();
    bodyEl.innerHTML = '<p class="g-loading">লোড হচ্ছে…</p>';
    loadJSON(BASE + "ch" + id + ".json").then(function (c) {
      if (chapterId !== id) return;
      chapter = c;
      renderVerses();
      try { window.scrollTo({ top: root.offsetTop - 70, behavior: "smooth" }); } catch (e) {}
      var h = location.hash;
      if (h && /^#v?\d+$/.test(h)) {
        var el = document.getElementById("v" + h.replace("#v", "").replace("#", ""));
        if (el) el.scrollIntoView({ block: "center" });
      }
    }).catch(function () {
      bodyEl.innerHTML = '<p class="g-empty">অধ্যায়টি লোড করা গেল না। পুনরায় চেষ্টা করুন।</p>';
    });
  }

  /* ---------- নিয়ন্ত্রণ ---------- */
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
    var prev = document.getElementById("g-prev"), next = document.getElementById("g-next");
    if (prev) prev.addEventListener("click", function () { if (chapterId > 1) openChapter(chapterId - 1); });
    if (next) next.addEventListener("click", function () {
      if (index && chapterId < index.chapters.length) openChapter(chapterId + 1);
    });
  }

  /* ---------- শুরু ---------- */
  var st = saved();
  if (typeof st.sk === "boolean") state.sk = st.sk;
  if (typeof st.bn === "boolean") state.bn = st.bn;
  if (typeof st.onlyBn === "boolean") state.onlyBn = st.onlyBn;
  var skBtn0 = document.getElementById("g-sk-btn"), bnBtn0 = document.getElementById("g-bn-btn");
  if (skBtn0) { skBtn0.classList.toggle("on", state.sk); skBtn0.setAttribute("aria-pressed", state.sk ? "true" : "false"); }
  if (bnBtn0) { bnBtn0.classList.toggle("on", state.bn); bnBtn0.setAttribute("aria-pressed", state.bn ? "true" : "false"); }
  if (onlyBnEl) onlyBnEl.checked = state.onlyBn;

  loadJSON(BASE + "index.json").then(function (d) {
    index = d;
    if (d.verseWord) VW = d.verseWord;
    bind();
    var start = 1;
    var m = (location.hash || "").match(/^#ch(\d+)$/);
    if (m) start = +m[1];
    else if (st.last && d.chapters.some(function (c) { return c.id === st.last; })) start = st.last;
    renderChapters();
    openChapter(start);
  }).catch(function () {
    bodyEl.innerHTML = '<p class="g-empty">সূচি লোড করা গেল না।</p>';
  });
})();
