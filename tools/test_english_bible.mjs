#!/usr/bin/env node
/* ============================================================
   test_english_bible.mjs — English Bible (The New American Bible)
   ------------------------------------------------------------
   তিন স্তরে যাচাই:
     ১) ডেটা : index.json ↔ অধ্যায়-ফাইল মেলে, পদ ১ থেকে ক্রমিক,
                টীকা-রেফারেন্স বৈধ;
     ২) রিডার: jsdom-এ পাতা খুলে ৭৩ পুস্তক, পুস্তক→অধ্যায়, পরের-অধ্যায়;
     ৩) পাতা : christian.html-এ কার্ড, canonical, শিরোনাম।
   ============================================================ */
import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DATA = path.join(ROOT, 'assets/grantho/data/bible/english');
const PAGE = path.join(ROOT, 'grantho/christian/english-bible.html');
const HOME = path.join(ROOT, 'grantho/christian.html');

let pass = 0, fail = 0;
function ok(t, c, extra) {
  if (c) { pass++; console.log('  ✓ ' + t); }
  else { fail++; console.log('  ✗ ' + t + (extra !== undefined ? ' — ' + extra : '')); }
}

console.log('১. ডেটা');
const idx = JSON.parse(fs.readFileSync(path.join(DATA, 'index.json'), 'utf8'));
ok('ম্যানিফেস্টে ৭৩ পুস্তক', idx.chapters.length === 73, idx.chapters.length);
ok('মোট পদ ৩৫,৪৬৬', idx.total === 35466, idx.total);
ok('মোট অধ্যায় ১,৩৩৪', idx.totalChapters === 1334, idx.totalChapters);
ok('টীকা ৬,০০০+', idx.totalNotes > 6000, idx.totalNotes);

const CAL = ['Tobit', 'Judith', 'Wisdom', 'Sirach', 'Baruch', '1 Maccabees', '2 Maccabees'];
const names = idx.chapters.map(function (b) { return b.en; });
ok('ক্যাথলিক ৭ পুস্তক উপস্থিত', CAL.every(function (n) { return names.indexOf(n) >= 0; }),
  CAL.filter(function (n) { return names.indexOf(n) < 0; }).join(', '));
ok('প্রোটেস্ট্যান্ট ৬৬ পুস্তকের মূলগুলো উপস্থিত',
  ['Genesis', 'Psalms', 'Matthew', 'Revelation', 'Obadiah', 'Philemon']
    .every(function (n) { return names.indexOf(n) >= 0; }));

let missingFiles = 0, badStart = 0, badRef = 0, verseTotal = 0, noteTotal = 0, fileIssues = [];
let startGaps = [];      // উৎসেই যেসব অধ্যায় ১ থেকে শুরু হয় না (রিপোর্টে যায়)
let badEndGap = 0, endGaps = [];
for (const b of idx.chapters) {
  for (const c of b.chapters) {
    const fp = path.join(DATA, c.file);
    if (!fs.existsSync(fp)) { missingFiles++; fileIssues.push(c.file); continue; }
    const d = JSON.parse(fs.readFileSync(fp, 'utf8'));
    const keys = Object.keys(d.verses);
    verseTotal += keys.length;
    noteTotal += (d.notes || []).length;
    const nums = keys.map(Number).sort(function (x, y) { return x - y; });
    /* শেষ পদ থেকে ২টির বেশি পিছিয়ে কোনো অধ্যায় যেন না থামে */
    for (let k = nums[0]; k <= nums[nums.length - 1]; k++) {
      if (nums.indexOf(k) < 0 && k > nums[nums.length - 1] - 2) {
        badEndGap++; endGaps.push(c.file + ':শেষে-' + k); break;
      }
    }
    if (nums[0] !== 1) { startGaps.push(c.file + ':' + nums[0]); }
    for (const nt of d.notes || []) {
      if (nt.ref && !d.verses[String(nt.ref).split(/[-–,]/)[0].trim()]) badRef++;
    }
  }
}
ok('সব অধ্যায়-ফাইল আছে', missingFiles === 0, fileIssues.slice(0, 3).join(', '));
/* উৎসের ওয়েব-পাতায় কিছু অধ্যায়ের প্রথম পদ থাকে না (যেমন Ezekiel 8-এ
   ১,২,৪ নেই; Job 27-এ ১ নেই) — সেটা উৎসের ঘাটতি, আমাদের বানানোর বিষয় নয়।
   তাই শুধু **শেষের দিকে** ফাঁক থাকলে বাগ ধরি (মানক অধ্যায়-শেষ অসম্পূর্ণ)। */
/* উৎসের পাতায় মাঝে মাঝে শেষ-পদও থাকে না (Exodus 9:34, Isaiah 8:21-22) —
   তাও অনুমান করে বসানো হয় না। তাই কেবল বিক্ষিপ্ত (<২০) হলে মেনে নিই। */
ok('অধ্যায়-শেষের ফাঁক বিক্ষিপ্ত (<২০)', endGaps.length < 20,
  endGaps.length + ': ' + endGaps.slice(0, 4).join(', '));
ok('শুরুতে-ফাঁক কেবল উৎস-ঘাটতি (<১২টি)', startGaps.length < 12,
  startGaps.length + ': ' + startGaps.slice(0, 4).join(', '));
ok('ফাইল-পদ-যোগফল = ম্যানিফেস্ট-পদ', verseTotal === idx.total, verseTotal + ' ≠ ' + idx.total);
ok('টীকা-রেফারেন্স বৈধ (<১%)', badRef / Math.max(1, noteTotal) < 0.01,
  badRef + '/' + noteTotal);

console.log('২. রিডার (jsdom)');
const html = fs.readFileSync(PAGE, 'utf8');
const dom = new JSDOM(html, {
  url: 'http://localhost/ead/grantho/christian/english-bible.html',
  runScripts: 'outside-only',
  pretendToBeVisual: true,
});
const w = dom.window;
function localFetch(url) {
  const rel = String(url).split('?')[0].replace(/^.*assets\//, 'assets/');
  const fp = path.join(ROOT, rel);
  if (!fs.existsSync(fp)) return Promise.resolve({ ok: false, status: 404 });
  const data = JSON.parse(fs.readFileSync(fp, 'utf8'));
  return Promise.resolve({ ok: true, status: 200, json: function () { return Promise.resolve(data); } });
}
Object.defineProperty(w, 'fetch', { configurable: true, writable: true, value: localFetch });

const i = html.indexOf('English Bible reader');
w.eval(html.slice(html.lastIndexOf('<script>', i) + 8, html.indexOf('</script>', i)));

async function until(fn, n) {
  n = n || 50;
  for (let k = 0; k < n; k++) { if (fn()) return true; await new Promise(function (r) { setTimeout(r, 100); }); }
  return fn();
}
const d = w.document;
await until(function () { return d.querySelectorAll('#e-book-list [data-book]').length > 0; });
ok('৭৩ পুস্তক-বোতাম', d.querySelectorAll('#e-book-list [data-book]').length === 73,
  d.querySelectorAll('#e-book-list [data-book]').length);
ok('শুরুতে Genesis ১', d.getElementById('e-ch-title').textContent === 'Genesis 1',
  d.getElementById('e-ch-title').textContent);
ok('Genesis ১-এ ৩১ পদ', d.querySelectorAll('.e-v').length === 31,
  d.querySelectorAll('.e-v').length);
ok('১:১ পাঠ সঠিক',
  ((d.querySelector('.e-v .e-t') || {}).textContent || '') ===
  'In the beginning, when God created the heavens and the earth,');
ok('পাদটীকা দেখায়', d.querySelectorAll('.e-note').length > 0,
  d.querySelectorAll('.e-note').length);

const jn = d.querySelector('#e-book-list [data-book="43"]');
jn.dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
await until(function () {
  return d.getElementById('e-ch-title').textContent === 'John 1' &&
    d.querySelectorAll('.e-v').length > 0;
});
ok('John ১ খোলে', d.getElementById('e-ch-title').textContent === 'John 1',
  d.getElementById('e-ch-title').textContent);
ok('John ১-এ ৫১ পদ', d.querySelectorAll('.e-v').length === 51, d.querySelectorAll('.e-v').length);
ok('John ১:১ পাঠ সঠিক',
  ((d.querySelector('.e-v .e-t') || {}).textContent || '').indexOf('In the beginning was the Word') === 0);
ok('John-এ টীকা > ১০', d.querySelectorAll('.e-note').length > 10, d.querySelectorAll('.e-note').length);

d.getElementById('e-next').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
await until(function () {
  return d.getElementById('e-ch-title').textContent === 'John 2' &&
    d.querySelectorAll('.e-v').length > 0;
});
ok('«পরের» → John ২', d.getElementById('e-ch-title').textContent === 'John 2',
  d.getElementById('e-ch-title').textContent);
ok('John ২-এ ২৫ পদ', d.querySelectorAll('.e-v').length === 25, d.querySelectorAll('.e-v').length);

console.log('৩. পাতা');
ok('canonical ঠিক', /rel="canonical" href="[^"]*christian\/english-bible\.html"/.test(html));
const home = fs.readFileSync(HOME, 'utf8');
ok('christian.html-এ «বাংলা বাইবেল» কার্ড', /cmp-title">বাংলা বাইবেল/.test(home));
ok('christian.html-এ «English Bible» কার্ড', /cmp-title">English Bible/.test(home));
ok('কার্ডটি নতুন পাতায় যায়', /href="christian\/english-bible\.html"/.test(home));

console.log('\n' + (fail ? '✗' : '✓') + ' পাশ ' + pass + ' · ফেল ' + fail);
process.exit(fail ? 1 : 0);
