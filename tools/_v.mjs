import {JSDOM,VirtualConsole} from 'jsdom';
const vc=new VirtualConsole(); vc.on('jsdomError',e=>{if(!/Could not load/.test(e.message))console.log('⚠',e.message.slice(0,90));});
const html=await (await fetch('http://127.0.0.1:8790/grantho/christian/bible.html')).text();
const dom=new JSDOM(html,{runScripts:'dangerously',resources:'usable',pretendToBeVisual:true,virtualConsole:vc,url:'http://127.0.0.1:8790/grantho/christian/bible.html'});
const w=dom.window,doc=w.document;
for(let i=0;i<40;i++){await new Promise(r=>setTimeout(r,300)); if(doc.querySelectorAll('#g-book-list [data-ch]').length)break;}
const books=[...doc.querySelectorAll('#g-book-list [data-ch]')];
console.log('পুস্তক-বাটন:',books.length);
console.log('নিয়ম:',(doc.querySelector('#g-book-list')?.textContent||'').replace(/\s+/g,' ').match(/পুরাতন নিয়ম\s*\d+ পুস্তক/)?.[0]||'?');
for(const id of [2,4,38,66]){
  books.find(b=>+b.dataset.ch===id)?.dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
  await new Promise(r=>setTimeout(r,800));
  const cells=[...doc.querySelectorAll('#g-chapter-grid [data-c]')];
  const off=cells.filter(c=>c.classList.contains('off')).map(c=>c.dataset.c);
  console.log(`  বই ${id}: ${cells.length} অধ্যায় · «পাঠ নেই» ${off.length?off.join(','):'নেই'}`);
}
books.find(b=>+b.dataset.ch===66)?.dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await new Promise(r=>setTimeout(r,800));
doc.querySelector('#g-chapter-grid [data-c="22"]')?.dispatchEvent(new w.MouseEvent('click',{bubbles:true}));
await new Promise(r=>setTimeout(r,1200));
console.log('শিরোনাম:',doc.querySelector('#g-chapter-title')?.textContent.trim(),'· পদ:',doc.querySelectorAll('#g-verses [data-v]').length);
