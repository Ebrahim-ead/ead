(function(){
"use strict";
var reduced=window.matchMedia("(prefers-reduced-motion: reduce)");
var fine=window.matchMedia("(hover:hover) and (pointer:fine)");
var supportsVT=typeof document.startViewTransition==="function";

function stagger(){
  var groups=[".article-list-grid",".grid",".book-list-grid",".fgrid",".info3"];
  var step=55,maxDelay=420;
  groups.forEach(function(sel){
    var box=document.querySelector(sel);
    if(!box)return;
    [].slice.call(box.children).forEach(function(el,i){
      var d=Math.min(i*step,maxDelay);
      if(i>=8)d=Math.min((i%8)*step,maxDelay);
      el.style.setProperty("--d",(d/1000)+"s");
      el.style.transitionDelay=(d/1000)+"s";
    });
  });
}

function cursor(){
  if(!fine.matches||reduced.matches)return;
  var ring=document.createElement("div");
  ring.className="m-cursor";
  ring.setAttribute("aria-hidden","true");
  ring.style.cssText="position:fixed;left:0;top:0;pointer-events:none;z-index:9999;";
  document.body.appendChild(ring);
  var x=-100,y=-100,rx=-100,ry=-100,hot=false,shown=false,lastTarget=null,dirty=false;

  document.addEventListener("pointermove",function(e){
    if(e.pointerType==="touch")return;
    x=e.clientX;y=e.clientY;dirty=true;
    if(!shown){rx=x;ry=y;shown=true;ring.classList.add("on");}
    if(e.target!==lastTarget){
      lastTarget=e.target;
      var t=e.target;
      var nowHot=!!(t&&t.closest&&t.closest("a,button,summary,.card,.qcard,article"));
      if(nowHot!==hot){hot=nowHot;ring.classList.toggle("hot",hot);}
    }
    wake();
  },{passive:true});

  document.addEventListener("pointerleave",function(){
    shown=false;dirty=false;ring.classList.remove("on");
  });

  document.addEventListener("pointerdown",function(){
    if(reduced.matches||!shown)return;
    ring.style.transform="translate3d("+rx+"px,"+ry+"px,0) scale(.82)";
    dirty=true;wake();
  },{passive:true});

  return function tick(){
    if(!shown)return false;
    rx+=(x-rx)*0.22;
    ry+=(y-ry)*0.22;
    if(Math.abs(x-rx)<0.1&&Math.abs(y-ry)<0.1){rx=x;ry=y;}
    if(!dirty&&rx===x&&ry===y)return false;
    dirty=false;
    ring.style.transform="translate3d("+rx+"px,"+ry+"px,0)";
    return rx!==x||ry!==y;
  };
}

function progress(){
  var bar=document.createElement("div");
  bar.className="m-progress";
  bar.setAttribute("aria-hidden","true");
  bar.style.cssText="position:fixed;left:0;right:0;top:0;pointer-events:none;";
  document.body.appendChild(bar);
  var max=0,y=0,last=0,scheduled=false;
  function measure(){
    y=window.pageYOffset||document.documentElement.scrollTop||0;
    max=document.documentElement.scrollHeight-window.innerHeight;
  }
  function update(){
    scheduled=false;
    var p=max>0?Math.min(1,Math.max(0,y/max)):0;
    if(Math.abs(p-last)<0.0015)return;
    last=p;
    bar.style.transform="scaleX("+p.toFixed(4)+")";
    bar.classList.toggle("on",p>0.005&&max>420);
    bar.style.opacity=p>0.005?"1":"0";
  }
  function scheduleUpdate(){
    if(scheduled)return;
    scheduled=true;
    if(typeof requestAnimationFrame==="function")requestAnimationFrame(update);
    else update();
  }
  window.addEventListener("scroll",function(){measure();scheduleUpdate();},{passive:true});
  window.addEventListener("resize",function(){if((window.pageYOffset||document.documentElement.scrollTop||0)>0||last>0){measure();scheduleUpdate();}},{passive:true});
  if((window.pageYOffset||document.documentElement.scrollTop||0)>0){
    if(typeof requestAnimationFrame==="function")requestAnimationFrame(function(){measure();update();});
    else{measure();update();}
  }
  return function tick(){update();};
}

function header(){
  var bar=document.querySelector("header.top");
  if(!bar)return;
  var stuck=false;
  function apply(){
    var s=(window.pageYOffset||0)>24;
    if(s!==stuck){stuck=s;bar.classList.toggle("m-stuck",s);}
  }
  if((window.pageYOffset||0)>24)apply();
  window.addEventListener("scroll",apply,{passive:true});
}

function theme(){
  if(!supportsVT||reduced.matches)return;
  var btn=document.querySelector("[data-theme-toggle]");
  if(!btn)return;
  var dispatching=false;
  btn.addEventListener("click",function(e){
    if(dispatching||!document.startViewTransition)return;
    e.stopImmediatePropagation();
    e.preventDefault();
    try{
      document.startViewTransition(function(){
        dispatching=true;
        try{btn.dispatchEvent(new MouseEvent("click",{bubbles:true,cancelable:true}));}
        finally{dispatching=false;}
      });
    }catch(err){
      dispatching=true;
      try{btn.dispatchEvent(new MouseEvent("click",{bubbles:true,cancelable:true}));}
      finally{dispatching=false;}
    }
  },true);
}

var tickers=[];
var running=false;
function loop(){
  var active=false;
  for(var i=0;i<tickers.length;i++){if(tickers[i]())active=true;}
  if(!active){running=false;return;}
  requestAnimationFrame(loop);
}
function wake(){
  if(reduced.matches||running||!tickers.length)return;
  running=true;
  requestAnimationFrame(loop);
}

function boot(){
  stagger();
  var ring=cursor();
  if(ring)tickers.push(ring);
  tickers=tickers.filter(Boolean);
  progress();
  header();
  theme();
  window.addEventListener("resize",stagger,{passive:true});
}

if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);
else boot();

var onChange=function(){
  if(reduced.matches){running=false;return;}
};
if(reduced.addEventListener)reduced.addEventListener("change",onChange);
else if(reduced.addListener)reduced.addListener(onChange);
})();
