(function(){
"use strict";
var nav=document.getElementById("site-nav");
if(!nav)return;
var reduced=window.matchMedia("(prefers-reduced-motion: reduce)");
var desktop=window.matchMedia("(min-width:1081px)");
var links=[].slice.call(nav.querySelectorAll("a")).filter(function(a){return!a.closest(".nav-sub");});
if(!links.length)return;
var current=links.filter(function(a){
  return a.getAttribute("aria-current")==="page"||(a.parentNode&&a.parentNode.classList&&a.parentNode.classList.contains("current"));
});
var active=current[0]||links.filter(function(a){return a.classList.contains("on");})[0]||links[0];
var hovered=null,lastX=null,lastW=null,lastO=null;

function place(el,beforeWrite){
  if(!el)return;
  var navRect=nav.getBoundingClientRect();
  var r=el.getBoundingClientRect();
  if(!r.width)return;
  if(beforeWrite&&!nav.hasAttribute("data-glide"))beforeWrite();
  var x=Math.max(0,r.left-navRect.left);
  var w=Math.min(r.width,navRect.width-x)-12;
  var xStr=(x+6)+"px";
  var wStr=(w>0?w:0)+"px";
  if(xStr!==lastX){lastX=xStr;nav.style.setProperty("--nav-glide-x",xStr);}
  if(wStr!==lastW){lastW=wStr;nav.style.setProperty("--nav-glide-w",wStr);}
  if(lastO!=="1"){lastO="1";nav.style.setProperty("--nav-glide-o","1");}
}

function sync(){
  if(!desktop.matches||reduced.matches){
    if(lastO==="1"){lastO="0";nav.style.setProperty("--nav-glide-o","0");}
    if(nav.hasAttribute("data-glide"))nav.removeAttribute("data-glide");
    return;
  }
  place(hovered||active,function(){nav.setAttribute("data-glide","");});
}

function readyGlide(){
  if(!nav.hasAttribute("data-glide-ready"))nav.setAttribute("data-glide-ready","");
}

links.forEach(function(a){
  a.addEventListener("pointerenter",function(e){
    if(e.pointerType==="touch")return;
    readyGlide();hovered=a;sync();
  });
  a.addEventListener("focus",function(){readyGlide();hovered=a;sync();});
  a.addEventListener("blur",function(){if(hovered===a){hovered=null;sync();}});
  a.addEventListener("pointermove",function(e){
    if(!desktop.matches||reduced.matches||e.pointerType==="touch")return;
    var r=a.getBoundingClientRect();
    if(!r.width||!r.height)return;
    a.style.setProperty("--px",((e.clientX-r.left)/r.width)*100+"%");
    a.style.setProperty("--py",((e.clientY-r.top)/r.height)*100+"%");
  },{passive:true});
});

nav.addEventListener("pointerleave",function(){hovered=null;sync();});

var queued=null;
function refresh(){
  if(queued)return;
  queued=requestAnimationFrame(function(){queued=null;sync();});
}

var listen=function(mql,fn){
  if(mql.addEventListener)mql.addEventListener("change",fn);
  else if(mql.addListener)mql.addListener(fn);
};
listen(desktop,refresh);
listen(reduced,refresh);
window.addEventListener("resize",refresh,{passive:true});
window.addEventListener("orientationchange",refresh,{passive:true});
window.addEventListener("load",refresh);
if(document.fonts&&document.fonts.ready)document.fonts.ready.then(refresh);
var themeBtn=document.querySelector("[data-theme-toggle]");
if(themeBtn)themeBtn.addEventListener("click",function(){setTimeout(refresh,80);});
if(window.ResizeObserver)new ResizeObserver(refresh).observe(nav);

function boot(){
  if(!desktop.matches||reduced.matches){sync();return;}
  requestAnimationFrame(function(){requestAnimationFrame(sync);});
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);
else boot();
})();

(function(){
"use strict";
var item=document.getElementById("nav-item-grantho");
if(!item)return;
var btn=item.querySelector(".nav-sub-toggle");
var panel=document.getElementById("nav-sub-grantho");
if(!btn||!panel)return;
var nav=document.getElementById("site-nav");
var wide=window.matchMedia("(min-width:1081px)");
var hoverOK=window.matchMedia("(hover:hover) and (pointer:fine)");
var hoverTimer=null;

function isOpen(){return btn.getAttribute("aria-expanded")==="true";}
function set(open){
  btn.setAttribute("aria-expanded",open?"true":"false");
  panel.classList.toggle("open",open);
}
function close(){if(isOpen())set(false);}

btn.addEventListener("click",function(e){e.preventDefault();e.stopPropagation();set(!isOpen());});
if(hoverOK){
  item.addEventListener("pointerenter",function(e){
    if(e.pointerType==="touch"||!wide.matches)return;
    clearTimeout(hoverTimer);if(!isOpen())set(true);
  });
  item.addEventListener("pointerleave",function(e){
    if(e.pointerType==="touch"||!wide.matches)return;
    clearTimeout(hoverTimer);hoverTimer=setTimeout(close,220);
  });
}
panel.addEventListener("pointerenter",function(){if(wide.matches&&hoverOK.matches)clearTimeout(hoverTimer);});
panel.addEventListener("pointerleave",function(){if(wide.matches&&hoverOK.matches)hoverTimer=setTimeout(close,220);});
document.addEventListener("click",function(e){if(!item.contains(e.target))close();});
document.addEventListener("keydown",function(e){if(e.key==="Escape"&&isOpen()){btn.focus({preventScroll:true});close();}});
panel.addEventListener("click",function(e){if(e.target.closest&&e.target.closest("a"))close();});
panel.addEventListener("click",function(e){var soon=e.target.closest&&e.target.closest(".nav-sub-item.is-soon");if(soon)e.preventDefault();});
var reset=function(){close();};
if(wide.addEventListener)wide.addEventListener("change",reset);else if(wide.addListener)wide.addListener(reset);
if(nav){
  new MutationObserver(function(){if(!nav.classList.contains("open"))close();}).observe(nav,{attributes:true,attributeFilter:["class"]});
}
})();

(function(){
"use strict";
var burger=document.querySelector(".burger");
var nav=document.querySelector(".nav");
if(!burger||!nav)return;
if(burger.dataset&&burger.dataset.menuBound==="1")return;
var body=document.body;
var backdrop=document.querySelector(".nav-backdrop");
var firstNavFocus=nav.querySelector("a[href],button");
function getMenuFocusables(){
  var navEls=Array.prototype.slice.call(nav.querySelectorAll("a[href],button")).filter(function(el){
    var sub=el.closest&&el.closest(".nav-sub");
    return !sub||sub.classList.contains("open");
  });
  var headerButtons=Array.prototype.slice.call(document.querySelectorAll(".header-actions button"));
  return navEls.concat(headerButtons);
}

function setMenuOpen(open,restoreFocus){
  nav.classList.toggle("open",open);
  if(backdrop)backdrop.classList.toggle("on",open);
  if(body)body.classList.toggle("menu-open",open);
  burger.setAttribute("aria-expanded",open?"true":"false");
  burger.setAttribute("aria-label",open?"মেনু বন্ধ করুন":"মেনু খুলুন");
  burger.title=open?"মেনু বন্ধ করুন":"মেনু খুলুন";
  burger.textContent=open?"\u00d7":"\u2630";
  if(open&&firstNavFocus)window.requestAnimationFrame(function(){firstNavFocus.focus();});
  else if(!open&&restoreFocus)burger.focus();
}

burger.addEventListener("click",function(){setMenuOpen(!nav.classList.contains("open"),false);});
nav.addEventListener("click",function(e){var link=e.target.closest?e.target.closest("a"):null;if(link)setMenuOpen(false,false);});
if(backdrop)backdrop.addEventListener("click",function(){setMenuOpen(false,true);});
document.addEventListener("keydown",function(e){
  if(!nav.classList.contains("open"))return;
  if(e.key==="Escape"){e.preventDefault();setMenuOpen(false,true);return;}
  if(e.key==="Tab"){
    var menuFocusables=getMenuFocusables();
    if(!menuFocusables.length)return;
    var first=menuFocusables[0],last=menuFocusables[menuFocusables.length-1],activeEl=document.activeElement;
    if(e.shiftKey&&(activeEl===first||menuFocusables.indexOf(activeEl)<0)){e.preventDefault();last.focus();}
    else if(!e.shiftKey&&(activeEl===last||menuFocusables.indexOf(activeEl)<0)){e.preventDefault();first.focus();}
  }
});
window.addEventListener("resize",function(){if(window.innerWidth>1080&&nav.classList.contains("open"))setMenuOpen(false,false);});
if(burger.dataset)burger.dataset.menuBound="1";
window.__eadMenuBound=true;
})();
