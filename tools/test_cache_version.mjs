#!/usr/bin/env node
/**
 * ক্যাশ-সংস্করণ পাহারা — ডেটা বদলালে DATA_VERSION বাড়ানো হয়েছে কি না।
 *
 * কেন: বাইবেল ৪৬ → ৬৬ পুস্তক করা হলো, কিন্তু sw.js-এর DATA_VERSION
 * 'v1'-ই থেকে গিয়েছিল। ফলে যাঁদের ব্রাউজারে পুরোনো ক্যাশ ছিল, তাঁরা
 * পুরোনো ৫০ পুস্তকের তালিকাই দেখতে পাচ্ছিলেন — নতুন ১৬টি পুস্তক
 * "উধাও" মনে হচ্ছিল। নতুন/পরিষ্কার ব্রাউজারে সব ঠিক দেখাত, তাই সাধারণ
 * টেস্টে ধরা পড়েনি।
 *
 * সমাধান: ডেটার একটি ফিঙ্গারপ্রিন্ট সংরক্ষণ করে রাখি। ডেটা বদলালে
 * ফিঙ্গারপ্রিন্ট বদলাবে, কিন্তু DATA_VERSION একই থাকলে এই টেস্ট ফেল করবে
 * — তখন SW-ভার্সন বাড়াতে হবে (বা সচেতন সিদ্ধান্ত নিয়ে ফিঙ্গারপ্রিন্ট
 * হালনাগাদ করতে হবে)।
 *
 * ব্যবহার:
 *   node tools/test_cache_version.mjs            # যাচাই
 *   node tools/test_cache_version.mjs --update   # ফিঙ্গারপ্রিন্ট হালনাগাদ
 *                                                #  (DATA_VERSION বাড়ানোর পরেই!)
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const STAMP = path.join(ROOT, 'tools', 'cache-fingerprint.json');
const SW = path.join(ROOT, 'sw.js');
const update = process.argv.includes('--update');

/* ---- ডেটা-ফিঙ্গারপ্রিন্ট: grantho/quran/hadith/filistin-এর সব JSON ---- */
const walk = (dir, out = []) => {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === '_debug' || e.name.startsWith('.')) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name.endsWith('.json')) out.push(p);
  }
  return out;
};

const dataRoot = path.join(ROOT, 'assets');
const files = [];
for (const sub of ['grantho', 'quran', 'hadith', 'filistin']) {
  const d = path.join(dataRoot, sub);
  if (fs.existsSync(d)) walk(d, files);
}
files.sort();

const h = crypto.createHash('sha256');
for (const f of files) {
  h.update(path.relative(ROOT, f));
  h.update(fs.readFileSync(f));
}
const fingerprint = h.digest('hex').slice(0, 16);

/* ---- sw.js থেকে সংস্করণ পড়ি (নিরাপদে — বাস্তব SW চালাই না) ---- */
const swSrc = fs.readFileSync(SW, 'utf8');
const ver = (name) => {
  const m = swSrc.match(new RegExp(`var\\s+${name}\\s*=\\s*['"]([^'"]+)['"]`));
  return m ? m[1] : null;
};
const SHELL_VERSION = ver('SHELL_VERSION');
const DATA_VERSION = ver('DATA_VERSION');

let pass = 0, fail = 0;
const ok = (m) => { pass++; console.log('  ✓ ' + m); };
const no = (m) => { fail++; console.log('  ✗ ' + m); };

console.log('\nসংস্করণ');
SHELL_VERSION ? ok(`SHELL_VERSION = ${SHELL_VERSION}`) : no('SHELL_VERSION পাওয়া যায়নি');
DATA_VERSION ? ok(`DATA_VERSION = ${DATA_VERSION}`) : no('DATA_VERSION পাওয়া যায়নি');

console.log('\nডেটা-ফিঙ্গারপ্রিন্ট');
console.log(`  ফাইল ${files.length}টি · ${fingerprint}`);

const stamp = fs.existsSync(STAMP) ? JSON.parse(fs.readFileSync(STAMP, 'utf8')) : null;

if (update) {
  fs.writeFileSync(STAMP, JSON.stringify({
    fingerprint,
    dataVersion: DATA_VERSION,
    files: files.length,
    at: new Date().toISOString(),
  }, null, 2) + '\n');
  ok(`হালনাগাদ হয়েছে → DATA_VERSION ${DATA_VERSION}`);
} else if (!stamp) {
  no('ফিঙ্গারপ্রিন্ট-ফাইল নেই — চালান: node tools/test_cache_version.mjs --update');
} else if (stamp.fingerprint === fingerprint) {
  ok('ডেটা অপরিবর্তিত — সংস্করণ বাড়ানোর দরকার নেই');
  (stamp.dataVersion === DATA_VERSION)
    ? ok(`ডেটা-সংস্করণ একই (${DATA_VERSION})`)
    : no(`DATA_VERSION বদলেছে (${stamp.dataVersion} → ${DATA_VERSION}) কিন্তু ডেটা একই — ফিঙ্গারপ্রিন্ট হালনাগাদ করুন`);
} else {
  /* ⚠ আসল পরীক্ষা: ডেটা বদলেছে, সংস্করণও বদলেছে কি? */
  if (stamp.dataVersion !== DATA_VERSION) {
    ok(`ডেটা বদলেছে (${stamp.files} → ${files.length} ফাইল) · DATA_VERSION ${stamp.dataVersion} → ${DATA_VERSION} ✓`);
    fs.writeFileSync(STAMP, JSON.stringify({
      fingerprint, dataVersion: DATA_VERSION, files: files.length,
      at: new Date().toISOString(),
    }, null, 2) + '\n');
    ok('ফিঙ্গারপ্রিন্ট স্বয়ংক্রিয়ভাবে হালনাগাদ');
  } else {
    no(`ডেটা বদলেছে কিন্তু DATA_VERSION এখনো ${DATA_VERSION} — পুরোনো ক্যাশ আটকে থাকবে!`);
    console.log(`\n  সমাধান: sw.js-এ DATA_VERSION বাড়ান (${DATA_VERSION} → পরের সংখ্যা), তারপর:`);
    console.log('    node tools/test_cache_version.mjs --update\n');
  }
}

console.log(`\n${fail ? '✗' : '✓'} পাশ ${pass} · ফেল ${fail}`);
process.exit(fail ? 1 : 0);
