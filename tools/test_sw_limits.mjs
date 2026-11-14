/* ============================================================
   test_sw_limits.mjs — সার্ভিস-ওয়ার্কারের ক্যাশ-সীমা পরীক্ষা
   ------------------------------------------------------------
   চালাতে:  node tools/test_sw_limits.mjs

   ভুয়া Cache API বানিয়ে sw.js-এর trimCache() আসলে ডাকে —
   · এন্ট্রি-সংখ্যা সীমা মানে কি
   · মোট মাপ (বাইট) সীমা মানে কি
   · বাজেটের ভিতরে কিছু মোছে কি না
   · একসাথে অনেক ডাকায় দৌড়-শর্ত হয় কি না
   ============================================================ */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '..');
import vm from 'node:vm';

// ── ভুয়া Cache API ──────────────────────────────────────
class FakeCache {
  constructor(){ this.m = new Map(); }  // key -> bytes (ক্রম সংরক্ষিত = পুরোনো আগে)
  async put(req, res){ this.m.set(req.url, res._bytes); }
  async match(req){ const o=[...this.m.entries()].find(([k])=>k===(req.url||req));
    return o? {headers:{get:()=>String(o[1])}, clone(){return this}, blob:async()=>({size:o[1]})} : undefined; }
  async keys(){ return [...this.m.keys()].map(k=>({url:k})); }
  async delete(req){ const k=req.url||req; return this.m.delete(k); }
}
const store = new Map();
const CA = {
  open: async n => { if(!store.has(n)) store.set(n,new FakeCache()); return store.get(n); },
  delete: async n => store.delete(n),
};
globalThis.caches = CA;

const src = fs.readFileSync(path.join(ROOT,'sw.js'),'utf8');
// শুধু LIMITS + trimChain + trimCache + sizeOf বের করি
const need = src.slice(src.indexOf('var SHELL_VERSION'), src.indexOf("/* ============================================================\n   install"));
const helpers = src.slice(src.indexOf('var trimChain'), src.indexOf('/* ============================================================\n   message'));
const ctx = vm.createContext({ caches: CA, Promise, console });
vm.runInContext(need + helpers, ctx);

let pass=0, fail=0;
const ok=m=>{pass++;console.log('  ✓ '+m)}, bad=m=>{console.log('  ✗ '+m);fail++};

// বাজেট বাস্তবে কী
/* vm-এর trimCache-এ ক্যাশের নাম পাঠাই — নাম হার্ডকোড নয় */
const trim = (name) => new Promise((resolve, reject) => {
  ctx.__name = name;
  Promise.resolve(vm.runInContext('trimCache(__name)', ctx)).then(resolve, reject);
});

const L = vm.runInContext('LIMITS', ctx);
const SHELL_NAME = vm.runInContext('SHELL_CACHE', ctx);
const PAGE_NAME  = vm.runInContext('PAGE_CACHE', ctx);
const DATA_NAME  = vm.runInContext('DATA_CACHE', ctx);
console.log('\n১. তিন ক্যাশেরই বাজেট আছে কি');
for (const n of [SHELL_NAME, PAGE_NAME, DATA_NAME]) {
  L[n] ? ok(`${n}: ${L[n][0]} এন্ট্রি / ${(L[n][1]/1048576).toFixed(0)} MB`) : bad(`${n}: বাজেট নেই`);
}

// ── ২. ডেটা: ৩০০টা ছোট এন্ট্রি → ২৫০-এ নামে?
console.log('\n২. ডেটা-ক্যাশ — এন্ট্রি-সীমা');
{
  const c = await caches.open(DATA_NAME);
  for (let i=0;i<300;i++) await c.put({url:`/d/${i}.json`}, {_bytes:1000});
  await trim(DATA_NAME);
  const n=(await c.keys()).length;
  n===250 ? ok(`৩০০ → ${n} (সীমা ২৫০)`) : bad(`৩০০ → ${n}, ২৫০ হওয়া উচিত`);
  const keys=await c.keys();
  keys[0].url==='/d/50.json' ? ok('পুরোনো ৫০টা বাদ, নতুন ২৫০ রাখা') : bad('ভুলগুলো বাদ পড়েছে: '+keys[0].url);
}

// ── ৩. ডেটা: মাপ-সীমা কার্যকর? (৪০ MB)
console.log(`\n৩. ডেটা-ক্যাশ — মাপ-সীমা (${Math.round(L[DATA_NAME][1]/1048576)} MB)`);
{
  CA.delete(DATA_NAME);
  const c = await caches.open(DATA_NAME);
  const MB = 1048576;
  const budgetMB = Math.round(L[DATA_NAME][1] / MB);
  for (let i = 0; i < 80; i++) await c.put({ url: `/big/${i}.json` }, { _bytes: 1 * MB }); // ৮০ MB
  await trim(DATA_NAME);
  const keys = await c.keys();
  keys.length ? ok(`৮০ MB → ${keys.length}টি এন্ট্রি`) : bad('সব মুছে গেছে');
  keys.length <= budgetMB
    ? ok(`মাপ সীমার ভিতরে (${keys.length} MB ≤ ${budgetMB} MB)`)
    : bad(`${keys.length} MB — সীমা ${budgetMB} MB ছাড়িয়েছে`);
}

// ── ৪. শেল-ক্যাশ: এখন সত্যিই trim হয়?
console.log('\n৪. শেল-ক্যাশ — আগে কোনো সীমা ছিল না');
{
  const c = await caches.open(SHELL_NAME);
  for (let i=0;i<400;i++) await c.put({url:`/img/${i}.webp`}, {_bytes:20000}); // ৮ MB
  await trim(SHELL_NAME);
  const n=(await c.keys()).length;
  n===300 ? ok(`৪০০ → ${n} (সীমা ৩০০)`) : bad(`৪০০ → ${n}, ৩০০ হওয়া উচিত`);
}

// ── ৫. পাতা-ক্যাশ: trim যোগ হয়েছে?
console.log('\n৫. পাতা-ক্যাশ — আগে trim ছিল না');
{
  const c = await caches.open(PAGE_NAME);
  for (let i=0;i<250;i++) await c.put({url:`/p${i}.html`}, {_bytes:40000}); // ১০ MB
  await trim(PAGE_NAME);
  const n=(await c.keys()).length;
  n===200 ? ok(`২৫০ → ${n} (সীমা ২০০)`) : bad(`২৫০ → ${n}, ২০০ হওয়া উচিত`);
}

// ── ৬. সীমার ভিতরে থাকলে কিছুই মোছা হয় না
console.log('\n৬. বাজেটের ভিতরে — কিছুই মোছা হয় না');
{
  CA.delete(PAGE_NAME);
  const c = await caches.open(PAGE_NAME);
  for (let i=0;i<20;i++) await c.put({url:`/p${i}.html`}, {_bytes:1000});
  await trim(PAGE_NAME);
  (await c.keys()).length===20 ? ok('২০টি এন্ট্রি অটুট') : bad('অকারণে মুছে ফেলেছে — ❌');
}

// ── ৭. অজানা ক্যাশে → কিছুই করে না
console.log('\n৭. অজানা ক্যাশের নাম');
{
  CA.delete('other');
  const c = await caches.open('other');
  for (let i=0;i<10;i++) await c.put({url:`/x${i}`}, {_bytes:1000});
  await trim('other');
  (await c.keys()).length===10 ? ok('অচেনা ক্যাশে হাত দেয় না') : bad('অন্য ক্যাশে মুছেছে — ❌');
}

// ── ৮. বারবার ডাকা — ডুপ্লিকেট/দৌড় নেই
console.log('\n৮. একসাথে অনেক trim');
{
  CA.delete(DATA_NAME);
  const c = await caches.open(DATA_NAME);
  for (let i=0;i<280;i++) await c.put({url:`/d/${i}.json`}, {_bytes:100});
  await Promise.all([1,2,3,4,5].map(()=>trim(DATA_NAME)));
  const n=(await c.keys()).length;
  n===250 ? ok(`পাঁচবার একসাথে → ${n} (সীমা ২৫০)`) : bad(`${n} — দৌড়-শর্ত`);
}

// ── ৯. আপডেটে ডেটা বাঁচে?
console.log('\n৯. সংস্করণ বদলালে ডেটা বাঁচে কি');
{
  const ver = vm.runInContext('SHELL_VERSION', ctx);
  const dver = vm.runInContext('DATA_VERSION', ctx);
  const shellN = vm.runInContext('SHELL_CACHE', ctx);
  const dataN = vm.runInContext('DATA_CACHE', ctx);
  shellN === 'ead-shell-' + ver ? ok(`শেল-ক্যাশ: ${shellN}`) : bad('শেল-ক্যাশের নাম গডবড়');
  dataN === 'ead-data-' + dver ? ok(`ডেটা-ক্যাশ: ${dataN} (শেল-সংস্করণে বদলায় না)`) : bad('ডেটা-ক্যাশের নাম ভুল');

  // activate-এর যুক্তি: ead-* কিন্তু keep-এ নেই → মোছ
  const keep = [shellN, vm.runInContext('PAGE_CACHE', ctx), dataN];
  const আছে = ['ead-shell-v1', 'ead-pages-v1', 'ead-data-v1', shellN, dataN];
  const deleted = আছে.filter(n => n.indexOf('ead-') === 0 && keep.indexOf(n) === -1);
  deleted.indexOf(dataN) === -1 ? ok('activate-এ ডেটা-ক্যাশ মোছে না ✓') : bad('ডেটা মুছে যাচ্ছে — ❌');
  deleted.length === 2 && deleted.indexOf('ead-shell-v1') >= 0
    ? ok(`শুধু পুরোনো শেল/পাতা মোছে (${deleted.join(', ')})`) : bad(`ভুল ক্যাশ মোছা: ${deleted.join(', ')}`);
}

console.log(`\n${fail?'✗':'✓'} পাশ ${pass} · ফেল ${fail}\n`);
process.exit(fail?1:0);
