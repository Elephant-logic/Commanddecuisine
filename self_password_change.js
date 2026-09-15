/* Self-service account controls for Command de Cuisine. */
(function(){
  'use strict';
  var PASSWORD_ROUTE='__PASSWORD_ROUTE__', LOGOUT_ROUTE='__LOGOUT_ROUTE__', session=null, adding=false, loggingOut=false;
  function norm(s){return String(s||'').replace(/\s+/g,' ').trim().toLowerCase();}
  function visible(el){if(!el||!el.isConnected)return false;var c=el;while(c&&c.nodeType===1){var s=getComputedStyle(c);if(s.display==='none'||s.visibility==='hidden'||s.opacity==='0')return false;c=c.parentElement;}return el.getClientRects().length>0;}
  async function getSession(){
    try{var r=await fetch('/api/session?cdc_account='+Date.now(),{credentials:'same-origin',cache:'no-store',headers:{'Cache-Control':'no-cache'}});var d=await r.json();if(r.ok&&d.authenticated){session=d;return d;}}catch(e){}
    return null;
  }
  async function isAuthenticated(){
    try{var r=await fetch('/api/session?cdc_logout_check='+Date.now(),{credentials:'same-origin',cache:'no-store',headers:{'Cache-Control':'no-cache'}});var d=await r.json();return !!(r.ok&&d&&d.authenticated);}catch(e){return true;}
  }
  function ensureStyle(){
    if(document.getElementById('cdc-self-account-style'))return;
    var s=document.createElement('style');s.id='cdc-self-account-style';s.textContent=
      '.cdc-self-account-btn{margin-left:8px;border:1px solid #4b5866;background:#29313a;color:#fff;border-radius:9px;padding:8px 10px;font-weight:800}'+
      '.cdc-self-logout-btn{color:#ff9b9b;border-color:#814646}'+
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
      try{var r=await fetch(PASSWORD_ROUTE,{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json','Cache-Control':'no-cache'},body:JSON.stringify({currentPassword:cur,newPassword:nxt})});var d={};try{d=await r.json();}catch(_e){}if(!r.ok)throw new Error(d.error||'Could not change password.');st.textContent='Password changed.';st.classList.add('ok');f.reset();setTimeout(close,900);}catch(err){st.textContent=err.message||'Could not change password.';st.classList.add('bad');btn.disabled=false;}
    };
    setTimeout(function(){var i=o.querySelector('input');if(i)i.focus();},0);
  }
  async function performLogout(btn){
    if(loggingOut)return;loggingOut=true;if(btn){btn.disabled=true;btn.textContent='Logging out…';}
    try{
      var globals=['logout','logOut','signOut','doLogout'];
      for(var g=0;g<globals.length;g++){
        var fn=window[globals[g]];
        if(typeof fn==='function'&&fn!==performLogout){
          try{var out=fn();if(out&&typeof out.then==='function')await out;}catch(e){}
          await new Promise(function(r){setTimeout(r,250);});
          if(!(await isAuthenticated())){location.replace('/');return;}
        }
      }
      var routes=[];
      [LOGOUT_ROUTE,'/api/logout','/api/auth/logout','/api/signout','/api/sign-out'].forEach(function(x){if(x&&x.indexOf('__')!==0&&routes.indexOf(x)<0)routes.push(x);});
      for(var i=0;i<routes.length;i++){
        for(var m=0;m<2;m++){
          try{await fetch(routes[i],{method:m===0?'POST':'GET',credentials:'same-origin',cache:'no-store',headers:{'Cache-Control':'no-cache','Content-Type':'application/json'},body:m===0?'{}':undefined});}catch(e){}
          if(!(await isAuthenticated())){location.replace('/');return;}
        }
      }
      throw new Error('Could not log out.');
    }catch(err){alert(err.message||'Could not log out.');if(btn){btn.disabled=false;btn.textContent='Log out';}loggingOut=false;}
  }
  function findOwnRow(){
    if(!session||!session.user)return null;var u=session.user, username=norm(u.username), name=norm(u.name), edits=[].slice.call(document.querySelectorAll('button')).filter(function(b){return visible(b)&&norm(b.textContent)==='edit';});
    for(var i=0;i<edits.length;i++){var n=edits[i];for(var j=0;j<6&&n;j++,n=n.parentElement){var t=norm(n.textContent);if((username&&t.indexOf(username)>=0)||(name&&t.indexOf(name)>=0))return {row:n,edit:edits[i]};}}
    return null;
  }
  function addButtons(){
    if(adding)return;adding=true;
    Promise.resolve(session||getSession()).then(function(){
      if(!session||!session.user)return;var found=findOwnRow();if(!found)return;ensureStyle();var p=found.edit.parentElement||found.row;
      if(!document.getElementById('cdc-self-pw-btn')){var pw=document.createElement('button');pw.type='button';pw.id='cdc-self-pw-btn';pw.className='cdc-self-account-btn';pw.textContent='Change password';pw.onclick=function(e){e.preventDefault();e.stopPropagation();openDialog();};p.appendChild(pw);}
      if(!document.getElementById('cdc-self-logout-btn')){var lo=document.createElement('button');lo.type='button';lo.id='cdc-self-logout-btn';lo.className='cdc-self-account-btn cdc-self-logout-btn';lo.textContent='Log out';lo.onclick=function(e){e.preventDefault();e.stopPropagation();performLogout(lo);};p.appendChild(lo);}
    }).finally(function(){adding=false;});
  }
  getSession().then(function(d){session=d;addButtons();});
  var obs=new MutationObserver(function(){setTimeout(addButtons,40);});obs.observe(document.documentElement,{subtree:true,childList:true});
  window.openChangePassword=openDialog;
  window.cdcLogout=function(){return performLogout(document.getElementById('cdc-self-logout-btn'));};
})();
