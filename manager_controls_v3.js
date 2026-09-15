/* Command de Cuisine — manager task management controls.
   Gives managers/admins an explicit Manage button on Cleaning Schedule and Daily Checks.
   Historic completion records are preserved because definitions are edited/removed by id,
   while completion/history collections are left untouched. */
(function () {
  'use strict';

  function appState() {
    try { if (typeof state !== 'undefined' && state && typeof state === 'object') return state; } catch (e) {}
    return (window.state && typeof window.state === 'object') ? window.state : null;
  }

  function currentUser() {
    try { if (typeof me !== 'undefined' && me) return me; } catch (e) {}
    return window.me || null;
  }

  function isManager() {
    var u = currentUser();
    var role = String(u && u.role || '').toLowerCase();
    return role === 'manager' || role === 'admin' || role === 'administrator';
  }

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function toastMsg(msg, kind) {
    if (typeof toast === 'function') toast(msg, kind || 'ok');
    else window.alert(msg);
  }

  async function persist(message) {
    if (typeof save !== 'function') throw new Error('Save function is unavailable');
    var r = save();
    if (r && typeof r.then === 'function') await r;
    if (message) toastMsg(message, 'ok');
  }

  function addStyles() {
    if (document.getElementById('cdc-manager-v3-css')) return;
    var s = document.createElement('style');
    s.id = 'cdc-manager-v3-css';
    s.textContent =
      '.cdc-manager-bar{display:flex;gap:10px;align-items:center;margin:12px 0 18px;flex-wrap:wrap}' +
      '.cdc-manager-bar .cdc-manage-btn{background:#d5a536;color:#17191d;border:1px solid rgba(255,255,255,.14);font-weight:800;border-radius:12px;padding:10px 14px;box-shadow:0 2px 0 rgba(0,0,0,.35)}' +
      '.cdc-manager-note{font-size:.82rem;opacity:.72}' +
      '.cdc-mgr-overlay{position:fixed;inset:0;z-index:2147483000;background:rgba(0,0,0,.72);display:flex;align-items:flex-end;justify-content:center;padding:12px}' +
      '.cdc-mgr-sheet{width:min(720px,100%);max-height:88vh;overflow:auto;background:#181c22;color:#f4f4f4;border:1px solid #343b46;border-radius:18px 18px 10px 10px;padding:18px;box-shadow:0 20px 60px rgba(0,0,0,.55)}' +
      '.cdc-mgr-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}.cdc-mgr-head h2{margin:0;font-size:1.25rem}' +
      '.cdc-close{background:transparent;color:#fff;border:1px solid #4b5360;border-radius:10px;padding:8px 11px;font-weight:700}' +
      '.cdc-mgr-row{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;border:1px solid #343b46;border-radius:13px;padding:12px;margin:9px 0;background:#20252d}' +
      '.cdc-mgr-row small{display:block;opacity:.7;margin-top:3px}.cdc-mgr-actions{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}' +
      '.cdc-edit,.cdc-remove,.cdc-save,.cdc-cancel{border-radius:10px;padding:8px 11px;font-weight:800;border:1px solid #4b5360;background:#282e38;color:#fff}' +
      '.cdc-remove{border-color:#8b3c3c;color:#ff8d8d}.cdc-save{background:#d5a536;color:#17191d;border-color:#d5a536}' +
      '.cdc-form{display:grid;gap:12px}.cdc-form label{display:grid;gap:6px;font-weight:700}.cdc-form input,.cdc-form select{width:100%;box-sizing:border-box;background:#101319;color:#fff;border:1px solid #454e5b;border-radius:10px;padding:11px;font:inherit}' +
      '.cdc-form-actions{display:flex;gap:9px;justify-content:flex-end;margin-top:4px}' +
      '@media(max-width:560px){.cdc-mgr-row{grid-template-columns:1fr}.cdc-mgr-actions{justify-content:flex-start}.cdc-manager-bar{margin-top:8px}.cdc-manager-bar .cdc-manage-btn{width:100%}}';
    document.head.appendChild(s);
  }

  function closeSheet() {
    var o = document.getElementById('cdc-manager-overlay');
    if (o) o.remove();
  }

  function openSheet(title, bodyHtml) {
    closeSheet();
    var overlay = document.createElement('div');
    overlay.id = 'cdc-manager-overlay';
    overlay.className = 'cdc-mgr-overlay';
    overlay.innerHTML = '<div class="cdc-mgr-sheet" role="dialog" aria-modal="true">' +
      '<div class="cdc-mgr-head"><h2>' + esc(title) + '</h2><button type="button" class="cdc-close">Close</button></div>' +
      '<div id="cdc-manager-body">' + bodyHtml + '</div></div>';
    overlay.addEventListener('click', function (ev) { if (ev.target === overlay) closeSheet(); });
    overlay.querySelector('.cdc-close').onclick = closeSheet;
    document.body.appendChild(overlay);
    return overlay;
  }

  function matchingTask(schedule) {
    var st = appState();
    var tasks = st && Array.isArray(st.cleaningTasks) ? st.cleaningTasks : [];
    return tasks.find(function (t) {
      return t && String(t.area || '') === String(schedule.area || '') && String(t.task || '') === String(schedule.task || '');
    }) || null;
  }

  function cleaningListHtml() {
    var st = appState();
    var schedules = st && Array.isArray(st.cleaningSchedules) ? st.cleaningSchedules : [];
    if (!schedules.length) return '<p>No active cleaning tasks are configured.</p>';
    return schedules.map(function (s) {
      var id = String(s.id || '');
      var freq = s.frequency || s.freq || '';
      return '<div class="cdc-mgr-row"><div><b>' + esc(s.task || 'Cleaning task') + '</b><small>' + esc((s.area || '') + (freq ? ' · ' + freq : '')) + '</small></div>' +
        '<div class="cdc-mgr-actions"><button class="cdc-edit" data-edit-clean="' + esc(id) + '">Edit</button><button class="cdc-remove" data-remove-clean="' + esc(id) + '">Remove</button></div></div>';
    }).join('');
  }

  function openCleaningManager() {
    var overlay = openSheet('Manage cleaning tasks', cleaningListHtml());
    Array.prototype.forEach.call(overlay.querySelectorAll('[data-edit-clean]'), function (b) {
      b.onclick = function () { editCleaning(b.getAttribute('data-edit-clean')); };
    });
    Array.prototype.forEach.call(overlay.querySelectorAll('[data-remove-clean]'), function (b) {
      b.onclick = function () { removeCleaning(b.getAttribute('data-remove-clean')); };
    });
  }

  function editCleaning(id) {
    var st = appState();
    var schedules = st && Array.isArray(st.cleaningSchedules) ? st.cleaningSchedules : [];
    var s = schedules.find(function (x) { return String(x && x.id || '') === String(id); });
    if (!s) return toastMsg('Cleaning task not found', 'bad');
    var freq = String(s.frequency || s.freq || 'Daily').toLowerCase();
    var body = '<form class="cdc-form" id="cdc-clean-edit">' +
      '<label>Task<input name="task" required value="' + esc(s.task || '') + '"></label>' +
      '<label>Area / equipment<input name="area" required value="' + esc(s.area || '') + '"></label>' +
      '<label>Frequency<select name="frequency"><option value="Daily"' + (freq === 'daily' ? ' selected' : '') + '>Daily</option><option value="Weekly"' + (freq === 'weekly' ? ' selected' : '') + '>Weekly</option><option value="Monthly"' + (freq === 'monthly' ? ' selected' : '') + '>Monthly</option></select></label>' +
      '<div class="cdc-form-actions"><button type="button" class="cdc-cancel">Cancel</button><button type="submit" class="cdc-save">Save changes</button></div></form>';
    var overlay = openSheet('Edit cleaning task', body);
    overlay.querySelector('.cdc-cancel').onclick = openCleaningManager;
    overlay.querySelector('#cdc-clean-edit').onsubmit = async function (ev) {
      ev.preventDefault();
      var fd = new FormData(ev.target);
      var taskName = String(fd.get('task') || '').trim();
      var area = String(fd.get('area') || '').trim();
      var frequency = String(fd.get('frequency') || 'Daily');
      if (!taskName || !area) return;
      var old = {task:s.task, area:s.area, frequency:s.frequency, freq:s.freq};
      var t = matchingTask(s);
      var oldTask = t ? {task:t.task, area:t.area, freq:t.freq, frequency:t.frequency} : null;
      try {
        s.task = taskName; s.area = area; s.frequency = frequency; if ('freq' in s) s.freq = frequency.toLowerCase();
        if (t) { t.task = taskName; t.area = area; t.freq = frequency.toLowerCase(); if ('frequency' in t) t.frequency = frequency; }
        await persist('Cleaning task updated');
        closeSheet();
        if (typeof render === 'function') render();
      } catch (err) {
        Object.assign(s, old); if (t && oldTask) Object.assign(t, oldTask);
        toastMsg(err.message || 'Could not update cleaning task', 'bad');
      }
    };
  }

  async function removeCleaning(id) {
    var st = appState();
    if (!st) return;
    var schedules = Array.isArray(st.cleaningSchedules) ? st.cleaningSchedules : [];
    var s = schedules.find(function (x) { return String(x && x.id || '') === String(id); });
    if (!s) return toastMsg('Cleaning task not found', 'bad');
    if (!window.confirm('Remove “' + (s.task || 'this cleaning task') + '” from the active cleaning schedule?\n\nHistoric completed records will stay in Reports/history.')) return;
    var beforeSchedules = JSON.parse(JSON.stringify(schedules));
    var beforeTasks = JSON.parse(JSON.stringify(Array.isArray(st.cleaningTasks) ? st.cleaningTasks : []));
    var t = matchingTask(s);
    try {
      st.cleaningSchedules = schedules.filter(function (x) { return String(x && x.id || '') !== String(id); });
      if (t && t.id != null) st.cleaningTasks = beforeTasks.filter(function (x) { return String(x && x.id || '') !== String(t.id); });
      await persist('Cleaning task removed');
      closeSheet();
      if (typeof render === 'function') render();
    } catch (err) {
      st.cleaningSchedules = beforeSchedules; st.cleaningTasks = beforeTasks;
      toastMsg(err.message || 'Could not remove cleaning task', 'bad');
    }
  }

  function dailyListHtml() {
    var st = appState();
    var checks = st && Array.isArray(st.checks) ? st.checks : [];
    if (!checks.length) return '<p>No active daily checks are configured.</p>';
    return checks.map(function (c) {
      var id = String(c.id || '');
      var period = String(c.period || '').toLowerCase() === 'close' ? 'Closing' : 'Opening';
      return '<div class="cdc-mgr-row"><div><b>' + esc(c.name || 'Check') + '</b><small>' + esc(period) + '</small></div>' +
        '<div class="cdc-mgr-actions"><button class="cdc-edit" data-edit-check="' + esc(id) + '">Edit</button><button class="cdc-remove" data-remove-check="' + esc(id) + '">Remove</button></div></div>';
    }).join('');
  }

  function openDailyManager() {
    var overlay = openSheet('Manage daily checks', dailyListHtml());
    Array.prototype.forEach.call(overlay.querySelectorAll('[data-edit-check]'), function (b) {
      b.onclick = function () { editDailyCheck(b.getAttribute('data-edit-check')); };
    });
    Array.prototype.forEach.call(overlay.querySelectorAll('[data-remove-check]'), function (b) {
      b.onclick = function () { removeDailyCheck(b.getAttribute('data-remove-check')); };
    });
  }

  function editDailyCheck(id) {
    var st = appState();
    var checks = st && Array.isArray(st.checks) ? st.checks : [];
    var c = checks.find(function (x) { return String(x && x.id || '') === String(id); });
    if (!c) return toastMsg('Daily check not found', 'bad');
    var close = String(c.period || '').toLowerCase() === 'close';
    var body = '<form class="cdc-form" id="cdc-check-edit">' +
      '<label>Check name<input name="name" required value="' + esc(c.name || '') + '"></label>' +
      '<label>When<select name="period"><option value="open"' + (!close ? ' selected' : '') + '>Opening</option><option value="close"' + (close ? ' selected' : '') + '>Closing</option></select></label>' +
      '<div class="cdc-form-actions"><button type="button" class="cdc-cancel">Cancel</button><button type="submit" class="cdc-save">Save changes</button></div></form>';
    var overlay = openSheet('Edit daily check', body);
    overlay.querySelector('.cdc-cancel').onclick = openDailyManager;
    overlay.querySelector('#cdc-check-edit').onsubmit = async function (ev) {
      ev.preventDefault();
      var fd = new FormData(ev.target);
      var name = String(fd.get('name') || '').trim();
      var period = String(fd.get('period') || 'open');
      if (!name) return;
      var old = {name:c.name, period:c.period};
      try {
        c.name = name; c.period = period;
        await persist('Daily check updated');
        closeSheet();
        if (typeof render === 'function') render();
      } catch (err) {
        Object.assign(c, old);
        toastMsg(err.message || 'Could not update daily check', 'bad');
      }
    };
  }

  async function removeDailyCheck(id) {
    var st = appState();
    if (!st) return;
    var checks = Array.isArray(st.checks) ? st.checks : [];
    var c = checks.find(function (x) { return String(x && x.id || '') === String(id); });
    if (!c) return toastMsg('Daily check not found', 'bad');
    if (!window.confirm('Remove “' + (c.name || 'this daily check') + '” from the active Daily Checks list?\n\nHistoric completed records will stay in Reports/history.')) return;
    var before = JSON.parse(JSON.stringify(checks));
    try {
      st.checks = checks.filter(function (x) { return String(x && x.id || '') !== String(id); });
      await persist('Daily check removed');
      closeSheet();
      if (typeof render === 'function') render();
    } catch (err) {
      st.checks = before;
      toastMsg(err.message || 'Could not remove daily check', 'bad');
    }
  }

  function exactHeading(text) {
    var wanted = String(text).toLowerCase();
    var nodes = document.querySelectorAll('h1,h2,h3,.page-title');
    for (var i=0; i<nodes.length; i++) {
      if (String(nodes[i].textContent || '').replace(/\s+/g,' ').trim().toLowerCase() === wanted) return nodes[i];
    }
    return null;
  }

  function insertBar(heading, id, label, handler) {
    if (!heading || document.getElementById(id)) return;
    var bar = document.createElement('div');
    bar.id = id; bar.className = 'cdc-manager-bar';
    bar.innerHTML = '<button type="button" class="cdc-manage-btn">' + esc(label) + '</button><span class="cdc-manager-note">Admin/manager controls</span>';
    bar.querySelector('button').onclick = handler;
    var anchor = heading.parentElement || heading;
    anchor.insertAdjacentElement('afterend', bar);
  }

  function ensureControls() {
    addStyles();
    if (!isManager() || !appState()) return;
    var cleanHead = exactHeading('Cleaning Schedule');
    if (cleanHead) insertBar(cleanHead, 'cdc-manage-cleaning', 'Manage cleaning tasks', openCleaningManager);
    var dailyHead = exactHeading('Daily Checks');
    if (dailyHead) insertBar(dailyHead, 'cdc-manage-daily', 'Manage daily checks', openDailyManager);
  }

  window.CDCManagerControls = {openCleaning:openCleaningManager, openDaily:openDailyManager};

  function start() {
    addStyles();
    ensureControls();
    var observer = new MutationObserver(function () { window.setTimeout(ensureControls, 0); });
    observer.observe(document.documentElement, {childList:true, subtree:true});
    window.setInterval(ensureControls, 1200);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
