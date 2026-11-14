/* ============================================================
   test_sw_appmode.mjs — ইনস্টল করা অ্যাপে «সাথে সাথে খোলা»
   ------------------------------------------------------------
   চালাতে:  node tools/test_sw_appmode.mjs

   যা যাচাই করে:
     · ইনস্টল-মোডে (standalone) পাতা ক্যাশ থেকে সাথে সাথে আসে
     · ক্যাশে না থাকলে নেটওয়ার্ক, নেটওয়ার্কও না থাকলে offline.html
     · ক্যাশে থাকা অবস্থাতেই নীরবে নেটওয়ার্ক থেকে নতুন কপি নামে (SWR)
     · ব্রাউজার-ট্যাবে আগের network-first আচরণই থাকে
     · navigationPreload চালু হয়
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
  async add() { return; }
}
const store = new Map();
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
async function boot({ standalone = false, net = true } = {}) {
  store.clear();
  vm.doFail; // noop

  let fetchCalls = 0;
  const ctx = vm.createContext({
    caches: CA,
    Promise, console, URL, Response: class {},
    fetch: (req) => {
      fetchCalls++;
      if (!net) return Promise.reject(new Error('offline'));
      return Promise.resolve(res('FRESH:' + (req.url || req)));
    },
    setTimeout, clearTimeout,
  });

  const handlers = {};
  ctx.self = {
    location: { origin: 'https://x.test' },
    clients: {
      matchAll: async () => (standalone ? [{ frameType: 'top-level', displayMode: 'standalone' }] : [{ frameType: 'top-level', displayMode: 'browser' }]),
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

/* ── ১. ইনস্টল-মোড, ক্যাশে পাতা আছে → তাৎক্ষণিক ── */
console.log('\n১. ইনস্টল-অ্যাপ — ক্যাশে থাকলে সাথে সাথে');
{
  const { handlers } = await boot({ standalone: true, net: true });
  const c = await CA.open(store.size ? [...store.keys()][0] : 'ead-pages-v2');
  // ক্যাশে আগের কপি রাখি
  for (const n of store.keys()) await (await CA.open(n)).put({ url: 'https://x.test/ead/index.html' }, res('CACHED'));

  const r = await navigate(handlers);
  r && r._body === 'CACHED' ? ok('ক্যাশের কপি সাথে সাথে (নেটওয়ার্কের অপেক্ষা নয়)')
                            : bad(`ক্যাশ ব্যবহার হয়নি — পেল: ${r && r._body}`);
}

/* ── ২. ইনস্টল-মোড, ক্যাশে কিছু নেই → নেটওয়ার্ক ── */
console.log('\n২. ইনস্টল-অ্যাপ — ক্যাশে না থাকলে নেটওয়ার্ক');
{
  const { handlers } = await boot({ standalone: true, net: true });
  const r = await navigate(handlers);
  r && /^FRESH:/.test(r._body) ? ok('নেটওয়ার্ক থেকে আনে') : bad(`আসেনি — ${r && r._body}`);
}

/* ── ৩. ইনস্টল-মোড, নেট নেই, ক্যাশে নেই → offline.html ── */
console.log('\n৩. অ্যাপে নেট নেই');
{
  const { handlers } = await boot({ standalone: true, net: false });
  const r = await navigate(handlers);
  r && r._body === 'OFFLINE-PAGE'
    ? ok('offline.html ফলব্যাক — অ্যাপ ফাঁকা থাকে না')
    : bad(`ফলব্যাক ভুল — পেল: ${r && r._body}`);
}

/* ── ৪. SWR: ক্যাশে থাকলেও নীরবে নতুন কপি নামে ── */
console.log('\n৪. stale-while-revalidate');
{
  const { handlers } = await boot({ standalone: true, net: true });
  for (const n of store.keys()) await (await CA.open(n)).put({ url: 'https://x.test/ead/index.html' }, res('CACHED'));
  await navigate(handlers);
  await new Promise((r) => setTimeout(r, 120));
  let updated = false;
  for (const n of store.keys()) {
    const v = await (await CA.open(n)).match({ url: 'https://x.test/ead/index.html' });
    if (v && /^FRESH:/.test(v._body)) updated = true;
  }
  updated ? ok('ক্যাশ নীরবে নতুন কপিতে হালনাগাদ') : bad('নতুন কপি সংরক্ষণ হয়নি — লেখা পুরোনোই থেকে যাবে');
}

/* ── ৫. ব্রাউজার-ট্যাব: আগের আচরণ অটুট ── */
console.log('\n৫. ব্রাউজার-ট্যাব — network-first অটুট');
{
  const { handlers } = await boot({ standalone: false, net: true });
  for (const n of store.keys()) await (await CA.open(n)).put({ url: 'https://x.test/ead/index.html' }, res('CACHED'));
  const r = await navigate(handlers);
  r && /^FRESH:/.test(r._body) ? ok('নতুন লেখা-ই আগে (network-first)') : bad(`ট্যাবে ক্যাশ আগে চলে গেল — ${r && r._body}`);
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

console.log(`\n${fail ? '✗' : '✓'} পাশ ${pass} · ফেল ${fail}\n`);
process.exit(fail ? 1 : 0);
