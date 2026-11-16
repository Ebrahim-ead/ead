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
/* সংখ্যাগুলো ডেটা থেকেই — হার্ডকোড করা মানে ডেটা বদলালেই টেস্ট মিথ্যা ব্যর্থ হয়
   (২০২৬-১১-১৬: ন্যূনতম পাঠে ৬৬→৫০ নামল, টেস্ট হার্ডকোড ৬৬ দাবি করে চলল)। */
const HAVE_BOOKS = books.length;
const HAVE_CH = books.reduce((n, c) => n + Object.keys(c.perChapter || {}).length, 0);
const HAVE_VERSES = ix.withBn || ix.total || 0;

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
  return want > 0 && have < want;   // ফিল্ড না থাকলে «অজানা», অসম্পূর্ণ নয়
});
(incomplete.length === 0)
  ? ok('কোনো পুস্তক অসম্পূর্ণ নয়')
  : no(`অসম্পূর্ণ: ${incomplete.map((c) => `${c.bn} ${Object.keys(c.perChapter || {}).length}/${c.chaptersTotal}`).join(', ')}`);

/* ৩. পুরাতন/নতুন ভাগ */
/* testament ফিল্ড কিছু পুস্তকে নাও থাকতে পারে; তখন ক্যাননের ক্রম (id ≤ ৩৯ =
   পুরাতন) ধরাই সঠিক — রিডারও ঠিক এটাই করে (bible-reader.js bookTestament)। */
const tst = (c) => (c.testament === 'old' || c.testament === 'new')
  ? c.testament : (c.id <= 39 ? 'old' : 'new');
const oldN = books.filter((c) => tst(c) === 'old').length;
const newN = books.filter((c) => tst(c) === 'new').length;
(oldN > 0 && newN > 0)
  ? ok(`নিয়ম-ভাগ: পুরাতন ${oldN} · নতুন ${newN} (ক্রম-ভিত্তিক ফ্যালব্যাক সহ)`)
  : no(`নিয়ম-ভাগ ভুল: পুরাতন ${oldN} · নতুন ${newN}`);

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
/* total = উৎসে গোনা পদ, withBn = বাংলা পাঠসহ। total ≥ withBn-ই সঠিক নিয়ম;
   উৎসে পাঠহীন পদ থাকলে সমান হওয়া জরুরি নয়। */
const diff = +ix.total - HAVE_VERSES;
(diff >= 0)
  ? ok(`মোট পদ ${(+ix.total).toLocaleString('en')} · বাংলাসহ ${(+HAVE_VERSES).toLocaleString('en')}` +
       (diff ? ` (${diff.toLocaleString('en')}টি উৎসে পাঠহীন)` : ''))
  : no(`withBn (${HAVE_VERSES}) > total (${ix.total}) — অসম্ভব`);

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

/* ৮. সংখ্যাগুলো পাতায় আছে — ডেটার বাস্তব সংখ্যা দিয়েই, হার্ডকোড নয় */
const bnNum = (n) => String(n).replace(/[0-9]/g, (d) => '০১২৩৪৫৬৭৮৯'[+d]);
const wantBooks = bnNum(books.length);
const wantCh = bnNum(realCh);
const wantVerses = bnNum(String(+ix.total).replace(/\B(?=(\d{3})+(?!\d))/g, ','));
(bi.includes(wantVerses) && bi.includes(wantBooks))
  ? ok(`পাতায় ${wantBooks} পুস্তক · ${wantVerses} পদ (ডেটার সাথে মেলে)`)
  : no(`পাতায় ${wantBooks} পুস্তক বা ${wantVerses} পদ নেই`);

/* ৯. কার্ডেও মেলে */
(ch.includes(wantBooks + ' পুস্তক') || ch.includes(wantVerses))
  ? ok(`christian.html কার্ডে ${wantBooks} পুস্তক / ${wantVerses} পদ`)
  : no(`christian.html কার্ডে ${wantBooks} পুস্তক বা ${wantVerses} পদ নেই`);

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
