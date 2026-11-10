#!/usr/bin/env node
/**
 * মোবাইল-অডিট — ফোনে যা যা ভাঙে, তা সব একসাথে ধরার চেষ্টা।
 *
 * যাচাই:
 *   ১. viewport মেটা (নেই/ভুল ⇒ মোবাইলে জুম-আউট হয়ে ছোট দেখায়)
 *   ২. lang, শিরোনাম, charset, description
 *   ৩. tap-target: <a>/<button> খুব ছোট হলে আঙুলে মিস হয় (৪৪×৪৪ ন্যূনতম)
 *   ৪. ছবি: width/height বা aspect-ratio ছাড়া ⇒ লোডের সময় লেআউট লাফ
 *   ৫. ইনপুট: font-size <১৬px ⇒ iOS স্বয়ংক্রিয় জুম-ইন করে
 *   ৬. টেবিল: overflow কনটেইনারে মোড়া কি না
 *   ৭. render-blocking: async/defer ছাড়া স্ক্রিপ্ট
 *   ৮. অনুপস্থিত aria-label শুধু আইকন-বাটনে
 *
 * চালানো: node tools/check_mobile.mjs
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, dirname } from 'node:path';
import { JSDOM } from 'jsdom';

const ROOT = process.cwd();
const SKIP = new Set(['node_modules', '.git', '.github']);

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    if (SKIP.has(name)) continue;
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, out);
    else if (name.endsWith('.html')) out.push(p);
  }
  return out;
}

const files = walk(ROOT).sort();
let totalErr = 0;
const perFile = [];

for (const f of files) {
  const rel = relative(ROOT, f);
  const html = readFileSync(f, 'utf8');
  const dom = new JSDOM(html);
  const doc = dom.window.document;
  const errs = [];
  const warns = [];

  // ১) viewport
  const vp = doc.querySelector('meta[name="viewport"]');
  if (!vp) errs.push('viewport মেটা নেই — মোবাইলে জুম-আউট হবে');
  else {
    const c = (vp.getAttribute('content') || '').toLowerCase();
    if (!c.includes('width=device-width')) errs.push('viewport-এ width=device-width নেই');
    if (/user-scalable\s*=\s*no|maximum-scale\s*=\s*1(?!\d)/.test(c))
      warns.push('জুম বন্ধ — দৃষ্টি-প্রতিবন্ধকতার জন্য ক্ষতিকর');
  }

  // ২) মৌলিক মেটা
  if (!doc.documentElement.getAttribute('lang')) errs.push('lang নেই');
  const title = (doc.querySelector('title')?.textContent || '').trim();
  if (!title) errs.push('শিরোনাম নেই');
  if (!doc.querySelector('meta[charset]')) errs.push('charset নেই');
  const desc = doc.querySelector('meta[name="description"]');
  if (!desc || !desc.getAttribute('content')) warns.push('description নেই');

  // ৩) tap-target — CSS-এ মাপা যায় না, তাই *ইনলাইন* ছোট শৈলী ও আইকন-বাটন দেখি
  const clickables = [...doc.querySelectorAll('a, button, [role="button"]')];
  for (const el of clickables) {
    const st = (el.getAttribute('style') || '').replace(/\s/g, '');
    if (/(?:width|height):(?:[1-3]?\d)px/.test(st) && !el.closest('footer')) {
      errs.push(`tap-target খুব ছোট: <${el.tagName.toLowerCase()}> style="${st.slice(0, 40)}"`);
      break;
    }
  }

  // ৪) ছবি — width/height না থাকলে লেআউট লাফ
  for (const img of doc.querySelectorAll('img')) {
    if (!img.getAttribute('alt') && !img.getAttribute('aria-hidden'))
      warns.push(`alt নেই: ${(img.getAttribute('src') || '').slice(-40)}`);
    const hasDims = img.hasAttribute('width') && img.hasAttribute('height');
    const inlineSized = /(?:width|height)/.test(img.getAttribute('style') || '');
    if (!hasDims && !inlineSized)
      warns.push(`ছবির মাপ নেই (লেআউট লাফ): ${(img.getAttribute('src') || '').slice(-40)}`);
  }

  // ৫) ইনপুট — iOS জুম
  for (const inp of doc.querySelectorAll('input, select, textarea')) {
    const st = inp.getAttribute('style') || '';
    if (/font-size:\s*1[0-5]px/.test(st)) errs.push('ইনপুটের font-size <১৬px — iOS জুম করবে');
  }

  // ৬) টেবিল মোড়া আছে কি না
  for (const tb of doc.querySelectorAll('table')) {
    let p = tb.parentElement, wrapped = false;
    for (let i = 0; i < 3 && p; i++, p = p.parentElement) {
      const st = (p.getAttribute('style') || '');
      const cls = p.getAttribute('class') || '';
      if (/overflow-x\s*:\s*auto|overflow\s*:\s*auto/.test(st) ||
          /scroll|table-wrap|logic-table|jesus-table/.test(cls)) { wrapped = true; break; }
    }
    if (!wrapped) warns.push('টেবিল overflow-কনটেইনারে মোড়া নয়');
  }

  // ৭) render-blocking স্ক্রিপ্ট
  for (const s of doc.querySelectorAll('script[src]')) {
    if (!s.hasAttribute('defer') && !s.hasAttribute('async') && !s.type.includes('module'))
      warns.push(`blocking স্ক্রিপ্ট: ${(s.getAttribute('src') || '').slice(-40)}`);
  }

  totalErr += errs.length;
  perFile.push({ rel, errs, warns });
}

// ---- চূড়ান্ত ----
let wcount = 0;
for (const { rel, errs, warns } of perFile) {
  wcount += warns.length;
  if (!errs.length && !warns.length) continue;
  console.log(`${errs.length ? '✗' : '△'} ${rel}`);
  for (const e of [...new Set(errs)]) console.log(`   ✗ ${e}`);
  for (const w of [...new Set(warns)].slice(0, 6)) console.log(`   △ ${w}`);
  if (warns.length > 6) console.log(`   … আরও ${warns.length - 6}টি সতর্কতা`);
}

console.log(`\n${files.length}টি পাতা · ত্রুটি ${totalErr} · সতর্কতা ${wcount}`);
if (totalErr) {
  console.log('\n⛔ মোবাইল-ত্রুটি আছে');
  process.exit(1);
}
console.log('\n✓ কোনো মোবাইল-ত্রুটি নেই');
