/* ============================================================
   test_ayahs.mjs — কুরআনের আয়াত-সার্চের পরীক্ষা (বাস্তব HTTP-তে)
   ------------------------------------------------------------
   চালাতে:  python3 -m http.server 8781 (আগে) → node tools/test_ayahs.mjs
   ============================================================ */
import { JSDOM, VirtualConsole } from 'jsdom';

// পোর্ট বদলাতে: PORT=8781 node tools/test_ayahs.mjs
const PORT = process.env.PORT || 8778;
const BASE = `http://127.0.0.1:${PORT}/`;
let pass = 0, fail = 0;
const ok = (m) => { pass++; console.log(`  ✓ ${m}`); };
const bad = (m) => { fail++; console.log(`  ✗ ${m}`); };

const vc = new VirtualConsole();
vc.on('jsdomError', (e) => {
  if (!/Could not load|Not implemented/.test(e.message)) console.log('  ⚠', e.message.slice(0, 100));
});

const html = await (await fetch(BASE + 'index.html')).text();
const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  resources: 'usable',
  url: BASE + 'index.html',
  virtualConsole: vc,
  beforeParse(win) {
    // jsdom-এ matchMedia নেই — সাইটের মোশন-স্ক্রিপ্ট এটা চায়
    win.matchMedia = win.matchMedia || function (q) {
      return { matches: false, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} };
    };
    win.requestAnimationFrame = win.requestAnimationFrame || ((cb) => setTimeout(cb, 16));
    win.scrollTo = win.scrollTo || function () {};
    win.IntersectionObserver = win.IntersectionObserver || class { observe() {} unobserve() {} disconnect() {} };
  },
});
const w = dom.window, d = w.document;
await new Promise((r) => setTimeout(r, 1200));

console.log('\nলোড');
w.SITE_SEARCH ? ok(`মূল সূচি ${w.SITE_SEARCH.length} এন্ট্রি`) : bad('মূল সূচি লোড হয়নি');
d.querySelector('.ss') ? ok('সার্চ-মোডাল তৈরি') : bad('মোডাল নেই');

/* বোতামে ক্লিক → আয়াত-সূচি নিজে নামবে */
d.querySelector('[data-search-open]').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
const inp = d.querySelector('.ss-input');

async function search(q, ms = 900) {
  inp.value = q;
  inp.dispatchEvent(new w.Event('input'));
  await new Promise((r) => setTimeout(r, ms));
  return [...d.querySelectorAll('.ss-result')].map((li) => ({
    name: li.querySelector('.ss-name')?.textContent || '',
    href: li.dataset.href,
    tag: li.querySelector('.ss-tag')?.textContent,
    desc: li.querySelector('.ss-desc')?.textContent || '',
  }));
}

console.log('\nআয়াত-সূচি (২.১ MB, চাহিদা-ভিত্তিক)');
const t0 = Date.now();
await search('ধৈর্য', 2500);
const loadMs = Date.now() - t0;
w.SITE_AYAHS ? ok(`আয়াত-সূচি লোড — ${w.SITE_AYAHS.length} আয়াত`) : bad('আয়াত-সূচি লোড হয়নি');
console.log(`     (প্রথম খোঁজে ${loadMs} ms)`);

console.log('\nসার্চ-মান');
const r1 = await search('ধৈর্য');
const ay1 = r1.filter((x) => x.tag === 'আয়াত');
ay1.length > 0 ? ok(`«ধৈর্য» → ${ay1.length}টি আয়াত-ফল`) : bad(`«ধৈর্য» → আয়াত-ফল নেই (${r1.length} ফল)`);
if (ay1[0]) console.log(`     ${ay1[0].name} → ${ay1[0].href}`);
const validHref = (u) => /^quran\.html#\d+:\d+$/.test(u || '');
ay1.every((x) => validHref(x.href)) ? ok('সব আয়াত-URL বৈধ (#সূরা:আয়াত)') : bad('ভুল আয়াত-URL');

/* আরও কিছু শব্দ */
const cases = [
  ['নামাজ', 5],
  ['জান্নাত', 5],
  ['সবর', 0],
  ['সালাত', 5],
];
for (const [q, min] of cases) {
  const r = await search(q);
  const n = r.filter((x) => x.tag === 'আয়াত').length;
  n >= min ? ok(`«${q}» → ${n}টি আয়াত`) : bad(`«${q}» → ${n}টি আয়াত (কমপক্ষে ${min} চাই)`);
}

console.log('\nকর্মক্ষমতা');
// আগে একবার খুঁজে ক্যাশ গরম করি
await search('রহমত', 900);
const t1 = Date.now();
await search('রহমত', 300);   // ক্যাশ-হিট
const cached = Date.now() - t1;
console.log(`     ক্যাশ-হিট খোঁজ (render সহ): ${cached} ms`);
cached < 500 ? ok('পুনরায় খোঁজ দ্রুত') : bad(`পুনরায় খোঁজ ধীর (${cached} ms)`);

console.log('\nনিরাপত্তা');
await search('<img src=x onerror=alert(1)>');
!d.querySelector('.ss-results img') ? ok('XSS ঠেকানো হয়েছে') : bad('XSS ঝুঁকি');

console.log(`\n${fail === 0 ? '✓' : '✗'} পাশ ${pass} · ফেল ${fail}\n`);
w.close();
process.exit(fail === 0 ? 0 : 1);
