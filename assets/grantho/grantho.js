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

  /* ---------- অধ্যায়-তালিকা ---------- */
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
    if (hasS) {
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
    } else {
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
    if (titleEl) titleEl.textContent = chapter.bn;
    if (metaEl) {
      var mm = bn(chapter.count) + " " + VW;
      if (hasS) mm += " · " + bn(chapter.suktaCount || 0) + " " + GW;
      if (chapter.preface || chapter.heading) mm += " · অনুক্রমণিকা সহ";
      var enCount = Object.keys(enMap(chapterEn)).length;
      if (enCount) {
        mm += " · ইংরেজি " + bn(enCount) + " পদে";
      }
      metaEl.textContent = mm;
    }
    if (langBox) langBox.hidden = !chapterEn;
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
  }

  /* ---------- অধ্যায় খোলা ---------- */
  function openChapter(id) {
    chapterId = id;
    paintToken++;
    save({ last: id });
    renderChapters();
    bodyEl.innerHTML = '<p class="g-loading">লোড হচ্ছে…</p>';
    Promise.all([
      loadJSON(BASE + "ch" + id + ".json"),
      loadJSON(BASE + "en/ch" + id + ".json").catch(function () { return null; })
    ]).then(function (r) {
      if (chapterId !== id) return;
      chapter = r[0]; chapterEn = r[1];
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
    buildLangBox();
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
