#!/usr/bin/env node
/**
 * PDF-টেস্ট — ফোনে ও ডেস্কটপে বইয়ের PDF সত্যিই খোলার পথ পায় কি না।
 *
 * ⚠ যে বাগটি ধরে (২০২৬-১১-১০, ব্যবহারকারীর রিপোর্ট):
 *   «ফোন ব্যবহার করে ওয়েবসাইটে বইয়ের PDF গুলো দেখা যায় না।»
 *   কারণ: PDF <iframe>-এ এমবেড ছিল; iOS Safari শুধু ১ম পৃষ্ঠা দেখায়,
 *   Android Chrome-এ ফাঁকা থাকে। ফলে «অনলাইনে পড়ুন» চাপলে কিছুই হত না।
 *
 * এই টেস্ট তিনটি জিনিস দেখে:
 *   ১. প্রতিটি বই-পাতায় `[data-book-viewer]` + `[data-book-fallback]` আছে
 *   ২. ফোন-অনুকরণে (মোবাইল UA, ছোট স্ক্রিন) iframe-এ src বসে না,
 *      ফলব্যাক প্যানেল দেখা যায় এবং PDF-লিংক সঠিক ফাইলে নেয়
 *   ৩. ডেস্কটপ-অনুকরণে আগের মতোই iframe-এ PDF লোড হয়
 *
 * চালানো: node tools/test_pdf.mjs
 */
import { readFileSync, existsSync } from 'node:fs';
import { JSDOM, VirtualConsole } from 'jsdom';

const PAGES = [
  { file: 'book-comparative-religion.html', pdf: 'files/comparative-religions-color.pdf' },
  { file: 'book-islam-response.html', pdf: 'files/islam-opponents-response.pdf' },
  { file: 'book-islam-science.html', pdf: 'files/islam-science-selection.pdf' },
];

const SCRIPT = readFileSync('assets/book-pdf.js', 'utf8');
let fail = 0;

/** একটি অনুকরণ-পরিবেশে book-pdf.js চালিয়ে ফলাফল ফেরায়। */
function runAs(page, { mobile }) {
  const html = readFileSync(page.file, 'utf8');
  const vc = new VirtualConsole();
  const dom = new JSDOM(html, {
    runScripts: 'outside-only',
    virtualConsole: vc,
    url: 'https://ebrahim-ead.github.io/ead/' + page.file,
    beforeParse(win) {
      Object.defineProperty(win.navigator, 'userAgent', {
        value: mobile
          ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1'
          : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
        configurable: true,
      });
      Object.defineProperty(win.navigator, 'maxTouchPoints', { value: mobile ? 5 : 0, configurable: true });
      Object.defineProperty(win.navigator, 'pdfViewerEnabled', { value: !mobile, configurable: true });
      win.matchMedia = (q) => ({
        matches: mobile ? /max-width/.test(q) : /pointer:\s*fine/.test(q),
        media: q, addListener() {}, removeListener() {},
        addEventListener() {}, removeEventListener() {},
      });
    },
  });
  const { window } = dom;
  window.eval(SCRIPT);
  const doc = window.document;
  const frame = doc.querySelector('[data-book-viewer] iframe');
  const fb = doc.querySelector('[data-book-fallback]');
  const open = doc.querySelector('[data-book-fallback] [data-book-open]');
  return {
    inlineOk: !!window.__bookPdf?.inlineOk,
    frameSrc: frame ? frame.getAttribute('src') : null,
    fbHidden: fb ? fb.hidden : null,
    openHref: open ? open.getAttribute('href') : null,
    hasViewer: !!doc.querySelector('[data-book-viewer]'),
    hasFallback: !!doc.querySelector('[data-book-fallback]'),
  };
}

for (const p of PAGES) {
  console.log(`\n${p.file}`);
  if (!existsSync(p.file)) { console.log('   ✗ পাতা নেই'); fail++; continue; }
  if (!existsSync(p.pdf)) { console.log(`   ✗ PDF নেই: ${p.pdf}`); fail++; continue; }

  // ---- কাঠামো
  const base = runAs(p, { mobile: true });
  if (!base.hasViewer) { console.log('   ✗ data-book-viewer নেই'); fail++; }
  if (!base.hasFallback) { console.log('   ✗ data-book-fallback নেই'); fail++; }

  // ---- ফোন
  const m = runAs(p, { mobile: true });
  const mErr = [];
  if (m.inlineOk) mErr.push('ফোনে inlineOk সত্য হল (হওয়া উচিত নয়)');
  if (m.frameSrc && m.frameSrc !== 'about:blank') mErr.push(`ফোনে iframe-এ src বসেছে: ${m.frameSrc}`);
  if (m.fbHidden !== false) mErr.push('ফোনে ফলব্যাক-প্যানেল লুকানো আছে');
  if (m.openHref !== p.pdf) mErr.push(`ফোনে «PDF খুলুন» ভুল ঠিকানায়: ${m.openHref}`);
  console.log(`   ${mErr.length ? '✗' : '✓'} ফোন  — inlineOk=${m.inlineOk} iframe-src=${m.frameSrc || '(নেই)'} ফলব্যাক-দৃশ্যমান=${m.fbHidden === false}`);
  mErr.forEach((e) => console.log('        · ' + e));
  fail += mErr.length;

  // ---- ডেস্কটপ
  const d = runAs(p, { mobile: false });
  const dErr = [];
  if (!d.inlineOk) dErr.push('ডেস্কটপে inlineOk মিথ্যা হল');
  if (d.frameSrc !== p.pdf) dErr.push(`ডেস্কটপে iframe-এ সঠিক PDF বসেনি: ${d.frameSrc}`);
  console.log(`   ${dErr.length ? '✗' : '✓'} ডেস্কটপ — inlineOk=${d.inlineOk} iframe-src=${d.frameSrc}`);
  dErr.forEach((e) => console.log('        · ' + e));
  fail += dErr.length;
}


/* ── ৪. ডাউনলোড-অগ্রগতি ─────────────────────────────────────
   ৯–১৫ MB PDF নামার সময় ব্যবহারকারী যেন «কিছুই হচ্ছে না» না ভাবেন।
   ভুয়া fetch + stream বানিয়ে দেখি অগ্রগতি সত্যিই দেখায়। */
console.log('\nডাউনলোড-অগ্রগতি');
{
  const html = readFileSync('book-islam-response.html', 'utf8');
  const dom = new JSDOM(html, {
    runScripts: 'outside-only',
    url: 'https://ebrahim-ead.github.io/ead/book-islam-response.html',
    beforeParse(win) {
      win.matchMedia = (q) => ({ matches: false, media: q, addEventListener(){}, removeEventListener(){}, addListener(){}, removeListener(){} });
      // ৩টি খণ্ডে ৩০ KB "PDF"
      const total = 30000;
      let sent = 0;
      const CHUNK = 10000;
      win.fetch = () => Promise.resolve({
        ok: true,
        headers: { get: (h) => (h.toLowerCase() === 'content-length' ? String(total) : null) },
        body: {
          getReader: () => ({
            read: () => {
              if (sent >= total) return Promise.resolve({ done: true });
              sent += CHUNK;
              return Promise.resolve({ done: false, value: new Uint8Array(CHUNK) });
            },
          }),
        },
      });
      win.__downloads = [];
      // <a>.click() ধরার জন্য প্যাচ
      const origClick = win.HTMLAnchorElement.prototype.click;
      win.HTMLAnchorElement.prototype.click = function () {
        if (this.hasAttribute('download')) win.__downloads.push(this.getAttribute('href'));
        else if (origClick) origClick.call(this);
      };
      // jsdom-এ Response নেই — stream-সহায়ক কিনা যাচাই করতে হয়
      win.Response = function () {};
      win.Response.prototype.body = null;
      win.URL.createObjectURL = () => 'blob:fake';
      win.URL.revokeObjectURL = () => {};
    },
  });
  const w = dom.window, d = w.document;
  w.eval(SCRIPT);

  const link = d.querySelector('a[download][href$=".pdf"]');
  link ? console.log('   ✓ ডাউনলোড-লিঙ্কে হাত দেওয়া হয়েছে') : (console.log('   ✗ লিঙ্ক পাওয়া যায়নি'), fail++);

  // চাপ দিই
  const ev = new w.MouseEvent('click', { bubbles: true, cancelable: true, button: 0 });
  const notCancelled = link.dispatchEvent(ev);
  if (!notCancelled) console.log('   ✓ ডিফল্ট ডাউনলোড ঠেকানো (নিজে নামাই)');
  else (console.log('   ✗ ডিফল্ট আচরণ ঠেকানো হয়নি'), fail++);

  // অগ্রগতি দেখা যায়?
  await new Promise((r) => setTimeout(r, 150));
  const bar = link.querySelector('[data-dl-bar]');
  const main = link.querySelector('.tx b')?.textContent || '';
  if (bar) console.log('   ✓ অগ্রগতি-বার তৈরি');
  else (console.log('   ✗ অগ্রগতি-বার নেই'), fail++);

  await new Promise((r) => setTimeout(r, 600));
  const finished = w.__downloads.length > 0;
  finished ? console.log('   ✓ নামা শেষে ফাইল সেভ হয়েছে') : (console.log('   ✗ ফাইল সেভ হয়নি'), fail++);
  const after = link.querySelector('.tx b')?.textContent || '';
  /ডাউনলোড হয়েছে/.test(after) ? console.log('   ✓ শেষে «ডাউনলোড হয়েছে ✓» দেখায়')
    : (console.log(`   ✗ শেষে ভুল লেখা: «${after}»`), fail++);
}

console.log(`\n${fail ? `⛔ ${fail}টি সমস্যা` : '✓ ফোন ও ডেস্কটপ — দুই জায়গাতেই PDF খোলার পথ ঠিক'}`);
process.exit(fail ? 1 : 0);
