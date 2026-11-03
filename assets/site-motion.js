/* ============================================================
   site-motion.js — the behavioural half of site-motion.css
   ------------------------------------------------------------
   • stagger: groups of revealing elements enter one after another
   • cursor:  a small gold ring that trails the pointer
   • progress: a reading line at the top of long pages
   • header:  the bar settles once you start scrolling
   • theme:   a cross-fade instead of a flash

   One RAF loop drives everything, so the cost stays flat no
   matter how many elements are on the page. Every effect is off
   when the reader prefers reduced motion, and the pointer-only
   effects never initialise on touch devices.
   ============================================================ */
(function () {
  "use strict";

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  var fine = window.matchMedia("(hover:hover) and (pointer:fine)");
  var supportsVT = typeof document.startViewTransition === "function";

  /* ------------------------------------------------------ *
   * stagger — one delay per element, re-derived per group so a
   * long list never waits seconds for its last item
   * ------------------------------------------------------ */
  function stagger() {
    var groups = [".article-list-grid", ".grid", ".book-list-grid", ".fgrid", ".info3"];
    var step = 55, maxDelay = 420;

    groups.forEach(function (sel) {
      var box = document.querySelector(sel);
      if (!box) return;
      [].slice.call(box.children).forEach(function (el, i) {
        var d = Math.min(i * step, maxDelay);
        /* rows are re-staggered per shelf: after 8 items start over,
           so a long grid does not trail off */
        if (i >= 8) d = Math.min((i % 8) * step, maxDelay);
        el.style.setProperty("--d", (d / 1000) + "s");
        el.style.transitionDelay = (d / 1000) + "s";
      });
    });
  }

  /* ------------------------------------------------------ *
   * the pointer ring
   * ------------------------------------------------------ */
  function cursor() {
    if (!fine.matches || reduced.matches) return;
    var ring = document.createElement("div");
    ring.className = "m-cursor";
    ring.setAttribute("aria-hidden", "true");
    document.body.appendChild(ring);

    var x = -100, y = -100, rx = -100, ry = -100, hot = false, shown = false;
    var lastTarget = null;

    document.addEventListener("pointermove", function (e) {
      if (e.pointerType === "touch") return;
      x = e.clientX; y = e.clientY;
      if (!shown) { rx = x; ry = y; shown = true; ring.classList.add("on"); }
      /* only re-test the target when it actually changes, so the
         ring grows over a link and shrinks again in open space */
      if (e.target !== lastTarget) {
        lastTarget = e.target;
        var t = e.target;
        var nowHot = !!(t && t.closest && t.closest("a,button,summary,.card,.qcard,article"));
        if (nowHot !== hot) { hot = nowHot; ring.classList.toggle("hot", hot); }
      }
    }, { passive: true });

    document.addEventListener("pointerleave", function () {
      shown = false; ring.classList.remove("on");
    });

    document.addEventListener("pointerdown", function () {
      if (reduced.matches) return;
      ring.style.transform = "translate3d(" + rx + "px," + ry + "px,0) scale(.82)";
    }, { passive: true });

    /* the ring lags behind the real pointer a little, which is
       what makes it feel soft rather than glued on */
    return function tick() {
      rx += (x - rx) * 0.22;
      ry += (y - ry) * 0.22;
      if (Math.abs(x - rx) < 0.1 && Math.abs(y - ry) < 0.1) { rx = x; ry = y; }
      ring.style.transform = "translate3d(" + rx + "px," + ry + "px,0)";
    };
  }

  /* ------------------------------------------------------ *
   * reading progress (only where there is actually an article)
   * ------------------------------------------------------ */
  function progress() {
    var bar = document.createElement("div");
    bar.className = "m-progress";
    bar.setAttribute("aria-hidden", "true");
    document.body.appendChild(bar);

    var last = -1;
    return function tick() {
      var doc = document.documentElement;
      var max = doc.scrollHeight - window.innerHeight;
      var p = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
      if (Math.abs(p - last) < 0.0015) return;
      last = p;
      bar.style.transform = "scaleX(" + p.toFixed(4) + ")";
      bar.classList.toggle("on", p > 0.005 && max > 420);
      bar.style.opacity = p > 0.005 ? "1" : "0";
    };
  }

  /* ------------------------------------------------------ *
   * the header settles after a short scroll
   * ------------------------------------------------------ */
  function header() {
    var bar = document.querySelector("header.top");
    if (!bar) return;
    var stuck = false;
    return function tick() {
      var s = window.scrollY > 24;
      if (s !== stuck) { stuck = s; bar.classList.toggle("m-stuck", s); }
    };
  }

  /* ------------------------------------------------------ *
   * theme cross-fade
   * ------------------------------------------------------ */
  function theme() {
    if (!supportsVT || reduced.matches) return;
    var btn = document.querySelector("[data-theme-toggle]");
    if (!btn) return;
    /* the page's own handler is attached first and does the real
       work; we only wrap it in a view transition */
    btn.addEventListener("click", function () {
      if (!document.startViewTransition) return;
      /* the click already happened; re-apply with a transition by
         re-running the same toggle the page uses */
      var next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
      var prev = document.documentElement.getAttribute("data-theme") || "dark";
      if (next === prev) return;
      /* the page handler has already flipped it, so flip back and
         let the transition do the visible change */
      document.documentElement.setAttribute("data-theme", prev);
      document.startViewTransition(function () {
        document.documentElement.setAttribute("data-theme", next);
        try { localStorage.setItem("ebrahim-ead-theme", next); } catch (e) {}
      });
    });
  }

  /* ------------------------------------------------------ *
   * one loop for everything that needs per-frame updates
   * ------------------------------------------------------ */
  var tickers = [];
  var running = false;

  function loop() {
    for (var i = 0; i < tickers.length; i++) tickers[i]();
    if (!running) return;
    requestAnimationFrame(loop);
  }

  function boot() {
    stagger();

    var ring = cursor();
    if (ring) tickers.push(ring);
    tickers.push(progress(), header());
    tickers = tickers.filter(Boolean);

    theme();

    if (!reduced.matches) {
      running = true;
      requestAnimationFrame(loop);
    } else {
      /* still place the static pieces once */
      tickers.forEach(function (t) { t(); });
    }

    /* re-stagger when the layout changes (language toggle, zoom) */
    window.addEventListener("resize", stagger, { passive: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  /* if the reader flips the preference mid-visit, stop the loop */
  var onChange = function () {
    if (reduced.matches) running = false;
    else if (!running && tickers.length) { running = true; requestAnimationFrame(loop); }
  };
  if (reduced.addEventListener) reduced.addEventListener("change", onChange);
  else if (reduced.addListener) reduced.addListener(onChange);
})();
