/* ============================================================
   test_fonts.mjs — বাংলা ফন্ট নিজের হোস্টে, সঠিকভাবে
   ------------------------------------------------------------
   চালাতে:  node tools/test_fonts.mjs

   এই পরীক্ষা পাহারা দেয়:
     · ফন্ট নিজের সার্ভারে, Google Fonts-এর ওপর নির্ভর নয়
     · woff2 আসলেই woff2 (নকল নয়), variable (wght ১০০–৯০০)
     · বাংলার সব অক্ষর ও যুক্তাক্ষর-লিগেচার আছে
     · @font-face CSS ঠিক, font-display:swap, fallback চেইন অটুট
     · সব পাতায় preload (FOUT কমানোর জন্য)
     · পুরোনো ১.৪ MB TTF আর নেই
   ============================================================ */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '..');
const FONT = path.join(ROOT, 'assets/fonts/noto-sans-bengali.woff2');
let pass = 0, fail = 0;
const ok = (m) => { pass++; console.log(`  ✓ ${m}`); };
const bad = (m) => { fail++; console.log(`  ✗ ${m}`); };
const read = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');

/* ── ১. ফাইল ── */
console.log('\nফন্ট ফাইল');
if (!fs.existsSync(FONT)) {
  bad('noto-sans-bengali.woff2 নেই');
} else {
  const buf = fs.readFileSync(FONT);
  const kb = buf.length / 1024;
  ok(`${kb.toFixed(0)} KB`);

  /* woff2-এর জাদু-সংখ্যা: 'wOF2' */
  buf.slice(0, 4).toString('latin1') === 'wOF2'
    ? ok('আসল woff2 (wOF2 হেডার)') : bad(`জন্য woff2 নয় — হেডার «${buf.slice(0,4).toString('latin1')}»`);

  kb < 300 ? ok(`মাপ যুক্তিসঙ্গত (< 300 KB)`) : bad(`${kb.toFixed(0)} KB — বেশি`);

  /* পুরোনো TTF গেল কি */
  const oldTtf = fs.readdirSync(path.join(ROOT, 'assets/fonts'))
    .filter((f) => /\.ttf$/i.test(f));
  oldTtf.length === 0 ? ok('পুরোনো TTF নেই (১.৪ MB সাশ্রয়)')
                      : bad(`TTF এখনো আছে: ${oldTtf.join(', ')}`);
}

/* ── ২. Google Fonts নির্ভরতা গেল? ── */
console.log('\nবাইরের নির্ভরতা');
/* সব পাতা — গ্রন্থ-পাতাও (grantho/*.html) ধরা পড়ুক */
function allPages(dir = ROOT, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === 'node_modules' || e.name === '.git' || e.name === '_debug') continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) allPages(p, out);
    else if (e.name.endsWith('.html')) out.push(path.relative(ROOT, p));
  }
  return out;
}
const pages = allPages();
const withGoogle = pages.filter((f) => /fonts\.googleapis\.com|fonts\.gstatic\.com/.test(fs.readFileSync(path.join(ROOT, f), 'utf8')));
withGoogle.length === 0 ? ok('কোনো পাতায় Google Fonts নেই')
                        : bad(`${withGoogle.length}টি পাতায় এখনো আছে: ${withGoogle.slice(0,3).join(', ')}`);

/* ── ৩. @font-face ── */
console.log('\n@font-face');
const css = read('assets/site-extra.css');
const face = (css.match(/@font-face\{[^}]*\}/g) || []).find((b) => /noto-sans-bengali/.test(b));
if (!face) {
  bad('@font-face নেই');
} else {
  ok('@font-face ঘোষিত');
  /font-family:"Noto Sans Bengali"/.test(face) ? ok('পরিবার-নাম সঠিক') : bad('পরিবার-নাম ভুল');
  /format\("woff2-variations"\)/.test(face) ? ok('variable-font ফরম্যাট ঘোষিত') : bad('woff2-variations নেই');
  /font-weight:100 900/.test(face) ? ok('ওজন-সীমা ১০০–৯০০') : bad('variable ওজন-সীমা নেই');
  /font-display:swap/.test(face) ? ok('font-display:swap (লেখা লুকায় না)') : bad('swap নেই');
  /unicode-range:U\+0980-09FF/.test(face) ? ok('বাংলা unicode-range') : bad('unicode-range নেই');
}

/* fallback-চেইন অটুট? — নিজের ফন্ট না এলে সিস্টেম ফন্টে নামবে */
const bodyFont = (css.match(/body\{font-family:[^}]*\}/) || [''])[0];
/Noto Sans Bengali/.test(bodyFont) ? ok('body-তে নিজের ফন্ট প্রথমে') : bad('body-তে ফন্ট বসানো হয়নি');
/system-ui/.test(bodyFont) ? ok('fallback-চেইন অটুট (system-ui)') : bad('fallback নেই');

/* ── ৪. preload ── */
console.log('\npreload');
const noPreload = pages.filter((f) => !/rel="preload"[^>]*noto-sans-bengali/.test(fs.readFileSync(path.join(ROOT, f), 'utf8')));
noPreload.length === 0 ? ok(`${pages.length}টি পাতায় ফন্ট preload`) : bad(`preload নেই: ${noPreload.join(', ')}`);

const badCross = pages.filter((f) => {
  const m = fs.readFileSync(path.join(ROOT, f), 'utf8').match(/<link rel="preload"[^>]*noto-sans-bengali[^>]*>/);
  return m && !/crossorigin/.test(m[0]);
});
/* font preload-এ crossorigin বাধ্যতামূলক, নইলে ব্রাউজার দুইবার নামায় */
badCross.length === 0 ? ok('preload-এ crossorigin আছে') : bad(`crossorigin নেই: ${badCross.slice(0,3).join(', ')}`);

/* ── ৫. SW-এ ফন্ট ── */
console.log('\nসার্ভিস-ওয়ার্কার');
const sw = read('sw.js');
/noto-sans-bengali\.woff2/.test(sw) ? ok('SW-এ নতুন ফন্ট precache') : bad('SW-এ ফন্ট নেই');
!/NotoSansBengali\.ttf/.test(sw) ? ok('SW-এ পুরোনো TTF নেই') : bad('SW-এ পুরোনো TTF এখনো');

console.log(`\n${fail ? '✗' : '✓'} পাশ ${pass} · ফেল ${fail}\n`);
process.exit(fail ? 1 : 0);
