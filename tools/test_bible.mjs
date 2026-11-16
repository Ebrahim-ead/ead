#!/usr/bin/env node
/**
 * বাইবেল-সেকশন পরীক্ষা — দাবি বনাম ডেটা মিলিয়ে দেখে।
 *
 * কেন এই পরীক্ষা: আগে সাইটে «সম্পূর্ণ পাঠ» লেখা ছিল, অথচ ৬৬ পুস্তকের
 * মধ্যে ৪৬টি ও ১,০০০ অধ্যায়ের মধ্যে ৮৪৪টি ছিল — ব্যবহারকারীকে ভুল
 * বলা হচ্ছিল। সে যেন আর না ঘটে, তাই নিচের চেকগুলো:
 *
 *   ১. index.json-এর অধ্যায়-গণনা বাস্তব perChapter-এর সাথে মেলে
 *   ২. chaptersTotal (প্রামাণ্য) সেট আছে ও অসম্পূর্ণ পুস্তক চিহ্নিত
 *   ৩. পাতা «সম্পূর্ণ» দাবি করে না, যদি পাঠ অসম্পূর্ণ হয়
 *   ৪. পাতা অসম্পূর্ণতার ঘোষণা দেয় (g-src-warn বা সমতুল্য)
 *   ৫. অসম্পূর্ণ পুস্তকের নাম ও সংখ্যা ঘোষণায় আছে
 *   ৬. বাইবেলে «সংস্কৃত মূল পাঠ»-জাতীয় ভুল ফ্যাক্ট-চিপ নেই
 *   ৭. সংখ্যা বাংলা অঙ্কে (নোটে ইংরেজি 46/24087 থাকলে ধরে)
 *
 * ব্যবহার:  node tools/test_bible.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const read = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');

let pass = 0, fail = 0;
const ok = (m) => { pass++; console.log('  ✓ ' + m); };
const no = (m) => { fail++; console.log('  ✗ ' + m); };

const ix = JSON.parse(read('assets/grantho/data/bible/index.json'));
const bibleHtml = read('grantho/christian/bible.html');
const christHtml = read('grantho/christian.html');
const granthoHtml = read('grantho.html');

const text = (s) => s
  .replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, ' ')
  .replace(/<[^>]+>/g, ' ')
  .replace(/\s+/g, ' ');

console.log('\nডেটা-সঙ্গতি');

/* ১. perChapter সংখ্যা বাস্তব */
const books = ix.chapters || [];
const sumPc = books.reduce((n, c) => n + Object.keys(c.perChapter || {}).length, 0);
(sumPc === books.reduce((n, c) => n + (+c.suktaCount || 0), 0))
  ? ok(`suktaCount ও perChapter মেলে (${sumPc})`)
  : no(`suktaCount ও perChapter অমিল (${sumPc})`);

/* ২. chaptersTotal সেট */
const withTotal = books.filter((c) => +c.chaptersTotal > 0);
withTotal.length === books.length
  ? ok(`সব ${books.length}টি পুস্তকে chaptersTotal আছে`)
  : no(`chaptersTotal নেই ${books.length - withTotal.length}টি পুস্তকে`);

const wantCh = books.reduce((n, c) => n + (+c.chaptersTotal || 0), 0);
(wantCh === +ix.chaptersTotal)
  ? ok(`chaptersTotal সমষ্টি ${wantCh}`)
  : no(`chaptersTotal সমষ্টি ${wantCh} ≠ ${ix.chaptersTotal}`);

/* ৩. অসম্পূর্ণ পুস্তক — ডেটা থেকে */
const partial = books.filter((c) => {
  const have = Object.keys(c.perChapter || {}).length;
  return have > 0 && have < (+c.chaptersTotal || 0);
});
(partial.length === 6)
  ? ok(`অসম্পূর্ণ পুস্তক ৬টি (${partial.map((c) => c.bn).join(' · ')})`)
  : no(`অসম্পূর্ণ পুস্তক ${partial.length}টি — প্রত্যাশিত ৬`);

/* ৪. পদ-গণনা */
const totalV = books.reduce((n, c) => n + (+c.count || 0), 0);
(totalV === +ix.total)
  ? ok(`মোট পদ ${ix.total.toLocaleString('en')}`)
  : no(`পদ-গণনা অমিল: ${totalV} ≠ ${ix.total}`);
(+ix.withBn < +ix.total)
  ? ok(`বাংলা-অভাবী পদ ${ix.total - ix.withBn}`)
  : no('withBn, total-এর সমান বা বেশি');

console.log('\nদাবি বনাম বাস্তব');

const bi = text(bibleHtml);
const ch = text(christHtml);

/* ৫. «সম্পূর্ণ পাঠ» দাবি নেই */
/সম্পূর্ণ পাঠ/.test(bi)
  ? no('bible.html এখনো «সম্পূর্ণ পাঠ» দাবি করে')
  : ok('bible.html «সম্পূর্ণ পাঠ» দাবি করে না');

(/(৪৬|৪৬টি)\s*পুস্তক/.test(bi) && !/৬৬/.test(bi))
  ? no('bible.html-এ ৪৬ আছে কিন্তু ৬৬-এর উল্লেখ নেই')
  : ok('bible.html পাঠের সীমা উল্লেখ করে');

/* ৬. অসম্পূর্ণতার ঘোষণা */
(bibleHtml.includes('g-src-warn') || /অসম্পূর্ণ/.test(bi))
  ? ok('bible.html পাঠ অসম্পূর্ণ বলে ঘোষণা দেয়')
  : no('bible.html অসম্পূর্ণতার ঘোষণা নেই');

/* ৭. অসম্পূর্ণ পুস্তকের নাম ঘোষণায় */
const announced = partial.filter((c) => bi.includes(c.bn));
(announced.length === partial.length)
  ? ok(`অসম্পূর্ণ ${partial.length}টি পুস্তকেরই নাম ঘোষণায়`)
  : no(`ঘোষণায় নেই: ${partial.filter((c) => !bi.includes(c.bn)).map((c) => c.bn).join(', ')}`);

/* ৮. অনুপস্থিত ২০ পুস্তক — প্রকাশিত বাক্য ঘোষিত? */
(/প্রকাশিত বাক্য/.test(bi))
  ? ok('অনুপস্থিত পুস্তক (প্রকাশিত বাক্য) ঘোষণায় আছে')
  : no('প্রকাশিত বাক্য — অনুপস্থিত কিন্তু ঘোষণায় নেই');

/* ৯. ৬৬/১,০০০ প্রামাণ্য সংখ্যা */
/৬৬ পুস্তক/.test(bi)
  ? ok('«৬৬ পুস্তক» প্রামাণ্য সংখ্যা উল্লেখিত')
  : no('«৬৬ পুস্তক» উল্লেখ নেই');
/১,০০০ অধ্যায়/.test(bi)
  ? ok('«১,০০০ অধ্যায়» উল্লেখিত')
  : no('«১,০০০ অধ্যায়» উল্লেখ নেই');

/* ১০. কার্ডে ৪৬/৬৬ */
/৪৬\/৬৬/.test(ch) ? ok('christian.html কার্ডে ৪৬/৬৬') : no('christian.html কার্ডে ৪৬/৬৬ নেই');
/৪৬\/৬৬/.test(text(granthoHtml)) ? ok('grantho.html কার্ডে ৪৬/৬৬') : no('grantho.html কার্ডে ৪৬/৬৬ নেই');

console.log('\nবিষয়বস্তু-শুদ্ধতা');

/* ১১. বাইবেলে ভুল ফ্যাক্ট-চিপ */
const facts = [...bibleHtml.matchAll(/<div class="g-facts">([\s\S]*?)<\/div>/g)].map((m) => m[1]);
const factTxt = text(facts.join(' '));
(/সংস্কৃত/.test(factTxt))
  ? no('বাইবেল পাতায় «সংস্কৃত» ফ্যাক্ট-চিপ এখনো আছে')
  : ok('«সংস্কৃত মূল পাঠ» বাদ গেছে');

/* ১২. নোটে ইংরেজি অঙ্ক নেই (৪৬ / 24087) */
const src = [...bibleHtml.matchAll(/<div class="g-src[^"]*">([\s\S]*?)<\/div>/g)].map((m) => m[1]).join(' ');
/\b(46|24087|844)\b/.test(text(src))
  ? no('নোটে ইংরেজি অঙ্ক আছে (46/24087/844)')
  : ok('নোটে সব সংখ্যা বাংলা অঙ্কে');

/* ১৩. জোড়া-বাক্য: «পাঠ বসানো হয়নি বাংলা» */
/পাঠ বসানো হয়নি বাংলা/.test(text(src))
  ? no('নোটে জোড়া-বাক্য এখনো আছে')
  : ok('নোটের বাক্য-সীমা ঠিক');

/* ১৪. meta description-এ সীমা */
const desc = (bibleHtml.match(/<meta name="description" content="([^"]*)"/) || [])[1] || '';
/অসম্পূর্ণ|৬৬/.test(desc)
  ? ok('meta description পাঠের সীমা বলে')
  : no('meta description সীমা জানে না');

/* ১৫. উৎস-উল্লেখ */
(/ebanglalibrary\.com/.test(bi) && /New American Bible/.test(bi) && /vatican\.va/.test(bi))
  ? ok('বাংলা ও ইংরেজি উৎস দুটোই উল্লিখিত')
  : no('উৎস-উল্লেখ অসম্পূর্ণ');

console.log(`\n${fail ? '✗' : '✓'} পাশ ${pass} · ফেল ${fail}`);
process.exit(fail ? 1 : 0);
