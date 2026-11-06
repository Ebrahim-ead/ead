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
  // হিন্দু ও খ্রিস্টান — দুই ফোল্ডারের গ্রন্থ-পাতাই পরীক্ষা হয় (বাইবেল খ্রিস্টানে)
  const dirs = ['hindu', 'christian'].map((d) => path.join(ROOT, 'grantho', d));
  return dirs.filter((d) => fs.existsSync(d))
    .flatMap((dir) => fs.readdirSync(dir)
      .filter((f) => f.endsWith('.html'))
      .map((f) => path.join(dir, f)))
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
    url: `https://example.invalid/ead/${rel.split(path.sep).join('/')}`,
  });
  const { window } = dom;
  window.scrollTo = () => {};
  window.fetch = async (u) => {
    const su = String(u);
    const name = su.split('/').pop().split('?')[0];
    // ইংরেজি ডেটা সাব-ফোল্ডারে (en/chN.json) — ফাইলনামে নামালে বাংলা
    // চ্যাপ্টার-ফাইলটিই ফিরত যেত (একবার এমন ভুল ধরা পড়েছে)
    const fp = su.includes('/en/') ? path.join(dataDir, 'en', name) : path.join(dataDir, name);
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
  /* দুই স্তর (পুস্তক → অধ্যায় → পদ): বাইবেলের ডেটাতেই চেনা যায় */
  const twoLevel = !!idx && idx.chapters.some((c) => c.testament === 'old' || c.testament === 'new')
    && idx.chapters.some((c) => (+c.suktaCount || 0) > 0);
  /* দুই স্তর: গ্রুপযুক্ত গ্রন্থে (বাইবেল) বাঁ পাশে পুস্তক, বইয়ে ক্লিকে আগে
     অধ্যায়-গ্রিড, তারপর অধ্যায়ের পদ। একক-স্তরে আগের মতোই খণ্ড-তালিকা। */
  const list = doc.getElementById(twoLevel ? 'g-book-list' : 'g-chapter-list');
  const nbtn = list ? list.querySelectorAll('[data-ch]').length : 0;
  if (idx && nbtn !== idx.chapters.length) {
    errs.push(`অধ্যায়-বাটন ${nbtn} ≠ ডেটার ${idx.chapters.length}`);
  }
  if (twoLevel) {
    // পুরাতন/নতুন নিয়ম-ভাগ: সংখ্যা ডেটার সাথে মিলতে হবে, আর ছাঁকনিতে দেখা যাবে
    const tb = doc.getElementById('g-testament');
    const nOld = idx.chapters.filter((c) => (c.testament || (c.id <= 39 ? 'old' : 'new')) === 'old').length;
    const nNew = idx.chapters.length - nOld;
    const grp = [...doc.querySelectorAll('#g-book-list .g-tgroup')].map((e) => e.textContent);
    if (!tb || tb.hidden) errs.push('নিয়ম-ছাঁকনি দেখা যাচ্ছে না');
    if (!grp.some((t) => /পুরাতন/.test(t) && t.includes(String(nOld).replace(/\d/g, (d) => '০১২৩৪৫৬৭৮৯'[d])))) {
      errs.push(`পুরাতন নিয়ম-শিরোনাম নেই/ভুল (${grp.join(' | ')})`);
    }
    if (!grp.some((t) => /নতুন/.test(t))) errs.push('নতুন নিয়ম-শিরোনাম নেই');
    const btn = [...tb.querySelectorAll('.g-tbtn')].find((b) => b.dataset.t === 'new');
    if (btn) {
      btn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
      await wait(300);
      const vis = [...list.querySelectorAll('[data-ch]')].filter((b) => !b.hidden).length;
      if (vis !== nNew) errs.push(`«নতুন নিয়ম» ছাঁকনিতে ${vis} পুস্তক, হওয়া উচিত ${nNew}`);
      const all = [...tb.querySelectorAll('.g-tbtn')].find((b) => b.dataset.t === 'all');
      all.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
      await wait(300);
    }
    // বইয়ে ক্লিক: আগে শুধু অধ্যায় — পদ তখনো নয়
    list.querySelector('[data-ch]').dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await wait(500);
    const grid = doc.getElementById('g-chapter-grid');
    const c0 = idx.chapters[0];
    const wantCh = (+c0.suktaCount || 0) + ((c0.missing || []).length);
    const gotCh = grid ? grid.querySelectorAll('[data-c]').length : 0;
    if (gotCh !== wantCh) errs.push(`অধ্যায়-বাটন ${gotCh} ≠ ডেটার ${wantCh}`);
    if (doc.querySelectorAll('.g-v').length) errs.push('বই খোলার সাথে সাথেই পদ দেখাচ্ছে (আগে অধ্যায়-তালিকা হওয়া উচিত)');
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
  if (list && nbtn && idx) {
    if (twoLevel) {
      // বই ইতিমধ্যেই খোলা; অধ্যায় ১-এ ক্লিক → নিচে তার পদ
      const g1 = doc.querySelector('#g-chapter-grid [data-c="1"]');
      if (!g1) errs.push('অধ্যায়-গ্রিডে «১» নেই');
      else g1.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    } else {
      list.children[0].dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    }
    await wait(1200);
    rendered = doc.querySelectorAll('.g-v').length;
    const tEl = doc.getElementById('g-ch-title');
    chTitle = tEl ? tEl.textContent.trim() : '';
    const chFile = JSON.parse(fs.readFileSync(path.join(dataDir, `ch${idx.chapters[0].id}.json`), 'utf8'));
    const vs = twoLevel
      ? chFile.verses.filter((v) => v.ch === 1)
      : chFile.verses;
    if (rendered < 1) errs.push('একটিও খণ্ড রেন্ডার হয়নি');
    if (twoLevel && rendered !== vs.length) {
      errs.push(`অধ্যায় ১-এ ${rendered} পদ, ফাইলে ${vs.length} — পুরো বই নয়, কেবল অধ্যায় দেখানোর কথা`);
    }
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
    const grouped = vs.some((v) => typeof v.vn === 'number');
    const want = vs.slice(0, badges.length).map((v) => (typeof v.vn === 'number' ? v.vn : v.n));
    if (want.length && shownNums.join(',') !== want.join(',')) {
      errs.push(`প্রদর্শিত নম্বর ডেটার সাথে মিলছে না: পাওয়া ${shownNums.slice(0, 6).join(',')} · আশা ${want.slice(0, 6).join(',')}`);
    }
    if (grouped) {
      // বাইবেলের মতো গ্রুপযুক্ত গ্রন্থ: পদ-নম্বর প্রতি অধ্যায়ে ১ থেকে শুরু ও ক্রমবর্ধমান
      // (উৎসে কোনো পদ না থাকলে ফাঁক বৈধ — অনুমান করে পদ বসানো হয় না)
      let pc = null, pv = 0;
      for (const v of vs) {
        if (v.ch !== pc) {
          if (v.vn !== 1) errs.push(`অধ্যায় ${v.ch}: পদ ${v.vn} থেকে শুরু (১ হওয়ার কথা)`);
          pc = v.ch; pv = v.vn;
        } else {
          if (v.vn <= pv) errs.push(`অধ্যায় ${v.ch}: পদ-ক্রম ভাঙা ${pv} → ${v.vn}`);
          pv = v.vn;
        }
        if (errs.length > 12) break;
      }
      const g = (JSON.parse(fs.readFileSync(path.join(dataDir, `ch${idx.chapters[0].id}.json`), 'utf8')).suktas) || [];
      if (g.length && idx.chapters[0].suktaCount !== g.length) {
        errs.push(`সূচির suktaCount ${idx.chapters[0].suktaCount} ≠ ফাইলের গ্রুপ ${g.length}`);
      }
    } else if (shownNums.length > 1) {
      const seqOK = shownNums.every((x, i) => i === 0 ? true : x > shownNums[i - 1]);
      if (!seqOK) errs.push(`প্রদর্শিত নম্বর ক্রমে নেই: ${shownNums.slice(0, 8).join(',')}`);
      if (shownNums[0] !== 1) errs.push(`প্রথম নম্বর ${shownNums[0]} — ১ থেকে শুরু হওয়ার কথা`);
    }

    // উৎসের অনুক্রমণিকা/ভূমিকা আলাদা ব্লকে দেখাতে হবে (মন্ত্র-তালিকায় নয়)
    const ch = chFile;
    const frontEl = doc.querySelector('.g-front');
    if (ch.preface && !frontEl) errs.push('ভূমিকা ডেটায় আছে কিন্তু রেন্ডার হয়নি');
    if (frontEl && !ch.preface) errs.push('ভূমিকা নেই অথচ ব্লক রেন্ডার হয়েছে');
    if (frontEl && frontEl.open) errs.push('ভূমিকা-ব্লক খোলা অবস্থায় আছে (কল্যাপ্স থাকার কথা)');

    // ইংরেজি অনুবাদ (বাইবেল): ডেটা থাকলে রেন্ডার, টগল ও নম্বর-মিল যাচাই
    const enPath = path.join(dataDir, 'en', `ch${idx.chapters[0].id}.json`);
    if (fs.existsSync(enPath)) {
      const en = JSON.parse(fs.readFileSync(enPath, 'utf8'));
      const enAll = en.verses || {};
      const enWant = twoLevel
        ? Object.keys(enAll).filter((k) => vs.some((v) => String(v.n) === k)).length
        : Object.keys(enAll).length;
      const enGot = doc.querySelectorAll('.g-v-en').length;
      if (enWant && enGot !== enWant) errs.push(`ইংরেজি লাইন ${enGot} ≠ ডেটার ${enWant}`);
      const lb = doc.querySelector('.g-lang');
      if (!lb || lb.hidden) errs.push('ইংরেজি ডেটা আছে, তবু ভাষা-টগল দেখা যায়নি');
      const ns = new Set(chFile.verses.map((v) => String(v.n)));
      const stray = Object.keys(enAll).filter((k) => !ns.has(k));
      if (stray.length) errs.push(`ইংরেজি-কী পদের বাইরে: ${stray.slice(0, 3).join(',')}`);
      const se = vs.filter((v) => v.srcEmpty).length;
      if (se && doc.querySelectorAll('.g-v-empty').length < se) {
        errs.push(`উৎস-ফাঁকা নোট ${doc.querySelectorAll('.g-v-empty').length} < ডেটার ${se}`);
      }
      const click = (mode) => {
        const b = [...doc.querySelectorAll('.g-lang-btn')].find((x) => x.getAttribute('data-lang') === mode);
        if (b) b.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
      };
      click('en'); await wait(900);
      if (doc.querySelectorAll('.g-v-bn').length) errs.push('«শুধু ইংরেজি» মোডে বাংলা থেকে গেছে');
      if (enWant && !doc.querySelectorAll('.g-v-en').length) errs.push('«শুধু ইংরেজি» মোডে ইংরেজি নেই');
      click('bn'); await wait(900);
      if (doc.querySelectorAll('.g-v-en').length) errs.push('«শুধু বাংলা» মোডে ইংরেজি থেকে গেছে');
      click('both'); await wait(900);
    }

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

  /* ২খ) দুই-স্তরের নেভিগেশনের ফাঁদগুলো — লাইভে যেগুলো একবার ধরা পড়েছিল */
  if (twoLevel && idx) {
    const grid = doc.getElementById('g-chapter-grid');
    const clickGrid = async (n) => {
      const b = grid.querySelector(`[data-c="${n}"]`);
      if (b) b.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
      await new Promise((r) => setTimeout(r, 700));
    };
    const bookWithMissing = idx.chapters.find((c) => (c.missing || []).length &&
      (c.suktaCount || 0) > 2);
    if (bookWithMissing) {
      const mb = doc.querySelector(`#g-book-list [data-ch="${bookWithMissing.id}"]`);
      mb.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
      await new Promise((r) => setTimeout(r, 600));
      const missId = +bookWithMissing.missing[0];
      const cell = grid.querySelector(`[data-c="${missId}"]`);
      if (!cell) errs.push(`পাঠ-হীন অধ্যায় ${missId}-এর ঘর গ্রিডে নেই`);
      else if (!cell.classList.contains('off')) errs.push(`অধ্যায় ${missId} «পাঠ নেই» হিসেবে চিহ্নিত নয়`);
      // নেভিগেশন ফাঁকা অধ্যায় পার হবে, আর পুরো বই ঢালবে না
      const before = missId - 1;
      if (before >= 1) {
        await clickGrid(before);
        const nv = doc.getElementById('g-next');
        const expectNext = missId + 1;
        if (!/অধ্যায়/.test(nv.textContent) || !nv.textContent.includes(String(expectNext).replace(/\d/g, (d) => '০১২৩৪৫৬৭৮৯'[d]))) {
          errs.push(`অধ্যায় ${before} থেকে «পরের» ফাঁকা অধ্যায় ${missId} পার হচ্ছে না («${nv.textContent.trim()}»)`);
        }
      }
      await clickGrid(missId);
      const nv2 = doc.querySelectorAll('#g-body .g-v').length;
      if (nv2) errs.push(`পাঠ-হীন অধ্যায় ${missId}-এ ${nv2}টি পদ দেখাচ্ছে (পুরো বই ঢেলে দেওয়া হয়েছে)`);
      if (!doc.querySelector('.g-miss')) errs.push(`পাঠ-হীন অধ্যায় ${missId}-এ স্পষ্ট বার্তা নেই`);
    }
    // ইংরেজি-কভারেজ নোট: যে বইয়ে ইংরেজি নেই সেখানে নোট, যেখানে সব ঠিক সেখানে নয়
    const noEn = idx.chapters.find((c) => c.aligned === 0);
    const allEn = idx.chapters.find((c) => c.aligned > 0 && !c.skipped);
    for (const [bk, want] of [[noEn, true], [allEn, false]]) {
      if (!bk) continue;
      doc.querySelector(`#g-book-list [data-ch="${bk.id}"]`)
        .dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
      await new Promise((r) => setTimeout(r, 600));
      const note = doc.getElementById('g-en-note');
      if (!note) { errs.push('ইংরেজি-কভারেজ নোটের জায়গা নেই'); break; }
      if (want && note.hidden) errs.push(`${bk.bn}: ইংরেজি নেই অথচ নোট দেখাচ্ছে না`);
      if (!want && !note.hidden) errs.push(`${bk.bn}: ইংরেজি ঠিক আছে অথচ সতর্ক-নোট দেখাচ্ছে`);
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
  console.log(`   data-base=${a.base} · ${twoLevel ? 'পুস্তক' : 'অধ্যায়'}-বাটন ${nbtn}` +
    (twoLevel ? ` · অধ্যায়-গ্রিড ${doc.querySelectorAll('#g-chapter-grid [data-c]').length}` : '') +
    ` · খণ্ড ${rendered} · শিরোনাম «${chTitle}»` +
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
