/* Command de Cuisine — reliable manager task controls v4.
   Works with the live app's uppercase STATE object and preserves historic records. */
(function(){
  'use strict';

  function appState(){
    try { if (typeof STATE !== 'undefined' && STATE && typeof STATE === 'object') return STATE; } catch(e) {}
    try { if (typeof state !== 'undefined' && state && typeof state === 'object') return state; } catch(e) {}
    if (window.STATE && typeof window.STATE === 'object') return window.STATE;
    if (window.state && typeof window.state === 'object') return window.state;
    return null;
  }

  function currentUser(){
    var names=['me','ME','currentUser','CURRENT_USER','user','USER','sessionUser','SESSION_USER'];
    for(var i=0;i<names.length;i++){
      try { var v=window[names[i]]; if(v && typeof v==='object' && v.role) return v; } catch(e) {}
    }
    try { if(typeof me!=='undefined' && me) return me; } catch(e) {}
    try { if(typeof ME!=='undefined' && ME) return ME; } catch(e) {}
    return null;
  }

  function roleIsManager(u){
    var r=String(u&&u.role||'').toLowerCase();
    return r==='manager'||r==='admin'||r==='administrator';
  }

  function canShow(){
    var st=appState();
    if(!st) return false;
    var u=currentUser();
    if(u) return roleIsManager(u);
    /* Fallback: the server still enforces manager-only changes.  Do not hide the
       control simply because the base app keeps the signed-in user in a lexical binding. */
    return true;
  }

  function esc(v){return String(v==null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
  function msg(t,k){if(typeof toast==='function')toast(t,k||'ok');else alert(t);}
  async function persist(t){if(typeof save!=='function')throw new Error('Save function is unavailable');var r=save();if(r&&typeof r.then==='function')await r;if(t)msg(t,'ok');}

  function styles(){
    if(document.getElementById('cdc-mgr-v4-css'))return;
    var s=document.createElement('style');s.id='cdc-mgr-v4-css';s.textContent=
      '.cdc-v4-bar{position:sticky;top:0;z-index:99999;display:flex;gap:10px;align-items:center;padding:10px 12px;margin:0 0 12px;background:#15191f;border:1px solid #333b46;border-radius:14px;box-shadow:0 8px 24px rgba(0,0,0,.3)}'+
      '.cdc-v4-manage{flex:1;background:#e0ad39!important;color:#17191d!important;border:0!important;border-radius:11px!important;padding:12px 14px!important;font-weight:900!important;font-size:16px!important}'+
      '.cdc-v4-label{font-size:12px;opacity:.7;white-space:nowrap}'+
      '.cdc-v4-overlay{position:fixed;inset:0;z-index:2147483640;background:rgba(0,0,0,.76);display:flex;align-items:flex-end;justify-content:center;padding:10px}'+
      '.cdc-v4-sheet{width:min(720px,100%);max-height:90vh;overflow:auto;background:#181c22;color:#f3f3f3;border:1px solid #39414d;border-radius:18px 18px 8px 8px;padding:16px}'+
      '.cdc-v4-head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px}.cdc-v4-head h2{margin:0}.cdc-v4-close{background:#292f38;color:white;border:1px solid #4a5360;border-radius:10px;padding:8px 12px;font-weight:800}'+
      '.cdc-v4-row{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;background:#20252d;border:1px solid #353d48;border-radius:12px;padding:12px;margin:8px 0}.cdc-v4-row small{display:block;opacity:.7;margin-top:3px}.cdc-v4-actions{display:flex;gap:7px;flex-wrap:wrap}'+
      '.cdc-v4-edit,.cdc-v4-remove,.cdc-v4-save,.cdc-v4-cancel{border-radius:10px;padding:9px 12px;font-weight:850;border:1px solid #4b5563;background:#2a3039;color:#fff}.cdc-v4-remove{border-color:#934343;color:#ff9999}.cdc-v4-save{background:#e0ad39;color:#17191d;border-color:#e0ad39}'+
      '.cdc-v4-form{display:grid;gap:12px}.cdc-v4-form label{display:grid;gap:6px;font-weight:800}.cdc-v4-form input,.cdc-v4-form select{width:100%;box-sizing:border-box;padding:11px;border-radius:10px;border:1px solid #47515e;background:#101319;color:#fff;font:inherit}.cdc-v4-form-actions{display:flex;justify-content:flex-end;gap:8px}'+
      '@media(max-width:560px){.cdc-v4-row{grid-template-columns:1fr}.cdc-v4-actions{justify-content:flex-start}.cdc-v4-label{display:none}}';
    document.head.appendChild(s);
  }

  function closeSheet(){var x=document.getElementById('cdc-v4-overlay');if(x)x.remove();}
  function sheet(title,html){closeSheet();var o=document.createElement('div');o.id='cdc-v4-overlay';o.className='cdc-v4-overlay';o.innerHTML='<div class="cdc-v4-sheet"><div class="cdc-v4-head"><h2>'+esc(title)+'</h2><button class="cdc-v4-close">Close</button></div><div id="cdc-v4-body">'+html+'</div></div>';o.onclick=function(e){if(e.target===o)closeSheet();};o.querySelector('.cdc-v4-close').onclick=closeSheet;document.body.appendChild(o);return o;}

  function cleanSchedules(){var st=appState();return st&&Array.isArray(st.cleaningSchedules)?st.cleaningSchedules:[];}
  function cleanTasks(){var st=appState();return st&&Array.isArray(st.cleaningTasks)?st.cleaningTasks:[];}
  function checks(){var st=appState();return st&&Array.isArray(st.checks)?st.checks:[];}
  function matchTask(s){return cleanTasks().find(function(t){return t&&String(t.area||'')===String(s.area||'')&&String(t.task||'')===String(s.task||'');})||null;}

  function openCleaning(){
    var list=cleanSchedules();
    var html=list.length?list.map(function(s){var f=s.frequency||s.freq||'';return '<div class="cdc-v4-row"><div><b>'+esc(s.task||'Cleaning task')+'</b><small>'+esc((s.area||'')+(f?' · '+f:''))+'</small></div><div class="cdc-v4-actions"><button class="cdc-v4-edit" data-ce="'+esc(s.id||'')+'">Edit</button><button class="cdc-v4-remove" data-cr="'+esc(s.id||'')+'">Remove</button></div></div>';}).join(''):'<p>No active cleaning tasks.</p>';
    var o=sheet('Manage cleaning tasks',html);
    o.querySelectorAll('[data-ce]').forEach(function(b){b.onclick=function(){editCleaning(b.getAttribute('data-ce'));};});
    o.querySelectorAll('[data-cr]').forEach(function(b){b.onclick=function(){removeCleaning(b.getAttribute('data-cr'));};});
  }

  function editCleaning(id){
    var s=cleanSchedules().find(function(x){return String(x&&x.id||'')===String(id);});if(!s)return msg('Cleaning task not found','bad');
    var f=String(s.frequency||s.freq||'Daily').toLowerCase();
    var o=sheet('Edit cleaning task','<form id="cdc-v4-clean-form" class="cdc-v4-form"><label>Task<input name="task" required value="'+esc(s.task||'')+'"></label><label>Area / equipment<input name="area" required value="'+esc(s.area||'')+'"></label><label>Frequency<select name="frequency"><option'+(f==='daily'?' selected':'')+'>Daily</option><option'+(f==='weekly'?' selected':'')+'>Weekly</option><option'+(f==='monthly'?' selected':'')+'>Monthly</option></select></label><div class="cdc-v4-form-actions"><button type="button" class="cdc-v4-cancel">Cancel</button><button class="cdc-v4-save" type="submit">Save changes</button></div></form>');
    o.querySelector('.cdc-v4-cancel').onclick=openCleaning;
    o.querySelector('#cdc-v4-clean-form').onsubmit=async function(e){e.preventDefault();var fd=new FormData(e.target),name=String(fd.get('task')||'').trim(),area=String(fd.get('area')||'').trim(),freq=String(fd.get('frequency')||'Daily');if(!name||!area)return;var old={task:s.task,area:s.area,frequency:s.frequency,freq:s.freq},t=matchTask(s),oldt=t?{task:t.task,area:t.area,frequency:t.frequency,freq:t.freq}:null;try{s.task=name;s.area=area;s.frequency=freq;if('freq'in s)s.freq=freq.toLowerCase();if(t){t.task=name;t.area=area;t.freq=freq.toLowerCase();if('frequency'in t)t.frequency=freq;}await persist('Cleaning task updated');closeSheet();if(typeof render==='function')render();}catch(err){Object.assign(s,old);if(t&&oldt)Object.assign(t,oldt);msg(err.message||'Could not update cleaning task','bad');}};
  }

  async function removeCleaning(id){
    var st=appState(),list=cleanSchedules(),s=list.find(function(x){return String(x&&x.id||'')===String(id);});if(!s)return msg('Cleaning task not found','bad');
    if(!confirm('Remove “'+(s.task||'this cleaning task')+'” from the active cleaning schedule?\n\nHistoric completed records will remain.'))return;
    var bs=JSON.parse(JSON.stringify(list)),bt=JSON.parse(JSON.stringify(cleanTasks())),t=matchTask(s);try{st.cleaningSchedules=list.filter(function(x){return String(x&&x.id||'')!==String(id);});if(t&&t.id!=null)st.cleaningTasks=bt.filter(function(x){return String(x&&x.id||'')!==String(t.id);});await persist('Cleaning task removed');closeSheet();if(typeof render==='function')render();}catch(err){st.cleaningSchedules=bs;st.cleaningTasks=bt;msg(err.message||'Could not remove cleaning task','bad');}
  }

  function openDaily(){
    var list=checks();var html=list.length?list.map(function(c){var p=String(c.period||'').toLowerCase()==='close'?'Closing':'Opening';return '<div class="cdc-v4-row"><div><b>'+esc(c.name||'Check')+'</b><small>'+p+'</small></div><div class="cdc-v4-actions"><button class="cdc-v4-edit" data-de="'+esc(c.id||'')+'">Edit</button><button class="cdc-v4-remove" data-dr="'+esc(c.id||'')+'">Remove</button></div></div>';}).join(''):'<p>No active daily checks.</p>';
    var o=sheet('Manage daily checks',html);o.querySelectorAll('[data-de]').forEach(function(b){b.onclick=function(){editDaily(b.getAttribute('data-de'));};});o.querySelectorAll('[data-dr]').forEach(function(b){b.onclick=function(){removeDaily(b.getAttribute('data-dr'));};});
  }

  function editDaily(id){
    var c=checks().find(function(x){return String(x&&x.id||'')===String(id);});if(!c)return msg('Daily check not found','bad');var close=String(c.period||'').toLowerCase()==='close';
    var o=sheet('Edit daily check','<form id="cdc-v4-daily-form" class="cdc-v4-form"><label>Check name<input name="name" required value="'+esc(c.name||'')+'"></label><label>When<select name="period"><option value="open"'+(!close?' selected':'')+'>Opening</option><option value="close"'+(close?' selected':'')+'>Closing</option></select></label><div class="cdc-v4-form-actions"><button type="button" class="cdc-v4-cancel">Cancel</button><button class="cdc-v4-save" type="submit">Save changes</button></div></form>');o.querySelector('.cdc-v4-cancel').onclick=openDaily;o.querySelector('#cdc-v4-daily-form').onsubmit=async function(e){e.preventDefault();var fd=new FormData(e.target),n=String(fd.get('name')||'').trim(),p=String(fd.get('period')||'open');if(!n)return;var old={name:c.name,period:c.period};try{c.name=n;c.period=p;await persist('Daily check updated');closeSheet();if(typeof render==='function')render();}catch(err){Object.assign(c,old);msg(err.message||'Could not update daily check','bad');}};
  }

  async function removeDaily(id){
    var st=appState(),list=checks(),c=list.find(function(x){return String(x&&x.id||'')===String(id);});if(!c)return msg('Daily check not found','bad');if(!confirm('Remove “'+(c.name||'this daily check')+'” from the active Daily Checks list?\n\nHistoric completed records will remain.'))return;var before=JSON.parse(JSON.stringify(list));try{st.checks=list.filter(function(x){return String(x&&x.id||'')!==String(id);});await persist('Daily check removed');closeSheet();if(typeof render==='function')render();}catch(err){st.checks=before;msg(err.message||'Could not remove daily check','bad');}
  }

  function pageKind(){var t=String(document.body&&document.body.innerText||'').toLowerCase();if(t.indexOf('cleaning schedule')>=0)return 'cleaning';if(t.indexOf('daily checks')>=0)return 'daily';return '';}
  function ensureBar(){
    styles();var kind=pageKind();var old=document.getElementById('cdc-v4-bar');if(!kind||!canShow()){if(old)old.remove();return;}if(old&&old.dataset.kind===kind)return;if(old)old.remove();
    var bar=document.createElement('div');bar.id='cdc-v4-bar';bar.dataset.kind=kind;bar.className='cdc-v4-bar';bar.innerHTML='<button type="button" class="cdc-v4-manage">'+(kind==='cleaning'?'Manage cleaning tasks':'Manage daily checks')+'</button><span class="cdc-v4-label">Edit / remove</span>';bar.querySelector('button').onclick=kind==='cleaning'?openCleaning:openDaily;
    var main=document.querySelector('main,#app,.app,.page,.content')||document.body;main.insertBefore(bar,main.firstChild);
  }

  window.CDCManagerControlsV4={openCleaning:openCleaning,openDaily:openDaily};
  function start(){styles();ensureBar();new MutationObserver(function(){setTimeout(ensureBar,0);}).observe(document.documentElement,{childList:true,subtree:true});setInterval(ensureBar,800);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();