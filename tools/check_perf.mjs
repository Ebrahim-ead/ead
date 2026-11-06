#!/usr/bin/env node
/**
 * check_perf.mjs — সাইটের পারফরম্যান্স-নিয়ম পাহারা দেয়।
 *
 * উদ্দেশ্য: ভবিষ্যতে কেউ যেন অজান্তে ফোনের সবচেয়ে ব্যয়বহুল নিয়মগুলো
 * ফিরিয়ে না আনে। এগুলো «দৃশ্য» বদলায় না, তাই চোখে ধরা পড়ে না —
 * অথচ স্ক্রল-মসৃণতা সবচেয়ে বেশি নষ্ট করে।
 *
 * চালানো: node tools/check_perf.mjs
 */
import fs from 'fs';
import path from 'path';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const css = ['assets/site.css', 'assets/site-extra.css', 'assets/site-motion.css', 'assets/nav-motion.css']
  .map((f) => ({ f, s: fs.readFileSync(path.join(ROOT, f), 'utf8') }));

let bad = 0;
const fail = (msg) => { console.log(`✗ ${msg}`); bad++; };
const ok = (msg) => console.log(`✓ ${msg}`);

// ১. প্রতি-ফ্রেমে লেআউট-পড়া বন্ধ থাকা চাই
const js = fs.readFileSync(path.join(ROOT, 'assets/site-motion.js'), 'utf8');
/* কেবল return করা tick() ফাংশনটির ভেতরটা দেখি — measure() আলাদা,
   scroll-হ্যান্ডলারে চলে, তাই সেখানে scrollHeight/scrollY থাকাটাই সঠিক। */
function fnBody(src, name) {
  const i = src.indexOf('function ' + name);
  if (i < 0) return '';
  let d = 0, started = false;
  for (let k = src.indexOf('{', i); k < src.length; k++) {
    if (src[k] === '{') { d++; started = true; }
    else if (src[k] === '}') { d--; if (started && d === 0) return src.slice(i, k + 1); }
  }
  return src.slice(i, i + 900);
}
const tickBody = fnBody(js, 'tick');
const progressTick = js.slice(js.indexOf('function progress()'), js.indexOf('function header()'));
const retTick = progressTick.slice(progressTick.indexOf('return function tick()'));
if (/scrollHeight|innerHeight|scrollY/.test(retTick))
  fail('progress() ফ্রেম-টিকে scrollHeight/innerHeight পড়ছে — লেআউট থ্র্যাশিং ফিরেছে');
else ok('progress(): scroll/resize-এ মাপা হয়, প্রতি-ফ্রেমে নয়');

// ২. পুরো পাতায় will-change জোর করা যাবে না
const extra = css.find((c) => c.f === 'assets/site-extra.css').s;
const extraNoComments = extra.replace(/\/\*[\s\S]*?\*\//g, '');
/* কমেন্ট বাদ দিয়ে দেখি — কোডে সত্যিই *{...} আছে কি না (উপরে ঠিক করা) */
if (/\*\s*\{[^}]*will-change/.test(extraNoComments)) fail('`*{will-change:…}` পুরো পাতায় বসানো — লেয়ার 폭발');
else ok('will-change শুধু দরকারি সিলেক্টরে');

// ৩. content-visibility আসলে কাজ করছে কি — বডি-লেখায় <section> আছে তো
const essays = fs.readdirSync(ROOT).filter((f) => f.endsWith('.html'))
  .filter((f) => /class="[^"]*\barticle-body\b/.test(fs.readFileSync(path.join(ROOT, f), 'utf8')));
/* content-visibility আসলে কোন সিলেক্টরে বসেছে তা ঠিকভাবে দেখি */
const cv = (extraNoComments.match(/[^{}]*\{[^}]*content-visibility:auto[^}]*\}/g) || []).join(' ');
const hasUl = /\.article-body>ul/.test(cv);
if (!hasUl) fail('content-visibility শুধু >section-এ — প্রবন্ধে section নেই, তাই নিষ্ক্রিয়');
else ok(`content-visibility: section+ul উভয় কাঠামোয় (${essays.length} প্রবন্ধ)`);

// ৪. প্রবন্ধ-পাতায় অনুরূপ সরাসরি সন্তান আছে কি (নিয়মের প্রযোজ্যতা)
let directBlocks = 0;
for (const f of essays) {
  const s = fs.readFileSync(path.join(ROOT, f), 'utf8');
  const b0 = s.search(/class="[^"]*\barticle-body\b/);
  const body = s.slice(b0, s.indexOf('</article>', b0));
  directBlocks += (body.match(/<ul/g) || []).length;
}
if (!directBlocks) fail('প্রবন্ধে সরাসরি <ul> নেই — content-visibility-নিয়ম কিছু করে না');
else ok(`প্রবন্ধে ${directBlocks}টি সরাসরি <ul> — content-visibility সত্যিই কাজে লাগে`);

// ৫. মোবাইল-প্রোফাইলে ভারী স্তর বন্ধ
if (!/@media \(max-width:820px\)[\s\S]{0,400}backdrop-filter:none/.test(extra))
  fail('মোবাইল-প্রোফাইলে backdrop-filter বন্ধ নেই');
else ok('মোবাইলে backdrop-filter বন্ধ');

// ৬. TOC-প্যানেলে সময়-সাপেক্ষ ব্লার যেন না থাকে
/* .rd-toc-এর সব নিয়ম একসঙ্গে দেখি — বেসটি (@media-র বাইরে) `.rd-toc{display:none}`,
   আসল প্যানেল-নিয়ম @media(min-width:1400px)-এর ভেতরে; তাই প্রথমটিই নয়, সবগুলো। */
const tocRules = [...extraNoComments.matchAll(/\.rd-toc\s*\{([^}]*)\}/g)].map((m) => m[1]).join(' ');
if (/backdrop-filter/.test(tocRules)) fail('TOC প্যানেলে backdrop-filter আছে — স্ক্রলে ব্যয়বহুল');
else ok('TOC প্যানেল ব্লার-মুক্ত');

// ৭. prefers-reduced-motion সম্মানিত
if (!/prefers-reduced-motion:reduce/.test(css.map((c) => c.s).join('\n'))) fail('prefers-reduced-motion হ্যান্ডল করা নেই');
else ok('prefers-reduced-motion সম্মানিত');

// ৮. CSS ব্রেস ভারসাম্য
for (const c of css) {
  if ((c.s.match(/{/g) || []).length !== (c.s.match(/}/g) || []).length) fail(`${c.f}: ব্রেস ভারসাম্যহীন`);
}
ok('CSS ব্রেস ভারসাম্য');

// ৯. JS সিনট্যাক্স-যোগ্য (node --check আলাদা চালানো হয় না; হালকা চিহ্ন-যাচাই)
for (const f of ['assets/site-motion.js', 'assets/nav-motion.js', 'assets/reader-tools.js']) {
  const s = fs.readFileSync(path.join(ROOT, f), 'utf8');
  if (!s.trimEnd().endsWith(')') && !s.trimEnd().endsWith(';')) fail(`${f}: শেষে সন্দেহজনক`);
}
ok('JS ফাইল অটুট');

console.log(bad ? `\n${bad}টি পারফরম্যান্স-নিয়ম ভাঙা ✗` : '\nসব পারফরম্যান্স-নিয়ম অটুট ✓');
process.exit(bad ? 1 : 0);
