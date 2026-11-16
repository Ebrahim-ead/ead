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
/* তিন ক্যাশেরই বাজেট থাকতে হবে — এন্ট্রি আর বাইট, দুটোই */
var limitCount = (sw.match(/LIMITS\[/g) || []).length;
limitCount >= 3 ? ok(`${limitCount}টি ক্যাশের বাজেট ঘোষিত`) : bad(`বাজেট কম (${limitCount})`);
/LIMITS\[PAGE_CACHE\]/.test(sw) ? ok('পাতা-ক্যাশে সীমা আছে') : bad('পাতা-ক্যাশে সীমা নেই');
/LIMITS\[SHELL_CACHE\]/.test(sw) ? ok('শেল-ক্যাশে সীমা আছে') : bad('শেল-ক্যাশে সীমা নেই');
/LIMITS\[DATA_CACHE\]/.test(sw) ? ok('ডেটা-ক্যাশে সীমা আছে') : bad('ডেটা-ক্যাশে সীমা নেই');
// trim আসলে তিন জায়গাতেই ডাকা হয়?
var trimCalls = (sw.match(/trimCache\(/g) || []).length - 1; // সংজ্ঞা বাদ
trimCalls >= 3 ? ok(`trimCache ${trimCalls} জায়গায় ডাকা`) : bad(`trimCache csak ${trimCalls} জায়গায়`);
// মাপ সত্যিই মাপা হয়?
/sizeOf/.test(sw) ? ok('বাইট-মাপ হিসাব হয় (sizeOf)') : bad('মাপ মাপা হয় না');
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
  /* ইনস্টল-সিস্টেম বাদ দেওয়া হয়েছে (ব্যবহারকারীর নির্দেশ) — নিশ্চিত করি
     যেন কোনোদিন ভুলে আবার ফিরে না আসে। */
  !/beforeinstallprompt/.test(js) ? ok('ইনস্টল-প্রম্পট নেই (বাদ দেওয়া)') : bad('beforeinstallprompt এখনো আছে');
  !/appinstalled/.test(js) ? ok('appinstalled শ্রোতা নেই') : bad('appinstalled এখনো আছে');
  !/install-btn/.test(js) ? ok('ইনস্টল-বোতাম কোড নেই') : bad('install-btn এখনো আছে');
  !/পুনরায়.*ইনস্টল|অ্যাপ হিসেবে ইনস্টল/.test(js) ? ok('ইনস্টল-ব্যানার লেখা নেই') : bad('ইনস্টল-ব্যানার লেখা আছে');
  /display-mode:/.test(js) ? ok('display-mode শনাক্তকরণ (অফলাইন-স্ক্রল)') : bad('display-mode শনাক্তকরণ নেই');
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

/* ── ৬. ইনস্টল-সিস্টেম সম্পূর্ণ বাদ ──
   ব্যবহারকারীর নির্দেশ: «অ্যাপ ইনস্টল সিস্টেম বাদ দিয়ে দাও»।
   তাই এখন উল্টো যাচাই — কোথাও যেন এর চিহ্ন না থাকে। */
console.log('\nইনস্টল-সিস্টেম বাদ');
const idx = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
!/id="install-btn"/.test(idx) ? ok('হিরোতে ইনস্টল-বোতাম নেই') : bad('#install-btn এখনো আছে');
!/id="install"/.test(idx) ? ok('#install আইকন-সিম্বল নেই') : bad('#install symbol এখনো আছে');

/* সব পাতায় সাবধান */
const htmlFiles = [];
(function walk(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    if (e.name === 'node_modules' || e.name === '.git') continue;
    const fp = path.join(d, e.name);
    if (e.isDirectory()) walk(fp);
    else if (e.name.endsWith('.html')) htmlFiles.push(fp);
  }
})(ROOT);

const withBtn = htmlFiles.filter((f) => /install-btn|id="install"/.test(fs.readFileSync(f, 'utf8')));
withBtn.length === 0
  ? ok(`${htmlFiles.length}টি পাতার কোথাও ইনস্টল-বোতাম/আইকন নেই`)
  : bad(`এখনো আছে: ${withBtn.map((f) => path.relative(ROOT, f)).slice(0, 5).join(', ')}`);

const css = fs.readFileSync(path.join(ROOT, 'assets/site-extra.css'), 'utf8');
!/pwa-banner|pwa-btn|pwa-hint|install-btn/.test(css)
  ? ok('ইনস্টল-ব্যানারের CSS সরানো') : bad('ইনস্টল-CSS এখনো আছে');
/\.pwa-offline/.test(css)
  ? ok('অফলাইন-নোটিশের CSS অটুট') : bad('অফলাইন-CSS হারিয়েছে');

/* ── ফল ── */
console.log(`\n${fail === 0 ? '✓' : '✗'} পাশ ${pass} · ফেল ${fail}\n`);
process.exit(fail === 0 ? 0 : 1);
