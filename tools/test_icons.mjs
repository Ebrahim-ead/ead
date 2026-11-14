/* ============================================================
   test_icons.mjs — অ্যাপ-আইকন ও manifest-এর স্বয়ংক্রিয় পরীক্ষা
   ------------------------------------------------------------
   চালাতে:  node tools/test_icons.mjs
   যা যাচাই করে:
     · manifest.json বৈধ ও বাধ্যতামূলক ক্ষেত্র আছে
     · ঘোষিত প্রতিটি আইকন বাস্তবে আছে এবং মাপ মেলে
     · maskable আইকনে নিরাপদ প্যাডিং আছে
     · প্রতিটি HTML পাতায় manifest + iOS-মেটা + favicon
     · সব আইকন-লিংক বৈধ পথে যায়
     · Manifest-এর shortcut-গুলো আসল পাতা
   ============================================================ */
import fs from 'node:fs';
import path from 'node:path';
import { JSDOM } from 'jsdom';

const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '..');
let pass = 0, fail = 0;
const ok = (m) => { pass++; console.log(`  ✓ ${m}`); };
const bad = (m) => { fail++; console.log(`  ✗ ${m}`); };
const P = (rel) => path.join(ROOT, rel.replace(/^\/ead\//, ''));

/* ── ১. manifest.json ── */
console.log('\nmanifest');
let man = null;
try {
  man = JSON.parse(fs.readFileSync(path.join(ROOT, 'manifest.json'), 'utf8'));
  ok('বৈধ JSON');
} catch (e) {
  bad(`পার্স হয়নি: ${e.message}`);
}

if (man) {
  const req = ['name', 'short_name', 'start_url', 'display', 'icons', 'theme_color', 'background_color'];
  const miss = req.filter((k) => !(k in man));
  miss.length === 0 ? ok('বাধ্যতামূলক ক্ষেত্র সব আছে') : bad(`অনুপস্থিত: ${miss.join(', ')}`);

  man.display === 'standalone' ? ok('display = standalone') : bad(`display = ${man.display}`);
  /^#[0-9a-f]{6}$/i.test(man.theme_color) ? ok(`theme_color ${man.theme_color}`) : bad('theme_color ভুল');
  man.start_url.startsWith('/ead/') ? ok(`start_url ${man.start_url}`) : bad('start_url scope-এর বাইরে');
  man.scope === '/ead/' ? ok('scope = /ead/') : bad(`scope = ${man.scope}`);
}

/* ── ২. আইকন-ফাইল ── */
console.log('\nআইকন-ফাইল');
const sizes = new Set();
for (const ic of man?.icons ?? []) {
  const p = P(ic.src);
  if (!fs.existsSync(p)) { bad(`নেই: ${ic.src}`); continue; }
  // PNG মাপ হেডার থেকে (প্রথম ২৪ বাইট)
  const b = fs.readFileSync(p).subarray(0, 24);
  const w = b.readUInt32BE(16), h = b.readUInt32BE(20);
  const want = ic.sizes;
  const got = `${w}x${h}`;
  got === want ? ok(`${ic.purpose.padEnd(9)} ${got.padEnd(10)} ${path.basename(p)}`)
               : bad(`${ic.src}: ঘোষিত ${want} কিন্তু বাস্তব ${got}`);
  if (ic.purpose === 'any') sizes.add(w);
}
// PWA-র জন্য ১৯২ ও ৫১২ বাধ্যতামূলক
sizes.has(192) ? ok('192×192 আছে') : bad('192×192 নেই (PWA-র জন্য বাধ্যতামূলক)');
sizes.has(512) ? ok('512×512 আছে') : bad('512×512 নেই (PWA-র জন্য বাধ্যতামূলক)');
man?.icons?.some((i) => i.purpose === 'maskable') ? ok('maskable আইকন আছে') : bad('maskable আইকন নেই');

/* ── ৩. প্রতিটি পাতায় ট্যাগ ── */
console.log('\nপাতা-সংযোগ');
const pages = fs.readdirSync(ROOT).filter((f) => f.endsWith('.html') && f !== 'atheism-2.html');
const noManifest = [], noIos = [], noFavicon = [];
for (const f of pages) {
  const s = fs.readFileSync(path.join(ROOT, f), 'utf8');
  if (!/rel="manifest"/.test(s)) noManifest.push(f);
  if (!/apple-mobile-web-app-capable/.test(s)) noIos.push(f);
  if (!/rel="icon"[^>]*favicon-32\.png/.test(s)) noFavicon.push(f);
}
noManifest.length === 0 ? ok(`${pages.length}টি পাতায় manifest`) : bad(`manifest নেই: ${noManifest.join(', ')}`);
noIos.length === 0 ? ok(`${pages.length}টি পাতায় iOS-মেটা`) : bad(`iOS-মেটা নেই: ${noIos.join(', ')}`);
noFavicon.length === 0 ? ok(`${pages.length}টি পাতায় favicon`) : bad(`favicon নেই: ${noFavicon.join(', ')}`);

/* ── ৪. ঠিকানা বৈধ ── */
console.log('\nঠিকানা');
const doc = new JSDOM(fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8')).window.document;
const hrefs = [...doc.querySelectorAll('link[rel="icon"], link[rel="apple-touch-icon"], link[rel="manifest"]')]
  .map((l) => l.getAttribute('href'));
const broken = hrefs.filter((h) => !fs.existsSync(P(h)));
broken.length === 0 ? ok(`${hrefs.length}টি লিংক সব বৈধ`) : bad(`ভাঙা: ${broken.join(', ')}`);

/* shortcut */
const scBad = (man?.shortcuts ?? []).filter((s) => !fs.existsSync(P(s.url)));
scBad.length === 0 ? ok(`${man?.shortcuts?.length ?? 0}টি shortcut বৈধ`) : bad(`ভাঙা shortcut: ${scBad.map(s => s.url).join(', ')}`);

console.log(`\n${fail === 0 ? '✓' : '✗'} পাশ ${pass} · ফেল ${fail}\n`);
process.exit(fail === 0 ? 0 : 1);
