/* Command de Cuisine — contextual manager controls v6.
   Only shows manager controls on the currently visible Cleaning Schedule or Daily Checks screen.
   Uses the standalone manager console for reliable edit/remove actions. */
(function(){
  'use strict';

  var allowed = false;
  var checkedRole = false;

  function norm(s){ return String(s||'').replace(/\s+/g,' ').trim().toLowerCase(); }
  function displayed(el){
    if(!el || !el.isConnected) return false;
    var cur = el;
    while(cur && cur.nodeType===1){
      var cs = window.getComputedStyle(cur);
      if(cs.display==='none' || cs.visibility==='hidden' || cs.opacity==='0') return false;
      cur = cur.parentElement;
    }
    return el.getClientRects().length > 0;
  }
  function visibleHeading(text){
    var wanted = norm(text);
    var nodes = document.querySelectorAll('h1,h2,h3,h4,.page-title,.screen-title,.section-title');
    for(var i=0;i<nodes.length;i++){
      if(displayed(nodes[i]) && norm(nodes[i].textContent)===wanted) return nodes[i];
    }
    return null;
  }
  function activeKind(){
    if(visibleHeading('Cleaning Schedule')) return 'cleaning';
    if(visibleHeading('Daily Checks')) return 'checks';
    return '';
  }
  function cleanupLegacy(){
    var selectors = [
      '#cdc-v4-bar','#cdc-v5-fab','#cdc-manager-bar','.cdc-manager-bar',
      '[id^="cdc-v3-"]','[id^="cdc-v4-"]','[id^="cdc-v5-"]'
    ];
    selectors.forEach(function(sel){
      document.querySelectorAll(sel).forEach(function(el){
        if(el.id==='cdc-v6-bar' || el.closest && el.closest('#cdc-v6-bar')) return;
        if(el.tagName==='STYLE') return;
        el.remove();
      });
    });
  }
  function ensureStyle(){
    if(document.getElementById('cdc-v6-style')) return;
    var s=document.createElement('style');
    s.id='cdc-v6-style';
    s.textContent=
      '#cdc-v6-bar{margin:12px 28px 16px;padding:0;display:block;position:relative;z-index:5}'+
      '#cdc-v6-bar button{width:100%;background:#e4ad37;color:#17191d;border:0;border-radius:12px;padding:12px 14px;font:inherit;font-weight:900;box-shadow:0 2px 0 rgba(0,0,0,.35)}'+
      '@media(max-width:720px){#cdc-v6-bar{margin:10px 28px 14px}}';
    document.head.appendChild(s);
  }
  function targetAfter(heading){
    if(!heading) return null;
    var p=heading.parentElement;
    if(p && displayed(p)) return p;
    return heading;
  }
  function place(){
    cleanupLegacy();
    ensureStyle();
    var old=document.getElementById('cdc-v6-bar');
    var kind=activeKind();
    if(!allowed || !kind){ if(old) old.remove(); return; }
    var heading=visibleHeading(kind==='cleaning'?'Cleaning Schedule':'Daily Checks');
    if(!heading){ if(old) old.remove(); return; }
    var anchor=targetAfter(heading);
    if(!anchor){ if(old) old.remove(); return; }
    if(old && old.dataset.kind===kind && old.previousElementSibling===anchor) return;
    if(old) old.remove();
    var bar=document.createElement('div');
    bar.id='cdc-v6-bar';
    bar.dataset.kind=kind;
    var btn=document.createElement('button');
    btn.type='button';
    btn.textContent=kind==='cleaning'?'Manage cleaning tasks':'Manage daily checks';
    btn.onclick=function(){
      window.location.href='/manager_console.html?tab='+encodeURIComponent(kind)+'&v=20260915-0358';
    };
    bar.appendChild(btn);
    anchor.insertAdjacentElement('afterend',bar);
  }
  async function checkRole(){
    if(checkedRole) return;
    checkedRole=true;
    try{
      var r=await fetch('/api/session?cdc_manager_ui=6&t='+Date.now(),{credentials:'same-origin',cache:'no-store',headers:{'Cache-Control':'no-cache'}});
      var d=await r.json();
      var role=norm(d&&d.user&&d.user.role);
      allowed=!!(d&&d.authenticated&&['manager','admin','administrator'].indexOf(role)>=0);
    }catch(e){ allowed=false; }
    place();
  }
  function start(){
    checkRole();
    place();
    new MutationObserver(function(){ setTimeout(place,0); }).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class','style','hidden']});
    setInterval(place,700);
    window.addEventListener('hashchange',place);
    window.addEventListener('popstate',place);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start); else start();
})();
