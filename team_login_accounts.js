/* Command de Cuisine - Team login account provisioning */
(function () {
  'use strict';
  if (window.__cdcTeamLoginAccounts) return;
  window.__cdcTeamLoginAccounts = true;

  function boot(fn) {
    if (typeof VIEWS !== 'undefined' && VIEWS && typeof VIEWS.team === 'function' && typeof STATE !== 'undefined') fn();
    else setTimeout(function () { boot(fn); }, 80);
  }

  function escText(v) { return String(v == null ? '' : v); }
  function normRole(v) {
    var r = String(v || 'staff').toLowerCase();
    return (r === 'manager' || r === 'admin' || r === 'administrator') ? 'manager' : 'staff';
  }
  function isManager() {
    try { return typeof ME !== 'undefined' && ME && normRole(ME.role) === 'manager'; }
    catch (e) { return false; }
  }
  function selfUsername() {
    try { return String(ME && ME.username || '').toLowerCase(); }
    catch (e) { return ''; }
  }
  function cleanUsername(v) {
    return String(v || '').trim().toLowerCase().replace(/^@+/, '');
  }
  function validUsername(v) {
    return /^[a-z0-9._-]{3,40}$/.test(String(v || ''));
  }

  function ensureStyle() {
    if (document.getElementById('cdc-team-account-style')) return;
    var s = document.createElement('style');
    s.id = 'cdc-team-account-style';
    s.textContent =
      '.cdc-team-head{display:flex;align-items:center;gap:12px;margin-bottom:16px}.cdc-team-head h3{margin:0}.cdc-team-head .spacer{flex:1}' +
      '.cdc-team-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;padding:16px;border:1px solid var(--line);border-left:4px solid var(--gold);border-radius:14px;background:var(--bg2);margin-top:10px}' +
      '.cdc-team-person{display:flex;gap:12px;align-items:center;min-width:0}.cdc-team-avatar{width:48px;height:48px;border-radius:12px;background:var(--bg3);display:grid;place-items:center;color:var(--gold);font-size:21px;flex:0 0 auto}' +
      '.cdc-team-copy{min-width:0}.cdc-team-name{font-weight:800;font-size:18px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}.cdc-team-meta{color:var(--muted);margin-top:4px;line-height:1.35}.cdc-team-role{font-size:12px;letter-spacing:.06em;text-transform:uppercase;padding:4px 8px;border-radius:999px;background:rgba(228,173,55,.16);color:var(--gold);font-weight:900}' +
      '.cdc-team-actions{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}.cdc-team-actions button{white-space:nowrap}' +
      '.cdc-team-modal{position:fixed;inset:0;z-index:2147483400;background:rgba(0,0,0,.75);display:flex;align-items:flex-end;justify-content:center;padding:10px}.cdc-team-sheet{width:min(560px,100%);max-height:92vh;overflow:auto;background:var(--card,#1b2027);color:var(--text,#fff);border:1px solid var(--line,#35404b);border-radius:18px 18px 8px 8px;padding:16px;box-shadow:0 20px 60px rgba(0,0,0,.55)}' +
      '.cdc-team-sheet h2{margin:0 0 14px}.cdc-team-form{display:grid;gap:12px}.cdc-team-form label{display:grid;gap:6px;font-weight:700}.cdc-team-form input,.cdc-team-form select{width:100%;padding:11px;border-radius:10px;border:1px solid #46515e;background:#0f1318;color:#fff;font:inherit}.cdc-team-form .hint{color:var(--muted);font-size:13px}.cdc-team-form .status{min-height:1.2em;color:var(--muted);font-size:13px}.cdc-team-form .status.bad{color:var(--danger,#ff7777)}.cdc-team-actions-modal{display:flex;gap:8px;justify-content:flex-end;margin-top:4px}' +
      '@media(max-width:620px){.cdc-team-row{grid-template-columns:1fr}.cdc-team-actions{justify-content:flex-start}.cdc-team-actions .btn{flex:1 1 auto}.cdc-team-head{align-items:flex-start;flex-wrap:wrap}.cdc-team-head .spacer{display:none}.cdc-team-head .btn{margin-left:auto}}';
    document.head.appendChild(s);
  }

  async function request(path, body) {
    var r = await fetch(path, {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: {'Content-Type':'application/json','Cache-Control':'no-cache'},
      body: JSON.stringify(body || {})
    });
    var d = {};
    try { d = await r.json(); } catch (e) {}
    if (!r.ok) {
      var err = new Error(d.error || 'Request failed.');
      err.status = r.status; err.data = d;
      throw err;
    }
    return d;
  }

  async function refresh() {
    if (typeof refreshSharedState === 'function') {
      await refreshSharedState();
    }
    if (typeof rerender === 'function') rerender();
  }

  function notify(msg, kind) {
    if (typeof toast === 'function') toast(msg, kind || 'ok');
    else window.alert(msg);
  }

  function closeModal() {
    var old = document.getElementById('cdc-team-account-modal');
    if (old) old.remove();
  }

  function modal(title, build) {
    ensureStyle(); closeModal();
    var overlay = document.createElement('div');
    overlay.id = 'cdc-team-account-modal';
    overlay.className = 'cdc-team-modal';
    var sheet = document.createElement('div');
    sheet.className = 'cdc-team-sheet';
    var h = document.createElement('h2'); h.textContent = title;
    sheet.appendChild(h); overlay.appendChild(sheet); document.body.appendChild(overlay);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) closeModal(); });
    build(sheet, closeModal);
    return overlay;
  }

  function field(form, label, input) {
    var l = document.createElement('label');
    var t = document.createElement('span'); t.textContent = label;
    l.append(t, input); form.appendChild(l); return input;
  }
  function input(type, name, value, autocomplete) {
    var i = document.createElement('input');
    i.type = type || 'text'; i.name = name; i.value = value || '';
    if (autocomplete) i.autocomplete = autocomplete;
    return i;
  }
  function roleSelect(value) {
    var s = document.createElement('select'); s.name = 'role';
    [['staff','Staff'],['manager','Manager / Admin']].forEach(function (x) {
      var o = document.createElement('option'); o.value = x[0]; o.textContent = x[1];
      if (x[0] === normRole(value)) o.selected = true; s.appendChild(o);
    });
    return s;
  }
  function modalButtons(form, close, submitText) {
    var row = document.createElement('div'); row.className = 'cdc-team-actions-modal';
    var cancel = document.createElement('button'); cancel.type = 'button'; cancel.className = 'btn ghost'; cancel.textContent = 'Cancel'; cancel.onclick = close;
    var save = document.createElement('button'); save.type = 'submit'; save.className = 'btn primary'; save.textContent = submitText;
    row.append(cancel, save); form.appendChild(row); return save;
  }

  function addPerson() {
    modal('Add person & login', function (sheet, close) {
      var form = document.createElement('form'); form.className = 'cdc-team-form';
      var name = field(form, 'Name', input('text','name','', 'name')); name.required = true;
      var username = field(form, 'Username', input('text','username','', 'username')); username.required = true; username.autocapitalize = 'none'; username.spellcheck = false;
      var userHint = document.createElement('div'); userHint.className = 'hint'; userHint.textContent = 'Username: 3–40 letters/numbers, dot, dash or underscore. You can type @ at the start — it will be removed automatically.'; form.appendChild(userHint);
      var job = field(form, 'Job title', input('text','jobTitle','', 'organization-title'));
      var role = roleSelect('staff'); field(form, 'Access level', role);
      var pw = field(form, 'Temporary password', input('password','password','', 'new-password')); pw.required = true; pw.minLength = 10;
      var confirm = field(form, 'Confirm temporary password', input('password','confirm','', 'new-password')); confirm.required = true; confirm.minLength = 10;
      var hint = document.createElement('div'); hint.className = 'hint'; hint.textContent = 'Password: any characters are allowed; it just needs to be at least 10 characters. Give it to the new staff member with their username.'; form.appendChild(hint);
      var status = document.createElement('div'); status.className = 'status'; form.appendChild(status);
      var save = modalButtons(form, close, 'Create person & login');
      form.onsubmit = async function (e) {
        e.preventDefault(); status.className = 'status';
        var n = name.value.trim(), u = cleanUsername(username.value), p = pw.value;
        username.value = u;
        if (!n || !u) { status.textContent = 'Name and username are required.'; status.classList.add('bad'); return; }
        if (!validUsername(u)) { status.textContent = 'The username is the problem — not the password. Use 3–40 letters/numbers plus dot, dash or underscore, with no spaces.'; status.classList.add('bad'); username.focus(); return; }
        if (p.length < 10) { status.textContent = 'Password is too short. It can use any characters, but must be at least 10 characters.'; status.classList.add('bad'); return; }
        if (p !== confirm.value) { status.textContent = 'Passwords do not match.'; status.classList.add('bad'); return; }
        save.disabled = true; status.textContent = 'Creating login…';
        try {
          await request('/api/users/create', {name:n, username:u, jobTitle:job.value.trim(), role:role.value, password:p});
          close(); await refresh(); notify('Person added — they can now sign in as @' + u, 'ok');
        } catch (err) {
          var msg = err.message || 'Could not create login.';
          if (/Username must be 3/i.test(msg)) msg = 'The username is the problem — not the password. Use 3–40 letters/numbers plus dot, dash or underscore, with no spaces.';
          status.textContent = msg; status.classList.add('bad'); save.disabled = false;
        }
      };
      sheet.appendChild(form); setTimeout(function(){name.focus();},0);
    });
  }

  function setPassword(user) {
    modal('Set login password', function (sheet, close) {
      var form = document.createElement('form'); form.className = 'cdc-team-form';
      var intro = document.createElement('div'); intro.className = 'hint'; intro.textContent = 'Set a temporary password for ' + (user.name || user.username) + ' (@' + user.username + '). This also repairs an older Team profile that does not yet have a login account.'; form.appendChild(intro);
      var pw = field(form, 'Temporary password', input('password','password','', 'new-password')); pw.required = true; pw.minLength = 10;
      var confirm = field(form, 'Confirm temporary password', input('password','confirm','', 'new-password')); confirm.required = true; confirm.minLength = 10;
      var status = document.createElement('div'); status.className = 'status'; form.appendChild(status);
      var save = modalButtons(form, close, 'Set password');
      form.onsubmit = async function (e) {
        e.preventDefault(); status.className = 'status';
        if (pw.value.length < 10) { status.textContent = 'Temporary password must be at least 10 characters.'; status.classList.add('bad'); return; }
        if (pw.value !== confirm.value) { status.textContent = 'Passwords do not match.'; status.classList.add('bad'); return; }
        save.disabled = true; status.textContent = 'Setting login password…';
        try {
          await request('/api/users/manage', {username:user.username, newPassword:pw.value});
          close(); await refresh(); notify('Login password set for @' + user.username, 'ok');
        } catch (err) {
          status.textContent = err.message || 'Could not set password.'; status.classList.add('bad'); save.disabled = false;
        }
      };
      sheet.appendChild(form); setTimeout(function(){pw.focus();},0);
    });
  }

  function editPerson(user) {
    modal('Edit person', function (sheet, close) {
      var form = document.createElement('form'); form.className = 'cdc-team-form';
      var name = field(form, 'Name', input('text','name',user.name || '', 'name')); name.required = true;
      var username = field(form, 'Username', input('text','username',user.username || '', 'username')); username.disabled = true;
      var job = field(form, 'Job title', input('text','jobTitle',user.jobTitle || '', 'organization-title'));
      var role = roleSelect(user.role); field(form, 'Access level', role);
      var status = document.createElement('div'); status.className = 'status'; form.appendChild(status);
      var save = modalButtons(form, close, 'Save');
      form.onsubmit = async function (e) {
        e.preventDefault(); save.disabled = true; status.textContent = 'Saving…'; status.className = 'status';
        try {
          await request('/api/users/manage', {username:user.username, name:name.value.trim(), jobTitle:job.value.trim(), role:role.value});
          close(); await refresh(); notify('Person updated', 'ok');
        } catch (err) {
          status.textContent = err.message || 'Could not update person.'; status.classList.add('bad'); save.disabled = false;
        }
      };
      sheet.appendChild(form);
    });
  }

  async function deletePerson(user) {
    if (!user || !user.username) return;
    var label = user.name || user.username;
    if (!window.confirm('Delete ' + label + ' from this venue?\n\nThey will no longer be able to sign in. Historic kitchen records and audit entries will stay in place.')) return;
    try {
      await request('/api/users/manage', {username:user.username, delete:true});
      await refresh();
      notify(label + ' deleted from Team', 'ok');
    } catch (err) {
      notify(err.message || 'Could not delete this person.', 'bad');
    }
  }

  function button(label, cls, fn) {
    var b = document.createElement('button'); b.type = 'button'; b.className = cls || 'btn ghost'; b.textContent = label; b.onclick = fn; return b;
  }

  function renderTeam(v) {
    ensureStyle();
    v.innerHTML = '';
    var card = document.createElement('div'); card.className = 'card';
    var head = document.createElement('div'); head.className = 'cdc-team-head';
    var title = document.createElement('h3'); title.textContent = 'TEAM';
    var spacer = document.createElement('div'); spacer.className = 'spacer';
    head.append(title, spacer);
    if (isManager()) head.appendChild(button('+  Add person', 'btn primary', addPerson));
    card.appendChild(head);

    var users = (STATE && Array.isArray(STATE.users) ? STATE.users : []).slice();
    users.forEach(function (user) {
      if (!user || !user.username) return;
      var row = document.createElement('div'); row.className = 'cdc-team-row';
      var person = document.createElement('div'); person.className = 'cdc-team-person';
      var avatar = document.createElement('div'); avatar.className = 'cdc-team-avatar'; avatar.textContent = (user.name || user.username || '?').trim().charAt(0).toUpperCase();
      var copy = document.createElement('div'); copy.className = 'cdc-team-copy';
      var nameLine = document.createElement('div'); nameLine.className = 'cdc-team-name';
      var n = document.createElement('span'); n.textContent = user.name || user.username; nameLine.appendChild(n);
      if (normRole(user.role) === 'manager') { var badge = document.createElement('span'); badge.className = 'cdc-team-role'; badge.textContent = 'MANAGER'; nameLine.appendChild(badge); }
      var meta = document.createElement('div'); meta.className = 'cdc-team-meta'; meta.textContent = '@' + user.username + (user.jobTitle ? ' · ' + user.jobTitle : '') + (user.active === false ? ' · Disabled' : '');
      copy.append(nameLine, meta); person.append(avatar, copy);
      var actions = document.createElement('div'); actions.className = 'cdc-team-actions';
      if (isManager()) {
        actions.appendChild(button('Edit', 'btn ghost', function(){ editPerson(user); }));
        if (String(user.username).toLowerCase() !== selfUsername()) {
          actions.appendChild(button('Set / reset password', 'btn ghost', function(){ setPassword(user); }));
          actions.appendChild(button('Delete', 'btn danger', function(){ deletePerson(user); }));
        }
      }
      row.append(person, actions); card.appendChild(row);
    });
    if (!users.length) {
      var empty = document.createElement('div'); empty.className = 'empty'; empty.textContent = 'No team members yet.'; card.appendChild(empty);
    }
    v.appendChild(card);
  }

  boot(function () {
    VIEWS.team = renderTeam;
    if (typeof rerender === 'function') rerender();
    console.info('[Command de Cuisine] Team login provisioning active: delete + clear username/password validation');
  });
})();