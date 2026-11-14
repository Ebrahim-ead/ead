/* ============================================================
   test_search.mjs — সাইট-সার্চের স্বয়ংক্রিয় পরীক্ষা
   ------------------------------------------------------------
   চালাতে:  node tools/test_search.mjs
   যা যাচাই করে:
     · সূচি লোড হয় ও आकार ঠিক
     · প্রতিটি পাতায় বোতাম ও স্ক্রিপ্ট আছে
     · সার্চ-ফল প্রাসঙ্গিক (সূরা, হাদিস, বই, প্রবন্ধ)
     · কোনো ইনজেকশন ঝুঁকি নেই (innerHTML-এ ব্যবহারকারীর লেখা যায় না)
     · লিংক-লক্ষ্য বৈধ hash/পাতা
   ============================================================ */
import { JSDOM } from 'jsdom';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '..');
let pass = 0, fail = 0;
const ok = (m) => { pass++; console.log(`  ✓ ${m}`); };
const bad = (m) => { fail++; console.log(`  ✗ ${m}`); };

/* ── ১. সূচি ── */
console.log('\nসূচি');
const idxSrc = fs.readFileSync(path.join(ROOT, 'assets/search-index.js'), 'utf8');
const dom0 = new JSDOM('<!doctype html><body></body>', { runScripts: 'outside-only' });
dom0.window.eval(idxSrc);
const DATA = dom0.window.SITE_SEARCH;
if (Array.isArray(DATA) && DATA.length > 100) ok(`সূচি লোড — ${DATA.length} এন্ট্রি`);
else bad(`সূচি লোড হয়নি (${DATA && DATA.length})`);

const bytes = fs.statSync(path.join(ROOT, 'assets/search-index.js')).size;
if (bytes < 300 * 1024) ok(`আকার ${(bytes / 1024).toFixed(0)} KB (< 300 KB)`);
else bad(`আকার বেশি — ${(bytes / 1024).toFixed(0)} KB`);

const types = {};
DATA.forEach((r) => { types[r.t] = (types[r.t] || 0) + 1; });
console.log(`     ${Object.entries(types).map(([k, v]) => `${k}:${v}`).join(' · ')}`);
const need = ['page', 'quran', 'hadith', 'grantho'];
need.every((t) => types[t]) ? ok('সব ধরন আছে') : bad('কোনো ধরন অনুপস্থিত');

/* প্রতিটি এন্ট্রির বাধ্যতামূলক ক্ষেত্র */
const malformed = DATA.filter((r) => !r.n || !r.u || !r.t);
malformed.length === 0 ? ok('সব এন্ট্রিতে নাম ও URL আছে') : bad(`${malformed.length}টি ভাঙা এন্ট্রি`);

/* ── ২. প্রতিটি পাতায় তারের সংযোগ ── */
console.log('\nপাতা-সংযোগ');
const pages = fs.readdirSync(ROOT).filter((f) => f.endsWith('.html') && f !== 'atheism-2.html');
const missingBtn = [], missingScript = [];
for (const f of pages) {
  const s = fs.readFileSync(path.join(ROOT, f), 'utf8');
  if (!s.includes('data-search-open')) missingBtn.push(f);
  if (!s.includes('assets/site-search.js')) missingScript.push(f);
}
missingBtn.length === 0 ? ok(`${pages.length}টি পাতায় বোতাম`) : bad(`বোতাম নেই: ${missingBtn.join(', ')}`);
missingScript.length === 0 ? ok(`${pages.length}টি পাতায় স্ক্রিপ্ট`) : bad(`স্ক্রিপ্ট নেই: ${missingScript.join(', ')}`);

/* ── ৩. সার্চ-লজিক (ব্রাউজারে চালিয়ে) ── */
console.log('\nসার্চ-ফল');
const page = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const dom = new JSDOM(page, { runScripts: 'dangerously', url: 'https://ebrahim-ead.github.io/ead/' });
const w = dom.window;
const d = w.document;

// সার্চ এখন সূচি চাহিদা-মতো লোড করে (document.currentScript → null in jsdom),
// তাই পাথটা হাতে বলে দিই; jsdom fetch করতে পারে না বলে সূচিটাও হাতে ইনজেক্ট করি।
w.__SEARCH_INDEX_PATH = 'assets/search-index.js';
w.SITE_SEARCH = undefined;
for (const src of ['assets/search-index.js', 'assets/site-search.js']) {
  const el = d.createElement('script');
  el.textContent = fs.readFileSync(path.join(ROOT, src), 'utf8');
  d.body.appendChild(el);
}

const modal = d.querySelector('.ss');
modal ? ok('মোডাল তৈরি হয়েছে') : bad('মোডাল নেই');
const btn = d.querySelector('[data-search-open]');
btn ? ok('সার্চ-বোতাম পাওয়া গেছে') : bad('সার্চ-বোতাম নেই');

function run(query) {
  const input = d.querySelector('.ss-input');
  const root = d.querySelector('.ss');
  // মোডাল খুলি — এখন সূচি চাহিদা-মতো নামে, open() ডাকলেই তা হয়
  const btn = d.querySelector('[data-search-open]');
  if (root.hidden) btn.dispatchEvent(new w.Event('click', { bubbles: true }));
  root.hidden = false;
  input.value = query;
  input.dispatchEvent(new w.Event('input'));
  // debounce ৯০ms — opoড়া
  const t0 = Date.now();
  while (Date.now() - t0 < 0) { /* noop */ }
  return new Promise((res) => setTimeout(() => res(collect()), 140));
}
function collect() {
  return [...d.querySelectorAll('.ss-result')].map((li) => ({
    name: li.querySelector('.ss-name')?.textContent || '',
    href: li.dataset.href,
    tag: li.querySelector('.ss-tag')?.textContent
  }));
}

const cases = [
  ['ইয়াসিন', (r) => r.some((x) => x.name.includes('ইয়াস') && x.name.includes('ন'))],
  ['বুখারী', (r) => r.some((x) => x.name.includes('বুখারী'))],
  ['ফিলিস্তিন', (r) => r.some((x) => x.name.includes('ফিলিস্তিন'))],
  ['বাইবেল', (r) => r.some((x) => x.name.includes('বাইবেল'))],
  ['গীতা', (r) => r.some((x) => x.name.includes('গীতা'))],
  ['zxqwv', (r) => r.length === 0],
];

for (const [q, test] of cases) {
  const r = await run(q);
  test(r) ? ok(`«${q}» → ${r.length} ফল`) : bad(`«${q}» → অপ্রাসঙ্গিক ${r.length} ফল: ${r.slice(0, 3).map((x) => x.name).join(' | ')}`);
}

/* ── ৩ক. গ্রন্থ (বাইবেল) ── */
console.log('\nগ্রন্থ-সার্চ');
const grantho = DATA.filter((r) => r.t === 'grantho');
grantho.length >= 100 ? ok(`${grantho.length}টি গ্রন্থ-এন্ট্রি`) : bad(`গ্রন্থ-এন্ট্রি কম: ${grantho.length}`);
const bibl = grantho.filter((r) => r.u.startsWith('grantho/christian/bible.html'));
bibl.length >= 40 ? ok(`বাইবেলের ${bibl.length}টি বই সূচিতে`) : bad(`বাইবেল-এন্ট্রি কম: ${bibl.length}`);
const noEmpty = grantho.every((r) => /[1-9]\d*টি শ্লোক/.test(r.d || ''));
noEmpty ? ok('ফাঁকা (0 শ্লোক) এন্ট্রি নেই') : bad('ফাঁকা এন্ট্রি আছে (count=0)');
for (const q of ['মথি', 'আদিপুস্তক', 'যোহন']) {
  const r = await run(q);
  const hit = r.some((x) => x.href && x.href.startsWith('grantho/christian/bible.html'));
  hit ? ok(`«${q}» → বাইবেলের বই মিলেছে`) : bad(`«${q}» → বাইবেলের বই মেলেনি`);
}

/* ── ৩খ. হাইলাইট ── */
console.log('\nহাইলাইট');
await run('সূরা');
const marks = d.querySelectorAll('.ss-results mark');
marks.length > 0 ? ok(`${marks.length}টি মিল-অংশ <mark>-এ`) : bad('হাইলাইট নেই');
const markText = marks[0]?.textContent || '';
markText.includes('সূরা') ? ok(`হাইলাইট-লেখা সঠিক «${markText}»`) : bad(`ভুল হাইলাইট «${markText}»`);

/* ── ৪. নিরাপত্তা: ব্যবহারকারীর লেখা HTML হিসেবে ঢোকে না ── */
console.log('\nনিরাপত্তা');
const xs = await run('<img src=x onerror=alert(1)>');
const injected = d.querySelector('.ss-results img');
!injected ? ok('HTML-ইনজেকশন ঠেকানো হয়েছে') : bad('XSS ঝুঁকি — <img> ঢুকে গেছে');

/* ── ৫. URL-লক্ষ্য বৈধ ── */
console.log('\nলিংক-লক্ষ্য');
const badUrls = DATA.filter((r) => {
  const base = r.u.split('#')[0].split('?')[0];
  return base && !fs.existsSync(path.join(ROOT, base));
});
badUrls.length === 0 ? ok('সব URL বিদ্যমান ফাইলে যায়') : bad(`${badUrls.length}টি ভাঙা: ${badUrls.slice(0, 3).map((r) => r.u).join(', ')}`);

/* ── ফলাফল ── */
console.log(`\n${fail === 0 ? '✓' : '✗'} পাশ ${pass} · ফেল ${fail}\n`);
process.exit(fail === 0 ? 0 : 1);
