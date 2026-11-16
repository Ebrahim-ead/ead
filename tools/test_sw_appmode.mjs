/* ============================================================
   test_sw_appmode.mjs — নেভিগেশন আচরণ (নেটওয়ার্ক-প্রথম)
   ------------------------------------------------------------
   চালাতে:  node tools/test_sw_appmode.mjs

   যা যাচাই করে:
     · নতুন লেখা-ই আগে আসে (network-first)
     · নেভিগেশন-preload ব্যবহার হয় — অতিরিক্ত অপেক্ষা নেই
     · নেট নেই → ক্যাশ → offline.html (কখনো ফাঁকা নয়)
     · install-এ PREFETCH আটকায় না (তাৎক্ষণিক সক্রিয়)

   ⚠ আগে ইনস্টল-মোডে cache-first আলাদা পথ ছিল; ইনস্টল-সিস্টেম
   বাদ দেওয়ায় সেটি সরানো হয়েছে। এখন সবাই একই নিরাপদ পথে।
   ============================================================ */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '..');
const SRC = fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf8');

let pass = 0, fail = 0;
const ok = (m) => { pass++; console.log(`  ✓ ${m}`); };
const bad = (m) => { fail++; console.log(`  ✗ ${m}`); };

/* ── ভুয়া Cache API ────────────────────────────────────── */
class FakeCache {
  constructor() { this.m = new Map(); }
  async put(req, res) { this.m.set(typeof req === 'string' ? req : (req.url || req), res); }
  async match(req) { return this.m.get(typeof req === 'string' ? req : req.url); }
  async keys() { return [...this.m.keys()].map((k) => ({ url: k })); }
  async delete(req) { return this.m.delete(typeof req === 'string' ? req : req.url); }
  async add(req) {
    const u = typeof req === 'string' ? req : (req.url || '');
    /* ১০ নম্বর পরীক্ষা: ধীর PREFETCH নকল করি */
    if (SLOW && /600|800/.test(u)) await new Promise((r) => setTimeout(r, 300));
    return;
  }
}
let SLOW = false;
const store = new Map();

/* ক্যাশের নাম ধরে কী বের করি — version বদলালেও কাজ করবে */
function storeKey(prefix) {
  for (const k of store.keys()) if (k.startsWith(prefix)) return k;
  return prefix;
}
const CA = {
  open: async (n) => { if (!store.has(n)) store.set(n, new FakeCache()); return store.get(n); },
  delete: async (n) => store.delete(n),
  match: async (u) => {
    let key = typeof u === 'string' ? u : (u.url || u);
    /* বাস্তব Cache API আপেক্ষিক পথকে মূলে মিলিয়ে খোঁজে */
    if (key.startsWith('/')) key = 'https://x.test' + key;
    for (const c of store.values()) { const h = await c.match({ url: key }); if (h) return h; }
    return undefined;
  },
  keys: async () => [...store.keys()],
};

function res(body, { ok = true } = {}) {
  return {
    ok, _body: body,
    headers: { get: () => null },
    clone() { return res(body, { ok }); },
    blob: async () => ({ size: 10 }),
  };
}

/* ── sw.js চালাই নিয়ন্ত্রিত পরিবেশে ───────────────────── */
async function boot({ net = true, fresh = true, overrideFetch = null } = {}) {
  if (fresh) store.clear();
  vm.doFail; // noop

  let fetchCalls = 0;
  const ctx = vm.createContext({
    caches: CA,
    Promise, console, URL, Response: class {},
    fetch: overrideFetch || ((req) => {
      fetchCalls++;
      if (!net) return Promise.reject(new Error('offline'));
      return Promise.resolve(res('FRESH:' + (req.url || req)));
    }),
    setTimeout, clearTimeout,
  });

  const handlers = {};
  ctx.self = {
    location: { origin: 'https://x.test' },
    clients: {
      matchAll: async () => [{ frameType: 'top-level' }],
      claim: async () => {},
    },
    registration: { navigationPreload: { enable: async () => { ctx.__preloadOn = true; } } },
    skipWaiting: async () => {},
    addEventListener: (t, fn) => { handlers[t] = fn; },
  };

  vm.runInContext(SRC, ctx);

  /* ইনস্টলের মতো শেল-ক্যাশে ফলব্যাক-পাতা ভরি — বাস্তবে install-এই এগুলো আসে */
  const shellName = vm.runInContext('SHELL_CACHE', ctx);
  const sc = await CA.open(shellName);
  await sc.put({ url: 'https://x.test/ead/offline.html' }, res('OFFLINE-PAGE'));

  return { ctx, handlers, fetchCalls: () => fetchCalls };
}

/* একটি নেভিগেশন-অনুরোধ চালাই, ফল Response ফেরায় */
async function navigate(h, { preload = null } = {}) {
  let out;
  const event = {
    request: { url: 'https://x.test/ead/index.html', mode: 'navigate', method: 'GET', headers: { get: () => null } },
    preloadResponse: Promise.resolve(preload),
    respondWith: (p) => { out = p; },
  };
  h.fetch(event);
  return await out;
}

/* ── ৩. ইনস্টল-মোড, নেট নেই, ক্যাশে নেই → offline.html ── */
console.log('\n৩. অ্যাপে নেট নেই');
{
  const { handlers } = await boot({ net: false });
  const r = await navigate(handlers);
  r && r._body === 'OFFLINE-PAGE'
    ? ok('offline.html ফলব্যাক — অ্যাপ ফাঁকা থাকে না')
    : bad(`ফলব্যাক ভুল — পেল: ${r && r._body}`);
}

/* ── ৪. নেট নেই, কিন্তু ক্যাশে আছে → ক্যাশ থেকেই ── */
console.log('\n৪. নেট নেই, ক্যাশে আছে → ক্যাশ থেকেই');
{
  const { handlers } = await boot({ net: true });
  /* PAGE_CACHE-এ আগের কপি জমাই (আগের কোনো ভিজিটের মতো) */
  const pageName = storeKey('ead-pages-v5');
  const pc = await CA.open(pageName);
  await pc.put({ url: 'https://x.test/ead/index.html' }, res('CACHED'));

  /* এবার নেট বন্ধ করে নতুন SW পরিবেশ */
  const { handlers: h2 } = await boot({ net: false, fresh: false });
  const r = await navigate(h2, { preload: null });  // preload-ও নেই = সত্যিকারের অফলাইন
  r && r._body === 'CACHED'
    ? ok('অফলাইনে আগের কপি পাওয়া যায়')
    : bad(`অফলাইনে ক্যাশ ব্যবহার হয়নি — পেল: ${r && r._body}`);
}

/* ── ৫. ব্রাউজার-ট্যাব: আগের আচরণ অটুট ── */
console.log('\n৫. ব্রাউজার-ট্যাব — network-first অটুট');
{
  const { handlers } = await boot({ standalone: false, net: true });
  for (const n of store.keys()) await (await CA.open(n)).put({ url: 'https://x.test/ead/index.html' }, res('CACHED'));
  const r = await navigate(handlers);
  r && /^FRESH/.test(r._body) ? ok('নতুন লেখা-ই আগে (network-first)') : bad(`ট্যাবে ক্যাশ আগে চলে গেল — ${r && r._body}`);
}

/* ── ৬. navigationPreload চালু হয় ── */
console.log('\n৬. navigationPreload');
{
  const { ctx, handlers } = await boot({ standalone: false });
  const ev = { waitUntil: (p) => p };
  handlers.activate(ev);
  await new Promise((r) => setTimeout(r, 150));
  ctx.__preloadOn ? ok('activate-এ preload চালু হয়') : bad('preload চালু হয়নি');
}

/* ── ৭. preloadResponse ব্যবহার হয় ── */
console.log('\n৭. preloadResponse ব্যবহার');
{
  const { handlers } = await boot({ standalone: false, net: false });
  const r = await navigate(handlers, { preload: res('PRELOADED') });
  r && r._body === 'PRELOADED' ? ok('preload-এর উত্তর কাজে লাগে (নেটওয়ার্ক-অপেক্ষা বাঁচে)')
                               : bad(`preload অবহেলিত — পেল ${r && r._body}`);
}


const withTimeout = (p, ms) => Promise.race([p, new Promise((r) => setTimeout(r, ms))]);

/* ── ১০. install-বিলম্ব: PREFETCH আটকায় না ───────────────────
   ⚠ আসল বাগ: PREFETCH-এর waitUntil install-শেষকে পিছিয়ে দিত,
   তাই ধীর নেটওয়ার্কে অ্যাপ ইনস্টলের পরও চালু হত না। */
console.log('\n১০. install-বিলম্ব');
{
  /* ধীর PREFETCH — প্রতিটা ফাইলে ৩০০ms */
  SLOW = true;
  const t0 = Date.now();
  const { handlers } = await boot({ standalone: false, net: true });
  await withTimeout(handlers.install, 1200);   // SHELL শেষ হলেই install শেষ
  const ms = Date.now() - t0;
  SLOW = false;
  ms < 250 ? ok(`install ${ms}ms-এ শেষ — PREFETCH (৩০০ms×২) আটকায়নি`)
           : bad(`install ${ms}ms — PREFETCH আটকে দিচ্ছে`);
  !/waitUntil\(\s*caches\.open\(SHELL_CACHE\)[\s\S]{0,400}PREFETCH/.test(
    fs.readFileSync(path.join(ROOT, 'sw.js'), 'utf8'))
    ? ok('PREFETCH waitUntil-এর ভিতরে নেই (কোড-যাচাই)')
    : bad('PREFETCH এখনো waitUntil-এ');
}

console.log(`\n${fail ? '✗' : '✓'} পাশ ${pass} · ফেল ${fail}\n`);
process.exit(fail ? 1 : 0);
