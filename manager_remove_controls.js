/* Manager-only removal controls.
   Active staff/tasks can be removed while historic records and audit attribution remain. */
(function () {
  function boot(fn) {
    if (window.VIEWS && typeof window.state === 'object') fn();
    else setTimeout(function () { boot(fn); }, 80);
  }

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function currentUser() {
    try {
      if (typeof me !== 'undefined' && me) return me;
    } catch (e) {}
    return window.me || null;
  }

  function isManager() {
    var u = currentUser();
    return !!(u && u.role === 'manager');
  }

  function labelCleaning(item) {
    if (!item) return 'Cleaning task';
    var task = item.task || item.name || 'Cleaning task';
    var area = item.area || item.area_or_equipment || '';
    var freq = item.frequency || item.freq || '';
    return task + (area ? ' — ' + area : '') + (freq ? ' · ' + freq : '');
  }

  function findTaskForSchedule(s) {
    var tasks = Array.isArray(state.cleaningTasks) ? state.cleaningTasks : [];
    return tasks.find(function (t) {
      return t && String(t.area || '') === String(s.area || '') && String(t.task || '') === String(s.task || '');
    }) || null;
  }

  function cleaningRows() {
    var schedules = Array.isArray(state.cleaningSchedules) ? state.cleaningSchedules : [];
    var tasks = Array.isArray(state.cleaningTasks) ? state.cleaningTasks : [];
    var usedTaskIds = {};
    var rows = [];

    schedules.forEach(function (s) {
      var match = findTaskForSchedule(s);
      if (match && match.id != null) usedTaskIds[String(match.id)] = true;
      var sid = s && s.id != null ? String(s.id) : '';
      var tid = match && match.id != null ? String(match.id) : '';
      var label = labelCleaning(s);
      rows.push('<div class="row"><span class="tick done"></span><div><b>' + esc(s.task || 'Cleaning task') + '</b><br><small>' + esc((s.area || '') + (s.frequency ? ' · ' + s.frequency : '')) + '</small></div>' +
        '<div class="btn-row"><button class="btn sm ghost" onclick="removeCleaningSetup(' + JSON.stringify(sid) + ',' + JSON.stringify(tid) + ',' + JSON.stringify(label).replace(/</g,'\\u003c') + ')">Remove</button></div></div>');
    });

    tasks.forEach(function (t) {
      var id = t && t.id != null ? String(t.id) : '';
      if (id && usedTaskIds[id]) return;
      var label = labelCleaning(t);
      rows.push('<div class="row"><span class="tick done"></span><div><b>' + esc(t.task || t.name || 'Cleaning task') + '</b><br><small>' + esc((t.area || '') + (t.freq ? ' · ' + t.freq : '')) + '</small></div>' +
        '<div class="btn-row"><button class="btn sm ghost" onclick="removeCleaningSetup(\'\',' + JSON.stringify(id) + ',' + JSON.stringify(label).replace(/</g,'\\u003c') + ')">Remove</button></div></div>');
    });

    return rows.join('') || '<p class="muted">No removable cleaning tasks are configured.</p>';
  }

  function staffRows() {
    var users = Array.isArray(state.users) ? state.users : [];
    var u = currentUser();
    var current = u && u.username ? String(u.username).toLowerCase() : '';
    return users.map(function (person) {
      var username = String(person.username || '');
      var self = username.toLowerCase() === current;
      var role = person.role === 'manager' ? 'Manager' : 'Staff';
      var button = self
        ? '<span class="badge">Signed in</span>'
        : '<button class="btn sm ghost" onclick="removeStaffAccount(' + JSON.stringify(username) + ',' + JSON.stringify(person.name || username).replace(/</g,'\\u003c') + ')">Remove account</button>';
      return '<div class="row"><span class="tick ' + (person.active !== false ? 'done' : '') + '"></span><div><b>' + esc(person.name || username) + '</b><br><small>@' + esc(username) + ' · ' + role + (person.active === false ? ' · disabled' : '') + '</small></div><div class="btn-row">' + button + '</div></div>';
    }).join('') || '<p class="muted">No team members.</p>';
  }

  function panelHtml() {
    return '<div id="manager-remove-controls" class="grid cols-even" style="margin-top:18px">' +
      '<div class="card"><div class="card-head"><div><h2>Remove staff</h2><p class="muted">Removes the login account from this venue. Historic records and audit attribution are kept.</p></div></div><div class="rows" style="margin-top:10px">' + staffRows() + '</div></div>' +
      '<div class="card"><div class="card-head"><div><h2>Remove cleaning tasks</h2><p class="muted">Removes tasks from the active cleaning setup. Historic completion records are kept.</p></div></div><div class="rows" style="margin-top:10px">' + cleaningRows() + '</div></div>' +
      '</div>';
  }

  function ensurePanel() {
    if (!isManager()) return;
    var host = document.getElementById('settingsBody');
    if (!host) return;
    var old = document.getElementById('manager-remove-controls');
    if (old) old.remove();
    host.insertAdjacentHTML('afterend', panelHtml());
  }

  function findCleaningCard(signoffButton, schedule) {
    var taskText = String(schedule.task || '').trim().toLowerCase();
    var areaText = String(schedule.area || '').trim().toLowerCase();
    var node = signoffButton;
    for (var i = 0; i < 7 && node; i++, node = node.parentElement) {
      var text = String(node.innerText || node.textContent || '').toLowerCase();
      if ((!taskText || text.indexOf(taskText) >= 0) && (!areaText || text.indexOf(areaText) >= 0)) return node;
    }
    return null;
  }

  function makeRemoveButton(text) {
    var remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'btn sm ghost manager-remove-inline';
    remove.textContent = text || 'Remove';
    remove.style.borderColor = 'rgba(239,83,80,.65)';
    remove.style.color = 'var(--danger,#ef5350)';
    remove.style.padding = '7px 11px';
    remove.style.fontSize = '.82em';
    remove.style.whiteSpace = 'nowrap';
    return remove;
  }

  function ensureCleaningCardButtons() {
    if (!isManager()) return;
    var schedules = Array.isArray(state.cleaningSchedules) ? state.cleaningSchedules : [];
    if (!schedules.length) return;

    var signoffButtons = Array.prototype.filter.call(document.querySelectorAll('button'), function (b) {
      return /^sign\s*off$/i.test(String(b.textContent || '').trim());
    });
    if (!signoffButtons.length) return;

    schedules.forEach(function (s) {
      var sid = s && s.id != null ? String(s.id) : '';
      if (!sid || document.querySelector('[data-remove-cleaning-schedule="' + CSS.escape(sid) + '"]')) return;
      var task = findTaskForSchedule(s);
      var tid = task && task.id != null ? String(task.id) : '';
      var label = labelCleaning(s);

      for (var i = 0; i < signoffButtons.length; i++) {
        var signoff = signoffButtons[i];
        var card = findCleaningCard(signoff, s);
        if (!card) continue;
        var remove = makeRemoveButton('Remove');
        remove.dataset.removeCleaningSchedule = sid;
        remove.style.marginLeft = '6px';
        remove.onclick = function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          window.removeCleaningSetup(sid, tid, label);
        };
        signoff.insertAdjacentElement('afterend', remove);
        break;
      }
    });
  }

  function exactTextElement(label) {
    var wanted = String(label || '').replace(/\s+/g, ' ').trim().toLowerCase();
    if (!wanted) return null;
    var selectors = 'b,strong,h1,h2,h3,h4,h5,p,span,div';
    var nodes = document.querySelectorAll(selectors);
    var best = null;
    var bestLen = 999999;
    for (var i = 0; i < nodes.length; i++) {
      var text = String(nodes[i].textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
      if (text !== wanted) continue;
      var len = String(nodes[i].outerHTML || '').length;
      if (len < bestLen) { best = nodes[i]; bestLen = len; }
    }
    return best;
  }

  function findDailyCard(titleNode, label) {
    var wanted = String(label || '').toLowerCase();
    var node = titleNode;
    var candidate = titleNode && titleNode.parentElement;
    for (var i = 0; i < 7 && node; i++, node = node.parentElement) {
      var text = String(node.innerText || node.textContent || '').toLowerCase();
      if (text.indexOf(wanted) < 0) continue;
      if (node.classList && node.classList.contains('row')) return node;
      if (text.indexOf('done by') >= 0 || text.indexOf('not done') >= 0 || text.indexOf('pending') >= 0) candidate = node;
    }
    return candidate;
  }

  function ensureDailyCheckButtons() {
    if (!isManager()) return;
    var checks = Array.isArray(state.checks) ? state.checks : [];
    checks.forEach(function (check) {
      var id = check && check.id != null ? String(check.id) : '';
      var name = String(check && check.name || '').trim();
      if (!id || !name || document.querySelector('[data-remove-daily-check="' + CSS.escape(id) + '"]')) return;
      var title = exactTextElement(name);
      if (!title) return;
      var card = findDailyCard(title, name);
      if (!card) return;
      var remove = makeRemoveButton('Remove');
      remove.dataset.removeDailyCheck = id;
      remove.style.marginLeft = 'auto';
      remove.onclick = function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        window.removeDailyCheckDefinition(id, name);
      };
      card.appendChild(remove);
    });
  }

  window.removeStaffAccount = async function (username, displayName) {
    if (!isManager() || !username) return;
    var who = displayName || username;
    if (!window.confirm('Remove ' + who + ' from the team?\n\nTheir login will stop working. Historic records and audit entries will remain.')) return;
    try {
      var response = await fetch('/api/users/manage', {
        method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username: username, delete: true})
      });
      var data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Could not remove staff account');
      if (typeof toast === 'function') toast('Staff account removed', 'ok');
      window.location.reload();
    } catch (err) {
      if (typeof toast === 'function') toast(err.message || 'Could not remove staff account', 'bad');
      else window.alert(err.message || 'Could not remove staff account');
    }
  };

  window.removeCleaningSetup = async function (scheduleId, taskId, displayName) {
    if (!isManager()) return;
    var label = displayName || 'this cleaning task';
    if (!window.confirm('Remove ' + label + ' from the active cleaning setup?\n\nHistoric completion records will remain in the record history.')) return;
    var beforeSchedules = JSON.parse(JSON.stringify(Array.isArray(state.cleaningSchedules) ? state.cleaningSchedules : []));
    var beforeTasks = JSON.parse(JSON.stringify(Array.isArray(state.cleaningTasks) ? state.cleaningTasks : []));
    try {
      if (scheduleId) state.cleaningSchedules = beforeSchedules.filter(function (x) { return String(x && x.id != null ? x.id : '') !== String(scheduleId); });
      if (taskId) state.cleaningTasks = beforeTasks.filter(function (x) { return String(x && x.id != null ? x.id : '') !== String(taskId); });
      if (typeof save !== 'function') throw new Error('Save function is unavailable');
      var result = save();
      if (result && typeof result.then === 'function') await result;
      if (typeof toast === 'function') toast('Cleaning task removed', 'ok');
      setTimeout(function () { window.location.reload(); }, 500);
    } catch (err) {
      state.cleaningSchedules = beforeSchedules;
      state.cleaningTasks = beforeTasks;
      if (typeof toast === 'function') toast(err.message || 'Could not remove cleaning task', 'bad');
      else window.alert(err.message || 'Could not remove cleaning task');
    }
  };

  window.removeDailyCheckDefinition = async function (checkId, displayName) {
    if (!isManager()) return;
    var label = displayName || 'this daily check';
    if (!window.confirm('Remove ' + label + ' from the active Daily Checks list?\n\nHistoric completed daily-check records will remain in the record history.')) return;
    var before = JSON.parse(JSON.stringify(Array.isArray(state.checks) ? state.checks : []));
    try {
      state.checks = before.filter(function (x) { return String(x && x.id != null ? x.id : '') !== String(checkId); });
      if (typeof save !== 'function') throw new Error('Save function is unavailable');
      var result = save();
      if (result && typeof result.then === 'function') await result;
      if (typeof toast === 'function') toast('Daily check removed', 'ok');
      setTimeout(function () { window.location.reload(); }, 500);
    } catch (err) {
      state.checks = before;
      if (typeof toast === 'function') toast(err.message || 'Could not remove daily check', 'bad');
      else window.alert(err.message || 'Could not remove daily check');
    }
  };

  function ensureAllControls() {
    ensureCleaningCardButtons();
    ensureDailyCheckButtons();
    if (document.getElementById('settingsBody')) ensurePanel();
  }

  boot(function () {
    if (window.VIEWS && typeof VIEWS.settings === 'function') {
      var originalSettings = VIEWS.settings;
      VIEWS.settings = function () {
        originalSettings.apply(this, arguments);
        setTimeout(ensurePanel, 0);
      };
    }

    setTimeout(ensureAllControls, 0);
    var observer = new MutationObserver(function () { setTimeout(ensureAllControls, 0); });
    observer.observe(document.body, {childList:true, subtree:true});
  });
})();
