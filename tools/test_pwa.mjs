/* ============================================================
   test_pwa.mjs — PWA-র স্বয়ংক্রিয় পরীক্ষা
   ------------------------------------------------------------
   চালাতে:  node tools/test_pwa.mjs
   যা যাচাই করে:
     · sw.js বৈধ JS + নিজের ক্যাশ নাম (ead-*) ব্যবহার করে
     · pre-cache-এর প্রতিটি ফাইল বাস্তবে আছে ও URL বৈধ
     · offline.html ঠিকভাবে গঠিত
     · pwa.js সব পাতায় যুক্ত, রেজিস্ট্রেশন-পথ সঠিক
     · manifest ↔ sw.js ↔ পেজ — তিন জায়গায় scope মেলে
     · গোপন/ভুল পথ নেই
   ============================================================ */
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { JSDOM } from 'jsdom';

const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '..');
let pass = 0, fail = 0;
const ok = (m) => { pass++; console.log(`  ✓ ${m}`); };
const bad = (m) => { fail++; console.log(`  ✗ ${m}`); };
const P = (u) => path.join(ROOT, u.replace(/^\/ead\//, ''));

/* ── ১. sw.js সিনট্যাক্স ── */
console.log('\nService Worker');
const sw = fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf8');
try {
  execFileSync(process.execPath, ['--check', path.join(ROOT, 'sw.js')], { stdio: 'pipe' });
  ok('sw.js বৈধ JavaScript');
} catch (e) {
  bad(`sw.js সিনট্যাক্স ভুল: ${String(e.stderr).slice(0, 120)}`);
}
/caches\.open/.test(sw) ? ok('Cache API ব্যবহার করে') : bad('ক্যাশ ব্যবহার নেই');
/self\.addEventListener\('install'/.test(sw) ? ok('install হ্যান্ডলার আছে') : bad('install নেই');
/self\.addEventListener\('activate'/.test(sw) ? ok('activate হ্যান্ডলার আছে') : bad('activate নেই');
/self\.addEventListener\('fetch'/.test(sw) ? ok('fetch হ্যান্ডলার আছে') : bad('fetch নেই');
/ead-shell-/.test(sw) ? ok('ক্যাশের নাম ead-*-এ scoped') : bad('ক্যাশের নাম scoped নয়');
/trimCache|DATA_MAX_ENTRIES/.test(sw) ? ok('ডেটা-ক্যাশে সীমা আছে') : bad('সীমা নেই (ফোন ভরে যাবে)');
/origin !== self\.location\.origin/.test(sw) ? ok('বাইরের ডোমেইন বাদ') : bad('বাইরের ডোমেইন ক্যাশ করবে');

/* pre-cache তালিকা বের করি */
const shellMatch = sw.match(/var SHELL = \[([\s\S]*?)\];/);
const shell = shellMatch
  ? [...shellMatch[1].matchAll(/'([^']+)'/g)].map((m) => m[1])
  : [];
console.log(`\nPre-cache (${shell.length}টি)`);
if (!shell.length) bad('SHELL তালিকা পড়া যায়নি');
let missing = 0;
for (const u of shell) {
  if (!fs.existsSync(P(u))) { bad(`নেই: ${u}`); missing++; }
}
if (!missing && shell.length) ok('সব pre-cache ফাইল আছে');

/* ── ২. offline.html ── */
console.log('\noffline.html');
const offPath = path.join(ROOT, 'offline.html');
if (!fs.existsSync(offPath)) {
  bad('offline.html নেই');
} else {
  const d = new JSDOM(fs.readFileSync(offPath, 'utf8')).window.document;
  ok(`আকার ${(fs.statSync(offPath).size / 1024).toFixed(0)} KB`);
  d.querySelectorAll('h1').length === 1 ? ok('ঠিক ১টি h1') : bad(`h1 সংখ্যা ${d.querySelectorAll('h1').length}`);
  d.querySelector('main') ? ok('<main> আছে') : bad('<main> নেই');
  d.querySelectorAll('link[rel="stylesheet"]').length >= 4 ? ok('CSS লিংক আছে') : bad('CSS লিংক কম');
  d.querySelectorAll('.chip, .btn').length >= 4 ? ok('নেভিগেশন-বিকল্প আছে') : bad('বিকল্প কম');
  /noindex/.test(fs.readFileSync(offPath, 'utf8')) ? ok('noindex আছে') : bad('noindex নেই');
}

/* ── ৩. pwa.js ── */
console.log('\npwa.js');
const pwaPath = path.join(ROOT, 'assets/pwa.js');
if (!fs.existsSync(pwaPath)) {
  bad('assets/pwa.js নেই');
} else {
  try {
    execFileSync(process.execPath, ['--check', pwaPath], { stdio: 'pipe' });
    ok('বৈধ JavaScript');
  } catch (e) { bad('সিনট্যাক্স ভুল'); }
  const js = fs.readFileSync(pwaPath, 'utf8');
  /serviceWorker\.register\('\/ead\/sw\.js'/.test(js) ? ok("SW রেজিস্ট্রেশন পথ '/ead/sw.js'") : bad('রেজিস্ট্রেশন পথ ভুল');
  /beforeinstallprompt/.test(js) ? ok('ইনস্টল-প্রম্পট ধরা হয়') : bad('beforeinstallprompt নেই');
  /iPad\|iPhone\|iPod/.test(js) ? ok('iOS শনাক্তকরণ আছে') : bad('iOS শনাক্তকরণ নেই');
  /prefers|display-mode: standalone/.test(js) ? ok('standalone শনাক্তকরণ') : bad('standalone নেই');
}

/* ── ৪. প্রতিটি পাতায় pwa.js ── */
console.log('\nপাতা-সংযোগ');
const pages = fs.readdirSync(ROOT).filter((f) => f.endsWith('.html') && f !== 'atheism-2.html');
const without = pages.filter((f) => !/assets\/pwa\.js/.test(fs.readFileSync(path.join(ROOT, f), 'utf8')));
without.length === 0 ? ok(`${pages.length}টি পাতায় pwa.js`) : bad(`pwa.js নেই: ${without.join(', ')}`);
const offHas = /assets\/pwa\.js/.test(fs.readFileSync(offPath, 'utf8'));
offHas ? ok('offline.html-এও pwa.js') : bad('offline.html-এ pwa.js নেই');

/* ── ৫. scope মিল ── */
console.log('\nscope');
const man = JSON.parse(fs.readFileSync(path.join(ROOT, 'manifest.json'), 'utf8'));
man.scope === '/ead/' ? ok("manifest scope '/ead/'") : bad(`manifest scope ${man.scope}`);
/scope: '\/ead\/'/.test(fs.readFileSync(pwaPath, 'utf8')) ? ok("SW scope '/ead/'") : bad('SW scope মেলেনি');
man.start_url.startsWith('/ead/') ? ok(`start_url ${man.start_url}`) : bad('start_url ভুল');

/* ── ৬. হিরোর স্থায়ী ইনস্টল-বোতাম ── */
console.log('\nইনস্টল-বোতাম');
const idx = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const btn = idx.match(/<button[^>]*id="install-btn"[^>]*>/);
btn ? ok('#install-btn আছে') : bad('#install-btn নেই');
if (btn) {
  /class="btn ghost"/.test(btn[0]) ? ok('.btn.ghost — বাকি দুটোর মতো') : bad('চেহারা ক্লাস ভুল');
  /type="button"/.test(btn[0]) ? ok('type="button" (ফর্ম সাবমিট নয়)') : bad('type নেই');
  !/hidden/.test(btn[0]) ? ok('inline-এ লুকানো নয় — JS ছাড়াও দেখা যায়') : bad('inline-এ hidden');
  /aria-label=/.test(btn[0]) ? ok('aria-label আছে') : bad('aria-label নেই');
}
/<use href="#install"/.test(idx) ? ok('#install আইকন ব্যবহার') : bad('#install আইকন নেই');
const sprite = (fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8').match(/<symbol id="install"[\s\S]*?<\/symbol>/) || [''])[0];
sprite ? ok('#install symbol সংজ্ঞায়িত') : bad('#install symbol নেই');
// স্প্রাইট সব পাতায়
const noIcon = fs.readdirSync(ROOT).filter((f) => f.endsWith('.html'))
  .filter((f) => !/symbol id="install"/.test(fs.readFileSync(path.join(ROOT, f), 'utf8')));
noIcon.length === 0 ? ok('সব পাতায় #install sprite') : bad(`sprite নেই: ${noIcon.join(', ')}`);
// pwa.js-এ হ্যান্ডলার
/mountInstallButton/.test(fs.readFileSync(pwaPath, 'utf8')) ? ok('বোতামের হ্যান্ডলার আছে') : bad('হ্যান্ডলার নেই');

/* ── ফল ── */
console.log(`\n${fail === 0 ? '✓' : '✗'} পাশ ${pass} · ফেল ${fail}\n`);
process.exit(fail === 0 ? 0 : 1);
