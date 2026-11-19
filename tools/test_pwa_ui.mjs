/* ============================================================
   test_pwa_ui.mjs — অফলাইন-নোটিশ/স্ক্রল-রিস্টোর/ইনস্টল-অনুপস্থিতি
   ------------------------------------------------------------
   চালাতে:  node tools/test_pwa_ui.mjs
   jsdom-এ pwa.js চালিয়ে বাস্তব ঘটনা (offline/online, ইনস্টল-প্রম্পট,
   iOS UA) পাঠিয়ে DOM-ফলাফল যাচাই করে।

   ⚠ ইনস্টল-সিস্টেম বাদ দেওয়া হয়েছে (ব্যবহারকারীর নির্দেশ)। তাই ২ ও ৪
   নম্বর এখন উল্টো যাচাই: ইনস্টল-প্রম্পট/iOS-হিন্ট পাঠালে **কিছুই**
   তৈরি হয় না — যেন ভুলে আবার ফিরে না আসে।
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

// ২. ইনস্টল-প্রম্পট পাঠালেও কিছু তৈরি হয় না (বাদ দেওয়া)
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
  !w.document.querySelector('.pwa-banner')
    ? ok('ইনস্টল-ব্যানার তৈরি হয় না (বাদ দেওয়া)') : bad('ব্যানার এখনো তৈরি হচ্ছে');
  !w.document.querySelector('.pwa-btn')
    ? ok('কোনো ইনস্টল-বোতাম নেই') : bad('ইনস্টল-বোতাম এখনো আছে');
  !prevented
    ? ok('ডিফল্ট প্রম্পট আর আটকানো হয় না') : bad('এখনো preventDefault চলছে');
  dom.window.close();
}

// ৩. offline ইভেন্ট → নোটিশ
{
  const {w,dom}=mk();
  w.eval(js);
  w.dispatchEvent(new w.Event('offline'));
  await new Promise(r=>setTimeout(r,200));
  const n=w.document.querySelector('.pwa-offline');
  n ? ok('অফলাইন-নোটিশ তৈরি') : bad('অফলাইন-নোটিশ নেই');
  n && n.classList.contains('is-open') ? ok('নোটিশ দেখা যায়') : bad('নোটিশ লুকানো');
  w.dispatchEvent(new w.Event('online'));
  await new Promise(r=>setTimeout(r,200));
  n && !n.classList.contains('is-open') ? ok('অনলাইনে নোটিশ যায়') : bad('নোটিশ যায়নি');
  dom.window.close();
}

// ৪. iOS Safari → কোনো ইনস্টল-হিন্ট নেই (বাদ দেওয়া)
{
  const {w,dom}=mk();
  Object.defineProperty(w.navigator,'userAgent',{value:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'});
  w.eval(js);
  await new Promise(r=>setTimeout(r,10600));
  !w.document.querySelector('.pwa-banner')
    ? ok('iOS-এ ইনস্টল-হিন্ট তৈরি হয় না') : bad('iOS হিন্ট এখনো দেখাচ্ছে');
  dom.window.close();
}

/* ── ৫. ইনস্টল-মোডে স্ক্রল-রিস্টোর অটুট ───────────────────────
   ইনস্টল-ব্যানার সরানোর সময় isApp() ভেঙে গিয়েছিল (isStandalone
   নামটা আর নেই) — এই পরীক্ষা সেটাই ধরে রাখে। */
console.log('\n৫. স্ক্রল-রিস্টোর (ইনস্টল-মোড)');
{
  const {w,dom}=mk();
  /* standalone মোড নকল করি */
  w.matchMedia=(q)=>({matches:/display-mode: standalone/.test(q),media:q,
    addEventListener(){},removeEventListener(){},addListener(){},removeListener(){}});
  const store={};
  Object.defineProperty(w,'sessionStorage',{value:{
    getItem:k=>store[k]??null, setItem:(k,v)=>{store[k]=v}, removeItem:k=>{delete store[k]}
  }});
  store['ead:scroll:/ead/index.html']='420';
  let scrolled=null;
  w.scrollTo=(x,y)=>{scrolled=y};
  Object.defineProperty(w,'pageYOffset',{configurable:true,get:()=>777});
  w.eval(js);
  await new Promise(r=>setTimeout(r,200));
  scrolled===420 ? ok('ফিরে এলে আগের জায়গায় (420px)') : bad(`স্ক্রল ফেরেনি (${scrolled})`);
  w.dispatchEvent(new w.Event('pagehide'));
  await new Promise(r=>setTimeout(r,40));
  store['ead:scroll:/ead/index.html']==='777' ? ok('পাতা ছাড়ার আগে জায়গা মনে রাখে (777px)') : bad(`সেভ হয়নি (${store['ead:scroll:/ead/index.html']})`);
  dom.window.close();
}

/* ── ৬. অ্যাপ না হলে স্ক্রল ছোঁয় না ── */
console.log('\n৬. সাধারণ ট্যাবে হস্তক্ষেপ নেই');
{
  const {w,dom}=mk();
  let touched=false;
  w.scrollTo=()=>{touched=true};
  w.eval(js);
  await new Promise(r=>setTimeout(r,120));
  !touched ? ok('ব্রাউজার-ট্যাবে scrollTo ডাকা হয় না') : bad('সাধারণ ট্যাবে স্ক্রল বদলাচ্ছে');
  dom.window.close();
}

/* ── ৭. SW আপডেট-বার (waiting worker-এ SKIP_WAITING, controller-এ নয়) ── */
console.log('\n৭. SW আপডেট-বার');
{
  const {w,dom}=mk();
  let waitingMsg=null, ctrlMsg=null;
  const swListeners={};
  const waitingWorker={postMessage:m=>{waitingMsg=m}};
  const reg={
    installing:null,
    waiting:waitingWorker,
    active:null,
    addEventListener(){},
    update(){return Promise.resolve()}
  };
  w.navigator.serviceWorker={
    register:()=>Promise.resolve(reg),
    ready:Promise.resolve(reg),
    controller:{postMessage:m=>{ctrlMsg=m}},
    addEventListener:(ev,fn)=>{(swListeners[ev]=swListeners[ev]||[]).push(fn)}
  };
  w.eval(js);
  await new Promise(r=>setTimeout(r,80));
  const bar=w.document.querySelector('.pwa-update-bar');
  bar && bar.classList.contains('is-open') ? ok('reg.waiting থাকলে আপডেট-বার খোলে') : bad('আপডেট-বার খোলেনি');
  !w.document.querySelector('.pwa-banner') && !w.document.querySelector('.pwa-btn')
    ? ok('পুরোনো .pwa-banner/.pwa-btn ক্লাস ব্যবহৃত হয়নি') : bad('নিষিদ্ধ ক্লাস ব্যবহৃত হয়েছে');
  const go=w.document.querySelector('.pwa-update-btn');
  go && go.dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
  await new Promise(r=>setTimeout(r,30));
  waitingMsg && waitingMsg.type==='SKIP_WAITING'
    ? ok('waiting worker-এ SKIP_WAITING পাঠানো হয়েছে') : bad('waiting worker-এ মেসেজ যায়নি');
  !ctrlMsg ? ok('পুরোনো controller-এ ভুল SKIP_WAITING পাঠানো হয়নি') : bad('পুরোনো controller-এ মেসেজ গেছে');
  const cls=w.document.querySelector('.pwa-update-close');
  cls && cls.dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
  await new Promise(r=>setTimeout(r,300));
  !w.document.querySelector('.pwa-update-bar')
    ? ok('✕ বোতামে আপডেট-বার বন্ধ ও অপসারিত হয়') : bad('আপডেট-বার বন্ধ হয়নি');
  dom.window.close();
}

console.log(`\n${fail?'✗':'✓'} পাশ ${pass} · ফেল ${fail}\n`);
process.exit(fail?1:0);
