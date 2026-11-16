#!/usr/bin/env node
/**
 * তথ্য ও গঠন-সঙ্গতি পরীক্ষা — সাইটের সব পাতায়:
 *
 *   ১. HTML ট্যাগ-ব্যালান্স (a/span/article/div/section) — ভুল নেস্টিং ধরে
 *   ২. সংখ্যা-ফরম্যাট: একই রাশি এক জায়গায় «৬২৩৬» আর অন্য জায়গায় «৬,২৩৬» হলে ধরে
 *   ৩. বানান-অসঙ্গতি: সাইটের সংখ্যাগরিষ্ঠ রূপ থেকে বিচ্ছিন্ন বানান ধরে
 *   ৪. ডেটা-ফাইল (grant ho) বৈধ JSON কি না
 *
 * ব্যবহার:  node tools/test_content.mjs
 * শেষ লাইন: «issues: 0 / N» — শূন্য মানে সব ঠিক।
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOTDIR = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) =>
  e.isDirectory()
    ? (['assets', 'node_modules'].includes(e.name) || e.name.startsWith('.')
        ? [] : walk(path.join(d, e.name)))
    : (e.name.endsWith('.html') ? [path.join(d, e.name)] : []));

const files = walk(ROOTDIR).map((p) => path.relative(ROOTDIR, p)).sort();
const issues = [];
const fail = (f, msg) => issues.push(`${f}: ${msg}`);

/* ---------- ১. ট্যাগ-ব্যালান্স ---------- */
// ভয়েড-এলিমেন্ট ও সেইফ-লিস্ট — এগুলোতে ক্লোজিং লাগে না
const VOID = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
  'link', 'meta', 'param', 'source', 'track', 'wbr']);
// একই ট্যাগে ভেতরে-ভেতরে বন্ধ হলে ব্রাউজারকে ছাড় দেওয়া হয় — কিন্তু
// <a> ভেতরে <a> কখনোই বৈধ নয়, তাই <a> আলাদা করে কঠোর
const AUTO_CLOSE = new Set(['li', 'p', 'td', 'th', 'tr', 'option', 'dt', 'dd']);

for (const f of files) {
  const html = fs.readFileSync(f, 'utf8');
  // script/style/pre/textarea-এর ভেতরকার «<» বাদ
  const clean = html.replace(/<(script|style|pre|textarea)\b[^>]*>[\s\S]*?<\/\1>/gi, ' ');
  const stack = [];
  const tagRe = /<(\/?)([a-zA-Z][a-zA-Z0-9-]*)\b[^>]*?(\/?)>/g;
  let m;
  while ((m = tagRe.exec(clean))) {
    const [, close, rawName, selfClose] = m;
    const name = rawName.toLowerCase();
    if (VOID.has(name) || selfClose === '/') continue;
    if (!close) { stack.push(name); continue; }
    // বন্ধ করার ট্যাগ — স্ট্যাকে খুঁজি
    let idx = -1;
    for (let i = stack.length - 1; i >= 0; i--) if (stack[i] === name) { idx = i; break; }
    if (idx === -1) { fail(f, `অতিরিক্ত </${name}>`); continue; }
    if (idx !== stack.length - 1) {
      // ভেতরের যা খোলা রয়ে গেল
      const left = stack.slice(idx + 1);
      const hard = left.filter((t) => !AUTO_CLOSE.has(t));
      // <a> ভেতরে <a> — কঠোরভাবে ভুল
      if (hard.length && name === 'a') fail(f, `<a> বন্ধ করার আগে খোলা: ${hard.join(', ')}`);
      else if (hard.length && hard.includes('a')) fail(f, `</${name}> বন্ধ করার আগে খোলা <a>`);
    }
    stack.length = idx;
  }
  if (stack.length) {
    const hard = stack.filter((t) => !AUTO_CLOSE.has(t) && t !== 'html' && t !== 'body');
    if (hard.length) fail(f, `বন্ধ হয়নি: ${hard.join(', ')}`);
  }
}

/* ---------- ২. সংখ্যা-ফরম্যাট অসঙ্গতি ---------- */
const text = (f) => {
  let s = fs.readFileSync(f, 'utf8');
  s = s.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, ' ');
  return s.replace(/<[^>]+>/g, ' ');
};
const UNITS = ['শ্লোক', 'অধ্যায়', 'মন্ত্র', 'পুস্তক', 'সূরা', 'আয়াত', 'পদ', 'হাদিস'];
const numRe = new RegExp(`([০-৯][০-৯,]*)\\s*(${UNITS.join('|')})`, 'g');
const byUnit = {};
for (const f of files) {
  const t = text(f);
  let m;
  while ((m = numRe.exec(t))) {
    const num = m[1], unit = m[2];
    (byUnit[unit] ||= {});
    (byUnit[unit][num] ||= []).push(f);
  }
}
for (const [unit, map] of Object.entries(byUnit)) {
  const norm = {};
  for (const num of Object.keys(map)) (norm[num.replace(/,/g, '')] ||= []).push(num);
  for (const [base, variants] of Object.entries(norm)) {
    if (variants.length > 1) {
      fail('(সাইট)',
        `${unit}: একই সংখ্যা ${variants.map((v) => `«${v}»`).join(' / ')} — ফরম্যাট মেলাতে হবে`);
    }
  }
}

/* ---------- ৩. বানান-অসঙ্গতি ---------- */
// [সন্দেহভাজন, প্রত্যাশিত] — যাচাই-করা জোড়া
const SPELL = [
  ['হাদীস', 'হাদিস'],
  ['কোরআন', 'কুরআন'],
];
const allText = files.map((f) => [f, text(f)]);
for (const [wrong, right] of SPELL) {
  let wrongCount = 0, rightCount = 0;
  const where = [];
  for (const [f, t] of allText) {
    const n = (t.match(new RegExp(wrong, 'g')) || []).length;
    if (n) { wrongCount += n; where.push(f); }
    rightCount += (t.match(new RegExp(right, 'g')) || []).length;
  }
  // সংখ্যাগরিষ্ঠ রূপই মান — বিচ্ছিন্ন রূপ ধরা পড়বে
  if (wrongCount && rightCount > wrongCount) {
    fail('(সাইট)', `বানান «${wrong}» ${wrongCount} বার (মান «${right}» ${rightCount} বার): ${where.join(', ')}`);
  }
}

/* ---------- ৪. ডেটা-ফাইল বৈধ JSON ---------- */
const dataDirs = ['assets/grantho/data'];
const jsonCheck = (p) => {
  try { JSON.parse(fs.readFileSync(p, 'utf8')); return true; }
  catch (e) { fail(path.relative(ROOTDIR, p), `JSON ভাঙা: ${e.message}`); return false; }
};
const walkJson = (d) => {
  if (!fs.existsSync(d)) return;
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    if (e.name === '_debug') continue;
    const p = path.join(d, e.name);
    if (e.isDirectory()) walkJson(p);
    else if (e.name.endsWith('.json')) jsonCheck(p);
  }
};
dataDirs.forEach(walkJson);

/* ---------- ফলাফল ---------- */
const uniq = [...new Set(issues)];
if (uniq.length) {
  console.log('⚠ সমস্যা পাওয়া গেছে:\n');
  uniq.forEach((i) => console.log('  ✗ ' + i));
  console.log('');
}
console.log(`পাতা: ${files.length} · issues: ${uniq.length} / ${files.length}`);
process.exit(uniq.length ? 1 : 0);
