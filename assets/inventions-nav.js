/* ============================================================
   inventions-nav.js — দীর্ঘ প্রবন্ধে (muslim-inventions)
   দ্রুত বিষয়-নেভিগেশন ও তাৎক্ষণিক কীওয়ার্ড ফিল্টার
   ============================================================ */
(function () {
  "use strict";
  var bar = document.getElementById("inv-bar");
  var article = document.querySelector(".article-body");
  if (!bar || !article) return;

  var rm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var BN_D = ["০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯"];
  function bn(n) { return String(n).replace(/[0-9]/g, function (d) { return BN_D[+d]; }); }
  function norm(s) {
    s = (s || "").toString();
    if (s.normalize) s = s.normalize("NFC");
    return s.toLowerCase()
      .replace(/\u09c0/g, "\u09bf")
      .replace(/\u09c2/g, "\u09c1")
      .replace(/\u09bc/g, "")
      .replace(/\u09df/g, "\u09af")
      .replace(/\u09ce/g, "\u09a4")
      .replace(/[\u200c\u200d]/g, "");
  }

  /* <h2> ভিত্তিক ভার্চুয়াল সেকশন তালিকা — DOM কাঠামো বদলায় না */
  var sections = [];
  var cur = null;
  var nodes = Array.prototype.slice.call(article.children);
  nodes.forEach(function (el) {
    if (el.tagName === "H2") {
      cur = { id: el.id || "", title: el.textContent.replace(/\s+/g, " ").trim(), h2: el, els: [], items: [] };
      sections.push(cur);
    } else if (cur) {
      cur.els.push(el);
      if (el.tagName === "UL" || el.tagName === "OL") {
        Array.prototype.forEach.call(el.children, function (li) {
          cur.items.push({ el: li, txt: norm(li.textContent) });
        });
      }
    }
  });
  if (!sections.length) return;

  var totalItems = sections.reduce(function (s, x) { return s + x.items.length; }, 0);

  function shortLabel(title) {
    var m = title.match(/^([০-৯]+\.\s*[^,ঃ:]+)/);
    if (m) return m[1].trim();
    if (/সূচিপত্র/.test(title)) return "সূচি";
    if (/ভূমিকা/.test(title)) return "ভূমিকা";
    if (/পতনের/.test(title)) return "পতনের বিতর্ক";
    if (/নির্দেশিকা/.test(title)) return "নির্দেশিকা";
    if (/পদ্ধতির/.test(title)) return "পদ্ধতি";
    if (/উপসংহার/.test(title)) return "উপসংহার";
    if (/গ্রন্থপঞ্জি/.test(title)) return "গ্রন্থপঞ্জি";
    var p = title.match(/^পরিশিষ্ট\s*[০-৯]+/);
    if (p) return p[0];
    return title.slice(0, 18);
  }

  /* পিল তালিকা — মূল অধ্যায়গুলো অগ্রাধিকার */
  var pillSecs = sections.filter(function (s) {
    return /^[০-৯]+\./.test(s.title) || /ভূমিকা|উপসংহার|পরিশিষ্ট/.test(s.title);
  });

  bar.innerHTML =
    '<div class="inv-top">' +
      '<input type="search" class="inv-search" id="inv-search" placeholder="বিষয়, বিজ্ঞানী বা আবিষ্কার খুঁজুন (যেমন: আল-খোয়ারিজমি, হাসপাতাল, চক্ষু)…" aria-label="প্রবন্ধের ভেতরে খুঁজুন" autocomplete="off">' +
      '<span class="inv-stat" id="inv-stat"></span>' +
      '<button type="button" class="inv-clear" id="inv-clear" hidden>পরিষ্কার</button>' +
    '</div>' +
    '<div class="inv-pills" role="navigation" aria-label="বিষয়ভিত্তিক দ্রুত লাফ">' +
      '<button type="button" class="inv-pill on" data-inv-sec="all">সব দেখান</button>' +
      pillSecs.map(function (s) {
        return '<button type="button" class="inv-pill" data-inv-sec="' + s.id + '">' + shortLabel(s.title) + '</button>';
      }).join("") +
    '</div>';

  var emptyMsg = document.createElement("p");
  emptyMsg.className = "inv-empty";
  emptyMsg.hidden = true;
  emptyMsg.textContent = "কোনো মিল পাওয়া যায়নি। অন্য শব্দে চেষ্টা করুন বা «পরিষ্কার» বোতামে চাপুন।";
  article.appendChild(emptyMsg);

  var inp = document.getElementById("inv-search");
  var stat = document.getElementById("inv-stat");
  var clr = document.getElementById("inv-clear");
  var pillsWrap = bar.querySelector(".inv-pills");
  var activeSec = "all";

  function setStat(secCnt, itemCnt, filtering) {
    if (!filtering) {
      stat.textContent = bn(sections.length) + " অধ্যায় · " + bn(totalItems) + " ভুক্তি";
    } else {
      stat.textContent = bn(secCnt) + " অধ্যায় · " + bn(itemCnt) + "টি মিল";
    }
  }
  setStat(sections.length, totalItems, false);

  function applyFilter() {
    var q = norm(inp.value.trim());
    var hasFilter = !!q || activeSec !== "all";
    clr.hidden = !hasFilter;

    var shownSecs = 0, shownItems = 0;
    sections.forEach(function (sec) {
      var secMatch = activeSec === "all" || sec.id === activeSec;
      var anyVisible = false;

      if (!secMatch) {
        sec.h2.hidden = true;
        sec.els.forEach(function (el) { el.hidden = true; });
        return;
      }

      if (!q) {
        sec.h2.hidden = false;
        sec.els.forEach(function (el) { el.hidden = false; });
        sec.items.forEach(function (it) { it.el.hidden = false; });
        shownSecs++;
        shownItems += sec.items.length;
        return;
      }

      var headMatch = norm(sec.title).indexOf(q) !== -1;
      sec.els.forEach(function (el) {
        if (el.tagName === "UL" || el.tagName === "OL") {
          var ulVis = 0;
          Array.prototype.forEach.call(el.children, function (li) {
            var hit = headMatch || norm(li.textContent).indexOf(q) !== -1;
            li.hidden = !hit;
            if (hit) { ulVis++; shownItems++; }
          });
          el.hidden = ulVis === 0;
          if (ulVis > 0) anyVisible = true;
        } else {
          var pHit = headMatch || norm(el.textContent).indexOf(q) !== -1;
          el.hidden = !pHit;
          if (pHit) anyVisible = true;
        }
      });
      sec.h2.hidden = !anyVisible && !headMatch;
      if (!sec.h2.hidden) shownSecs++;
    });

    emptyMsg.hidden = shownSecs > 0;
    setStat(shownSecs, shownItems, hasFilter);
  }

  var timer = null;
  inp.addEventListener("input", function () {
    clearTimeout(timer);
    timer = setTimeout(applyFilter, 110);
  });

  clr.addEventListener("click", function () {
    inp.value = "";
    activeSec = "all";
    bar.querySelectorAll("[data-inv-sec]").forEach(function (b) {
      b.classList.toggle("on", b.getAttribute("data-inv-sec") === "all");
    });
    applyFilter();
  });

  pillsWrap.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest("[data-inv-sec]");
    if (!btn) return;
    var targetId = btn.getAttribute("data-inv-sec");
    bar.querySelectorAll("[data-inv-sec]").forEach(function (b) {
      b.classList.toggle("on", b === btn);
    });
    if (targetId === "all") {
      activeSec = "all";
      applyFilter();
      return;
    }
    /* যদি সার্চ না থাকে, পিল চাপে ঐ অধ্যায়ে মসৃণ লাফ + ফিল্টার-পুনর্গঠন ছাড়াই */
    if (!inp.value.trim() && activeSec === "all") {
      var h = document.getElementById(targetId);
      if (h) {
        var top = h.getBoundingClientRect().top + window.pageYOffset - 165;
        window.scrollTo({ top: Math.max(0, top), behavior: rm ? "auto" : "smooth" });
        if (history.replaceState) history.replaceState(null, "", "#" + targetId);
        return;
      }
    }
    activeSec = targetId;
    applyFilter();
  });
})();
