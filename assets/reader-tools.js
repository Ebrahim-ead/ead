/* ============================================================
   reader-tools.js — দীর্ঘ প্রবন্ধের পাঠ-সহায়ক
   ------------------------------------------------------------
   • সূচিপত্র: প্রবন্ধের প্রতিটি <h2>-কে id দিয়ে ডান পাশে ভাসমান
     একটা সংক্ষিপ্ত সূচি বানায়; স্ক্রল করলে কোন অংশে আছেন তা দেখায়
     ও উপরে একটা সরু অগ্রগতি-রেখা ভরে। চওড়া পর্দায় (≥1240px) দেখা যায়,
     স্পর্শ-পর্দা/ছোট পর্দায় কিছুই যোগ হয় না।
   • উদ্ধৃতি-কপি: লেখকের নাম, শিরোনাম ও লিংক এক ক্লিকে কপি —
     সূত্র উল্লেখ করে কেউ সহজে শেয়ার করতে পারে।

   কোনো HTML বদলাতে হয় না: সব নিজে থেকেই যোগ হয়, JS না চললে
   পাঠ হুবহু আগের মতোই থাকে। prefers-reduced-motion মানা হয়।
   ============================================================ */
(function () {
  "use strict";

  var doc = document;
  var body = doc.querySelector(".article-body");
  if (!body) return;

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");

  /* ------------------------------------------------------ *
   * ১) প্রতিটি h2-তে স্থিতিশীল id (আগে থেকে থাকলে ছোঁব না)
   * ------------------------------------------------------ */
  function slugify(text, i) {
    var t = text.trim().toLowerCase()
      .replace(/[\s\u200c\u200d]+/g, "-")
      .replace(/[^\u0980-\u09FFa-z0-9-]/g, "")
      .replace(/-{2,}/g, "-")
      .replace(/^-|-$/g, "");
    return "sec-" + (i + 1) + (t ? "-" + t.slice(0, 40) : "");
  }

  var heads = [].slice.call(body.querySelectorAll("h2"));
  if (heads.length < 3) return; /* ছোট লেখায় সূচি দরকার নেই */

  var used = Object.create(null);
  heads.forEach(function (h, i) {
    var text = h.textContent.replace(/\s+/g, " ").trim();
    if (!text) return;
    var id = h.id || slugify(text, i);
    while (used[id]) id += "-x";
    used[id] = true;
    h.id = id;
  });
  heads = heads.filter(function (h) { return h.id; });

  /* ------------------------------------------------------ *
   * ২) ডান পাশের সূচিপত্র
   * ------------------------------------------------------ */
  var toc = doc.createElement("nav");
  toc.className = "rd-toc";
  toc.setAttribute("aria-label", "এই নিবন্ধের সূচিপত্র");

  var head = doc.createElement("div");
  head.className = "rd-toc-head";
  head.innerHTML = '<b>সূচিপত্র</b><span class="rd-toc-count">' + bn(heads.length) + '</span>';
  toc.appendChild(head);

  var barWrap = doc.createElement("div");
  barWrap.className = "rd-toc-bar";
  var bar = doc.createElement("i");
  barWrap.appendChild(bar);
  toc.appendChild(barWrap);

  var list = doc.createElement("ol");
  var links = heads.map(function (h) {
    var li = doc.createElement("li");
    var a = doc.createElement("a");
    a.href = "#" + h.id;
    a.textContent = h.textContent.replace(/\s+/g, " ").trim();
    a.addEventListener("click", function (e) {
      /* মসৃণ স্ক্রল নিজে করি, যাতে হেডারের নিচে ঠিক জায়গায় থামে */
      e.preventDefault();
      var top = h.getBoundingClientRect().top + window.pageYOffset - 84;
      window.scrollTo({ top: top, behavior: reduced.matches ? "auto" : "smooth" });
      if (history.replaceState) history.replaceState(null, "", "#" + h.id);
      h.setAttribute("tabindex", "-1");
      h.focus({ preventScroll: true });
    });
    li.appendChild(a);
    list.appendChild(li);
    return a;
  });
  toc.appendChild(list);

  var topLink = doc.createElement("a");
  topLink.className = "rd-toc-top";
  topLink.href = "#main-content";
  topLink.innerHTML = "উপরে ফিরুন ↑";
  topLink.addEventListener("click", function (e) {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: reduced.matches ? "auto" : "smooth" });
  });
  toc.appendChild(topLink);
  doc.body.appendChild(toc);

  /* ------------------------------------------------------ *
   * ৩) স্ক্রল-অনুসরণ: কোন অংশে আছেন + কতটা পড়া হলো
   * ------------------------------------------------------ */
  var ticking = false;
  var current = -1;

  function follow() {
    ticking = false;
    var y = window.pageYOffset;
    var h = doc.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    var pct = max > 0 ? Math.min(1, y / max) : 0;
    bar.style.width = (pct * 100).toFixed(1) + "%";

    /* সূচি তখনই দেখাই যখন প্রবন্ধের ভেতরে আছি */
    var first = heads[0].getBoundingClientRect().top + y;
    var articleEnd = body.getBoundingClientRect().bottom + y;
    var on = y + 220 > first && y < articleEnd - 120;
    toc.classList.toggle("on", on);

    /* শেষ যে হেডিং স্ক্রল করে পেরিয়েছি, সেটাই «এখানে আছেন» */
    var at = 0;
    for (var i = 0; i < heads.length; i++) {
      if (heads[i].getBoundingClientRect().top + y <= y + 120) at = i;
    }
    if (at !== current) {
      if (links[current]) links[current].classList.remove("here");
      if (links[current]) links[current].removeAttribute("aria-current");
      if (links[at]) {
        links[at].classList.add("here");
        links[at].setAttribute("aria-current", "true");
      }
      current = at;
    }
  }

  function queue() {
    if (!ticking) { ticking = true; window.requestAnimationFrame(follow); }
  }

  window.addEventListener("scroll", queue, { passive: true });
  window.addEventListener("resize", queue, { passive: true });
  follow();

  /* ------------------------------------------------------ *
   * ৪) উদ্ধৃতি-কপি
   * ------------------------------------------------------ */
  var h1 = doc.querySelector(".article-heading h1");
  var kicker = doc.querySelector(".article-kicker");
  var title = (h1 ? h1.textContent : doc.title).replace(/\s+/g, " ").trim();
  var label = kicker ? kicker.textContent.replace(/·/g, " ").replace(/\s+/g, " ").trim() : "";

  var wrap = doc.createElement("div");
  wrap.className = "rd-actions";

  var lab = doc.createElement("span");
  lab.className = "rd-actions-label";
  lab.textContent = "এই লেখাটি সূত্রসহ শেয়ার করুন:";
  wrap.appendChild(lab);

  var btn = doc.createElement("button");
  btn.type = "button";
  btn.className = "rd-copy";
  btn.innerHTML = copyIcon() + "<span>উদ্ধৃতি কপি</span>";
  btn.setAttribute("aria-live", "polite");
  btn.addEventListener("click", function () {
    var cite =
      "«" + title + "» — Ebrahim Ead" +
      (label ? " · " + label : "") +
      "\n" + location.href.split("#")[0];
    copy(cite).then(function (ok) {
      var span = btn.querySelector("span");
      btn.classList.add("done");
      span.textContent = ok ? "কপি হয়েছে ✓" : "কপি করা যায়নি";
      setTimeout(function () {
        btn.classList.remove("done");
        span.textContent = "উদ্ধৃতি কপি";
      }, 2200);
    });
  });
  wrap.appendChild(btn);

  /* জায়গা: পাঠ শেষ হওয়ার ঠিক পরে, লেখকের নাম-লেখা ব্লকের আগে —
     পাঠক লেখা পড়া শেষ করে যেখানে থামেন, বোতামও সেখানেই। */
  var endBlock = doc.querySelector(".article-end-section .article-end, .article-end");
  if (endBlock && endBlock.parentNode && endBlock.parentNode.classList.contains("wrap")) {
    endBlock.parentNode.insertBefore(wrap, endBlock);
  } else {
    /* কোনো নিবন্ধ-শেষ ব্লক নেই: পাঠের ভেতরেই, শেষ অনুচ্ছেদের পরে */
    var last = body.lastElementChild;
    while (last && /^(SCRIPT|STYLE)$/.test(last.tagName)) last = last.previousElementSibling;
    if (last && last.parentNode === body) body.insertBefore(wrap, last.nextSibling);
    else body.appendChild(wrap);
  }

  function copy(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(function () { return true; },
        function () { return fallbackCopy(text); });
    }
    return Promise.resolve(fallbackCopy(text));
  }

  function fallbackCopy(text) {
    try {
      var ta = doc.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.cssText = "position:fixed;top:-1000px;opacity:0";
      doc.body.appendChild(ta);
      ta.select();
      var ok = doc.execCommand && doc.execCommand("copy");
      doc.body.removeChild(ta);
      return !!ok;
    } catch (e) { return false; }
  }

  function copyIcon() {
    return '<svg viewBox="0 0 24 24" aria-hidden="true">' +
      '<rect x="9" y="9" width="12" height="12" rx="2.5"/>' +
      '<path d="M6.5 15H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1.5"/></svg>';
  }

  /* বাংলা সংখ্যা */
  function bn(n) {
    var d = "০১২৩৪৫৬৭৮৯";
    return String(n).replace(/[0-9]/g, function (c) { return d[+c]; });
  }
})();
