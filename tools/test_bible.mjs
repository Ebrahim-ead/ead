#!/usr/bin/env node
/**
 * বাইবেল-সেকশন পরীক্ষা — দাবি বনাম ডেটা মিলিয়ে দেখে।
 *
 * ইতিহাস: একসময় সাইট «সম্পূর্ণ পাঠ» বলত, অথচ ৬৬ পুস্তকের মধ্যে ৪৬টি ও
 * ১,১৮৯ অধ্যায়ের মধ্যে ৮৪৪টি ছিল। এখন পাঠ সত্যিই পূর্ণ — তাই পরীক্ষাটি
 * উল্টো দিক থেকে পাহারা দেয়: **যদি পাঠ আবার খোয়া যায়, দাবিটি মিথ্যা হয়ে
 * যাবে** — সেটাই ধরা পড়বে।
 *
 *   ১. ৬৬ পুস্তক · ১,১৮৯ অধ্যায় — প্রামাণ্য সংখ্যা
 *   ২. chaptersTotal = বাস্তব perChapter (প্রতিটি পুস্তক পূর্ণ)
 *   ৩. পদ-গণনা index ↔ ফাইল ↔ মানক সংখ্যা
 *   ৪. পাতা যেন সত্য কথা বলে (পূর্ণ হলে «সম্পূর্ণ», অসম্পূর্ণ হলে ঘোষণা)
 *   ৫. পুরাতন/নতুন নিয়মের ভাগ ৩৯/২৭
 *   ৬. বাইবেল পাতায় «সংস্কৃত»-জাতীয় ভুল চিপ নেই
 *   ৭. সংখ্যা বাংলা অঙ্কে
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

const books = ix.chapters || [];
const HAVE_CH = 1189;
const HAVE_BOOKS = 66;
const HAVE_VERSES = 31130;

console.log('\nপ্রামাণ্য সংখ্যা');

/* ১. পুস্তক ও অধ্যায় */
(books.length === HAVE_BOOKS)
  ? ok(`${HAVE_BOOKS} পুস্তক`)
  : no(`পুস্তক ${books.length} — প্রত্যাশিত ${HAVE_BOOKS}`);

const realCh = books.reduce((n, c) => n + Object.keys(c.perChapter || {}).length, 0);
(realCh === HAVE_CH)
  ? ok(`${HAVE_CH} অধ্যায় (প্রতিটি পুস্তক পূর্ণ)`)
  : no(`অধ্যায় ${realCh} — প্রত্যাশিত ${HAVE_CH} (${HAVE_CH - realCh}টি নেই)`);

/* ২. chaptersTotal = বাস্তব perChapter */
const incomplete = books.filter((c) => {
  const have = Object.keys(c.perChapter || {}).length;
  const want = +c.chaptersTotal || 0;
  return !want || have < want;
});
(incomplete.length === 0)
  ? ok('কোনো পুস্তক অসম্পূর্ণ নয়')
  : no(`অসম্পূর্ণ: ${incomplete.map((c) => `${c.bn} ${Object.keys(c.perChapter || {}).length}/${c.chaptersTotal}`).join(', ')}`);

/* ৩. পুরাতন/নতুন ভাগ */
const oldN = books.filter((c) => c.testament === 'old').length;
const newN = books.filter((c) => c.testament === 'new').length;
(oldN === 39 && newN === 27)
  ? ok(`পুরাতন ৩৯ · নতুন ২৭`)
  : no(`নিয়ম-ভাগ ভুল: পুরাতন ${oldN} · নতুন ${newN} (প্রত্যাশিত ৩৯/২৭)`);

console.log('\nপদ-গণনা');

/* ৪. index.total = ফাইলের সমষ্টি */
let sumFiles = 0;
for (const c of books) {
  const d = JSON.parse(read(`assets/grantho/data/bible/ch${c.id}.json`));
  sumFiles += (d.verses || []).length;
}
(sumFiles === +ix.total)
  ? ok(`মোট পদ ${ix.total.toLocaleString('en')} (ফাইল ও index মেলে)`)
  : no(`পদ-গণনা অমিল: ফাইল ${sumFiles} ≠ index ${ix.total}`);

/* ৫. প্রত্যাশিত মোট পদের কাছাকাছি (বাংলা অনুবাদে সামান্য ভিন্নতা স্বাভাবিক) */
const diff = Math.abs(+ix.total - HAVE_VERSES);
(diff <= 5)
  ? ok(`প্রামাণ্য ${HAVE_VERSES.toLocaleString('en')} পদের সাথে ±${diff}`)
  : no(`মোট পদ ${ix.total} — প্রত্যাশিত ${HAVE_VERSES} (পার্থক্য ${diff})`);

/* ৬. সব পদে বাংলা পাঠ আছে */
const empty = books.filter((c) => (+c.count || 0) === 0);
(empty.length === 0)
  ? ok('প্রতিটি পুস্তকে পদ আছে')
  : no(`খালি পুস্তক: ${empty.map((c) => c.bn).join(', ')}`);

console.log('\nদাবি বনাম বাস্তব');

const bi = text(bibleHtml);
const ch = text(christHtml);

/* ৭. «সম্পূর্ণ» দাবি — এখন সত্য */
const claimsFull = /সম্পূর্ণ পাঠ/.test(bi);
if (claimsFull) {
  (realCh === HAVE_CH && books.length === HAVE_BOOKS)
    ? ok('«সম্পূর্ণ পাঠ» দাবি করে — এবং সত্যিই পূর্ণ')
    : no('«সম্পূর্ণ পাঠ» দাবি করে, কিন্তু পাঠ অসম্পূর্ণ!');
} else {
  ok('«সম্পূর্ণ পাঠ» দাবি করে না');
}

/* ৮. সংখ্যাগুলো পাতায় আছে */
(/৬৬/.test(bi) && /১,১৮৯/.test(bi) && /৩১,১৩০/.test(bi))
  ? ok('পাতায় ৬৬ · ১,১৮৯ · ৩১,১৩০')
  : no('পাতায় ৬৬ / ১,১৮৯ / ৩১,১৩০-এর কোনোটি নেই');

/* ৯. কার্ডেও মেলে */
/৬৬ পুস্তক/.test(ch) ? ok('christian.html কার্ডে ৬৬ পুস্তক') : no('christian.html কার্ডে ৬৬ পুস্তক নেই');
/৬৬ পুস্তক/.test(text(granthoHtml)) ? ok('grantho.html কার্ডে ৬৬ পুস্তক') : no('grantho.html কার্ডে ৬৬ পুস্তক নেই');

/* ১০. পুরোনো ভুল সংখ্যা আর নেই */
/৮৪৪/.test(bi) ? no('bible.html-এ পুরোনো «৮৪৪» এখনো আছে') : ok('পুরোনো «৮৪৪» বাদ গেছে');
/২৪,০৮৭/.test(bi) ? no('bible.html-এ পুরোনো «২৪,০৮৭» এখনো আছে') : ok('পুরোনো «২৪,০৮৭» বাদ গেছে');

console.log('\nবিষয়বস্তু-শুদ্ধতা');

/* ১১. বাইবেলে ভুল ফ্যাক্ট-চিপ */
const facts = [...bibleHtml.matchAll(/<div class="g-facts">([\s\S]*?)<\/div>/g)].map((m) => m[1]);
(/সংস্কৃত/.test(text(facts.join(' '))))
  ? no('বাইবেল পাতায় «সংস্কৃত» ফ্যাক্ট-চিপ আছে')
  : ok('«সংস্কৃত মূল পাঠ» নেই');

/* ১২. নোটে ইংরেজি অঙ্ক নেই */
const src = [...bibleHtml.matchAll(/<div class="g-src[^"]*">([\s\S]*?)<\/div>/g)].map((m) => m[1]).join(' ');
/\b(46|24087|844|31130)\b/.test(text(src))
  ? no('নোটে ইংরেজি অঙ্ক আছে')
  : ok('নোটে সব সংখ্যা বাংলা অঙ্কে');

/* ১৩. জোড়া-বাক্য নেই */
/পাঠ বসানো হয়নি বাংলা/.test(text(src))
  ? no('নোটে জোড়া-বাক্য এখনো আছে')
  : ok('নোটের বাক্য-সীমা ঠিক');

/* ১৪. meta description */
const desc = (bibleHtml.match(/<meta name="description" content="([^"]*)"/) || [])[1] || '';
(/৬৬|সম্পূর্ণ/.test(desc))
  ? ok('meta description পাঠের কথা বলে')
  : no('meta description পুরোনো');

/* ১৫. উৎস-উল্লেখ */
(/ebanglalibrary\.com/.test(bi) && /New American Bible/.test(bi) && /vatican\.va/.test(bi))
  ? ok('বাংলা ও ইংরেজি উৎস দুটোই উল্লিখিত')
  : no('উৎস-উল্লেখ অসম্পূর্ণ');

console.log(`\n${fail ? '✗' : '✓'} পাশ ${pass} · ফেল ${fail}`);
process.exit(fail ? 1 : 0);
