/* ============================================================
   grantho-common.js — ধর্মগ্রন্থ পাঠকের শেয়ার্ড ইউটিলিটি ও ফিচার
   ------------------------------------------------------------
   grantho.js, bible-reader.js, mahabharata-reader.js ও english-bible-এর জন্য:
     · বাংলা সংখ্যা রূপান্তর, HTML এস্কেপিং ও safe localStorage
     · ফন্ট-সাইজ নিয়ন্ত্রণ (--g-scale, সর্বত্র মনে থাকে)
     · অধ্যায়/শ্লোক/পদ/গাথা/সূত্র বুকমার্ক ও কপি-বোতাম
     · সাইটব্যাপী সংরক্ষিত পাঠ তালিকা (কুরআন · হাদিস · গ্রন্থ · বাইবেল)
   ============================================================ */
(function (global) {
  "use strict";

  var BN_DIGITS = "০১২৩৪৫৬৭৮৯";
  var FS_KEY = "grantho.fontScale.v1";
  var BM_PREFIX = "grantho.bm.v1.";

  function bn(n) {
    return String(n).replace(/[0-9]/g, function (d) { return BN_DIGITS[+d]; });
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
  function storeGet(key, fallback) {
    try {
      var raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }
  function storeSet(key, val) {
    try { localStorage.setItem(key, JSON.stringify(val)); } catch (e) {}
  }

  function copyText(text, btn) {
    if (!text) return;
    var done = function () {
      if (!btn) return;
      btn.classList.add("on");
      var old = btn.getAttribute("data-old-title") || btn.title || "";
      if (!btn.getAttribute("data-old-title")) btn.setAttribute("data-old-title", old);
      btn.title = "কপি হয়েছে";
      clearTimeout(btn._copyTimer);
      btn._copyTimer = setTimeout(function () {
        btn.classList.remove("on");
        btn.title = btn.getAttribute("data-old-title") || "কপি";
      }, 1300);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, fallbackCopy);
    } else {
      fallbackCopy();
    }
    function fallbackCopy() {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.cssText = "position:fixed;left:-9999px;top:0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch (e) {}
      document.body.removeChild(ta);
      done();
    }
  }

  /* ---------- সাইটের মূল-পথ (relative links সব পাতায় ঠিক রাখতে) ---------- */
  function siteRootRel() {
    var path = (location && location.pathname) || "/";
    var clean = path.replace(/[^\/]*$/, "");
    /* /ead/grantho/hindu/ -> depth 2 after /ead/; fallback by script tag */
    var me = document.querySelector('script[src*="grantho-common.js"], script[src*="grantho.js"], script[src*="bible-reader.js"], script[src*="mahabharata-reader.js"]');
    if (me) {
      var src = me.getAttribute("src") || "";
      var m = src.match(/^((?:\.\.\/)+)/);
      if (m) return m[1];
    }
    if (/\/grantho\/[^/]+\//.test(clean)) return "../../";
    if (/\/grantho\//.test(clean)) return "../";
    return "";
  }

  /* ---------- ফন্টের আকার (৮৫% – ১৪৫%) ---------- */
  function initFontSize(root, bar) {
    if (!root || !bar) return null;
    var scale = 1;
    var saved = storeGet(FS_KEY, 1);
    if (typeof saved === "number" && saved >= 0.85 && saved <= 1.45) {
      scale = Math.round(saved * 100) / 100;
    }

    function apply(next, persist) {
      scale = Math.max(0.85, Math.min(1.45, Math.round(next * 10) / 10));
      root.style.setProperty("--g-scale", String(scale));
      if (valEl) valEl.textContent = bn(Math.round(scale * 100)) + "%";
      if (decBtn) decBtn.disabled = scale <= 0.86;
      if (incBtn) incBtn.disabled = scale >= 1.44;
      if (persist) storeSet(FS_KEY, scale);
    }

    var wrap = document.createElement("div");
    wrap.className = "g-fs";
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-label", "অক্ষরের আকার");
    wrap.innerHTML =
      '<button type="button" class="g-fs-btn" data-fs="-0.1" aria-label="অক্ষর ছোট করুন" title="অক্ষর ছোট করুন">অ-</button>' +
      '<span class="g-fs-val" aria-live="polite"></span>' +
      '<button type="button" class="g-fs-btn" data-fs="0.1" aria-label="অক্ষর বড় করুন" title="অক্ষর বড় করুন">অ+</button>';

    var hits = bar.querySelector(".g-hits");
    if (hits && hits.parentNode === bar) bar.insertBefore(wrap, hits);
    else bar.appendChild(wrap);

    var decBtn = wrap.querySelector('[data-fs="-0.1"]');
    var incBtn = wrap.querySelector('[data-fs="0.1"]');
    var valEl = wrap.querySelector(".g-fs-val");

    wrap.addEventListener("click", function (e) {
      var b = e.target.closest && e.target.closest("[data-fs]");
      if (!b) return;
      apply(scale + parseFloat(b.dataset.fs), true);
    });
    apply(scale, false);
    return {
      get: function () { return scale; },
      set: function (v) { apply(v, true); }
    };
  }

  /* ---------- সাইটব্যাপী সংরক্ষিত পাঠ সংগ্রহ ---------- */
  var SLUG_NAMES = {
    "gita": "ভগবদ্গীতা",
    "rigveda": "ঋগ্বেদ",
    "samaveda": "সামবেদ",
    "yajurveda-shukla": "শুক্ল যজুর্বেদ",
    "atharvaveda": "অথর্ববেদ",
    "shvetashvatara": "শ্বেতাশ্বতর উপনিষদ",
    "prashna": "প্রশ্ন উপনিষদ",
    "chandogya": "ছান্দোগ্য উপনিষদ",
    "brihadaranyaka": "বৃহদারণ্যক উপনিষদ",
    "mahabharata": "মহাভারত",
    "bible": "বাংলা বাইবেল",
    "english-bible": "English Bible",
    "dhammapada": "ধম্মপদ",
    "digha-nikaya": "দীর্ঘ নিকায়",
    "majjhima-nikaya": "মধ্যম নিকায়",
    "samyutta-nikaya": "সংযুক্ত নিকায়",
    "anguttara-nikaya": "অঙ্গুত্তর নিকায়",
    "vinaya-vibhanga": "ভিক্ষু বিভঙ্গ"
  };

  function collectAllBookmarks() {
    var out = [];
    try {
      var qBm = storeGet("quran:bookmarks", []);
      if (Array.isArray(qBm)) {
        for (var qi = qBm.length - 1; qi >= 0; qi--) {
          var qid = String(qBm[qi]);
          var qp = qid.split(":");
          out.push({
            source: "quran",
            sourceLabel: "কুরআন",
            key: "quran:bookmarks",
            rawId: qid,
            title: "সূরা " + bn(qp[0] || "") + " · আয়াত " + bn(qp[1] || ""),
            url: "quran.html#" + qid
          });
        }
      }
      var hBm = storeGet("hadith:bookmarks", []);
      if (Array.isArray(hBm)) {
        for (var hi = hBm.length - 1; hi >= 0; hi--) {
          var hid = String(hBm[hi]);
          var hp = hid.split(":");
          var ch = hp.length >= 3 ? hp[1] : "1";
          var num = hp.length >= 3 ? hp[2] : hp[1];
          out.push({
            source: "hadith",
            sourceLabel: "হাদিস",
            key: "hadith:bookmarks",
            rawId: hid,
            title: (hp[0] || "") + " · হাদিস " + bn(num || ""),
            url: "hadith.html#" + (hp[0] || "") + ":" + ch
          });
        }
      }
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (!k || k.indexOf(BM_PREFIX) !== 0) continue;
        var slug = k.slice(BM_PREFIX.length);
        var arr = storeGet(k, []);
        if (!Array.isArray(arr)) continue;
        for (var j = arr.length - 1; j >= 0; j--) {
          var it = arr[j];
          if (!it || !it.id) continue;
          out.push({
            source: slug,
            sourceLabel: SLUG_NAMES[slug] || slug,
            key: k,
            rawId: it.id,
            title: it.label || it.ref || it.id,
            url: it.url || ""
          });
        }
      }
    } catch (e) {}
    return out;
  }

  /* ---------- বুকমার্ক ম্যানেজার ---------- */
  function initBookmarks(opts) {
    var root = opts.root;
    var bar = opts.bar || (root && root.querySelector(".g-toolbar"));
    var slug = opts.slug || "grantho";
    var storeKey = BM_PREFIX + slug;
    var items = storeGet(storeKey, []);
    if (!Array.isArray(items)) items = [];

    var panelTab = "book"; // "book" | "all"
    var bmBtn = null, bmPanel = null;

    function findIdx(id) {
      for (var i = 0; i < items.length; i++) {
        if (items[i] && items[i].id === id) return i;
      }
      return -1;
    }

    function has(id) { return findIdx(id) !== -1; }

    function saveList() { storeSet(storeKey, items); }

    function updateBadge() {
      if (!bmBtn) return;
      var cnt = bmBtn.querySelector(".g-bm-cnt");
      if (cnt) cnt.textContent = items.length ? " (" + bn(items.length) + ")" : "";
    }

    function removeByRaw(key, rawId) {
      var list = storeGet(key, []);
      if (!Array.isArray(list)) return;
      var next;
      if (key === storeKey) {
        items = items.filter(function (x) { return x && x.id !== rawId; });
        saveList();
        syncVisibleButtons();
        updateBadge();
      } else if (key.indexOf(BM_PREFIX) === 0) {
        next = list.filter(function (x) { return x && x.id !== rawId; });
        storeSet(key, next);
      } else {
        next = list.filter(function (x) { return String(x) !== String(rawId); });
        storeSet(key, next);
      }
      renderPanel();
    }

    function syncVisibleButtons() {
      if (!root) return;
      root.querySelectorAll("[data-bm]").forEach(function (b) {
        var on = has(b.getAttribute("data-bm"));
        b.classList.toggle("on", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
        var card = b.closest(".g-v, .g-mbh-upa, .g-prose-en, .e-v");
        if (card) card.classList.toggle("bm", on);
      });
    }

    function toggle(entry) {
      if (!entry || !entry.id) return false;
      var idx = findIdx(entry.id);
      var added = idx === -1;
      if (added) items.push(entry);
      else items.splice(idx, 1);
      saveList();
      updateBadge();
      syncVisibleButtons();
      if (bmPanel && !bmPanel.hidden) renderPanel();
      return added;
    }

    function renderPanel() {
      if (!bmPanel) return;
      var relPrefix = siteRootRel();
      var allItems = collectAllBookmarks();
      var head =
        '<div class="g-bm-head">' +
          '<div class="g-bm-tabs" role="tablist">' +
            '<button type="button" role="tab" class="g-bm-tab' + (panelTab === "book" ? " on" : "") + '" data-bmtab="book" aria-selected="' + (panelTab === "book" ? "true" : "false") + '">এই গ্রন্থ (' + bn(items.length) + ')</button>' +
            '<button type="button" role="tab" class="g-bm-tab' + (panelTab === "all" ? " on" : "") + '" data-bmtab="all" aria-selected="' + (panelTab === "all" ? "true" : "false") + '">সব সংরক্ষিত (' + bn(allItems.length) + ')</button>' +
          '</div>' +
          '<button type="button" class="g-bm-close" aria-label="বুকমার্ক প্যানেল বন্ধ করুন" title="বন্ধ করুন">✕</button>' +
        '</div>';

      var body = "";
      if (panelTab === "book") {
        if (!items.length) {
          body = '<p class="g-bm-empty">এখনো কিছু বুকমার্ক করা হয়নি। প্রতিটি পাঠের পাশের বুকমার্ক আইকনে চাপুন।</p>';
        } else {
          body = '<div class="g-bm-list">' + items.slice().reverse().map(function (it) {
            return '<div class="g-bm-row">' +
              '<button type="button" class="g-bm-go" data-bm-go="' + esc(it.id) + '">' +
                '<span class="g-bm-ref">' + esc(it.ref || it.label) + '</span>' +
                (it.snippet ? '<span class="g-bm-snip">' + esc(it.snippet) + '</span>' : '') +
              '</button>' +
              '<button type="button" class="g-bm-del" data-bm-del="' + esc(storeKey) + '" data-bm-id="' + esc(it.id) + '" aria-label="মুছুন" title="বুকমার্ক মুছুন">✕</button>' +
            '</div>';
          }).join("") + '</div>';
        }
      } else {
        if (!allItems.length) {
          body = '<p class="g-bm-empty">সাইটের কোথাও এখনো বুকমার্ক যোগ করা হয়নি।</p>';
        } else {
          body = '<div class="g-bm-list">' + allItems.map(function (it) {
            var targetHref = it.url ? (relPrefix + it.url) : "#";
            var sameBook = it.source === slug;
            return '<div class="g-bm-row">' +
              (sameBook
                ? '<button type="button" class="g-bm-go" data-bm-go="' + esc(it.rawId) + '">'
                : '<a class="g-bm-go" href="' + esc(targetHref) + '">') +
                '<span class="g-bm-badge">' + esc(it.sourceLabel) + '</span>' +
                '<span class="g-bm-ref">' + esc(it.title) + '</span>' +
              (sameBook ? '</button>' : '</a>') +
              '<button type="button" class="g-bm-del" data-bm-del="' + esc(it.key) + '" data-bm-id="' + esc(it.rawId) + '" aria-label="মুছুন" title="বুকমার্ক মুছুন">✕</button>' +
            '</div>';
          }).join("") + '</div>';
        }
      }
      bmPanel.innerHTML = head + body;
    }

    if (bar && root) {
      bmBtn = document.createElement("button");
      bmBtn.type = "button";
      bmBtn.className = "g-btn g-bm-toggle";
      bmBtn.id = "g-bm-btn";
      bmBtn.setAttribute("aria-expanded", "false");
      bmBtn.innerHTML = '<svg class="g-ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12v18l-6-4-6 4z"/></svg><span>বুকমার্ক</span><span class="g-bm-cnt"></span>';
      var hits = bar.querySelector(".g-hits");
      if (hits && hits.parentNode === bar) bar.insertBefore(bmBtn, hits);
      else bar.appendChild(bmBtn);

      bmPanel = document.createElement("div");
      bmPanel.className = "g-bm-panel";
      bmPanel.id = "g-bm-panel";
      bmPanel.hidden = true;
      bar.parentNode.insertBefore(bmPanel, bar.nextSibling);

      bmBtn.addEventListener("click", function () {
        var open = bmPanel.hidden;
        bmPanel.hidden = !open;
        bmBtn.classList.toggle("on", open);
        bmBtn.setAttribute("aria-expanded", open ? "true" : "false");
        if (open) renderPanel();
      });

      bmPanel.addEventListener("click", function (e) {
        var tab = e.target.closest && e.target.closest("[data-bmtab]");
        if (tab) {
          panelTab = tab.getAttribute("data-bmtab");
          renderPanel();
          return;
        }
        if (e.target.closest && e.target.closest(".g-bm-close")) {
          bmPanel.hidden = true;
          bmBtn.classList.remove("on");
          bmBtn.setAttribute("aria-expanded", "false");
          return;
        }
        var del = e.target.closest && e.target.closest("[data-bm-del]");
        if (del) {
          removeByRaw(del.getAttribute("data-bm-del"), del.getAttribute("data-bm-id"));
          return;
        }
        var go = e.target.closest && e.target.closest("[data-bm-go]");
        if (go) {
          var gid = go.getAttribute("data-bm-go");
          var found = items[findIdx(gid)];
          bmPanel.hidden = true;
          bmBtn.classList.remove("on");
          bmBtn.setAttribute("aria-expanded", "false");
          if (found && typeof opts.onOpen === "function") opts.onOpen(found);
        }
      });

      updateBadge();
    }

    return {
      has: has,
      toggle: toggle,
      sync: syncVisibleButtons,
      list: function () { return items.slice(); },
      iconHTML: function (id, isOn) {
        return '<span class="g-v-tools">' +
          '<button type="button" class="g-v-icon' + (isOn ? " on" : "") + '" data-bm="' + esc(id) + '" aria-label="বুকমার্ক" aria-pressed="' + (isOn ? "true" : "false") + '" title="বুকমার্ক"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12v18l-6-4-6 4z"/></svg></button>' +
          '<button type="button" class="g-v-icon" data-copy="' + esc(id) + '" aria-label="কপি" title="কপি"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg></button>' +
          '</span>';
      }
    };
  }

  /* ---------- কীবোর্ড নেভিগেশন (← / → অধ্যায়/পর্ব বদল) ---------- */
  function bindArrowNav(onStep) {
    if (typeof onStep !== "function") return;
    document.addEventListener("keydown", function (e) {
      if (document.documentElement.classList.contains("ss-open")) return;
      var t = e.target;
      if (t && (/INPUT|TEXTAREA|SELECT/.test(t.tagName) || t.isContentEditable)) return;
      if (t && t.closest && t.closest(".g-side")) return;
      if (e.key === "ArrowLeft") onStep(-1);
      else if (e.key === "ArrowRight") onStep(1);
    });
  }

  global.GranthoCommon = {
    bn: bn,
    comma: comma,
    bnNum: bnNum,
    esc: esc,
    storeGet: storeGet,
    storeSet: storeSet,
    copyText: copyText,
    collectAllBookmarks: collectAllBookmarks,
    initFontSize: initFontSize,
    initBookmarks: initBookmarks,
    bindArrowNav: bindArrowNav
  };
})(window);
