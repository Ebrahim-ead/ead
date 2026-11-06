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
  /* গ্লাইডার কেবল প্রধান আইটেমগুলোর জন্য — ড্রপডাউনের ভেতরের সাব-লিংক
     (.nav-sub-item) আলাদা, ওগুলোর নিজের হোভার-আলো আছে। */
  var links = [].slice.call(nav.querySelectorAll("a")).filter(function (a) {
    return !a.closest(".nav-sub");
  });
  if (!links.length) return;

  /* একটি দাগই থাকবে: পুরোনো টেমপ্লেটে দুই লিংকে «current» বসে থাকলেও
     (ধর্মীয় গ্রন্থ পাতায় «পরিচিতি»-ও রঙিন হতো) গ্লাইড কেবল
     true-current লিংকের নিচে বসবে, নইলে প্রথমটির নিচে। */
  var current = links.filter(function (a) {
    return a.getAttribute("aria-current") === "page" ||
      (a.parentNode && a.parentNode.classList && a.parentNode.classList.contains("current"));
  });
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

/* ============================================================
   ধর্মীয় গ্রন্থ — নেভ ড্রপডাউন
   ডেস্কটপ: লিংকের পাশের তির-বোতামে খোলে/বন্ধ হয় (হোভারেও)।
   ফোন: একই বোতাম ড্রয়ারের ভেতরে সাব-লিস্ট খোলে।
   Esc / বাইরে চাপ / লিংকে গেলে বন্ধ।
   ============================================================ */
(function () {
  "use strict";
  var item = document.getElementById("nav-item-grantho");
  if (!item) return;
  var btn = item.querySelector(".nav-sub-toggle");
  var panel = document.getElementById("nav-sub-grantho");
  if (!btn || !panel) return;

  var nav = document.getElementById("site-nav");
  var wide = window.matchMedia("(min-width:1081px)");
  var hoverOK = window.matchMedia("(hover:hover) and (pointer:fine)");
  var hoverTimer = null;

  function isOpen() { return btn.getAttribute("aria-expanded") === "true"; }
  function set(open) {
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    panel.classList.toggle("open", open);
  }
  function close() { if (isOpen()) set(false); }

  btn.addEventListener("click", function (e) {
    e.preventDefault();
    e.stopPropagation();
    set(!isOpen());
  });

  /* ডেস্কটপে হোভার করলেই খোলা — মেনুতে ঢুকতে বোতাম খোঁজার দরকার নেই */
  if (hoverOK) {
    item.addEventListener("pointerenter", function (e) {
      if (e.pointerType === "touch" || !wide.matches) return;
      clearTimeout(hoverTimer);
      if (!isOpen()) set(true);
    });
    item.addEventListener("pointerleave", function (e) {
      if (e.pointerType === "touch" || !wide.matches) return;
      clearTimeout(hoverTimer);
      hoverTimer = setTimeout(close, 220);
    });
  }
  /* প্যানেলের ভেতরে ঢুকলে খোলা থাকবে — নইলে সাব-লিংকে ক্লিক করা যেত না */
  panel.addEventListener("pointerenter", function () {
    if (wide.matches && hoverOK.matches) clearTimeout(hoverTimer);
  });
  panel.addEventListener("pointerleave", function () {
    if (wide.matches && hoverOK.matches) hoverTimer = setTimeout(close, 220);
  });

  /* বাইরে চাপ / Esc */
  document.addEventListener("click", function (e) {
    if (!item.contains(e.target)) close();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && isOpen()) {
      btn.focus({ preventScroll: true });
      close();
    }
  });
  panel.addEventListener("click", function (e) {
    if (e.target.closest && e.target.closest("a")) close();
  });
  /* তৈরি-হয়নি এমন ধর্মে চাপলে কোথাও যাবে না */
  panel.addEventListener("click", function (e) {
    var soon = e.target.closest && e.target.closest(".nav-sub-item.is-soon");
    if (soon) e.preventDefault();
  });

  /* breakpoint বদলালে খোলা-অবস্থা যেন আটকে না থাকে */
  var reset = function () { close(); };
  if (wide.addEventListener) wide.addEventListener("change", reset);
  else if (wide.addListener) wide.addListener(reset);

  /* ড্রয়ার বন্ধ হলে সাব-লিস্টও বন্ধ */
  if (nav) {
    new MutationObserver(function () {
      if (!nav.classList.contains("open")) close();
    }).observe(nav, { attributes: true, attributeFilter: ["class"] });
  }
})();
