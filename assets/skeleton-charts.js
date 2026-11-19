/* ============================================================
   skeleton-charts.js — শিমার স্কেলেটন ও ডেটা-নির্ভর চার্ট ইঞ্জিন
   ------------------------------------------------------------
   • ১০০% GPU-কম্পোজিটেড শিমার (CSS transform: translate3d ওভারলে)
   • কোনো বহিরাগত চার্ট-লাইব্রেরি নয় — খাঁটি SVG ও DOM বার
   • সব সংখ্যা সরাসরি JSON ম্যানিফেস্ট থেকে গণনাকৃত (হার্ডকোড নয়)
   ============================================================ */
(function () {
  "use strict";

  var BN = "০১২৩৪৫৬৭৮৯";
  function bn(n) {
    return String(n).replace(/[0-9]/g, function (d) { return BN[+d]; });
  }
  function bnNum(n) {
    return bn(String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","));
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ---------- ১. সাইডবার সূচি স্কেলেটন ---------- */
  function navRows(count) {
    var n = count || 8;
    var widths = ["w-70", "w-85", "w-55", "w-95", "w-70", "w-85", "w-55", "w-70"];
    var rows = [];
    for (var i = 0; i < n; i++) {
      rows.push(
        '<div class="skel-nav-row">' +
          '<span class="skel-bone skel-nav-num"></span>' +
          '<span class="skel-nav-lines">' +
            '<span class="skel-bone skel-line ' + widths[i % widths.length] + '"></span>' +
            '<span class="skel-bone skel-line skel-sm w-40"></span>' +
          '</span>' +
        '</div>'
      );
    }
    return '<div class="skel-nav-list" aria-hidden="true">' + rows.join("") + '</div>';
  }

  /* ---------- ২. পাঠক প্যানেল স্কেলেটন (আয়াত/হাদিস/শ্লোক) ---------- */
  function readerSkeleton(opts) {
    var o = opts || {};
    var count = o.cards || 4;
    var showHead = o.head !== false;
    var rtl = !!o.rtl;
    var label = o.label || "লোড হচ্ছে…";
    var out = ['<div class="skel-stack" role="status" aria-busy="true">',
      '<span class="sr-only">' + esc(label) + '</span>'];

    if (showHead) {
      out.push(
        '<div class="skel-head" aria-hidden="true">' +
          '<div class="skel-card-top">' +
            '<span class="skel-bone skel-line skel-lg w-55"></span>' +
            (rtl ? '<span class="skel-bone skel-badge" style="margin-inline-start:auto"></span>' : '') +
          '</div>' +
          '<div class="skel-card-top">' +
            '<span class="skel-bone skel-badge"></span>' +
            '<span class="skel-bone skel-badge" style="width:110px"></span>' +
          '</div>' +
        '</div>'
      );
    }

    var wSets = [
      ["w-95", "w-85", "w-55"],
      ["w-85", "w-95", "w-70"],
      ["w-95", "w-70", "w-40"],
      ["w-85", "w-95", "w-55"]
    ];
    for (var i = 0; i < count; i++) {
      var ws = wSets[i % wSets.length];
      out.push(
        '<div class="skel-card" aria-hidden="true">' +
          '<div class="skel-card-top">' +
            '<span class="skel-bone skel-num"></span>' +
            '<span class="skel-bone skel-badge"></span>' +
          '</div>' +
          (rtl ? '<span class="skel-bone skel-line skel-rtl ' + ws[0] + '"></span>' : '') +
          '<span class="skel-bone skel-line ' + ws[0] + '"></span>' +
          '<span class="skel-bone skel-line ' + ws[1] + '"></span>' +
          '<span class="skel-bone skel-line skel-sm ' + ws[2] + '"></span>' +
        '</div>'
      );
    }
    out.push('</div>');
    return out.join("");
  }

  /* ---------- ৩. সার্চ ফলাফল স্কেলেটন ---------- */
  function searchSkeleton(count, label) {
    var n = count || 4;
    var rows = ['<li class="sr-only" role="status">' + esc(label || "খোঁজা হচ্ছে…") + '</li>'];
    var ws = ["w-55", "w-70", "w-40", "w-55"];
    for (var i = 0; i < n; i++) {
      rows.push(
        '<li class="skel-ss-item" aria-hidden="true">' +
          '<div class="skel-card-top">' +
            '<span class="skel-bone skel-badge" style="width:62px;height:18px"></span>' +
            '<span class="skel-bone skel-line ' + ws[i % ws.length] + '"></span>' +
          '</div>' +
          '<span class="skel-bone skel-line skel-sm w-95"></span>' +
          '<span class="skel-bone skel-line skel-sm w-70"></span>' +
        '</li>'
      );
    }
    return rows.join("");
  }

  /* ---------- ৪. স্কেলেটন চার্ট (bars / hbar / donut / area) ---------- */
  function chartSkeleton(kind, opts) {
    var o = opts || {};
    var title = o.title || "";
    var sub = o.sub || "";
    var head =
      '<div class="dc-card-head">' +
        (title ? '<h3>' + esc(title) + '</h3>' : '<span class="skel-bone skel-line w-40" style="height:15px"></span>') +
        (sub ? '<span class="dc-card-sub">' + esc(sub) + '</span>' : '<span class="skel-bone skel-badge" style="width:64px;height:20px"></span>') +
      '</div>';

    var body = "";
    if (kind === "donut") {
      body =
        '<div class="skel-chart-donut" aria-hidden="true">' +
          '<div class="skel-ring">' +
            '<div class="skel-bone skel-ring-ring"></div>' +
            '<div class="skel-ring-mid">' +
              '<span class="skel-bone skel-line w-70" style="height:15px"></span>' +
              '<span class="skel-bone skel-line skel-sm w-55"></span>' +
            '</div>' +
          '</div>' +
          '<div class="skel-leg">' +
            '<div class="skel-leg-row"><span class="skel-bone skel-dot"></span><span class="skel-bone skel-line w-70"></span><span class="skel-bone skel-line skel-sm w-20"></span></div>' +
            '<div class="skel-leg-row"><span class="skel-bone skel-dot"></span><span class="skel-bone skel-line w-55"></span><span class="skel-bone skel-line skel-sm w-20"></span></div>' +
            '<div class="skel-leg-row"><span class="skel-bone skel-dot"></span><span class="skel-bone skel-line w-85"></span><span class="skel-bone skel-line skel-sm w-20"></span></div>' +
            '<div class="skel-leg-row"><span class="skel-bone skel-dot"></span><span class="skel-bone skel-line w-40"></span><span class="skel-bone skel-line skel-sm w-20"></span></div>' +
          '</div>' +
        '</div>';
    } else if (kind === "hbar") {
      var hw = ["92%", "76%", "58%", "42%", "28%"];
      var hrows = hw.map(function (pct) {
        return '<div class="skel-hbar-row">' +
          '<span class="skel-bone skel-hbar-lbl"></span>' +
          '<span class="skel-hbar-track"><span class="skel-bone skel-hbar-fill" style="display:block;width:' + pct + '"></span></span>' +
          '<span class="skel-bone skel-hbar-val"></span>' +
        '</div>';
      }).join("");
      body = '<div class="skel-chart-hbar" aria-hidden="true">' + hrows + '</div>';
    } else if (kind === "area") {
      body =
        '<div class="skel-chart-area" aria-hidden="true">' +
          '<div class="skel-bone skel-area-box">' +
            '<svg class="skel-area-svg" viewBox="0 0 320 120" preserveAspectRatio="none">' +
              '<path d="M0 95 Q 48 64, 92 78 T 185 46 T 270 62 L 320 34 L 320 120 L 0 120 Z" fill="var(--skel-bg)"></path>' +
              '<path d="M0 95 Q 48 64, 92 78 T 185 46 T 270 62 L 320 34" fill="none" stroke="var(--gold3)" stroke-width="2" opacity=".45"></path>' +
            '</svg>' +
          '</div>' +
          '<div class="skel-x-ticks">' +
            '<span class="skel-bone skel-x-tick"></span><span class="skel-bone skel-x-tick"></span>' +
            '<span class="skel-bone skel-x-tick"></span><span class="skel-bone skel-x-tick"></span>' +
            '<span class="skel-bone skel-x-tick"></span><span class="skel-bone skel-x-tick"></span>' +
          '</div>' +
        '</div>';
    } else {
      var heights = [42, 78, 56, 94, 68, 84, 48, 62, 74, 38];
      var cols = heights.map(function (h) {
        return '<span class="skel-bone skel-bar-col" style="height:' + h + '%"></span>';
      }).join("");
      var ticks = heights.map(function () {
        return '<span class="skel-bone skel-x-tick"></span>';
      }).join("");
      body =
        '<div class="skel-chart-bars" aria-hidden="true">' +
          '<div class="skel-bar-plot">' + cols + '</div>' +
          '<div class="skel-x-ticks">' + ticks + '</div>' +
        '</div>';
    }

    return '<div class="dc-card" aria-busy="true">' + head + body +
      '<span class="sr-only">চার্ট ডেটা লোড হচ্ছে…</span></div>';
  }

  /* ---------- ৫. আসল SVG ডোনাট চার্ট ---------- */
  var PALETTE = ["var(--chart-c1)", "var(--chart-c2)", "var(--chart-c3)", "var(--chart-c4)", "var(--chart-c5)"];

  function renderDonut(el, cfg) {
    if (!el || !cfg) return;
    var items = cfg.items || [];
    var total = items.reduce(function (s, x) { return s + (+x.value || 0); }, 0);
    var R = 44, C = 2 * Math.PI * R;
    var offset = 0;

    var segs = items.map(function (it, idx) {
      var val = +it.value || 0;
      var frac = total > 0 ? val / total : 0;
      var len = Math.max(0, frac * C);
      var col = it.color || PALETTE[idx % PALETTE.length];
      var s = '<circle class="dc-donut-seg" cx="56" cy="56" r="' + R + '"' +
        ' stroke="' + col + '" stroke-dasharray="' + len.toFixed(2) + ' ' + C.toFixed(2) + '"' +
        ' stroke-dashoffset="' + (-offset).toFixed(2) + '"' +
        (it.title ? '><title>' + esc(it.title) + '</title></circle>' : '/>');
      offset += len;
      return s;
    }).join("");

    var legs = items.map(function (it, idx) {
      var val = +it.value || 0;
      var pct = total > 0 ? Math.round((val / total) * 100) : 0;
      var col = it.color || PALETTE[idx % PALETTE.length];
      var tag = it.href ? "a" : (typeof it.onClick === "function" ? "button" : "div");
      var attrs = tag === "a"
        ? ' href="' + esc(it.href) + '"'
        : (tag === "button" ? ' type="button" data-leg-idx="' + idx + '"' : '');
      return '<' + tag + ' class="dc-leg-item' + (it.active ? ' on' : '') + '"' + attrs + '>' +
        '<span class="dc-leg-l">' +
          '<span class="dc-leg-sw" style="background:' + col + '"></span>' +
          '<span class="dc-leg-lbl">' + esc(it.label) + '</span>' +
        '</span>' +
        '<span class="dc-leg-val">' + esc(it.valueText || bnNum(val)) + ' · ' + bn(pct) + '%</span>' +
      '</' + tag + '>';
    }).join("");

    el.innerHTML =
      '<div class="dc-card-head">' +
        '<h3>' + esc(cfg.title || "") + '</h3>' +
        (cfg.badge ? '<span class="dc-pill">' + esc(cfg.badge) + '</span>' : '') +
      '</div>' +
      '<div class="dc-donut-wrap">' +
        '<div class="dc-donut-box">' +
          '<svg class="dc-donut-svg" viewBox="0 0 112 112" aria-hidden="true">' +
            '<circle class="dc-donut-track" cx="56" cy="56" r="' + R + '"/>' +
            segs +
          '</svg>' +
          '<div class="dc-donut-center">' +
            '<b>' + esc(cfg.centerValue || bnNum(total)) + '</b>' +
            '<small>' + esc(cfg.centerLabel || "") + '</small>' +
          '</div>' +
        '</div>' +
        '<div class="dc-legend">' + legs + '</div>' +
      '</div>';

    el.removeAttribute("aria-busy");
    el.querySelectorAll("button[data-leg-idx]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var it = items[+btn.getAttribute("data-leg-idx")];
        if (it && typeof it.onClick === "function") it.onClick(it);
      });
    });
  }

  /* ---------- ৬. আসল উল্লম্ব বার চার্ট ---------- */
  function renderBarChart(el, cfg) {
    if (!el || !cfg) return;
    var bars = cfg.bars || [];
    var max = bars.reduce(function (m, b) { return Math.max(m, +b.value || 0); }, 0) || 1;

    var cols = bars.map(function (b, idx) {
      var val = +b.value || 0;
      var pct = Math.max(4, Math.round((val / max) * 100));
      var interactive = typeof b.onClick === "function";
      var tag = interactive ? "button" : "div";
      var attrs = interactive
        ? ' type="button" data-bar-idx="' + idx + '" aria-label="' + esc(b.aria || (b.label + ": " + (b.valueText || bnNum(val)))) + '"'
        : '';
      var style = b.color ? ' style="background:' + b.color + ';height:' + pct + '%"' : ' style="height:' + pct + '%"';
      return '<' + tag + ' class="dc-bar-btn" title="' + esc(b.title || (b.label + " — " + (b.valueText || bnNum(val)))) + '"' + attrs + '>' +
        '<span class="dc-bar-val">' + esc(b.shortVal || bn(val)) + '</span>' +
        '<span class="dc-bar-fill"' + style + '></span>' +
      '</' + tag + '>';
    }).join("");

    var xLabels = bars.map(function (b) {
      return '<span class="dc-bar-xlbl">' + esc(b.label) + '</span>';
    }).join("");

    el.innerHTML =
      '<div class="dc-card-head">' +
        '<h3>' + esc(cfg.title || "") + '</h3>' +
        (cfg.badge ? '<span class="dc-pill">' + esc(cfg.badge) + '</span>' : '') +
      '</div>' +
      '<div class="dc-bars-wrap">' +
        '<div class="dc-bars">' + cols + '</div>' +
        '<div class="dc-bar-x" aria-hidden="true">' + xLabels + '</div>' +
      '</div>';

    el.removeAttribute("aria-busy");
    el.querySelectorAll("button[data-bar-idx]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var b = bars[+btn.getAttribute("data-bar-idx")];
        if (b && typeof b.onClick === "function") b.onClick(b);
      });
    });
  }

  /* ---------- ৭. আসল অনুভূমিক বার চার্ট ---------- */
  function renderHBarChart(el, cfg) {
    if (!el || !cfg) return;
    var rows = cfg.rows || [];
    var max = rows.reduce(function (m, r) { return Math.max(m, +r.value || 0); }, 0) || 1;

    var html = rows.map(function (r, idx) {
      var val = +r.value || 0;
      var pct = Math.max(3, Math.round((val / max) * 100));
      var interactive = typeof r.onClick === "function";
      var tag = r.href ? "a" : (interactive ? "button" : "div");
      var attrs = r.href
        ? ' href="' + esc(r.href) + '"'
        : (interactive ? ' type="button" data-hbar-idx="' + idx + '"' : '');
      var bg = r.color ? 'background:' + r.color + ';' : '';
      return '<' + tag + ' class="dc-hbar-row' + (r.active ? ' on' : '') + '"' + attrs + '>' +
        '<div class="dc-hbar-top">' +
          '<span class="dc-hbar-name">' + esc(r.label) + '</span>' +
          '<span class="dc-hbar-num">' + esc(r.meta || bnNum(val)) + '</span>' +
        '</div>' +
        '<div class="dc-hbar-track">' +
          '<div class="dc-hbar-fill" style="' + bg + 'width:' + pct + '%"></div>' +
        '</div>' +
      '</' + tag + '>';
    }).join("");

    el.innerHTML =
      '<div class="dc-card-head">' +
        '<h3>' + esc(cfg.title || "") + '</h3>' +
        (cfg.badge ? '<span class="dc-pill">' + esc(cfg.badge) + '</span>' : '') +
      '</div>' +
      '<div class="dc-hbar-list">' + html + '</div>';

    el.removeAttribute("aria-busy");
    el.querySelectorAll("button[data-hbar-idx]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var r = rows[+btn.getAttribute("data-hbar-idx")];
        if (r && typeof r.onClick === "function") r.onClick(r);
      });
    });
  }

  /* ---------- ৮. সাইট-ব্যাপী সংগ্রহ ও বিন্যাস চার্ট হাইড্রেটর ---------- */
  function safeFetchJSON(url) {
    if (typeof window.fetch !== "function") return Promise.resolve(null);
    return fetch(url).then(function (r) {
      return r.ok ? r.json() : null;
    }).catch(function () { return null; });
  }

  function hydrateArchiveNode(box) {
    if (!box || box.dataset.hydrated) return;
    box.dataset.hydrated = "1";
    var prefix = box.getAttribute("data-base-prefix") || box.getAttribute("data-archive-base") || "";
    var cardBars = box.querySelector('[data-chart="archive-bars"]');
    var cardDonut = box.querySelector('[data-chart="archive-donut"]');
    var sumBadge = box.querySelector("[data-archive-total]");

    Promise.all([
      safeFetchJSON(prefix + "assets/quran/data/index.json"),
      safeFetchJSON(prefix + "assets/hadith/data/index.json"),
      safeFetchJSON(prefix + "assets/grantho/data/bible/index.json"),
      safeFetchJSON(prefix + "assets/grantho/data/bible/english/index.json"),
      safeFetchJSON(prefix + "assets/grantho/data/rigveda/index.json"),
      safeFetchJSON(prefix + "assets/grantho/data/samaveda/index.json"),
      safeFetchJSON(prefix + "assets/grantho/data/atharvaveda/index.json"),
      safeFetchJSON(prefix + "assets/grantho/data/yajurveda-shukla/index.json"),
      safeFetchJSON(prefix + "assets/grantho/data/gita/index.json"),
      safeFetchJSON(prefix + "assets/grantho/data/shvetashvatara/index.json"),
      safeFetchJSON(prefix + "assets/grantho/data/prashna/index.json"),
      safeFetchJSON(prefix + "assets/grantho/data/chandogya/index.json"),
      safeFetchJSON(prefix + "assets/grantho/data/brihadaranyaka/index.json")
    ]).then(function (res) {
      var quran = res[0], hadith = res[1], bnBible = res[2], enBible = res[3], rig = res[4], sama = res[5], ath = res[6], yaj = res[7], gita = res[8], shv = res[9], pra = res[10], cha = res[11], bri = res[12];
      var items = [
        { label: "হাদিস (৭ কিতাব)", value: (hadith && hadith.total) || 0, unit: "হাদিস", group: "islam", href: prefix + "hadith.html", color: "var(--chart-c1)" },
        { label: "English Bible (NAB)", value: (enBible && enBible.total) || 0, unit: "পদ", group: "christian", href: prefix + "grantho/christian/english-bible.html", color: "var(--chart-c2)" },
        { label: "বাংলা বাইবেল", value: (bnBible && bnBible.total) || 0, unit: "পদ", group: "christian", href: prefix + "grantho/christian/bible.html", color: "var(--chart-c2)" },
        { label: "ঋগ্বেদ সংহিতা", value: (rig && rig.total) || 0, unit: "মন্ত্র", group: "hindu", href: prefix + "grantho/hindu/rigveda.html", color: "var(--chart-c3)" },
        { label: "আল-কুরআনুল কারীম", value: (quran && quran.total) || 0, unit: "আয়াত", group: "islam", href: prefix + "quran.html", color: "var(--chart-c1)" },
        { label: "অথর্ববেদ সংহিতা", value: (ath && ath.total) || 0, unit: "মন্ত্র", group: "hindu", href: prefix + "grantho/hindu/atharvaveda.html", color: "var(--chart-c3)" },
        { label: "সামবেদ সংহিতা", value: (sama && sama.total) || 0, unit: "মন্ত্র", group: "hindu", href: prefix + "grantho/hindu/samaveda.html", color: "var(--chart-c3)" },
        { label: "শুক্ল যজুর্বেদ", value: (yaj && yaj.total) || 0, unit: "মন্ত্র", group: "hindu", href: prefix + "grantho/hindu/yajurveda-shukla.html", color: "var(--chart-c3)" },
        { label: "শ্রীমদ্ভগবদ্গীতা", value: (gita && gita.total) || 0, unit: "শ্লোক", group: "hindu", href: prefix + "grantho/hindu/gita.html", color: "var(--chart-c3)" },
        { label: "ছান্দোগ্য উপনিষদ", value: (cha && cha.total) || 0, unit: "মন্ত্র", group: "hindu", href: prefix + "grantho/hindu/chandogya.html", color: "var(--chart-c3)" },
        { label: "বৃহদারণ্যক উপনিষদ", value: (bri && bri.total) || 0, unit: "মন্ত্র", group: "hindu", href: prefix + "grantho/hindu/brihadaranyaka.html", color: "var(--chart-c3)" },
        { label: "শ্বেতাশ্বতর উপনিষদ", value: (shv && shv.total) || 0, unit: "মন্ত্র", group: "hindu", href: prefix + "grantho/hindu/shvetashvatara.html", color: "var(--chart-c3)" },
        { label: "প্রশ্ন উপনিষদ", value: (pra && pra.total) || 0, unit: "মন্ত্র", group: "hindu", href: prefix + "grantho/hindu/prashna.html", color: "var(--chart-c3)" }
      ].filter(function (x) { return x.value > 0; });

      if (!items.length) return;
      var grandTotal = items.reduce(function (s, x) { return s + x.value; }, 0);
      if (sumBadge) sumBadge.textContent = bn(items.length) + " গ্রন্থ · " + bnNum(grandTotal) + " পাঠ্যাংশ";

      if (cardBars) {
        renderHBarChart(cardBars, {
          title: "গ্রন্থভিত্তিক পাঠ্য সংখ্যা",
          badge: bn(items.length) + "টি সংগ্রহ",
          rows: items.map(function (it) {
            return {
              label: it.label,
              value: it.value,
              meta: bnNum(it.value) + " " + it.unit,
              href: it.href,
              color: it.color
            };
          })
        });
      }

      if (cardDonut) {
        var islamSum = items.filter(function (x) { return x.group === "islam"; }).reduce(function (s, x) { return s + x.value; }, 0);
        var chrisSum = items.filter(function (x) { return x.group === "christian"; }).reduce(function (s, x) { return s + x.value; }, 0);
        var hinduSum = items.filter(function (x) { return x.group === "hindu"; }).reduce(function (s, x) { return s + x.value; }, 0);
        renderDonut(cardDonut, {
          title: "ঐতিহ্য অনুযায়ী সংগ্রহ ভাগ",
          badge: "সরাসরি ডেটা",
          centerValue: bnNum(grandTotal),
          centerLabel: "মোট পাঠ্যাংশ",
          items: [
            { label: "খ্রিস্টান (বাইবেল বাংলা+ইংরেজি)", value: chrisSum, href: prefix + "grantho/christian.html", color: "var(--chart-c2)" },
            { label: "ইসলাম (কুরআন ও হাদিস)", value: islamSum, href: prefix + "grantho/islam.html", color: "var(--chart-c1)" },
            { label: "হিন্দু (গীতা, বেদ ও উপনিষদ)", value: hinduSum, href: prefix + "grantho/hindu.html", color: "var(--chart-c3)" }
          ].filter(function (x) { return x.value > 0; })
        });
      }
    });
  }

  function initArchiveCharts() {
    var nodes = document.querySelectorAll("[data-archive-charts]");
    if (!nodes.length) return;
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries, observer) {
        entries.forEach(function (en) {
          if (en.isIntersecting) {
            hydrateArchiveNode(en.target);
            try { (observer || io).unobserve(en.target); } catch (e) {}
          }
        });
      }, { rootMargin: "180px 0px" });
      nodes.forEach(function (el) { io.observe(el); });
    } else {
      nodes.forEach(hydrateArchiveNode);
    }
  }

  window.EadSkeleton = {
    bn: bn,
    bnNum: bnNum,
    esc: esc,
    navRows: navRows,
    readerSkeleton: readerSkeleton,
    searchSkeleton: searchSkeleton,
    chartSkeleton: chartSkeleton,
    renderDonut: renderDonut,
    renderBarChart: renderBarChart,
    renderHBarChart: renderHBarChart,
    hydrateArchiveNode: hydrateArchiveNode
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initArchiveCharts);
  } else {
    initArchiveCharts();
  }
})();
