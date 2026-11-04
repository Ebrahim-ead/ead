const fs=require('fs'),path=require('path'),{JSDOM}=require('jsdom');
const pages=process.argv.slice(2).length?process.argv.slice(2):['chandogya','rigveda','katha','gita','shvetashvatara','samaveda'];
(async()=>{
for(const p of pages){
  const f=`grantho/hindu/${p}.html`;
  if(!fs.existsSync(f)){console.log(p,'MISSING');continue;}
  let html=fs.readFileSync(f,'utf8');
  const gj=fs.readFileSync('assets/grantho/grantho.js','utf8');
  html=html.replace(/<script src="[^"]*grantho\.js"[^>]*><\/script>/,'<script>'+gj+'</script>');
  const dom=new JSDOM(html,{runScripts:'dangerously',url:'http://localhost/grantho/hindu/'+p+'.html',
    pretendToBeVisual:true,
    beforeParse(w){
      w.matchMedia=()=>({matches:false,addListener(){},removeListener(){},addEventListener(){},removeEventListener(){}});
      w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};
      w.scrollTo=()=>{};
      w.fetch=(u)=>{
        const rel=String(u).replace(/^.*\/assets\/grantho\/data\//,'assets/grantho/data/');
        if(!fs.existsSync(rel)) return Promise.resolve({ok:false,status:404,json:()=>Promise.reject('404')});
        return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve(JSON.parse(fs.readFileSync(rel,'utf8')))});
      };
    }});
  const w=dom.window;
  await new Promise(r=>setTimeout(r,2500));
  const idx=JSON.parse(fs.readFileSync(`assets/grantho/data/${p}/index.json`,'utf8'));
  const chs=w.document.querySelectorAll('[data-ch]').length;
  const total=(w.document.getElementById('g-total')||{}).textContent;
  const bn=w.document.querySelectorAll('.g-v-bn').length;
  const first=(w.document.querySelector('.g-v-bn')||{}).textContent||'';
  const err=w.__err||'';
  console.log(`${p}: বোতাম ${chs}/${idx.chapters.length} | total="${total}" | বাংলা ${bn} | ${first.slice(0,45)} ${err}`);
  dom.window.close();
}
})();
