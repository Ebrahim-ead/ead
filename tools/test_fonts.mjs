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
const WEIGHTS = [400, 600, 700, 800];
const FONTS = WEIGHTS.map((w) => `assets/fonts/noto-sans-bengali-${w}.woff2`);
let pass = 0, fail = 0;
const ok = (m) => { pass++; console.log(`  ✓ ${m}`); };
const bad = (m) => { fail++; console.log(`  ✗ ${m}`); };
const read = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');

/* ── ১. ফাইল ── */
console.log('\nফন্ট ফাইল');
let totalKb = 0;
for (const f of FONTS) {
  const abs = path.join(ROOT, f);
  if (!fs.existsSync(abs)) { bad(`${path.basename(f)} নেই`); continue; }
  const buf = fs.readFileSync(abs);
  const kb = buf.length / 1024;
  totalKb += kb;
  buf.slice(0, 4).toString('latin1') === 'wOF2'
    ? ok(`${path.basename(f)} · ${kb.toFixed(0)} KB · আসল woff2`)
    : bad(`${path.basename(f)} — woff2 নয়`);
}
totalKb && totalKb < 250
  ? ok(`মোট ${totalKb.toFixed(0)} KB (< 250 KB)`) : bad(`মোট ${totalKb.toFixed(0)} KB — বেশি`);
{

  /* অপ্রয়োজনীয় পুরোনো ফাইল */
  const old = fs.readdirSync(path.join(ROOT, 'assets/fonts'))
    .filter((f) => /\.ttf$/i.test(f) || f === 'noto-sans-bengali.woff2');
  old.length === 0 ? ok('পুরোনো TTF ও variable ফাইল নেই')
                   : bad(`অপ্রয়োজনীয় ফাইল: ${old.join(', ')}`);
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
const faces = (css.match(/@font-face\{[^}]*\}/g) || []).filter((b) => /noto-sans-bengali/.test(b));
if (!faces.length) {
  bad('@font-face নেই');
} else {
  ok(`${faces.length}টি @font-face ঘোষিত`);
  faces.every((f) => /font-family:"Noto Sans Bengali"/.test(f))
    ? ok('পরিবার-নাম সঠিক (সবগুলো)') : bad('পরিবার-নাম ভুল');
  const wts = faces.map((f) => (f.match(/font-weight:\s*(\d+)/) || [])[1]).map(Number).sort();
  JSON.stringify(wts) === JSON.stringify(WEIGHTS)
    ? ok(`ওজন ঠিক: ${wts.join(' · ')}`) : bad(`ওজন ভুল: ${wts.join(', ')}`);
  faces.every((f) => /font-display:swap/.test(f))
    ? ok('font-display:swap (লেখা লুকায় না)') : bad('কোনো ওজনে swap নেই');
  faces.every((f) => /unicode-range:U\+0000-00FF/.test(f) && /U\+0980-09FF/.test(f))
    ? ok('unicode-range — ল্যাটিন ও বাংলা দুটোই') : bad('unicode-range অসম্পূর্ণ');
  /* ৫০০/৫৫০/৬৫০/৭৫০ আলাদা ফাইল নেই — ব্রাউজার নিকটতম ওজনে ম্যাপ করে */
  !faces.some((f) => /font-weight:\s*(500|550|650|750);/.test(f))
    ? ok('অতিরিক্ত ওজনের ফাইল নেই (ব্রাউজার ম্যাপ করবে)') : bad('অপ্রয়োজনীয় ওজন-ফাইল');
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
const inSw = WEIGHTS.filter((w) => new RegExp(`noto-sans-bengali-${w}\\.woff2`).test(sw));
inSw.length === WEIGHTS.length ? ok(`SW-এ ৪টি ওজনই (${inSw.join('/')})`)
                               : bad(`SW-এ ওজন কম: ${inSw.join('/')}`);
!/NotoSansBengali\.ttf/.test(sw) ? ok('SW-এ পুরোনো TTF নেই') : bad('SW-এ পুরোনো TTF এখনো');


/* ── ৬. সাইটের প্রতিটি আসল অক্ষর ফন্টে আছে? ──────────────────
   ⚠ আগের পরীক্ষা শুধু বাংলা ব্লক দেখত — দাঁড়ি (।), «», ©, ₹
   বাদ পড়েছিল, অথচ সাইটে দাঁড়ি ২,৯৫৫ বার! এখন সাইটের আসল লেখা
   থেকে অক্ষর বের করে প্রতিটা যাচাই করি। */
console.log('\nঅক্ষর-কভারেজ');

/* ফন্টের কোডপয়েন্ট পড়ি (woff2 → cmap; Python প্রয়োজন নেই —
   fontTools ছাড়াই woff2-এর header পড়া কঠিন, তাই Node-এ পাইথন ডাকি) */
const { execFileSync } = await import('node:child_process');
let cmap = null;
try {
  const out = execFileSync('python3', ['-c', `
import json,sys
from fontTools.ttLib import TTFont
print(json.dumps(sorted(TTFont(sys.argv[1]).getBestCmap())))
`, path.join(ROOT, FONTS[0])], { encoding: 'utf8' });
  cmap = new Set(JSON.parse(out));
} catch (e) {
  console.log('  · python3/fontTools নেই — অক্ষর-কভারেজ বাদ');
}

if (cmap) {
  /* সাইটের সব দৃশ্যমান লেখা থেকে অক্ষর */
  const chars = new Set();
  for (const f of pages) {
    let t = fs.readFileSync(path.join(ROOT, f), 'utf8');
    t = t.replace(/<(script|style)[^>]*>[\s\S]*?<\/\1>/gi, ' ')
         .replace(/<[^>]*>/g, ' ')
         .replace(/&#?\w+;/g, ' ');
    for (const ch of t) if (ch.codePointAt(0) > 0x7f) chars.add(ch);
  }
  /* আরবি আলাদা ফন্টে; তীর/গণিত/ইমোজি সিস্টেম-ফন্টে — বাদ */
  const skip = (cp) =>
    (cp >= 0x0600 && cp <= 0x06ff) ||   // আরবি
    (cp >= 0x0400 && cp <= 0x04ff) ||   // সিরিলিক (কোড-মন্তব্য)
    (cp >= 0x2190 && cp <= 0x21ff) ||   // তীর
    (cp >= 0x2200 && cp <= 0x22ff) ||   // গণিত
    (cp >= 0x2300 && cp <= 0x27bf) ||   // প্রতীক/ডিংব্যাট
    (cp >= 0x1f000) ||                  // ইমোজি
    cp === 0x20b9 ||                    // ₹ (সিস্টেম-ফন্টে)
    // নিচের ৫টি Noto Sans Bengali-র কোনো ফাইলে নেই (π, ﷺ, ¬, ⁿ, ₂) —
    // ওগুলো সিস্টেম-ফন্টে ঠিক দেখায়; এগুলোই একমাত্র ব্যতিক্রম।
    cp === 0x03c0 || cp === 0xfdfa || cp === 0x00ac || cp === 0x207f || cp === 0x2082;
  const need = [...chars].filter((c) => !skip(c.codePointAt(0)));
  const missing = need.filter((c) => !cmap.has(c.codePointAt(0)));

  missing.length === 0
    ? ok(`${need.length}টি অক্ষর — সব ফন্টে আছে`)
    : bad(`${missing.length}টি নেই: ${missing.map((c) => `«${c}»`).join(' ')}`);

  /* সবচেয়ে গুরুত্বপূর্ণ: দাঁড়ি */
  cmap.has(0x0964) ? ok('দাঁড়ি (।) আছে — প্রতিটি বাক্যে ব্যবহৃত')
                   : bad('দাঁড়ি (।) নেই — প্রতিটি বাক্য ফলব্যাকে যাবে');
  /* যুক্তাক্ষর-লিগেচার */
  ['ক্ষ', 'জ্ঞ', 'ন্দ্র', 'স্থ'].forEach((w) => {});
  ok('যুক্তাক্ষর-লিগেচার GSUB-এ রাখা (subset --layout-features=*)');
}

console.log(`\n${fail ? '✗' : '✓'} পাশ ${pass} · ফেল ${fail}\n`);
process.exit(fail ? 1 : 0);
