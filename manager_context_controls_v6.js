/* Command de Cuisine — contextual manager controls v7.
   Manager/admin controls appear only on the visible Cleaning Schedule or Daily Checks screen.
   Management happens in-app (no separate HTML page), avoiding static-file MIME/cache issues. */
(function(){
  'use strict';

  var allowed=false, checkedRole=false, live=null, saving=false;

  function norm(s){return String(s||'').replace(/\s+/g,' ').trim().toLowerCase();}
  function esc(v){return String(v==null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
  function displayed(el){
    if(!el||!el.isConnected)return false;
    var cur=el;
    while(cur&&cur.nodeType===1){
      var cs=getComputedStyle(cur);
      if(cs.display==='none'||cs.visibility==='hidden'||cs.opacity==='0')return false;
      cur=cur.parentElement;
    }
    return el.getClientRects().length>0;
  }
  function visibleHeading(text){
    var wanted=norm(text), nodes=document.querySelectorAll('h1,h2,h3,h4,.page-title,.screen-title,.section-title');
    for(var i=0;i<nodes.length;i++) if(displayed(nodes[i])&&norm(nodes[i].textContent)===wanted) return nodes[i];
    return null;
  }
  function activeKind(){
    if(visibleHeading('Cleaning Schedule'))return 'cleaning';
    if(visibleHeading('Daily Checks'))return 'checks';
    return '';
  }
  function cleanupLegacy(){
    ['#cdc-v4-bar','#cdc-v5-fab','#cdc-manager-bar','.cdc-manager-bar','[id^="cdc-v3-"]','[id^="cdc-v4-"]','[id^="cdc-v5-"]'].forEach(function(sel){
      document.querySelectorAll(sel).forEach(function(el){if(!el.closest('#cdc-v7-bar')&&el.id!=='cdc-v7-bar'&&el.tagName!=='STYLE')el.remove();});
    });
  }
  function ensureStyle(){
    if(document.getElementById('cdc-v7-style'))return;
    var s=document.createElement('style'); s.id='cdc-v7-style';
    s.textContent=
      '#cdc-v7-bar{margin:10px 28px 16px;position:relative;z-index:5}'+
      '#cdc-v7-bar button{width:100%;background:#e4ad37;color:#17191d;border:0;border-radius:12px;padding:12px 14px;font:inherit;font-weight:900;box-shadow:0 2px 0 rgba(0,0,0,.35)}'+
      '#cdc-v7-overlay{position:fixed;inset:0;z-index:2147483600;background:rgba(0,0,0,.78);display:flex;align-items:flex-end;justify-content:center;padding:10px}'+
      '#cdc-v7-sheet{width:min(720px,100%);max-height:90vh;overflow:auto;background:#181d23;color:#f4f5f7;border:1px solid #35404b;border-radius:18px 18px 8px 8px;padding:16px;box-shadow:0 22px 70px rgba(0,0,0,.6)}'+
      '.cdc-v7-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}.cdc-v7-head h2{margin:0;font-size:1.2rem}'+
      '.cdc-v7-close,.cdc-v7-edit,.cdc-v7-remove,.cdc-v7-save,.cdc-v7-cancel{border:1px solid #4b5866;background:#29313a;color:#fff;border-radius:10px;padding:9px 11px;font-weight:800}'+
      '.cdc-v7-remove{color:#ff9b9b;border-color:#814646}.cdc-v7-edit{color:#f4d27b}.cdc-v7-save{background:#e4ad37;color:#17191d;border-color:#e4ad37}'+
      '.cdc-v7-row{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;background:#20262e;border:1px solid #35404b;border-radius:14px;padding:13px;margin:9px 0}'+
      '.cdc-v7-row small{display:block;color:#9ca6b3;margin-top:4px}.cdc-v7-actions{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}'+
      '.cdc-v7-form{display:grid;gap:12px}.cdc-v7-form label{display:grid;gap:6px;font-weight:700}.cdc-v7-form input,.cdc-v7-form select{width:100%;padding:11px;border-radius:10px;border:1px solid #46515e;background:#0f1318;color:#fff;font:inherit}.cdc-v7-form-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:4px}'+
      '.cdc-v7-status{color:#9ca6b3;padding:8px 0}.cdc-v7-error{color:#ff9b9b}'+
      '@media(max-width:560px){.cdc-v7-row{grid-template-columns:1fr}.cdc-v7-actions{justify-content:flex-start}#cdc-v7-bar{margin:10px 28px 14px}}';
    document.head.appendChild(s);
  }
  function targetAfter(h){return h&&h.parentElement&&displayed(h.parentElement)?h.parentElement:h;}
  function closeSheet(){var o=document.getElementById('cdc-v7-overlay'); if(o)o.remove();}
  function sheet(title,html){
    closeSheet(); ensureStyle();
    var o=document.createElement('div'); o.id='cdc-v7-overlay';
    o.innerHTML='<div id="cdc-v7-sheet" role="dialog" aria-modal="true"><div class="cdc-v7-head"><h2>'+esc(title)+'</h2><button class="cdc-v7-close" type="button">Close</button></div><div id="cdc-v7-body">'+html+'</div></div>';
    o.onclick=function(e){if(e.target===o)closeSheet();}; o.querySelector('.cdc-v7-close').onclick=closeSheet; document.body.appendChild(o); return o;
  }
  async function loadLive(){
    var r=await fetch('/api/session?cdc_manager_ui=7&t='+Date.now(),{credentials:'same-origin',cache:'no-store',headers:{'Cache-Control':'no-cache'}});
    var d=await r.json(); if(!r.ok||!d.authenticated)throw new Error('Please sign in again.');
    var role=norm(d.user&&d.user.role); if(['manager','admin','administrator'].indexOf(role)<0)throw new Error('Manager/Admin access required.');
    live={state:d.state,revision:Number(d.revision||0),user:d.user}; return live;
  }
  async function saveLive(reason){
    if(saving)return; saving=true;
    try{
      var r=await fetch('/api/state',{method:'PUT',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json','Cache-Control':'no-cache'},body:JSON.stringify({state:live.state,revision:live.revision,reason:reason})});
      var d=await r.json();
      if(!r.ok){if(r.status===409)throw new Error('Another change was saved first. Reopen Manage and try again.'); throw new Error(d.error||'Save failed.');}
      live.revision=Number(d.revision||live.revision+1);
    } finally {saving=false;}
  }
  function cleaningSchedules(){return live&&live.state&&Array.isArray(live.state.cleaningSchedules)?live.state.cleaningSchedules:[];}
  function cleaningTasks(){return live&&live.state&&Array.isArray(live.state.cleaningTasks)?live.state.cleaningTasks:[];}
  function checks(){return live&&live.state&&Array.isArray(live.state.checks)?live.state.checks:[];}
  function matchingTask(s){return cleaningTasks().find(function(t){return t&&String(t.area||'')===String(s.area||'')&&String(t.task||'')===String(s.task||'');})||null;}
  function cleaningHtml(){
    var a=cleaningSchedules(); if(!a.length)return '<div class="cdc-v7-status">No active cleaning tasks.</div>';
    return a.map(function(s,i){var f=s.frequency||s.freq||'';return '<div class="cdc-v7-row"><div><b>'+esc(s.task||'Cleaning task')+'</b><small>'+esc(s.area||'')+(f?' · '+esc(f):'')+'</small></div><div class="cdc-v7-actions"><button class="cdc-v7-edit" data-ce="'+i+'">Edit</button><button class="cdc-v7-remove" data-cr="'+i+'">Remove</button></div></div>';}).join('');
  }
  function checksHtml(){
    var a=checks(); if(!a.length)return '<div class="cdc-v7-status">No active daily checks.</div>';
    return a.map(function(c,i){var p=norm(c.period)==='close'?'Closing':'Opening';return '<div class="cdc-v7-row"><div><b>'+esc(c.name||'Check')+'</b><small>'+p+'</small></div><div class="cdc-v7-actions"><button class="cdc-v7-edit" data-de="'+i+'">Edit</button><button class="cdc-v7-remove" data-dr="'+i+'">Remove</button></div></div>';}).join('');
  }
  function bindCleaning(o){
    o.querySelectorAll('[data-ce]').forEach(function(b){b.onclick=function(){editCleaning(Number(b.dataset.ce));};});
    o.querySelectorAll('[data-cr]').forEach(function(b){b.onclick=function(){removeCleaning(Number(b.dataset.cr));};});
  }
  function bindChecks(o){
    o.querySelectorAll('[data-de]').forEach(function(b){b.onclick=function(){editCheck(Number(b.dataset.de));};});
    o.querySelectorAll('[data-dr]').forEach(function(b){b.onclick=function(){removeCheck(Number(b.dataset.dr));};});
  }
  async function openManager(kind){
    var o=sheet(kind==='cleaning'?'Manage cleaning tasks':'Manage daily checks','<div class="cdc-v7-status">Loading live data…</div>');
    try{await loadLive(); var body=o.querySelector('#cdc-v7-body'); body.innerHTML=kind==='cleaning'?cleaningHtml():checksHtml(); if(kind==='cleaning')bindCleaning(o); else bindChecks(o);}catch(e){o.querySelector('#cdc-v7-body').innerHTML='<div class="cdc-v7-status cdc-v7-error">'+esc(e.message||e)+'</div>';}
  }
  function editCleaning(i){
    var s=cleaningSchedules()[i]; if(!s)return; var f=norm(s.frequency||s.freq||'daily');
    var o=sheet('Edit cleaning task','<form class="cdc-v7-form" id="cdc-v7-form"><label>Task<input name="task" required value="'+esc(s.task||'')+'"></label><label>Area / equipment<input name="area" required value="'+esc(s.area||'')+'"></label><label>Frequency<select name="frequency"><option '+(f==='daily'?'selected':'')+'>Daily</option><option '+(f==='weekly'?'selected':'')+'>Weekly</option><option '+(f==='monthly'?'selected':'')+'>Monthly</option></select></label><div class="cdc-v7-form-actions"><button type="button" class="cdc-v7-cancel">Cancel</button><button type="submit" class="cdc-v7-save">Save</button></div></form>');
    o.querySelector('.cdc-v7-cancel').onclick=function(){openManager('cleaning');};
    o.querySelector('#cdc-v7-form').onsubmit=async function(e){e.preventDefault();var fd=new FormData(e.target),oldTask=s.task,oldArea=s.area,t=matchingTask(s);s.task=String(fd.get('task')||'').trim();s.area=String(fd.get('area')||'').trim();s.frequency=String(fd.get('frequency')||'Daily');if('freq'in s)s.freq=s.frequency.toLowerCase();if(t){t.task=s.task;t.area=s.area;t.freq=s.frequency.toLowerCase();if('frequency'in t)t.frequency=s.frequency;}try{await saveLive('manager edit cleaning task');location.reload();}catch(err){s.task=oldTask;s.area=oldArea;alert(err.message||err);}};
  }
  async function removeCleaning(i){
    var a=cleaningSchedules(),s=a[i]; if(!s)return; if(!confirm('Remove “'+(s.task||'this task')+'” from the active cleaning schedule?\n\nHistoric completed records will stay in Reports/history.'))return;
    var t=matchingTask(s),ti=t?cleaningTasks().indexOf(t):-1; live.state.cleaningSchedules=a.filter(function(_,x){return x!==i;}); if(ti>=0)live.state.cleaningTasks=cleaningTasks().filter(function(_,x){return x!==ti;});
    try{await saveLive('manager remove cleaning task');location.reload();}catch(e){alert(e.message||e);await openManager('cleaning');}
  }
  function editCheck(i){
    var c=checks()[i]; if(!c)return; var close=norm(c.period)==='close';
    var o=sheet('Edit daily check','<form class="cdc-v7-form" id="cdc-v7-form"><label>Check name<input name="name" required value="'+esc(c.name||'')+'"></label><label>When<select name="period"><option value="open" '+(!close?'selected':'')+'>Opening</option><option value="close" '+(close?'selected':'')+'>Closing</option></select></label><div class="cdc-v7-form-actions"><button type="button" class="cdc-v7-cancel">Cancel</button><button type="submit" class="cdc-v7-save">Save</button></div></form>');
    o.querySelector('.cdc-v7-cancel').onclick=function(){openManager('checks');};
    o.querySelector('#cdc-v7-form').onsubmit=async function(e){e.preventDefault();var fd=new FormData(e.target);c.name=String(fd.get('name')||'').trim();c.period=String(fd.get('period')||'open');try{await saveLive('manager edit daily check');location.reload();}catch(err){alert(err.message||err);}};
  }
  async function removeCheck(i){
    var a=checks(),c=a[i]; if(!c)return; if(!confirm('Remove “'+(c.name||'this check')+'” from the active Daily Checks list?\n\nHistoric completed records will stay in Reports/history.'))return;
    live.state.checks=a.filter(function(_,x){return x!==i;}); try{await saveLive('manager remove daily check');location.reload();}catch(e){alert(e.message||e);await openManager('checks');}
  }
  function place(){
    cleanupLegacy(); ensureStyle();
    var old=document.getElementById('cdc-v7-bar'), kind=activeKind();
    if(!allowed||!kind){if(old)old.remove();return;}
    var heading=visibleHeading(kind==='cleaning'?'Cleaning Schedule':'Daily Checks'), anchor=targetAfter(heading); if(!anchor){if(old)old.remove();return;}
    if(old&&old.dataset.kind===kind&&old.previousElementSibling===anchor)return; if(old)old.remove();
    var bar=document.createElement('div');bar.id='cdc-v7-bar';bar.dataset.kind=kind;var btn=document.createElement('button');btn.type='button';btn.textContent=kind==='cleaning'?'Edit / remove cleaning tasks':'Edit / remove daily checks';btn.onclick=function(){openManager(kind);};bar.appendChild(btn);anchor.insertAdjacentElement('afterend',bar);
  }
  async function checkRole(){
    if(checkedRole)return;checkedRole=true;
    try{var r=await fetch('/api/session?cdc_manager_ui=7&t='+Date.now(),{credentials:'same-origin',cache:'no-store',headers:{'Cache-Control':'no-cache'}}),d=await r.json(),role=norm(d&&d.user&&d.user.role);allowed=!!(d&&d.authenticated&&['manager','admin','administrator'].indexOf(role)>=0);}catch(e){allowed=false;} place();
  }
  function start(){checkRole();place();new MutationObserver(function(){setTimeout(place,0);}).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class','style','hidden']});setInterval(place,700);window.addEventListener('hashchange',place);window.addEventListener('popstate',place);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
