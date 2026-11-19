#!/usr/bin/env node
/* ============================================================
   test_mobile_drawers.mjs — মোবাইল ড্রয়ার, সাইডবার ভাঁজ, নেভ ও SW ক্যাশ যাচাই
   ------------------------------------------------------------
   চালাতে:  node tools/test_mobile_drawers.mjs
   ============================================================ */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
let pass = 0, fail = 0;
const ok = (m) => { pass++; console.log(`  ✓ ${m}`); };
const bad = (m, extra) => { fail++; console.log(`  ✗ ${m}${extra ? ' — ' + extra : ''}`); };
const check = (m, cond, extra) => (cond ? ok(m) : bad(m, extra));
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

function localFetch(url) {
  const clean = String(url).split('?')[0].split('#')[0];
  let rel = clean.replace(/^https?:\/\/[^/]+/, '');
  rel = rel.replace(/^\/ead\//, '').replace(/^\/+/, '');
  rel = rel.replace(/^(?:grantho\/(?:hindu|christian|buddhist)\/)/, '');
  const idxAssets = rel.indexOf('assets/');
  if (idxAssets > -1) rel = rel.slice(idxAssets);
  const fp = path.join(ROOT, rel);
  if (!fs.existsSync(fp)) {
    return Promise.resolve({ ok: false, status: 404, text: async () => '', json: async () => ({}) });
  }
  const raw = fs.readFileSync(fp, 'utf8');
  return Promise.resolve({
    ok: true,
    status: 200,
    text: async () => raw,
    json: async () => JSON.parse(raw),
  });
}

function makeNarrowMatchMedia(maxW) {
  return (query) => {
    const mMax = /max-width\s*:\s*(\d+)px/.exec(query);
    const mMin = /min-width\s*:\s*(\d+)px/.exec(query);
    let matches = false;
    if (mMax) matches = maxW <= Number(mMax[1]);
    if (mMin) matches = maxW >= Number(mMin[1]);
    return { matches, media: query, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} };
  };
}

function bootDom(relHtml, width, height = 640) {
  const html = fs.readFileSync(path.join(ROOT, relHtml), 'utf8');
  const dom = new JSDOM(html, {
    url: `http://localhost/ead/${relHtml}`,
    runScripts: 'outside-only',
    pretendToBeVisual: true,
  });
  const w = dom.window;
  Object.defineProperty(w, 'innerWidth', { configurable: true, writable: true, value: width });
  Object.defineProperty(w, 'innerHeight', { configurable: true, writable: true, value: height });
  Object.defineProperty(w, 'matchMedia', { configurable: true, writable: true, value: makeNarrowMatchMedia(width) });
  Object.defineProperty(w, 'fetch', { configurable: true, writable: true, value: localFetch });
  w.HTMLElement.prototype.scrollIntoView = function () {};
  w.scrollTo = function () {};
  return { dom, w, d: w.document };
}

function mediaBlock(css, query) {
  const idx = css.indexOf(query);
  if (idx < 0) return '';
  let i = css.indexOf('{', idx), depth = 0, out = '';
  for (; i < css.length; i++) {
    const c = css[i];
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (depth === 0) return out; }
    out += c;
  }
  return out;
}

console.log('\n১. CSS ও HTML স্ট্রাকচার');
{
  const hCss = fs.readFileSync(path.join(ROOT, 'assets/hadith/hadith.css'), 'utf8');
  const h960 = mediaBlock(hCss, '@media(max-width:960px)');
  check('hadith.css: .h-toolbar মোবাইলে static (bottom:0 নেই)', /\.h-toolbar\{position:static/.test(h960) && !/bottom:0/.test(h960));
  check('hadith.css: 560px মিডিয়াতে 1fr জোর করে না', !/\.h-books\{grid-template-columns:1fr\}/.test(mediaBlock(hCss, '@media(max-width:560px)')));
  check('hadith.css: .h-list flex:1 1 0%', /\.h-list\{flex:1 1 0%;min-height:/.test(hCss));
  check('hadith.css: .h-books-wrap.collapsed নিয়ম আছে', /\.h-books-wrap\.collapsed \.h-books\{display:none\}/.test(hCss));
  check('hadith.css: --h-stick-top ব্যবহৃত', /var\(--h-stick-top/.test(hCss));
  check('hadith.css: মোবাইলে 16px ইনপুট', /\.h-aside-filter input[^{]*\{font-size:16px/.test(h960));

  const qCss = fs.readFileSync(path.join(ROOT, 'assets/quran/quran.css'), 'utf8');
  const q960 = mediaBlock(qCss, '@media(max-width:960px)');
  check('quran.css: .q-toolbar মোবাইলে static', /\.q-toolbar\{position:static/.test(q960) && !/bottom:0/.test(q960));
  check('quran.css: .q-list flex:1 1 0%', /\.q-list\{flex:1 1 0%;min-height:/.test(qCss));
  check('quran.css: --q-stick-top ব্যবহৃত', /var\(--q-stick-top/.test(qCss));
  check('quran.css: মোবাইলে 16px ইনপুট', /\.q-aside-filter input[^{]*\{font-size:16px/.test(q960));

  const gCss = fs.readFileSync(path.join(ROOT, 'assets/grantho/grantho.css'), 'utf8');
  const g980 = mediaBlock(gCss, '@media(max-width:980px)');
  check('grantho.css: .g-toolbar মোবাইলে static (top:62px নেই)', /\.g-toolbar\{position:static/.test(g980) && !/top:62px/.test(g980));
  check('grantho.css: --g-stick-top ব্যবহৃত', /var\(--g-stick-top/.test(gCss));
  check('grantho.css: মোবাইলে 16px সার্চ', /\.g-search input\{font-size:16px\}/.test(g980));

  const nCss = fs.readFileSync(path.join(ROOT, 'assets/nav-motion.css'), 'utf8');
  const n1080 = mediaBlock(nCss, '@media(max-width:1080px)');
  check('nav-motion.css: মোবাইলে .nav-item গ্রিড সারিবদ্ধ', /\.nav-item\{display:grid;grid-template-columns:minmax\(0,1fr\) 46px/.test(n1080));
  check('nav-motion.css: .nav-sub full-span (grid-column:1 / -1)', /\.nav-sub\{grid-column:1 \/ -1/.test(n1080));
  check('nav-motion.css: .nav-sub-toggle 46x46px টাচ টার্গেট', /\.nav-sub-toggle\{width:46px;height:46px/.test(n1080));
}

console.log('\n২. হাদিস মোবাইল ড্রয়ার ও কিতাব-সঙ্কোচন');
{
  const { w, d } = bootDom('hadith.html', 360, 640);
  w.eval(fs.readFileSync(path.join(ROOT, 'assets/hadith/hadith.js'), 'utf8'));
  await wait(80);
  check('html.h-drawer সক্রিয় (360px)', d.documentElement.classList.contains('h-drawer'));

  d.getElementById('h-drawer-btn').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await wait(30);
  check('ড্রয়ার খোলে (.h-aside.open)', d.getElementById('h-aside').classList.contains('open'));
  check('body scroll লক হয়', d.body.style.overflow === 'hidden');
  check('ক্লোজ (✕) বোতাম আছে', !!d.getElementById('h-drawer-close'));

  const booksToggle = d.getElementById('h-books-toggle');
  const booksWrap = d.getElementById('h-books-wrap');
  booksToggle.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  check('কিতাব-টগলে ভাঁজ হয় (.collapsed)', booksWrap.classList.contains('collapsed') && booksToggle.getAttribute('aria-expanded') === 'false');
  booksToggle.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  check('কিতাব-টগলে আবার খোলে', !booksWrap.classList.contains('collapsed') && booksToggle.getAttribute('aria-expanded') === 'true');

  const muslimBtn = d.querySelector('#h-books [data-book="muslim"]');
  muslimBtn.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await wait(50);
  check('ড্রয়ারের ভেতরে কিতাব বাছাইয়ে ড্রয়ার খোলা থাকে', d.getElementById('h-aside').classList.contains('open'));
  check('কিতাব বাছাইয়ের পর ৭ কিতাব ভাঁজ হয়ে অধ্যায় দেখায়', booksWrap.classList.contains('collapsed'));
  check('নতুন কিতাবের অধ্যায়-তালিকা রেন্ডার হয়েছে', d.querySelectorAll('#h-chapter-list .h-ch').length > 5);

  d.querySelector('#h-chapter-list [data-ch="2"]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  await wait(50);
  check('অধ্যায়ে ক্লিকে ড্রয়ার বন্ধ ও scroll আনলক হয়', !d.getElementById('h-aside').classList.contains('open') && d.body.style.overflow === '');

  const pagerDrawer = d.querySelector('.h-pager [data-open-drawer]');
  check('পেজারে «☰ কিতাব ও অধ্যায়» বোতাম আছে', !!pagerDrawer);
  pagerDrawer.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  check('পেজার-বোতামে ড্রয়ার খোলে', d.getElementById('h-aside').classList.contains('open'));

  d.getElementById('h-drawer-close').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  check('✕ বোতামে ড্রয়ার বন্ধ হয়', !d.getElementById('h-aside').classList.contains('open'));

  // সার্চ খুললে ড্রয়ার বন্ধ হওয়া উচিত
  d.getElementById('h-drawer-btn').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  w.dispatchEvent(new w.CustomEvent('ead:overlay-open', { detail: 'search' }));
  check('সার্চ খুললে হাদিস-ড্রয়ার বন্ধ হয়', !d.getElementById('h-aside').classList.contains('open'));
}

console.log('\n৩. কুরআন মোবাইল ড্রয়ার');
{
  const { w, d } = bootDom('quran.html', 390, 844);
  w.eval(fs.readFileSync(path.join(ROOT, 'assets/quran/quran.js'), 'utf8'));
  await wait(80);
  check('html.q-drawer সক্রিয় (390px)', d.documentElement.classList.contains('q-drawer'));
  d.getElementById('q-drawer-btn').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  check('কুরআন-ড্রয়ার খোলে', d.getElementById('q-aside').classList.contains('open') && d.body.style.overflow === 'hidden');
  check('পেজারে «☰ সূরাসমূহ» বোতাম', !!d.querySelector('.q-pager [data-open-drawer]'));
  d.getElementById('q-drawer-close').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  check('✕ বোতামে কুরআন-ড্রয়ার বন্ধ ও scroll আনলক', !d.getElementById('q-aside').classList.contains('open') && d.body.style.overflow === '');
}

console.log('\n৪. গীতা, বাংলা বাইবেল ও English Bible ভাঁজ (মোবাইল বনাম ডেস্কটপ)');
{
  // গীতা (অ-গ্রুপযুক্ত গ্রন্থ) ফোনে স্বয়ংক্রিয় ভাঁজ
  const { w, d } = bootDom('grantho/hindu/gita.html', 390, 844);
  w.eval(fs.readFileSync(path.join(ROOT, 'assets/grantho/grantho.js'), 'utf8'));
  await wait(80);
  const gSide = d.getElementById('g-side');
  const gNow = d.getElementById('g-side-now');
  check('গীতা: ফোনে #g-side স্বয়ংক্রিয় ভাঁজ হয়', gSide && gSide.classList.contains('folded'));
  check('গীতা: ভাঁজ অবস্থায় #g-side-now বর্তমান অধ্যায় দেখায়', gNow && !gNow.hidden && gNow.textContent.trim().length > 0, gNow?.textContent);

  // English Bible ফোনে .folded ও desktop-এ unfolded
  const eb = bootDom('grantho/christian/english-bible.html', 390, 844);
  const ebHtml = fs.readFileSync(path.join(ROOT, 'grantho/christian/english-bible.html'), 'utf8');
  const i = ebHtml.indexOf('English Bible reader');
  eb.w.eval(ebHtml.slice(ebHtml.lastIndexOf('<script>', i) + 8, ebHtml.indexOf('</script>', i)));
  await wait(80);
  const eSide = eb.d.getElementById('e-side');
  const eBody = eb.d.getElementById('e-side-body');
  const eToggle = eb.d.getElementById('e-side-toggle');
  check('English Bible: ফোনে #e-side স্বয়ংক্রিয় .folded', eSide.classList.contains('folded') && eBody.hidden);
  eToggle.dispatchEvent(new eb.w.MouseEvent('click', { bubbles: true }));
  check('English Bible: টগল করলে .folded ও hidden একসাথে বদলায়', !eSide.classList.contains('folded') && !eBody.hidden && eToggle.getAttribute('aria-expanded') === 'true');
  eToggle.dispatchEvent(new eb.w.MouseEvent('click', { bubbles: true }));
  check('English Bible: পুনরায় টগলে ভাঁজ ও #e-side-now দৃশ্যমান', eSide.classList.contains('folded') && !eb.d.getElementById('e-side-now').hidden);

  // বাংলা বাইবেল ফোনের localStorage স্টোরেজের পরেও ডেস্কটপে খোলা থাকে
  const br = bootDom('grantho/christian/bible.html', 1280, 800);
  br.w.localStorage.setItem('grantho.bible.v1', JSON.stringify({ fold: true, book: 1 }));
  br.w.eval(fs.readFileSync(path.join(ROOT, 'assets/grantho/bible-reader.js'), 'utf8'));
  await wait(80);
  check('বাংলা বাইবেল: ডেস্কটপে (1280px) সাইডবার ভাঁজ থাকে না', !br.d.getElementById('g-side').classList.contains('folded'));
}

console.log('\n৫. মোবাইল নেভ ও সার্চ ওভারলে সমন্বয়');
{
  const { w, d } = bootDom('index.html', 390, 844);
  w.eval(fs.readFileSync(path.join(ROOT, 'assets/nav-motion.js'), 'utf8'));
  w.eval(fs.readFileSync(path.join(ROOT, 'assets/site-search.js'), 'utf8'));
  const burger = d.querySelector('.burger');
  const nav = d.getElementById('site-nav');
  burger.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  check('মোবাইল নেভ মেনু খোলে', nav.classList.contains('open'));
  d.querySelector('[data-search-open]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  check('সার্চ মোডাল খুললে খোলা মোবাইল নেভ বন্ধ হয়', d.documentElement.classList.contains('ss-open') && !nav.classList.contains('open'));
  d.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  check('Escape চাপলে সার্চ বন্ধ হয়', !d.documentElement.classList.contains('ss-open'));
}

console.log('\n৬. সার্ভিস ওয়ার্কার ক্যাশ রাউটিং ও পুরোনো JS/CSS পরিষ্কার');
{
  const swSrc = fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf8');
  const cachesMap = new Map();
  class FakeCache {
    constructor() { this.m = new Map(); }
    async put(req, res) { this.m.set(typeof req === 'string' ? req : req.url, res); }
    async add() {}
    async keys() { return [...this.m.keys()].map((u) => ({ url: u })); }
    async delete(req) { return this.m.delete(typeof req === 'string' ? req : req.url); }
  }
  const fakeCaches = {
    open: async (n) => { if (!cachesMap.has(n)) cachesMap.set(n, new FakeCache()); return cachesMap.get(n); },
    keys: async () => [...cachesMap.keys()],
    delete: async (n) => cachesMap.delete(n),
  };
  const listeners = {};
  const fetchCalls = [];
  const ctx = vm.createContext({
    caches: fakeCaches,
    Promise,
    URL,
    console,
    fetch: async (req, opts) => {
      fetchCalls.push({ url: typeof req === 'string' ? req : req.url, opts });
      return { ok: true, clone: () => ({ ok: true }) };
    },
    Request: function (u) { this.url = u; },
    Response: function () {},
    self: {
      location: { origin: 'https://ebrahim-ead.github.io' },
      registration: { navigationPreload: { enable: async () => {} } },
      clients: { claim: async () => {} },
      skipWaiting: async () => {},
      addEventListener: (ev, fn) => { listeners[ev] = fn; },
    },
  });
  vm.runInContext(swSrc, ctx);
  fakeCaches.match = async (req) => {
    const k = typeof req === 'string' ? req : req.url;
    for (const c of cachesMap.values()) { if (c.m.has(k)) return c.m.get(k); }
    return undefined;
  };

  const isData = ctx.isData;
  const isShell = ctx.isShellAsset;
  const u = (p) => new URL('https://ebrahim-ead.github.io' + p);
  check('isData: hadith.css/js ডেটা-ক্যাশে যায় না', !isData(u('/ead/assets/hadith/hadith.css')) && !isData(u('/ead/assets/hadith/hadith.js')));
  check('isData: quran/grantho JS/CSS ডেটা-ক্যাশে যায় না', !isData(u('/ead/assets/quran/quran.js')) && !isData(u('/ead/assets/grantho/grantho.css')) && !isData(u('/ead/assets/grantho/bible-reader.js')));
  check('isShellAsset: reader CSS/JS (ও ?v= সহ) শেল-ক্যাশে যায়', isShell(u('/ead/assets/hadith/hadith.css')) && isShell(u('/ead/assets/grantho/grantho.js')) && isShell(u('/ead/assets/grantho/grantho.css?v=df282762')));
  check('isData: JSON ডেটা ও search-ayahs.js ডেটা-ক্যাশে থাকে', isData(u('/ead/assets/hadith/data/index.json')) && isData(u('/ead/assets/search-ayahs.js')));

  let cssResP;
  listeners.fetch({
    request: { method: 'GET', mode: 'no-cors', url: 'https://ebrahim-ead.github.io/ead/assets/grantho/grantho.css?v=df282762' },
    respondWith: (p) => { cssResP = p; },
  });
  await cssResP;
  const cssFetch = fetchCalls.find((c) => c.url.includes('grantho.css?v=df282762'));
  check('fetch: CSS মিস হলে cache:no-cache দিয়ে নেট থেকে আসে', !!cssFetch && cssFetch.opts && cssFetch.opts.cache === 'no-cache');

  // সিমুলেটেড activate: ead-shell-v20 মুছবে, ead-data-v11-এর ভেতরের পুরোনো CSS/JS মুছবে, কিন্তু JSON অটুট থাকবে
  const oldShell = await fakeCaches.open('ead-shell-v20');
  await oldShell.put('https://ebrahim-ead.github.io/ead/assets/site.css', {});
  const dataCache = await fakeCaches.open(ctx.DATA_CACHE);
  await dataCache.put('https://ebrahim-ead.github.io/ead/assets/hadith/hadith.css', {});
  await dataCache.put('https://ebrahim-ead.github.io/ead/assets/grantho/grantho.js', {});
  await dataCache.put('https://ebrahim-ead.github.io/ead/assets/hadith/data/index.json', {});
  await dataCache.put('https://ebrahim-ead.github.io/ead/assets/search-ayahs.js', {});

  let waitP = Promise.resolve();
  listeners.activate({ waitUntil: (p) => { waitP = p; } });
  await waitP;
  const remNames = await fakeCaches.keys();
  const remDataKeys = (await dataCache.keys()).map((k) => k.url);
  check('activate: পুরোনো ead-shell-v20 মুছে গেছে', !remNames.includes('ead-shell-v20'));
  check('activate: DATA_CACHE অটুট আছে', remNames.includes(ctx.DATA_CACHE));
  check('activate: DATA_CACHE থেকে পুরোনো CSS/JS মুছে গেছে', !remDataKeys.some((x) => x.endsWith('.css') || x.endsWith('grantho.js')));
  check('activate: DATA_CACHE-এর JSON ও search-ayahs.js অক্ষত আছে', remDataKeys.some((x) => x.endsWith('index.json')) && remDataKeys.some((x) => x.endsWith('search-ayahs.js')));
}

console.log(`\n${fail ? '✗' : '✓'} পাশ ${pass} · ফেল ${fail}`);
process.exit(fail ? 1 : 0);
