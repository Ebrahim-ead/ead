/* ============================================================
   nav-motion.js — drives the shared header navigation glide.
   Measures the hovered (or current) link and parks the shared
   indicator under it, then feeds the pointer position to that
   link's gold fleck. Re-measured on resize, font load and a
   theme flip so the indicator never drifts out of place.
   ============================================================ */
(function () {
  "use strict";

  var nav = document.getElementById("site-nav");
  if (!nav) return;

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  var desktop = window.matchMedia("(min-width:1081px)");
  var links = [].slice.call(nav.querySelectorAll("a"));
  if (!links.length) return;

  /* একটি দাগই থাকবে: পুরোনো টেমপ্লেটে দুই লিংকে «current» বসে থাকলেও
     (ধর্মীয় গ্রন্থ পাতায় «পরিচিতি»-ও রঙিন হতো) গ্লাইড কেবল
     true-current লিংকের নিচে বসবে, নইলে প্রথমটির নিচে। */
  var current = links.filter(function (a) { return a.getAttribute("aria-current") === "page"; });
  var active = current[0] || links.filter(function (a) { return a.classList.contains("on"); })[0] || links[0];
  var hovered = null;

  function place(el) {
    if (!el) return;
    var w = el.offsetWidth - 12;
    nav.style.setProperty("--nav-glide-x", (el.offsetLeft + 6) + "px");
    nav.style.setProperty("--nav-glide-w", (w > 0 ? w : 0) + "px");
    nav.style.setProperty("--nav-glide-o", "1");
  }

  function sync() {
    if (!desktop.matches || reduced.matches) {
      nav.style.setProperty("--nav-glide-o", "0");
      nav.removeAttribute("data-glide");
      return;
    }
    nav.setAttribute("data-glide", "");   /* CSS drops the old underline now */
    place(hovered || active);
  }

  links.forEach(function (a) {
    a.addEventListener("pointerenter", function (e) {
      if (e.pointerType === "touch") return;
      hovered = a; sync();
    });
    a.addEventListener("focus", function () { hovered = a; sync(); });
    a.addEventListener("blur", function () {
      if (hovered === a) { hovered = null; sync(); }
    });
    a.addEventListener("pointermove", function (e) {
      if (!desktop.matches || reduced.matches || e.pointerType === "touch") return;
      var r = a.getBoundingClientRect();
      if (!r.width || !r.height) return;
      a.style.setProperty("--px", ((e.clientX - r.left) / r.width) * 100 + "%");
      a.style.setProperty("--py", ((e.clientY - r.top) / r.height) * 100 + "%");
    }, { passive: true });
  });

  nav.addEventListener("pointerleave", function () {
    hovered = null;
    sync();
  });

  /* keep the indicator glued to the right link when anything moves.
     sync() rather than place(), so crossing the mobile breakpoint or
     flipping the motion preference also updates the fallback state. */
  var queued = null;
  function refresh() {
    if (queued) return;
    queued = requestAnimationFrame(function () {
      queued = null;
      sync();
    });
  }

  var listen = function (mql, fn) {
    if (mql.addEventListener) mql.addEventListener("change", fn);
    else if (mql.addListener) mql.addListener(fn);
  };
  listen(desktop, refresh);
  listen(reduced, refresh);

  window.addEventListener("resize", refresh, { passive: true });
  window.addEventListener("orientationchange", refresh, { passive: true });
  window.addEventListener("load", refresh);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(refresh);

  var themeBtn = document.querySelector("[data-theme-toggle]");
  if (themeBtn) themeBtn.addEventListener("click", function () { setTimeout(refresh, 80); });

  if (window.ResizeObserver) new ResizeObserver(refresh).observe(nav);

  function boot() {
    sync();
    /* the pill animates in from just under the header the first time */
    if (desktop.matches && !reduced.matches) {
      nav.style.setProperty("--nav-glide-o", "0");
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { sync(); });
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
