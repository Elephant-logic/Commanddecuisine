/* Command de Cuisine — contextual manager controls v8.
   Manager/admin controls appear only on the visible Cleaning Schedule or Daily Checks screen.
   Add/edit/remove actions are saved directly through the authenticated live-state API.
   Historic completion records are never deleted. */
(function(){
  'use strict';

  var allowed=false, checkedRole=false, live=null, busy=false;

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
    ['#cdc-v4-bar','#cdc-v5-fab','#cdc-manager-bar','.cdc-manager-bar','[id^="cdc-v3-"]','[id^="cdc-v4-"]','[id^="cdc-v5-"]','#cdc-v6-bar'].forEach(function(sel){
      document.querySelectorAll(sel).forEach(function(el){if(el.id!=='cdc-v8-bar'&&el.tagName!=='STYLE')el.remove();});
    });
  }
  function ensureStyle(){
    if(document.getElementById('cdc-v8-style'))return;
    var s=document.createElement('style'); s.id='cdc-v8-style';
    s.textContent=
      '#cdc-v8-bar{margin:10px 28px 16px;position:relative;z-index:5}'+
      '#cdc-v8-bar button{width:100%;background:#e4ad37;color:#17191d;border:0;border-radius:12px;padding:12px 14px;font:inherit;font-weight:900;box-shadow:0 2px 0 rgba(0,0,0,.35)}'+
      '.cdc-v8-overlay{position:fixed;inset:0;z-index:2147483000;background:rgba(0,0,0,.76);display:flex;align-items:flex-end;justify-content:center;padding:10px}'+
      '.cdc-v8-sheet{width:min(720px,100%);max-height:90vh;overflow:auto;background:#181d23;color:#f4f5f7;border:1px solid #35404b;border-radius:18px 18px 8px 8px;padding:16px;box-shadow:0 20px 60px rgba(0,0,0,.55)}'+
      '.cdc-v8-head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px}.cdc-v8-head h2{margin:0;font-size:1.22rem}'+
      '.cdc-v8-close,.cdc-v8-btn{border:1px solid #4b5866;background:#29313a;color:#fff;border-radius:10px;padding:9px 11px;font-weight:800}'+
      '.cdc-v8-add{width:100%;background:#e4ad37;color:#17191d;border-color:#e4ad37;margin:0 0 10px}'+
      '.cdc-v8-row{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;background:#20262e;border:1px solid #35404b;border-radius:14px;padding:13px;margin:9px 0}'+
      '.cdc-v8-row small{display:block;color:#9ca6b3;margin-top:4px}.cdc-v8-actions{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}'+
      '.cdc-v8-edit{color:#f4d27b}.cdc-v8-remove{color:#ff8b8b;border-color:#814646}'+
      '.cdc-v8-form{display:grid;gap:12px}.cdc-v8-form label{display:grid;gap:6px;font-weight:700}.cdc-v8-form input,.cdc-v8-form select{width:100%;padding:11px;border-radius:10px;border:1px solid #46515e;background:#0f1318;color:#fff;font:inherit}'+
      '.cdc-v8-form-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:4px}.cdc-v8-save{background:#e4ad37;color:#17191d;border-color:#e4ad37}'+
      '.cdc-v8-status{font-size:.88rem;color:#9ca6b3;margin:8px 0}.cdc-v8-status.bad{color:#ff8b8b}.cdc-v8-status.ok{color:#55c98b}'+
      '@media(max-width:560px){.cdc-v8-row{grid-template-columns:1fr}.cdc-v8-actions{justify-content:flex-start}#cdc-v8-bar{margin:10px 28px 14px}}';
    document.head.appendChild(s);
  }
  function uid(prefix){return prefix+'_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,8);}
  function closeSheet(){var x=document.getElementById('cdc-v8-overlay');if(x)x.remove();}
  function sheet(title,body){
    closeSheet(); ensureStyle();
    var o=document.createElement('div'); o.id='cdc-v8-overlay'; o.className='cdc-v8-overlay';
    o.innerHTML='<div class="cdc-v8-sheet" role="dialog" aria-modal="true"><div class="cdc-v8-head"><h2>'+esc(title)+'</h2><button type="button" class="cdc-v8-close">Close</button></div><div id="cdc-v8-body">'+body+'</div></div>';
    o.onclick=function(e){if(e.target===o)closeSheet();};
    o.querySelector('.cdc-v8-close').onclick=closeSheet;
    document.body.appendChild(o); return o;
  }
  function status(msg,bad){
    var el=document.querySelector('#cdc-v8-overlay .cdc-v8-status');
    if(el){el.textContent=msg;el.className='cdc-v8-status '+(bad?'bad':'ok');}
  }
  async function getLive(){
    var r=await fetch('/api/session?cdc_mgr8='+Date.now(),{credentials:'same-origin',cache:'no-store',headers:{'Cache-Control':'no-cache'}});
    var d=await r.json();
    if(!r.ok||!d.authenticated)throw new Error((d&&d.error)||'Please sign in again.');
    var role=norm(d.user&&d.user.role);
    if(['manager','admin','administrator'].indexOf(role)<0)throw new Error('Manager/Admin access is required.');
    live=d; return d;
  }
  async function mutateAndSave(reason,mutator){
    if(busy)throw new Error('A save is already in progress.');
    busy=true;
    try{
      for(var attempt=0;attempt<2;attempt++){
        var d=await getLive();
        var st=JSON.parse(JSON.stringify(d.state||{}));
        mutator(st,d);
        var r=await fetch('/api/state',{method:'PUT',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json','Cache-Control':'no-cache'},body:JSON.stringify({state:st,revision:Number(d.revision||0),reason:reason})});
        var out=await r.json();
        if(r.ok){live={authenticated:true,user:d.user,state:st,revision:Number(out.revision||Number(d.revision||0)+1)};return live;}
        if(r.status===409&&attempt===0)continue;
        throw new Error((out&&out.error)||'Could not save the change.');
      }
      throw new Error('Could not save because the live record changed at the same time. Try again.');
    }finally{busy=false;}
  }
  function schedules(st){return st&&Array.isArray(st.cleaningSchedules)?st.cleaningSchedules:[];}
  function tasks(st){return st&&Array.isArray(st.cleaningTasks)?st.cleaningTasks:[];}
  function checks(st){return st&&Array.isArray(st.checks)?st.checks:[];}
  function currentPeriod(){
    if(visibleHeading('Closing Checks'))return 'close';
    if(visibleHeading('Opening Checks'))return 'open';
    var bs=document.querySelectorAll('button');
    for(var i=0;i<bs.length;i++){
      if(!displayed(bs[i]))continue;
      var t=norm(bs[i].textContent);
      if((t==='opening'||t==='closing')&&(bs[i].classList.contains('active')||bs[i].getAttribute('aria-selected')==='true')) return t==='closing'?'close':'open';
    }
    return 'open';
  }
  function renderCleaningManager(){
    var st=live&&live.state||{}, a=schedules(st);
    var html='<button type="button" class="cdc-v8-btn cdc-v8-add" id="cdc-v8-add-clean">+ Add cleaning task</button><div class="cdc-v8-status">Changes save to the live venue. Historic completed records are kept.</div>';
    html+=a.length?a.map(function(s,i){return '<div class="cdc-v8-row"><div><b>'+esc(s.task||'Cleaning task')+'</b><small>'+esc(s.area||'')+(s.frequency||s.freq?' · '+esc(s.frequency||s.freq):'')+'</small></div><div class="cdc-v8-actions"><button class="cdc-v8-btn cdc-v8-edit" data-edit-clean="'+i+'">Edit</button><button class="cdc-v8-btn cdc-v8-remove" data-remove-clean="'+i+'">Remove</button></div></div>';}).join(''):'<p>No active cleaning tasks.</p>';
    var o=sheet('Manage cleaning tasks',html);
    o.querySelector('#cdc-v8-add-clean').onclick=addCleaningForm;
    o.querySelectorAll('[data-edit-clean]').forEach(function(b){b.onclick=function(){editCleaningForm(+b.dataset.editClean);};});
    o.querySelectorAll('[data-remove-clean]').forEach(function(b){b.onclick=function(){removeCleaning(+b.dataset.removeClean);};});
  }
  async function openCleaning(){try{await getLive();renderCleaningManager();}catch(e){alert(e.message||e);}}
  function cleaningForm(title,values,onSubmit){
    values=values||{}; var f=norm(values.frequency||values.freq||'daily');
    var o=sheet(title,'<form class="cdc-v8-form" id="cdc-v8-clean-form"><label>Task<input name="task" required value="'+esc(values.task||'')+'"></label><label>Area / equipment<input name="area" required value="'+esc(values.area||'')+'"></label><label>Frequency<select name="frequency"><option value="Daily" '+(f==='daily'?'selected':'')+'>Daily</option><option value="Weekly" '+(f==='weekly'?'selected':'')+'>Weekly</option><option value="Monthly" '+(f==='monthly'?'selected':'')+'>Monthly</option></select></label><div class="cdc-v8-status"></div><div class="cdc-v8-form-actions"><button type="button" class="cdc-v8-btn" id="cdc-v8-cancel">Cancel</button><button class="cdc-v8-btn cdc-v8-save">Save</button></div></form>');
    o.querySelector('#cdc-v8-cancel').onclick=renderCleaningManager;
    o.querySelector('#cdc-v8-clean-form').onsubmit=async function(e){e.preventDefault();var fd=new FormData(e.target);await onSubmit(String(fd.get('task')||'').trim(),String(fd.get('area')||'').trim(),String(fd.get('frequency')||'Daily'));};
  }
  function addCleaningForm(){
    cleaningForm('Add cleaning task',{},async function(task,area,frequency){
      if(!task||!area)return status('Task and area are required.',true);
      try{status('Saving…',false);await mutateAndSave('manager add cleaning task',function(st,d){
        var sid=uid('clean_sched'), tid=uid('clean_task'), who=(d.user&&d.user.name)||'Manager', now=new Date().toISOString();
        st.cleaningSchedules=schedules(st).slice(); st.cleaningTasks=tasks(st).slice();
        st.cleaningSchedules.push({id:sid,area:area,task:task,active:true,method:'',createdAt:now,createdBy:who,frequency:frequency,assignedTo:'Kitchen team',source:'manager_created'});
        st.cleaningTasks.push({id:tid,area:area,task:task,freq:frequency.toLowerCase(),lastDone:null,by:'',source:'manager_created'});
      });status('Cleaning task added.',false);setTimeout(function(){location.reload();},250);}catch(e){status(e.message||e,true);}
    });
  }
  function editCleaningForm(i){
    var s=schedules(live&&live.state)[i]; if(!s)return;
    var oldArea=s.area||'', oldTask=s.task||'';
    cleaningForm('Edit cleaning task',s,async function(task,area,frequency){
      if(!task||!area)return status('Task and area are required.',true);
      try{status('Saving…',false);await mutateAndSave('manager edit cleaning task',function(st){
        var a=schedules(st), target=a.find(function(x){return String(x.id||'')===String(s.id||'');})||a[i];
        if(!target)throw new Error('Cleaning task no longer exists.');
        var ts=tasks(st), mt=ts.find(function(x){return String(x.area||'')===String(oldArea)&&String(x.task||'')===String(oldTask);});
        target.task=task;target.area=area;target.frequency=frequency;if('freq' in target)target.freq=frequency.toLowerCase();
        if(mt){mt.task=task;mt.area=area;mt.freq=frequency.toLowerCase();if('frequency' in mt)mt.frequency=frequency;}
      });status('Cleaning task updated.',false);setTimeout(function(){location.reload();},250);}catch(e){status(e.message||e,true);}
    });
  }
  async function removeCleaning(i){
    var s=schedules(live&&live.state)[i]; if(!s)return;
    if(!confirm('Remove “'+(s.task||'this cleaning task')+'” from the active schedule?\n\nHistoric completed records will remain.'))return;
    try{status('Removing…',false);await mutateAndSave('manager remove cleaning task',function(st){
      var a=schedules(st), old=a.find(function(x){return String(x.id||'')===String(s.id||'');})||a[i]; if(!old)return;
      st.cleaningSchedules=a.filter(function(x){return x!==old;});
      var ts=tasks(st); st.cleaningTasks=ts.filter(function(t){return !(String(t.area||'')===String(old.area||'')&&String(t.task||'')===String(old.task||''));});
    });status('Cleaning task removed.',false);setTimeout(function(){location.reload();},250);}catch(e){status(e.message||e,true);}
  }
  function renderChecksManager(){
    var a=checks(live&&live.state), html='<button type="button" class="cdc-v8-btn cdc-v8-add" id="cdc-v8-add-check">+ Add daily check</button><div class="cdc-v8-status">Changes save to the live venue. Historic completed records are kept.</div>';
    html+=a.length?a.map(function(c,i){var p=norm(c.period)==='close'?'Closing':'Opening';return '<div class="cdc-v8-row"><div><b>'+esc(c.name||'Check')+'</b><small>'+p+'</small></div><div class="cdc-v8-actions"><button class="cdc-v8-btn cdc-v8-edit" data-edit-check="'+i+'">Edit</button><button class="cdc-v8-btn cdc-v8-remove" data-remove-check="'+i+'">Remove</button></div></div>';}).join(''):'<p>No active daily checks.</p>';
    var o=sheet('Manage daily checks',html);
    o.querySelector('#cdc-v8-add-check').onclick=function(){checkForm('Add daily check',{period:currentPeriod()},addCheckSave);};
    o.querySelectorAll('[data-edit-check]').forEach(function(b){b.onclick=function(){editCheckForm(+b.dataset.editCheck);};});
    o.querySelectorAll('[data-remove-check]').forEach(function(b){b.onclick=function(){removeCheck(+b.dataset.removeCheck);};});
  }
  async function openChecks(){try{await getLive();renderChecksManager();}catch(e){alert(e.message||e);}}
  function checkForm(title,values,onSubmit){
    values=values||{}; var close=norm(values.period)==='close';
    var o=sheet(title,'<form class="cdc-v8-form" id="cdc-v8-check-form"><label>Check name<input name="name" required value="'+esc(values.name||'')+'"></label><label>When<select name="period"><option value="open" '+(!close?'selected':'')+'>Opening</option><option value="close" '+(close?'selected':'')+'>Closing</option></select></label><div class="cdc-v8-status"></div><div class="cdc-v8-form-actions"><button type="button" class="cdc-v8-btn" id="cdc-v8-cancel">Cancel</button><button class="cdc-v8-btn cdc-v8-save">Save</button></div></form>');
    o.querySelector('#cdc-v8-cancel').onclick=renderChecksManager;
    o.querySelector('#cdc-v8-check-form').onsubmit=async function(e){e.preventDefault();var fd=new FormData(e.target);await onSubmit(String(fd.get('name')||'').trim(),String(fd.get('period')||'open'));};
  }
  async function addCheckSave(name,period){
    if(!name)return status('Check name is required.',true);
    try{status('Saving…',false);await mutateAndSave('manager add daily check',function(st){st.checks=checks(st).slice();st.checks.push({id:uid('check'),name:name,period:period,source:'manager_created'});});status('Daily check added.',false);setTimeout(function(){location.reload();},250);}catch(e){status(e.message||e,true);}
  }
  function editCheckForm(i){
    var c=checks(live&&live.state)[i]; if(!c)return;
    checkForm('Edit daily check',c,async function(name,period){
      if(!name)return status('Check name is required.',true);
      try{status('Saving…',false);await mutateAndSave('manager edit daily check',function(st){var a=checks(st),t=a.find(function(x){return String(x.id||'')===String(c.id||'');})||a[i];if(!t)throw new Error('Daily check no longer exists.');t.name=name;t.period=period;});status('Daily check updated.',false);setTimeout(function(){location.reload();},250);}catch(e){status(e.message||e,true);}
    });
  }
  async function removeCheck(i){
    var c=checks(live&&live.state)[i]; if(!c)return;
    if(!confirm('Remove “'+(c.name||'this daily check')+'” from the active list?\n\nHistoric completed records will remain.'))return;
    try{status('Removing…',false);await mutateAndSave('manager remove daily check',function(st){var a=checks(st);st.checks=a.filter(function(x,idx){return c.id?String(x.id||'')!==String(c.id):idx!==i;});});status('Daily check removed.',false);setTimeout(function(){location.reload();},250);}catch(e){status(e.message||e,true);}
  }
  function place(){
    cleanupLegacy();ensureStyle();
    var old=document.getElementById('cdc-v8-bar'),kind=activeKind();
    if(!allowed||!kind){if(old)old.remove();return;}
    var h=visibleHeading(kind==='cleaning'?'Cleaning Schedule':'Daily Checks'); if(!h){if(old)old.remove();return;}
    var anchor=h.parentElement&&displayed(h.parentElement)?h.parentElement:h;
    if(old&&old.dataset.kind===kind&&old.previousElementSibling===anchor)return;
    if(old)old.remove();
    var bar=document.createElement('div');bar.id='cdc-v8-bar';bar.dataset.kind=kind;
    var b=document.createElement('button');b.type='button';b.textContent=kind==='cleaning'?'Manage cleaning tasks':'Manage daily checks';b.onclick=kind==='cleaning'?openCleaning:openChecks;
    bar.appendChild(b);anchor.insertAdjacentElement('afterend',bar);
  }
  async function checkRole(){
    if(checkedRole)return;checkedRole=true;
    try{var d=await getLive();var role=norm(d.user&&d.user.role);allowed=['manager','admin','administrator'].indexOf(role)>=0;}catch(e){allowed=false;}
    place();
  }
  function visibleCheckInput(){
    var ins=document.querySelectorAll('input');
    for(var i=0;i<ins.length;i++){var p=norm(ins[i].getAttribute('placeholder'));if(displayed(ins[i])&&p.indexOf('add a check')>=0)return ins[i];}
    return null;
  }
  async function interceptNativeAdd(e){
    if(!allowed||activeKind()!=='checks')return;
    var b=e.target.closest&&e.target.closest('button'); if(!b||norm(b.textContent)!=='add'||!displayed(b))return;
    var inp=visibleCheckInput(); if(!inp)return;
    e.preventDefault();e.stopPropagation();if(e.stopImmediatePropagation)e.stopImmediatePropagation();
    var name=String(inp.value||'').trim();if(!name){inp.focus();return;}
    b.disabled=true;
    try{await mutateAndSave('manager add daily check from Daily Checks screen',function(st){st.checks=checks(st).slice();st.checks.push({id:uid('check'),name:name,period:currentPeriod(),source:'manager_created'});});inp.value='';setTimeout(function(){location.reload();},180);}catch(err){alert(err.message||err);b.disabled=false;}
  }
  function start(){
    checkRole();place();
    document.addEventListener('click',interceptNativeAdd,true);
    new MutationObserver(function(){setTimeout(place,0);}).observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class','style','hidden']});
    setInterval(place,800);window.addEventListener('hashchange',place);window.addEventListener('popstate',place);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
