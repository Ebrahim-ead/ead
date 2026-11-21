/* ============ Personal-site shared behaviour ============ */
(function () {
  "use strict";
  var rm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- tiny toast helper ---- */
  function toast(msg, ms) {
    var t = document.createElement("div");
    t.textContent = msg;
    t.style.cssText = "position:fixed;left:50%;bottom:26px;transform:translateX(-50%) translateY(12px);z-index:120;" +
      "background:rgba(8,20,28,.97);color:#ffe9ad;border:1px solid #f5b81c;border-radius:14px;padding:12px 18px;" +
      "max-width:min(560px,92vw);font-size:14px;line-height:1.6;box-shadow:0 18px 40px rgba(0,0,0,.45);opacity:0;" +
      "transition:opacity .35s ease,transform .35s ease;text-align:center";
    document.body.appendChild(t);
    requestAnimationFrame(function () { t.style.opacity = "1"; t.style.transform = "translateX(-50%)"; });
    setTimeout(function () {
      t.style.opacity = "0"; t.style.transform = "translateX(-50%) translateY(12px)";
      setTimeout(function () { t.remove(); }, 400);
    }, ms || 7000);
  }
  window.__eadToast = toast;

  /* ---- reveal on scroll ---- */
  function revealObs() {
    var els = document.querySelectorAll(".rv:not(.in),.rv-l:not(.in),.rv-s:not(.in)");
    if (!("IntersectionObserver" in window) || rm) {
      els.forEach(function (e) { e.classList.add("in"); });
      return;
    }
    var io = new IntersectionObserver(function (ents) {
      ents.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.06 });
    els.forEach(function (e) { io.observe(e); });
  }
  window.__reveal = revealObs;

  /* ---- header, menu, progress, to-top ---- */
  function shell() {
    var prog = document.querySelector(".prog");
    var up = document.querySelector(".up");
    var ticking = false, scrolled = false;
    function onScroll() {
      ticking = false;
      var h = document.documentElement;
      var y = window.scrollY || h.scrollTop || 0;
      if (!y && !scrolled) return;
      scrolled = true;
      var max = h.scrollHeight - h.clientHeight;
      if (prog) prog.style.transform = "scaleX(" + (max > 0 ? Math.min(1, y / max) : 0).toFixed(4) + ")";
      if (up) up.classList.toggle("show", y > 420);
    }
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; requestAnimationFrame(onScroll); }
    }, { passive: true });
    if ((window.scrollY || document.documentElement.scrollTop || 0) > 0) {
      if (typeof requestAnimationFrame === "function") requestAnimationFrame(onScroll); else onScroll();
    }

    if (up) up.onclick = function () { window.scrollTo({ top: 0, behavior: rm ? "auto" : "smooth" }); };

    /* ---- dark / light theme switch (saved locally in this browser) ---- */
    var themeToggle = document.querySelector("[data-theme-toggle]");
    if (themeToggle) {
      var themeIcon = themeToggle.querySelector(".theme-toggle-icon");
      var themeLabel = themeToggle.querySelector(".theme-toggle-label");
      var themeKey = "ebrahim-ead-theme";
      function applyTheme(theme, save) {
        theme = theme === "light" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", theme);
        var nextLabel = theme === "light" ? "ডার্ক" : "লাইট";
        var nextAction = theme === "light" ? "ডার্ক থিমে যান" : "লাইট থিমে যান";
        if (themeIcon) themeIcon.textContent = theme === "light" ? "☾" : "☀";
        if (themeLabel) themeLabel.textContent = nextLabel;
        themeToggle.setAttribute("aria-label", nextAction);
        themeToggle.title = nextAction;
        if (save) { try { localStorage.setItem(themeKey, theme); } catch (e) { } }
      }
      var initialTheme = document.documentElement.getAttribute("data-theme") || "dark";
      try {
        var savedTheme = localStorage.getItem(themeKey);
        if (savedTheme === "dark" || savedTheme === "light") initialTheme = savedTheme;
      } catch (e) { }
      applyTheme(initialTheme, false);
      themeToggle.addEventListener("click", function () {
        applyTheme(document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light", true);
      });
    }

    /* ---- counters ---- */
    document.querySelectorAll("[data-count]").forEach(function (el) {
      var target = parseFloat(el.getAttribute("data-count")) || 0;
      var dur = 1500, t0 = 0;
      var bn = /[০-৯]/.test(el.textContent);
      function bn2(n) { return bn ? String(n).replace(/[0-9]/g, function (d) { return "০১২৩৪৫৬৭৮৯"[+d]; }) : String(n); }
      function step(ts) {
        if (!t0) t0 = ts;
        var p = Math.min(1, (ts - t0) / dur);
        var eased = 1 - Math.pow(1 - p, 3);
        el.textContent = bn2(Math.round(target * eased).toLocaleString("en-US"));
        if (p < 1) requestAnimationFrame(step);
      }
      if (rm || !("IntersectionObserver" in window)) { el.textContent = bn2(target.toLocaleString("en-US")); return; }
      var io2 = new IntersectionObserver(function (es) {
        es.forEach(function (en) { if (en.isIntersecting) { requestAnimationFrame(step); io2.disconnect(); } });
      }, { threshold: 0.4 });
      io2.observe(el);
    });

    /* ---- typewriter hero ---- */
    var tw = document.querySelector("[data-type]");
    if (tw) {
      var words;
      try { words = JSON.parse(tw.getAttribute("data-type")); } catch (e) { words = []; }
      var w = 0, del = true;
      var segmenter = typeof Intl !== "undefined" && Intl.Segmenter ? new Intl.Segmenter("bn", { granularity: "grapheme" }) : null;
      function graphemes(word) { return segmenter ? Array.from(segmenter.segment(word), function (s) { return s.segment; }) : Array.from(word); }
      var letters = graphemes(words[0] || ""), i = letters.length;
      var span = document.createElement("span");
      span.className = "tword";
      var cur = document.createElement("i");
      cur.className = "cursor";
      tw.innerHTML = "";
      tw.appendChild(span); tw.appendChild(cur);
      span.textContent = letters.join("");
      function tick() {
        if (del) {
          i = Math.max(0, i - 1); span.textContent = letters.slice(0, i).join("");
          if (i === 0) { del = false; w = (w + 1) % words.length; letters = graphemes(words[w]); return setTimeout(tick, 320); }
          setTimeout(tick, 45);
        } else {
          i = Math.min(letters.length, i + 1); span.textContent = letters.slice(0, i).join("");
          if (i === letters.length) { del = true; return setTimeout(tick, 2400); }
          setTimeout(tick, 85);
        }
      }
      var startDelay = parseInt(tw.getAttribute("data-type-delay"), 10) || 2600;
      if (!rm && words.length > 1) setTimeout(tick, startDelay);
    }

    /* ---- year + subscribe form ---- */
    var yr = document.getElementById("yr");
    if (yr) yr.textContent = String(new Date().getFullYear()).replace(/[0-9]/g,
      function (c) { return "০১২৩৪৫৬৭৮৯"[+c]; });
    var sb = document.getElementById("sb");
    if (sb) {
      sb.onclick = function () {
        var em = document.getElementById("em"), msg = document.getElementById("subm");
        var v = (em && em.value || "").trim();
        if (!/^\S+@\S+\.\S+$/.test(v)) { msg.textContent = "সঠিক ইমেইল ঠিকানা দিন।"; return; }
        msg.textContent = "ধন্যবাদ! ইনশাআল্লাহ আপডেট পৌঁছে দেওয়ার ব্যবস্থা করা হবে।";
        em.value = "";
      };
    }
    var asb = document.getElementById("askbtn");
    if (asb && !asb.dataset.askEnhanced) {
      asb.onclick = function () {
        var an = document.getElementById("an"), ac = document.getElementById("ac"),
            at2 = document.getElementById("at"), aq = document.getElementById("aq"),
            m = document.getElementById("askm");
        var q = (aq.value || "").trim();
        if (q.length < 8) { m.textContent = "অনুগ্রহ করে আপনার প্রশ্নটি একটু বিস্তারিত লিখুন।"; return; }
        var txt = "প্রশ্ন (" + at2.value + "): " + q +
          (an.value ? "\nনাম: " + an.value : "") + (ac.value ? "\nযোগাযোগ: " + ac.value : "");
        m.innerHTML = 'ধন্যবাদ! বার্তাটি কপি করার চেষ্টা করা হয়েছে। <a target="_blank" rel="noopener" class="soc-fb" href="https://www.facebook.com/ebrahim.rahul">Facebook</a>, <a target="_blank" rel="noopener" class="soc-ig" href="https://www.instagram.com/ead2212/">Instagram</a>, <a target="_blank" rel="noopener" class="soc-rd" href="https://www.reddit.com/user/Zealousideal_Dig2819/">Reddit</a>, <a target="_blank" rel="noopener" class="soc-x" href="https://x.com/ebrahimn23o">X</a> অথবা <a target="_blank" rel="noopener" class="soc-wa" href="https://wa.me/8801783543026">WhatsApp</a>-এ পাঠান।';
        try { navigator.clipboard.writeText(txt); } catch (e) { }
      };
    }
  }

  /* ---- pointer-reactive 3D lighting and tilt (desktop pointers only) ---- */
  function tilt() {
    if (rm || !window.matchMedia || !window.matchMedia("(hover:hover) and (pointer:fine)").matches) return;
    var sel = ".card,.qcard,.stat,.infobox,.book-part,.article-card,.cta,.profile-card,.book-teaser,.book-hero,.book-wrap-card,.hero-photo,.about-photo,.book-cover,.book-teaser-art,.book-wrap-image";
    var imageSel = ".hero-photo,.about-photo,.book-cover,.book-teaser-art,.book-wrap-image";
    var wideSel = ".cta,.profile-card,.book-teaser,.book-hero,.book-wrap-card";
    document.addEventListener("pointermove", function (e) {
      var el = e.target.closest ? e.target.closest(sel) : null;
      if (!el) return;
      var r = el.getBoundingClientRect();
      var maxWidth = el.matches(wideSel) ? 1220 : 720;
      if (!r.width || !r.height || r.width > maxWidth || r.height > 840) return;
      var x = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
      var y = Math.max(0, Math.min(1, (e.clientY - r.top) / r.height));
      var maxAngle = el.matches(imageSel) ? 7.4 : (el.matches(wideSel) ? 2.7 : 5.8);
      el.style.setProperty("--pointer-x", (x * 100).toFixed(1) + "%");
      el.style.setProperty("--pointer-y", (y * 100).toFixed(1) + "%");
      el.style.transform = "perspective(980px) rotateX(" + (-(y - .5) * maxAngle).toFixed(2) + "deg) rotateY(" + ((x - .5) * maxAngle).toFixed(2) + "deg) translateY(-4px)";
    }, { passive: true });
    document.addEventListener("pointerout", function (e) {
      var el = e.target.closest ? e.target.closest(sel) : null;
      if (!el || (e.relatedTarget && el.contains(e.relatedTarget))) return;
      el.style.transform = "";
      el.style.removeProperty("--pointer-x");
      el.style.removeProperty("--pointer-y");
    }, { passive: true });
  }

  document.addEventListener("DOMContentLoaded", function () { shell(); revealObs(); tilt(); });
})();
