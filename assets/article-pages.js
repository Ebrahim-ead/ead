/* ============================================================
   article-pages.js — প্রবন্ধ-তালিকার পৃষ্ঠা-বিভাজন
   ------------------------------------------------------------
   প্রতিটি পৃষ্ঠায় ৮টি কার্ড; বাকিগুলো ?page=N-এ।
   · নতুন কার্ড যোগ করলেই পৃষ্ঠা-সংখ্যা নিজে থেকে বাড়ে — হাতে
     পেজার বানাতে হয় না, আলাদা HTML ফাইলও লাগে না।
   · JS না চললে সব কার্ড একসঙ্গেই দেখা যায় (কিছু হারায় না)।
   · ?page=N শেয়ারযোগ্য; ব্রাউজারের Back/Forward কাজ করে।
   ============================================================ */
(function () {
  'use strict';

  var PER_PAGE = 8;
  var grid = document.querySelector('.article-list-grid');
  if (!grid) return;

  var cards = [].slice.call(grid.querySelectorAll(':scope > .article-card'));
  if (cards.length <= PER_PAGE) return;          // এক পৃষ্ঠাতেই শেষ — কিছু করতে হবে না

  var total = Math.ceil(cards.length / PER_PAGE);
  var BN = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'];
  function bn(n) { return String(n).replace(/\d/g, function (d) { return BN[+d]; }); }

  function pageFromUrl() {
    var m = /[?&]page=(\d+)/.exec(location.search);
    var n = m ? parseInt(m[1], 10) : 1;
    if (!isFinite(n) || n < 1) n = 1;
    return n > total ? total : n;
  }

  /* পেজার বানাই (আগে থেকে থাকলে নতুন করে লিখি) */
  var pager = document.querySelector('.pager');
  if (!pager) {
    pager = document.createElement('nav');
    pager.className = 'pager';
    pager.setAttribute('aria-label', 'প্রবন্ধের পৃষ্ঠা');
    grid.parentNode.insertBefore(pager, grid.nextSibling);
  }

  var current = 0;

  function render(page) {
    if (page === current) return;
    current = page;

    /* কার্ড দেখানো/লুকানো — hidden অ্যাট্রিবিউট, তাই CSS-এর সংঘর্ষ নেই */
    cards.forEach(function (c, i) {
      var show = i >= (page - 1) * PER_PAGE && i < page * PER_PAGE;
      c.hidden = !show;
    });

    /* পেজার */
    pager.textContent = '';
    for (var n = 1; n <= total; n++) {
      if (n > 1) {
        var sep = document.createElement('span');
        sep.className = 'pager-sep';
        sep.setAttribute('aria-hidden', 'true');
        sep.textContent = '|';
        pager.appendChild(sep);
      }
      var a = document.createElement('a');
      a.className = 'pager-num';
      a.href = n === 1 ? location.pathname : location.pathname + '?page=' + n;
      a.textContent = bn(n);
      a.setAttribute('aria-label', 'পৃষ্ঠা ' + bn(n));
      if (n === page) a.setAttribute('aria-current', 'page');
      a.addEventListener('click', function (ev) {
        var p = +this.getAttribute('data-p');
        if (!p || ev.metaKey || ev.ctrlKey || ev.shiftKey) return;
        ev.preventDefault();
        go(p);
      });
      a.setAttribute('data-p', n);
      pager.appendChild(a);
    }

    /* স্ক্রিন-রিডারকে জানাই */
    var live = document.getElementById('ap-live');
    if (!live) {
      live = document.createElement('p');
      live.id = 'ap-live';
      live.className = 'sr-only';
      live.setAttribute('role', 'status');
      live.setAttribute('aria-live', 'polite');
      pager.parentNode.insertBefore(live, pager);
    }
    var count = page === total ? (cards.length - (total - 1) * PER_PAGE) : PER_PAGE;
    live.textContent = 'পৃষ্ঠা ' + bn(page) + ' / ' + bn(total) + ' — ' +
      bn(count) + 'টি প্রবন্ধ';
  }

  function go(page) {
    render(page);
    try {
      var url = page === 1 ? location.pathname : location.pathname + '?page=' + page;
      history.pushState({ page: page }, '', url);
    } catch (e) {}
    grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  window.addEventListener('popstate', function () { render(pageFromUrl()); });

  /* পেজার-লিংকে কী-বোর্ড/মাঝের-ক্লিক স্বাভাবিক থাকুক */
  render(pageFromUrl());
})();
