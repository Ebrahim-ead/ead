import {JSDOM} from 'jsdom';
const html=await (await fetch('http://127.0.0.1:8795/about.html')).text();
const d=new JSDOM(html).window.document;
const ft=d.querySelector('footer');
const cols=[...ft.querySelectorAll('.fgrid > div')];
console.log('ফুটার কলাম:',cols.length);
const col=cols.find(c=>c.querySelector('h2')?.textContent.trim()==='পাঠ্য');
console.log('\n“পাঠ্য” কলামের লিংকগুলো:');
[...col.querySelectorAll('a')].forEach(a=>{
  const ext=/^https?:/.test(a.getAttribute('href'));
  console.log(`  ${ext?'↗':' '} ${a.textContent.trim()}${ext?'  →  '+a.href:''}`);
});
const a=[...col.querySelectorAll('a')].at(-1);
console.log('\nনতুন লিংক:', a.textContent.trim());
console.log('  href:', a.getAttribute('href'));
console.log('  target:', a.getAttribute('target'), '| rel:', a.getAttribute('rel'), '| বাহ্যিক:', /^https?:/.test(a.getAttribute('href')));
