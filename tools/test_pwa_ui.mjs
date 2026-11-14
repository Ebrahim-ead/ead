/* ============================================================
   test_pwa_ui.mjs — ইনস্টল-ব্যানার/আপডেট/অফলাইন-নোটিশের আচরণ
   ------------------------------------------------------------
   চালাতে:  node tools/test_pwa_ui.mjs
   jsdom-এ pwa.js চালিয়ে বাস্তব ঘটনা (beforeinstallprompt,
   offline/online, iOS UA) পাঠিয়ে DOM-ফলাফল যাচাই করে।
   ============================================================ */
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '..');
import { JSDOM, VirtualConsole } from 'jsdom';
const js = fs.readFileSync(path.join(ROOT, 'assets/pwa.js'), 'utf8');
let pass=0, fail=0;
const ok=m=>{pass++;console.log('  ✓ '+m)}, bad=m=>{fail++;console.log('  ✗ '+m)};

function mk(){
  const vc=new VirtualConsole();
  const dom=new JSDOM(`<!doctype html><html><head></head><body><main>x</main></body></html>`,
    {runScripts:'outside-only',url:'https://x.test/ead/index.html',virtualConsole:vc});
  const w=dom.window;
  w.matchMedia=w.matchMedia||(()=>({matches:false,media:'',addEventListener(){},removeEventListener(){},addListener(){},removeListener(){}}));
  // SW stub
  const reg={installing:null,waiting:null,active:null,addEventListener(){},update(){return Promise.resolve()}};
  w.navigator.serviceWorker={register:()=>Promise.resolve(reg),ready:Promise.resolve(reg),addEventListener(){},controller:null};
  return {w,dom,reg};
}

// ১. সাধারণ পেজ: SW রেজিস্টার হয়
{
  const {w,dom}=mk();
  let regUrl=null;
  w.navigator.serviceWorker.register=(u)=>{regUrl=u;return Promise.resolve({installing:null,waiting:null,addEventListener(){}});};
  w.eval(js);
  await new Promise(r=>setTimeout(r,50));
  regUrl==='/ead/sw.js' ? ok('SW রেজিস্টার হয়: '+regUrl) : bad('রেজিস্ট্রেশন হয়নি ('+regUrl+')');
  dom.window.close();
}

// ২. beforeinstallprompt → ৩s পরে ব্যানার
{
  const {w,dom}=mk();
  w.eval(js);
  let prevented=false;
  const ev=new w.Event('beforeinstallprompt');
  ev.preventDefault=()=>{prevented=true};
  ev.prompt=()=>{};
  ev.userChoice=Promise.resolve({outcome:'dismissed'});
  w.dispatchEvent(ev);
  await new Promise(r=>setTimeout(r,3400));
  const b=w.document.querySelector('.pwa-banner');
  b ? ok('ইনস্টল-ব্যানার তৈরি ('+b.className+')') : bad('ব্যানার তৈরি হয়নি');
  b && b.classList.contains('is-open') ? ok('ব্যানার দেখা যাচ্ছে (.is-open)') : bad('ব্যানার লুকানো');
  prevented ? ok('ডিফল্ট প্রম্পট ঠেকানো') : bad('ডিফল্ট প্রম্পট আটকায়নি');
  b && w.document.querySelector('.pwa-btn.primary') ? ok('«ইনস্টল» বোতাম আছে') : bad('ইনস্টল বোতাম নেই');
  b && w.document.querySelector('.pwa-btn.ghost') ? ok('«পরে» বোতাম আছে') : bad('পরে বোতাম নেই');
  // ডিসমিস
  const ghost=w.document.querySelector('.pwa-btn.ghost');
  if(ghost){ ghost.click(); await new Promise(r=>setTimeout(r,50));
    b.classList.contains('is-open') ? bad('ডিসমিসে বন্ধ হয়নি') : ok('«পরে» → ব্যানার বন্ধ');
    w.localStorage.getItem('ead:install-dismissed') ? ok('ডিসমিস ৩০ দিন মনে রাখে') : bad('ডিসমিস সংরক্ষণ হয়নি');
  }
  dom.window.close();
}

// ৩. offline ইভেন্ট → নোটিশ
{
  const {w,dom}=mk();
  w.eval(js);
  w.dispatchEvent(new w.Event('offline'));
  await new Promise(r=>setTimeout(r,80));
  const n=w.document.querySelector('.pwa-offline');
  n ? ok('অফলাইন-নোটিশ তৈরি') : bad('অফলাইন-নোটিশ নেই');
  n && n.classList.contains('is-open') ? ok('নোটিশ দেখা যায়') : bad('নোটিশ লুকানো');
  w.dispatchEvent(new w.Event('online'));
  await new Promise(r=>setTimeout(r,80));
  n && !n.classList.contains('is-open') ? ok('অনলাইনে নোটিশ যায়') : bad('নোটিশ যায়নি');
  dom.window.close();
}

// ৪. iOS Safari → হিন্ট
{
  const {w,dom}=mk();
  Object.defineProperty(w.navigator,'userAgent',{value:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'});
  w.eval(js);
  await new Promise(r=>setTimeout(r,10600));
  const b=w.document.querySelector('.pwa-banner');
  b ? ok('iOS হিন্ট দেখায়') : bad('iOS হিন্ট নেই');
  b && /হোম স্ক্রিন|Home Screen|শেয়ার/.test(b.textContent) ? ok('শেয়ার→হোম স্ক্রিন নির্দেশনা') : bad('নির্দেশনা নেই');
  dom.window.close();
}


/* ── ৫. হিরোর স্থায়ী ইনস্টল-বোতাম ─────────────────────────── */
// বোতামটা index.html-এই inline থাকে; এখানে সেই বাস্তব HTML-ই লোড করি।
const realHtml = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

function mkWithButton({standalone = false, ua} = {}) {
  const vc = new VirtualConsole();
  const dom = new JSDOM(realHtml, {
    runScripts: 'outside-only', url: 'https://x.test/ead/index.html', virtualConsole: vc,
  });
  const w = dom.window;
  w.matchMedia = (q) => ({ matches: standalone && /standalone/.test(q), media: q, addEventListener(){}, removeEventListener(){}, addListener(){}, removeListener(){} });
  if (ua) Object.defineProperty(w.navigator, 'userAgent', { value: ua });
  const reg = { installing:null, waiting:null, active:null, addEventListener(){}, update(){ return Promise.resolve(); } };
  w.navigator.serviceWorker = { register: () => Promise.resolve(reg), ready: Promise.resolve(reg), addEventListener(){}, controller: null };
  return { w, dom };
}

{
  const { w, dom } = mkWithButton();
  w.eval(js);
  await new Promise(r => setTimeout(r, 60));
  const btn = w.document.querySelector('#install-btn');
  btn ? ok('হিরোতে #install-btn আছে') : bad('#install-btn নেই');
  btn && btn.classList.contains('btn') && btn.classList.contains('ghost')
    ? ok('বাকি দুটোর মতো .btn.ghost চেহারা') : bad('চেহারার ক্লাস ভুল');
  btn && !btn.hidden ? ok('ব্রাউজার-প্রম্পট ছাড়াই বোতাম দেখা যায়') : bad('বোতাম লুকানো');
  // বোতামটা সত্যিই দুটোর পাশে — .btns-এর তৃতীয় সন্তান
  const btns = w.document.querySelector('.btns');
  btns && btns.children.length === 3 && btns.children[2] === btn
    ? ok('«আলোচনার বিষয়»-এর ডান পাশে তৃতীয় বোতাম') : bad(`সারিতে ${btns ? btns.children.length : '?'}টি বোতাম`);
  dom.window.close();
}

// ৫খ. ইনস্টল-প্রম্পট এলে চাপে সেটাই চলে
{
  const { w, dom } = mkWithButton();
  w.eval(js);
  await new Promise(r => setTimeout(r, 60));
  let prompted = 0;
  const ev = new w.Event('beforeinstallprompt');
  ev.preventDefault = () => {};
  ev.prompt = () => { prompted++; };
  ev.userChoice = Promise.resolve({ outcome: 'accepted' });
  w.dispatchEvent(ev);
  await new Promise(r => setTimeout(r, 60));
  w.document.querySelector('#install-btn').click();
  await new Promise(r => setTimeout(r, 60));
  prompted === 1 ? ok('চাপলে ব্রাউজারের আসল ইনস্টল-প্রম্পট') : bad(`প্রম্পট চলেনি (${prompted})`);
  dom.window.close();
}

// ৫গ. প্রম্পট না থাকলে (iOS) — কীভাবে ইনস্টল করবেন বলে দেয়
{
  const { w, dom } = mkWithButton({ ua: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1' });
  w.eval(js);
  await new Promise(r => setTimeout(r, 60));
  w.document.querySelector('#install-btn').click();
  await new Promise(r => setTimeout(r, 80));
  const h = w.document.querySelector('.pwa-hint');
  h ? ok('প্রম্পট না থাকলে নির্দেশনা দেখায়') : bad('কোনো নির্দেশনা নেই');
  h && /শেয়ার/.test(h.textContent) && /হোম স্ক্রিন/.test(h.textContent)
    ? ok('iOS-এ «শেয়ার ▸ হোম স্ক্রিনে যোগ করুন»') : bad('iOS নির্দেশনা ভুল');
  h && w.document.querySelector('.pwa-hint .pwa-btn.ghost') ? ok('নির্দেশনা বন্ধ করার বোতাম') : bad('বন্ধের বোতাম নেই');
  dom.window.close();
}

// ৫ঘ. ইনস্টল হয়ে গেলে বোতাম আর দেখায় না
{
  const { w, dom } = mkWithButton({ standalone: true });
  w.eval(js);
  await new Promise(r => setTimeout(r, 60));
  const btn = w.document.querySelector('#install-btn');
  btn && btn.hidden ? ok('standalone-এ বোতাম লুকায়') : bad('standalone-এও দেখা যাচ্ছে');
  dom.window.close();
}

// ৫ঙ. appinstalled ইভেন্টেও লুকায়
{
  const { w, dom } = mkWithButton();
  w.eval(js);
  await new Promise(r => setTimeout(r, 60));
  const btn = w.document.querySelector('#install-btn');
  const before = !btn.hidden;
  w.dispatchEvent(new w.Event('appinstalled'));
  before && btn.hidden ? ok('appinstalled-এ বোতাম লুকায়') : bad('appinstalled-এ লুকায়নি');
  dom.window.close();
}

console.log(`\n${fail?'✗':'✓'} পাশ ${pass} · ফেল ${fail}\n`);
process.exit(fail?1:0);
