#!/usr/bin/env node
/**
 * সাইট-অডিট — প্রতিটি পাতায় JS error, ভাঙা script, SEO, base64 ছবি ও ফুটার যাচাই।
 *
 * ব্যবহার:
 *     npm i jsdom            # একবার
 *     node tools/audit_site.mjs            # ৩১টি পাতা
 *     node tools/audit_site.mjs hadith.html
 *
 * যা দেখে: inline/Ext JS চালিয়ে error, script ফাইল আছে কি না, site.css ও
 * site-extra.css, og:image, canonical, base64 ছবি (data:…;base64), ফুটারের বছর (id="yr")।
 * fetch-স্টাব লোকাল ফাইল থেকেই ডেটা দেয়, তাই নেটওয়ার্ক লাগে না।
 * শেষ লাইন: «issues: 0 / 31» — শূন্য হলেই সব ঠিক।
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOTDIR = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
import { JSDOM, VirtualConsole } from 'jsdom';
const arg = process.argv.slice(2);
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).flatMap((e) => e.isDirectory()
  ? (e.name === 'assets' || e.name.startsWith('.') ? [] : walk(path.join(d, e.name)))
  : (e.name.endsWith('.html') ? [path.join(d, e.name)] : []));
const files = arg.length ? arg : walk(ROOTDIR).map((p) => path.relative(ROOTDIR, p));
let issues=0;
for(const f of files){
  const html=fs.readFileSync(f,'utf8');
  const errs=[];
  const vc=new VirtualConsole();
  vc.on('jsdomError',e=>errs.push('jsdomError: '+e.message));
  vc.on('error',(...a)=>errs.push('console.error: '+a.join(' ')));
  const dom=new JSDOM(html,{runScripts:'outside-only',pretendToBeVisual:true,url:'https://ebrahim-ead.github.io/ead/'+path.relative(ROOTDIR,f),virtualConsole:vc});
  const {window}=dom, doc=window.document;
  window.requestAnimationFrame=cb=>setTimeout(()=>cb(Date.now()),0);
  window.matchMedia=window.matchMedia||(()=>({matches:false,addEventListener(){},removeEventListener(){},addListener(){},removeListener(){}}));
  window.IntersectionObserver=class{constructor(cb){this.cb=cb}observe(){}unobserve(){}disconnect(){}};

  // fetch-stub: ব্রাউজারে fetch থাকে; jsdom-এ নেই — লোকাল ফাইল থেকেই সেবা দিই
  window.fetch=(u)=>{try{
    const rel=String(u.src||u).replace(/^https?:\/\/[^/]+\/ead\//,'').split('?')[0].replace(/^\.\.\/\.\.\//,'');
    const fp=path.join(ROOTDIR,rel);
    if(!fs.existsSync(fp)) return Promise.resolve({ok:false,status:404,json:()=>Promise.resolve({}),text:()=>Promise.resolve('')});
    const t=fs.readFileSync(fp,'utf8');
    return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve(JSON.parse(t)),text:()=>Promise.resolve(t)});
  }catch(e){return Promise.reject(e)}};
  // inline scripts (pages keep JS inline)
  for(const s of [...doc.querySelectorAll('script:not([src])')]){
    try{ new window.Function(s.textContent).call(window); }catch(e){ errs.push('inline JS: '+e.message); }
  }
  for(const s of [...doc.querySelectorAll('script[src]')]){
    const raw=s.getAttribute('src').split('?')[0];
    const p=raw.startsWith('http')?path.join('ROOTDIR',raw.replace(/^https?:\/\/[^/]+\/ead\//,'')):path.resolve(path.dirname(path.resolve(f)),raw);
    if(!fs.existsSync(p)){ errs.push('missing script: '+src); continue; }
    try{ new window.Function(fs.readFileSync(p,'utf8')).call(window); }catch(e){ errs.push('ext JS '+src+': '+e.message); }
  }
  // structure checks
  const need=['site.css','site-extra.css'];
  for(const n of need) if(!html.includes(n)) errs.push('missing '+n);
  if(!/property="og:image"/.test(html)) errs.push('no og:image');
  if(!/rel="canonical"/.test(html)) errs.push('no canonical');
  if(/data:image\/[a-z+]*;base64/.test(html)) errs.push('base64 image');
  if(!/id="yr"/.test(html)) errs.push('no footer year');
  if(errs.length){issues++;console.log('✗ '+f);errs.slice(0,6).forEach(e=>console.log('    '+e));}
}
console.log(`\nissues: ${issues} / ${files.length}`);
// ব্রাউজার-অনুকরণের টাইমার ঝুলে থাকে — সোজা বেরিয়ে পড়ি (CI-তে exit code কাজে লাগে)
process.exit(issues ? 1 : 0);
