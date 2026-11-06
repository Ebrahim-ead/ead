/* গ্রন্থ-পাতার রিডার-টেস্ট — প্রতিটি পাতা যেন নিজের ডেটাই দেখায়।
 *
 * কেন দরকার: build_pages.py টেমপ্লেট হিসেবে অন্য গ্রন্থের পাতা ব্যবহার করে।
 * আগে পরিচয়-বদলিগুলো হার্ডকোডেড "সামবেদ …" স্ট্রিং ধরে লেখা ছিল, তাই টেমপ্লেট
 * ঋগ্বেদ হলে data-base ঋগ্বেদের ফোল্ডারেই থেকে যেত — শুক্ল যজুর্বেদের পাতায়
 * পাঠক ঋগ্বেদের মন্ত্র দেখত। এই টেস্ট পাতার নিজের data-base থেকে ডেটা লোড
 * করে, তাই ওই ধরনের অমিল ধরা পড়ে।
 *
 * চালাতে:  node tools/test_reader.mjs [পাতা …]
 * বিল্ডি:   jsdom (npm i jsdom)
 */
import { JSDOM } from 'jsdom';
import fs from 'fs';
import path from 'path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');

function pages() {
  const args = process.argv.slice(2);
  if (args.length) return args.map((a) => path.resolve(ROOT, a));
  const dir = path.join(ROOT, 'grantho', 'hindu');
  return fs.readdirSync(dir)
    .filter((f) => f.endsWith('.html'))
    .map((f) => path.join(dir, f))
    .filter((f) => /data-base="/.test(fs.readFileSync(f, 'utf8')));
}

function attrs(html) {
  const g = (re) => (html.match(re) || [])[1] || '';
  return {
    granth: g(/data-granth="([^"]*)"/),
    base: g(/data-base="([^"]*)"/),
    title: (html.match(/<title>([^<]*)<\/title>/) || [])[1] || '',
    h1: (html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/) || [])[1] || '',
  };
}

async function testPage(file) {
  const rel = path.relative(ROOT, file);
  const html = fs.readFileSync(file, 'utf8');
  const slug = path.basename(file, '.html');
  const a = attrs(html);
  const errs = [];

  // ১) পাতার নিজের পরিচয় ডেটা-ফোল্ডারের সাথে মিলতে হবে
  const wantBase = `../../assets/grantho/data/${slug}/`;
  if (a.base !== wantBase) errs.push(`data-base "${a.base}" ≠ "${wantBase}"`);
  if (a.granth !== slug) errs.push(`data-granth "${a.granth}" ≠ "${slug}"`);

  // ২) রেন্ডার: jsdom-এ পাতাটি চালিয়ে ডেটা লোড করা হয় — fetch স্টাব পাতার
  //    নিজের data-base অনুসরণ করে (আমাদের ঠিকানা দিয়ে নয়)
  const dataDir = path.resolve(path.dirname(file), a.base || wantBase);
  const idxPath = path.join(dataDir, 'index.json');
  if (!fs.existsSync(idxPath)) errs.push(`ডেটা নেই: ${path.relative(ROOT, idxPath)}`);

  const dom = new JSDOM(html, {
    runScripts: 'dangerously', pretendToBeVisual: true,
    url: `https://example.invalid/ead/grantho/hindu/${slug}.html`,
  });
  const { window } = dom;
  window.scrollTo = () => {};
  window.fetch = async (u) => {
    const name = String(u).split('/').pop().split('?')[0];
    const fp = path.join(dataDir, name);
    const ok = fs.existsSync(fp);
    return {
      ok,
      status: ok ? 200 : 404,
      json: async () => (ok ? JSON.parse(fs.readFileSync(fp, 'utf8')) : null),
      text: async () => (ok ? fs.readFileSync(fp, 'utf8') : ''),
    };
  };
  try {
    window.eval(fs.readFileSync(path.join(ROOT, 'assets/grantho/grantho.js'), 'utf8'));
  } catch (e) {
    errs.push(`grantho.js চালানো যায়নি: ${e.message}`);
  }
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  await wait(1200);

  const doc = window.document;
  const idx = fs.existsSync(idxPath) ? JSON.parse(fs.readFileSync(idxPath, 'utf8')) : null;
  const list = doc.getElementById('g-chapter-list');
  const nbtn = list ? list.children.length : 0;
  if (idx && nbtn !== idx.chapters.length) {
    errs.push(`অধ্যায়-বাটন ${nbtn} ≠ ডেটার ${idx.chapters.length}`);
  }
  // অধ্যায়-তালিকায় গ্রন্থের নাম থাকে না (সেটি অধ্যায়ের শিরোনাম) — তাই এখানে
  // শুধু বাটনগুলো খালি নয় এবং সংখ্যা ডেটার সাথে মিলছে, এটুকুই দেখা হয়।
  if (nbtn && [...list.children].some((b) => !b.textContent.trim())) {
    errs.push('অধ্যায়-তালিকায় খালি বাটন আছে');
  }

  // প্রথম অধ্যায় খুলে যাচাই: অধ্যায়-শিরোনাম ডেটার index.bn থেকে তৈরি (অর্থাৎ
  // সত্যিই এই গ্রন্থের ডেটা লোড হয়েছে), আর খণ্ড রেন্ডার হয়েছে।
  // খণ্ড-সংখ্যা সমান হতে বাধ্য নয় — বড় গ্রন্থে রিডার ধাপে ধাপে দেখায়।
  let rendered = 0;
  let chTitle = '';
  if (list && list.children.length && idx) {
    list.children[0].dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await wait(1200);
    rendered = doc.querySelectorAll('.g-v').length;
    const tEl = doc.getElementById('g-ch-title');
    chTitle = tEl ? tEl.textContent.trim() : '';
    const vs = JSON.parse(fs.readFileSync(path.join(dataDir, `ch${idx.chapters[0].id}.json`), 'utf8')).verses;
    if (rendered < 1) errs.push('একটিও খণ্ড রেন্ডার হয়নি');
    if (rendered > vs.length) errs.push(`রেন্ডার খণ্ড ${rendered} > চ্যাপ্টার-ফাইলের ${vs.length}`);
    if (!chTitle || chTitle.includes('লোড হচ্ছে')) {
      errs.push(`অধ্যায়-শিরোনাম লোড হয়নি («${chTitle}»)`);
    }
    // সবচেয়ে জোরালো যাচাই: রেন্ডার হওয়া প্রথম খণ্ডের পাঠ এই গ্রন্থের নিজের
    // চ্যাপ্টার-ফাইলের প্রথম খণ্ডের সাথে মিলতে হবে — অন্য গ্রন্থের ডেটা লোড
    // হলে (যেমন data-base ভুল থাকলে) এখানেই ধরা পড়ে।
    // প্রদর্শিত নম্বর: সংখ্যাই হতে হবে এবং ১..N ক্রমে — নইলে পাঠককে
    // মন্ত্র উল্টাপাল্টা মনে হয় (যজুর্বেদে একবার এমনই হয়েছিল)
    const badges = [...doc.querySelectorAll('.g-v-num')].map((e) => e.textContent.trim());
    if (badges.some((b) => !/^[০-৯]+$/.test(b))) {
      errs.push(`সংখ্যা-ব্যাজে অ-সংখ্যা লেবেল: ${badges.filter((b) => !/^[০-৯]+$/.test(b)).slice(0, 3).join(', ')}`);
    }
    const BN = { '০':0,'১':1,'২':2,'৩':3,'৪':4,'৫':5,'৬':6,'৭':7,'৮':8,'৯':9 };
    const nums = badges.map((b) => [...b].reduce((a, c) => a * 10 + (BN[c] ?? NaN), 0));
    const shownNums = nums.filter((x) => !Number.isNaN(x));
    if (shownNums.length > 1) {
      const seqOK = shownNums.every((x, i) => i === 0 ? true : x > shownNums[i - 1]);
      if (!seqOK) errs.push(`প্রদর্শিত নম্বর ক্রমে নেই: ${shownNums.slice(0, 8).join(',')}`);
      if (shownNums[0] !== 1) errs.push(`প্রথম নম্বর ${shownNums[0]} — ১ থেকে শুরু হওয়ার কথা`);
    }

    // উৎসের অনুক্রমণিকা/ভূমিকা আলাদা ব্লকে দেখাতে হবে (মন্ত্র-তালিকায় নয়)
    const ch = JSON.parse(fs.readFileSync(path.join(dataDir, `ch${idx.chapters[0].id}.json`), 'utf8'));
    const frontEl = doc.querySelector('.g-front');
    if (ch.preface && !frontEl) errs.push('ভূমিকা ডেটায় আছে কিন্তু রেন্ডার হয়নি');
    if (frontEl && !ch.preface) errs.push('ভূমিকা নেই অথচ ব্লক রেন্ডার হয়েছে');
    if (frontEl && frontEl.open) errs.push('ভূমিকা-ব্লক খোলা অবস্থায় আছে (কল্যাপ্স থাকার কথা)');

    // সব খণ্ডে বাংলা থাকলে অকেজো ছাঁকনি দেখানো যাবে না
    const onlyBn = doc.getElementById('g-only-bn');
    if (idx.withBn === idx.total && onlyBn && !onlyBn.hidden &&
        !(onlyBn.closest && onlyBn.closest('label') && onlyBn.closest('label').hidden)) {
      errs.push('সব খণ্ডে বাংলা আছে, তবু «কেবল যেগুলোর অনুবাদ আছে» ছাঁকনি দেখা যাচ্ছে');
    }

    // অধ্যায়-তালিকার বাটনে ভূমিকার উপস্থিতি দেখানো হচ্ছে কি না
    const c0 = idx.chapters[0];
    const btn0 = list.children[0] ? list.children[0].textContent : '';
    if (c0.prefaceCount && !btn0.includes('অনুক্রমণিকা')) {
      errs.push('অধ্যায়-বাটনে ভূমিকা-চিহ্ন নেই (prefaceCount আছে)');
    }

    const strip = (x) => String(x || '').replace(/\s+/g, ' ').trim();
    const firstBn = strip(vs[0] && vs[0].bn).slice(0, 60);
    const shown = [...doc.querySelectorAll('.g-v .g-v-bn')]
      .map((e) => strip(e.textContent)).filter(Boolean);
    if (firstBn && !shown.some((t) => t.slice(0, 40) === firstBn.slice(0, 40))) {
      errs.push('রেন্ডার হওয়া পাঠ এই গ্রন্থের চ্যাপ্টার-ফাইলের সাথে মিলছে না '
                + '(অন্য গ্রন্থের ডেটা লোড হয়েছে?)');
    }
  }

  // ৩) অন্য গ্রন্থের নাম পাতায় থেকে গেলে তাও ভুল
  const others = ['ঋগ্বেদ', 'সামবেদ', 'কৃষ্ণ যজুর্বেদ', 'অথর্ববেদ', 'শ্রীমদ্ভগবদ্গীতা']
    .filter((w) => !a.title.includes(w) && !slug.includes(w.split(' ')[0]));
  const body = doc.body ? doc.body.textContent : '';
  for (const w of others) {
    if (html.includes(w)) errs.push(`পাতার HTML-এ অন্য গ্রন্থের নাম: «${w}»`);
  }

  const facts = (html.match(/<div class="g-facts">([\s\S]*?)<\/div>/) || [])[1] || '';
  const factNums = [...facts.replace(/<[^>]+>/g, ' ').matchAll(/[০-৯,]+/g)].map((m) => m[0]);
  console.log(`${errs.length ? '✗' : '✓'} ${rel}`);
  console.log(`   data-base=${a.base} · অধ্যায়-বাটন ${nbtn} · খণ্ড ${rendered} · শিরোনাম «${chTitle}»` +
    (idx ? ` · ডেটা: ${idx.total} ${idx.verseWord || ''} / ${idx.chapters.length} অধ্যায়` : '') +
    ` · ফ্যাক্টস: ${factNums.join(' ')}`);
  for (const e of errs) console.log(`   ! ${e}`);
  window.close();
  return errs.length === 0;
}

let ok = true;
for (const f of pages()) ok = (await testPage(f)) && ok;
console.log(ok ? '\nসব পাতা নিজের ডেটাই দেখাচ্ছে ✓' : '\nকিছু পাতায় সমস্যা আছে ✗');
process.exit(ok ? 0 : 1);
