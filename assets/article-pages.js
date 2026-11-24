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
  function pubTime(el) {
    var v = el.getAttribute('data-publish-at');
    if (!v) return 0;
    var t = Date.parse(v);
    return isFinite(t) ? t : 0;
  }

  var BN = ['০', '১', '২', '৩', '৪', '৫', '৬', '৭', '৮', '৯'];
  function bn(n, pad2) {
    var s = String(n);
    if (pad2 && s.length < 2) s = '0' + s;
    return s.replace(/\d/g, function (d) { return BN[+d]; });
  }

  function formatLeft(ms) {
    var totalSec = Math.max(0, Math.ceil(ms / 1000));
    var days = Math.floor(totalSec / 86400);
    var hours = Math.floor((totalSec % 86400) / 3600);
    var mins = Math.floor((totalSec % 3600) / 60);
    var secs = totalSec % 60;
    var parts = [];
    if (days > 0) parts.push(bn(days, false) + ' দিন');
    parts.push(bn(hours, true) + ' ঘ.');
    parts.push(bn(mins, true) + ' মি.');
    parts.push(bn(secs, true) + ' সে.');
    return 'বাকি: ' + parts.join(' ');
  }

  var scheduled = [];
  cards.forEach(function (c) {
    var t = pubTime(c);
    if (!t) return;
    scheduled.push({ card: c, time: t });
    var link = c.querySelector('.article-card-link');
    if (link && !link._schedBound) {
      link._schedBound = true;
      link.addEventListener('click', function (ev) {
        if (Date.now() < t) {
          ev.preventDefault();
          var bar = c.querySelector('[data-card-timer]');
          var note = c.querySelector('[data-timer-note]');
          if (note) note.hidden = false;
          if (bar) {
            bar.classList.remove('is-nudged');
            setTimeout(function () { bar.classList.add('is-nudged'); }, 15);
          }
        }
      });
    }
  });

  var tickTimer = 0;
  function syncCardTimers() {
    if (!scheduled.length) return;
    var now = Date.now();
    var anyLocked = false;
    scheduled.forEach(function (item) {
      var c = item.card;
      var link = c.querySelector('.article-card-link');
      var bar = c.querySelector('[data-card-timer]');
      var clock = c.querySelector('[data-timer-clock]');
      var note = c.querySelector('[data-timer-note]');
      var lockedMore = c.querySelector('.card-more-locked');
      var openMore = c.querySelector('.card-more-open');
      var diff = item.time - now;

      if (diff <= 0) {
        c.classList.remove('is-scheduled-locked');
        c.classList.add('is-card-unlocked');
        if (link) link.removeAttribute('aria-disabled');
        if (bar) bar.hidden = true;
        if (note) note.hidden = true;
        if (lockedMore) lockedMore.hidden = true;
        if (openMore) openMore.hidden = false;
      } else {
        anyLocked = true;
        c.classList.add('is-scheduled-locked');
        c.classList.remove('is-card-unlocked');
        if (link) link.setAttribute('aria-disabled', 'true');
        if (bar) bar.hidden = false;
        if (clock) clock.textContent = formatLeft(diff);
        if (lockedMore) lockedMore.hidden = false;
        if (openMore) openMore.hidden = true;
      }
    });

    if (!anyLocked) {
      if (tickTimer) { clearInterval(tickTimer); tickTimer = 0; }
    } else {
      if (!tickTimer) tickTimer = setInterval(syncCardTimers, 1000);
    }
  }

  syncCardTimers();
  if (cards.length <= PER_PAGE) return;

  var total = Math.ceil(cards.length / PER_PAGE);
  var pager = document.querySelector('.pager');
  var current = 0;

  function pageFromUrl() {
    var m = /[?&]page=(\d+)/.exec(location.search);
    var n = m ? parseInt(m[1], 10) : 1;
    if (!isFinite(n) || n < 1) n = 1;
    return n > total ? total : n;
  }

  function render(page) {
    if (page === current) return;
    current = page;

    if (!pager) {
      pager = document.createElement('nav');
      pager.className = 'pager';
      pager.setAttribute('aria-label', 'প্রবন্ধের পৃষ্ঠা');
      grid.parentNode.insertBefore(pager, grid.nextSibling);
    }
    pager.hidden = false;

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

  render(pageFromUrl());
})();
