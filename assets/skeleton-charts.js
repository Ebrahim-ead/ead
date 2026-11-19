/* ============================================================
   skeleton-charts.js — শিমার স্কেলেটন ইঞ্জিন
   ------------------------------------------------------------
   • ১০০% GPU-কম্পোজিটেড শিমার (CSS transform: translate3d ওভারলে)
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

  window.EadSkeleton = {
    bn: bn,
    bnNum: bnNum,
    esc: esc,
    navRows: navRows,
    readerSkeleton: readerSkeleton,
    searchSkeleton: searchSkeleton
  };
})();
