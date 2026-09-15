/* Self-service password change control for Command de Cuisine. */
(function(){
  'use strict';
  var ROUTE='__PASSWORD_ROUTE__', session=null, adding=false;
  function norm(s){return String(s||'').replace(/\s+/g,' ').trim().toLowerCase();}
  function visible(el){if(!el||!el.isConnected)return false;var c=el;while(c&&c.nodeType===1){var s=getComputedStyle(c);if(s.display==='none'||s.visibility==='hidden'||s.opacity==='0')return false;c=c.parentElement;}return el.getClientRects().length>0;}
  function esc(v){return String(v==null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
  async function getSession(){
    try{var r=await fetch('/api/session?cdc_pw='+Date.now(),{credentials:'same-origin',cache:'no-store',headers:{'Cache-Control':'no-cache'}});var d=await r.json();if(r.ok&&d.authenticated){session=d;return d;}}catch(e){}
    return null;
  }
  function ensureStyle(){
    if(document.getElementById('cdc-self-pw-style'))return;
    var s=document.createElement('style');s.id='cdc-self-pw-style';s.textContent=
      '.cdc-self-pw-btn{margin-left:8px;border:1px solid #4b5866;background:#29313a;color:#fff;border-radius:9px;padding:8px 10px;font-weight:800}'+
      '.cdc-self-pw-overlay{position:fixed;inset:0;z-index:2147483500;background:rgba(0,0,0,.76);display:flex;align-items:flex-end;justify-content:center;padding:10px}'+
      '.cdc-self-pw-sheet{width:min(520px,100%);background:#181d23;color:#f4f5f7;border:1px solid #35404b;border-radius:18px 18px 8px 8px;padding:16px;box-shadow:0 20px 60px rgba(0,0,0,.55)}'+
      '.cdc-self-pw-sheet h2{margin:0 0 12px}.cdc-self-pw-form{display:grid;gap:12px}.cdc-self-pw-form label{display:grid;gap:6px;font-weight:700}'+
      '.cdc-self-pw-form input{width:100%;padding:11px;border-radius:10px;border:1px solid #46515e;background:#0f1318;color:#fff;font:inherit}'+
      '.cdc-self-pw-actions{display:flex;justify-content:flex-end;gap:8px}.cdc-self-pw-actions button{border:1px solid #4b5866;background:#29313a;color:#fff;border-radius:10px;padding:9px 12px;font-weight:800}'+
      '.cdc-self-pw-actions .save{background:#e4ad37;color:#17191d;border-color:#e4ad37}.cdc-self-pw-status{font-size:.9rem;color:#9ca6b3;min-height:1.2em}.cdc-self-pw-status.bad{color:#ff8b8b}.cdc-self-pw-status.ok{color:#55c98b}';
    document.head.appendChild(s);
  }
  function close(){var x=document.getElementById('cdc-self-pw-overlay');if(x)x.remove();}
  function openDialog(){
    ensureStyle();close();
    var o=document.createElement('div');o.id='cdc-self-pw-overlay';o.className='cdc-self-pw-overlay';
    o.innerHTML='<div class="cdc-self-pw-sheet" role="dialog" aria-modal="true"><h2>Change password</h2><form class="cdc-self-pw-form" id="cdc-self-pw-form"><label>Current password<input type="password" name="current" autocomplete="current-password" required></label><label>New password<input type="password" name="next" autocomplete="new-password" minlength="10" required></label><label>Confirm new password<input type="password" name="confirm" autocomplete="new-password" minlength="10" required></label><div class="cdc-self-pw-status">Use at least 10 characters.</div><div class="cdc-self-pw-actions"><button type="button" id="cdc-self-pw-cancel">Cancel</button><button class="save" type="submit">Change password</button></div></form></div>';
    o.onclick=function(e){if(e.target===o)close();};document.body.appendChild(o);o.querySelector('#cdc-self-pw-cancel').onclick=close;
    o.querySelector('#cdc-self-pw-form').onsubmit=async function(e){
      e.preventDefault();var f=e.target,cur=f.current.value,nxt=f.next.value,con=f.confirm.value,st=o.querySelector('.cdc-self-pw-status'),btn=f.querySelector('.save');
      st.className='cdc-self-pw-status';
      if(nxt.length<10){st.textContent='New password must be at least 10 characters.';st.classList.add('bad');return;}
      if(nxt!==con){st.textContent='New passwords do not match.';st.classList.add('bad');return;}
      if(cur===nxt){st.textContent='Choose a different password.';st.classList.add('bad');return;}
      btn.disabled=true;st.textContent='Changing password…';
      try{var r=await fetch(ROUTE,{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json','Cache-Control':'no-cache'},body:JSON.stringify({currentPassword:cur,newPassword:nxt})});var d={};try{d=await r.json();}catch(_e){}if(!r.ok)throw new Error(d.error||'Could not change password.');st.textContent='Password changed.';st.classList.add('ok');f.reset();setTimeout(close,900);}catch(err){st.textContent=err.message||'Could not change password.';st.classList.add('bad');btn.disabled=false;}
    };
    setTimeout(function(){var i=o.querySelector('input');if(i)i.focus();},0);
  }
  function findOwnRow(){
    if(!session||!session.user)return null;var u=session.user, username=norm(u.username), name=norm(u.name), edits=[].slice.call(document.querySelectorAll('button')).filter(function(b){return visible(b)&&norm(b.textContent)==='edit';});
    for(var i=0;i<edits.length;i++){var n=edits[i];for(var j=0;j<6&&n;j++,n=n.parentElement){var t=norm(n.textContent);if((username&&t.indexOf(username)>=0)||(name&&t.indexOf(name)>=0))return {row:n,edit:edits[i]};}}
    return null;
  }
  function addButton(){
    if(adding||document.getElementById('cdc-self-pw-btn'))return;adding=true;
    Promise.resolve(session||getSession()).then(function(){
      if(!session||!session.user)return;var found=findOwnRow();if(!found)return;
      var b=document.createElement('button');b.type='button';b.id='cdc-self-pw-btn';b.className='cdc-self-pw-btn';b.textContent='Change password';b.onclick=function(e){e.preventDefault();e.stopPropagation();openDialog();};
      var p=found.edit.parentElement||found.row;p.appendChild(b);
    }).finally(function(){adding=false;});
  }
  getSession().then(function(d){session=d;addButton();});
  var obs=new MutationObserver(function(){setTimeout(addButton,40);});obs.observe(document.documentElement,{subtree:true,childList:true});
  window.openChangePassword=openDialog;
})();
