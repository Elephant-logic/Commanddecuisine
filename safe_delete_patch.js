/* ============================================================================
   safe_delete_patch.js  —  Command de Cuisine
   ----------------------------------------------------------------------------
   Makes deletion safe and consistent without rewriting the app's many existing
   inline delete handlers.

   1. CONFIRM  — real deletes require confirmation.
   2. UNDO     — for ~8 seconds, Undo restores ONLY the rows/links removed by
      that delete. It never rewinds the whole STATE object, so unrelated edits
      made after the delete are preserved.
   3. AUDIT    — removal of food-safety records is recorded as record_voided;
      undoing one is recorded as record_void_restored. The audit history itself
      is not erased by Undo.

   The patch intercepts the click, confirms, then re-fires the app's own handler.
   ========================================================================== */
(function () {
  'use strict';
  if (window.__cdcSafeDelete) return;
  window.__cdcSafeDelete = true;

  var CONFIG = {
    confirmOperational: true,
    confirmRecords: true,
    recordsManagerOnly: true,
    undoSeconds: 8
  };

  var RECORD_ROUTES = { temps:1, records:1, cooking:1, cleaning:1, checks:1, allergens:1, deliveries:1, fryer:1 };
  var RECORD_TITLES = /calibration|fitness|pest|cook|cool|temperature|corrective|haccp|cleaning|delivery check|allergen/i;

  function ready() {
    return typeof STATE !== 'undefined' && typeof rerender === 'function' &&
           typeof save === 'function' && typeof el === 'function';
  }
  function route() { try { return String(typeof ROUTE !== 'undefined' ? ROUTE : ''); } catch (e) { return ''; } }
  function mgr() { try { return typeof isMgr === 'function' ? !!isMgr() : true; } catch (e) { return true; } }
  function clone(o) { try { return structuredClone(o); } catch (e) { return JSON.parse(JSON.stringify(o)); } }
  function isObj(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }
  function sig(v) { try { return typeof v + ':' + JSON.stringify(v); } catch (e) { return typeof v + ':' + String(v); } }

  function deleteControl(elm) {
    var b = elm.closest && elm.closest('button');
    if (!b || b.__cdcBypassDeleteGuard) return null;
    if (b.classList.contains('rowdel')) return b;
    var txt = (b.textContent || '').trim().toLowerCase();
    if (b.classList.contains('danger') && /^(delete|remove)\b/.test(txt)) return b;
    if (b.classList.contains('x') && !b.closest('.modal') && !b.closest('.modal-body')) {
      if (!b.closest('.modal-head')) return b;
    }
    return null;
  }

  function labelFor(b) {
    var row = b.closest('tr') || b.closest('.docket') || b.closest('.card') || b.parentElement;
    if (!row) return 'this item';
    var t = '';
    var cell = row.querySelector('td:nth-child(2), .dk-t, b, span');
    if (cell) t = (cell.textContent || '').trim();
    if (!t) t = (row.textContent || '').trim();
    t = t.replace(/\s+/g, ' ').slice(0, 60);
    return t || 'this item';
  }

  function isRecord(b) {
    if (RECORD_ROUTES[route()]) return true;
    var card = b.closest('.card');
    var h = card && card.querySelector('h3');
    return !!(h && RECORD_TITLES.test(h.textContent || ''));
  }

  function buildUndoOps(before, after) {
    var ops = [];
    function walk(a, b, path) {
      if (Array.isArray(a) && Array.isArray(b)) {
        var afterById = {};
        b.forEach(function (item) {
          if (isObj(item) && item.id != null) afterById[String(item.id)] = item;
        });
        a.forEach(function (item, index) {
          if (!isObj(item) || item.id == null) return;
          var id = String(item.id), match = afterById[id];
          if (!match) ops.push({ type:'arrayInsert', path:path.slice(), index:index, value:clone(item), id:id });
          else walk(item, match, path.concat([{ id:id }]));
        });
        var counts = {};
        b.forEach(function (item) {
          if (isObj(item) && item.id != null) return;
          var k = sig(item); counts[k] = (counts[k] || 0) + 1;
        });
        a.forEach(function (item, index) {
          if (isObj(item) && item.id != null) return;
          var k = sig(item);
          if (counts[k]) counts[k]--;
          else ops.push({ type:'arrayInsert', path:path.slice(), index:index, value:clone(item), signature:k });
        });
        return;
      }
      if (isObj(a) && isObj(b)) {
        Object.keys(a).forEach(function (key) {
          if (!(key in b)) ops.push({ type:'setMissing', path:path.slice(), key:key, value:clone(a[key]) });
          else walk(a[key], b[key], path.concat([key]));
        });
      }
    }
    walk(before, after, []);
    return ops;
  }

  function resolvePath(root, path) {
    var cur = root;
    for (var i = 0; i < path.length; i++) {
      var seg = path[i];
      if (typeof seg === 'string') {
        if (cur == null) return null;
        cur = cur[seg];
      } else if (seg && seg.id != null) {
        if (!Array.isArray(cur)) return null;
        cur = cur.find(function (x) { return x && x.id != null && String(x.id) === String(seg.id); });
      }
      if (cur == null) return null;
    }
    return cur;
  }

  function applyUndoOps(ops) {
    ops.forEach(function (op) {
      if (op.type === 'arrayInsert') {
        var arr = resolvePath(STATE, op.path);
        if (!Array.isArray(arr)) return;
        var exists = false;
        if (op.id != null) exists = arr.some(function (x) { return x && x.id != null && String(x.id) === String(op.id); });
        else {
          var targetSig = op.signature || sig(op.value);
          exists = arr.some(function (x) { return sig(x) === targetSig; });
        }
        if (!exists) arr.splice(Math.max(0, Math.min(op.index, arr.length)), 0, clone(op.value));
      } else if (op.type === 'setMissing') {
        var parent = resolvePath(STATE, op.path);
        if (parent && typeof parent === 'object' && !(op.key in parent)) parent[op.key] = clone(op.value);
      }
    });
  }

  function showUndo(ops, what, record) {
    if (!ops || !ops.length) return;
    var old = document.getElementById('cdcUndoBar');
    if (old) old.remove();
    var bar = el('div', { id: 'cdcUndoBar' });
    bar.style.cssText = 'position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:4000;' +
      'display:flex;align-items:center;gap:14px;background:#1c1c1e;color:#fff;padding:11px 14px 11px 16px;' +
      'border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,.35);font-size:14px;max-width:calc(100vw - 32px)';
    var msg = el('span', {}, 'Deleted ' + what);
    var btn = el('button', { html: 'Undo' });
    btn.style.cssText = 'background:#f0c419;color:#1c1c1e;border:0;border-radius:8px;padding:7px 14px;font-weight:700;cursor:pointer';
    var timer = setTimeout(function () { bar.remove(); }, CONFIG.undoSeconds * 1000);
    btn.onclick = function () {
      clearTimeout(timer);
      try {
        applyUndoOps(ops);
        if (record && typeof audit === 'function') audit('record_void_restored', what);
        save(record ? 'undo record void' : 'undo delete');
        rerender();
        if (typeof toast === 'function') toast('Restored', 'ok');
      } catch (e) {
        if (typeof toast === 'function') toast('Could not undo', 'bad');
      }
      bar.remove();
    };
    bar.append(msg, btn);
    document.body.appendChild(bar);
  }

  function askConfirm(opts, onYes) {
    if (typeof modal !== 'function') {
      if (window.confirm(opts.message)) onYes('');
      return;
    }
    var body = el('div', {});
    body.innerHTML = '<p style="margin:0 0 10px;font-size:14px;line-height:1.5">' + opts.message.replace(/</g, '&lt;') + '</p>';
    var reasonInput = null;
    if (opts.reason) {
      reasonInput = el('input', { class: 'inp', placeholder: 'Reason (kept in the audit trail)' });
      body.append(reasonInput);
    }
    var confirmBtn = el('button', {
      class: 'btn danger', html: opts.confirmLabel || 'Delete',
      onclick: function () {
        var r = reasonInput ? (reasonInput.value || '').trim() : '';
        if (opts.reason && !r) { if (typeof toast === 'function') toast('Please give a reason', 'warn'); return; }
        m.close();
        onYes(r);
      }
    });
    confirmBtn.__cdcBypassDeleteGuard = true;
    var m = modal({
      title: opts.title,
      body: body,
      footer: [
        el('button', { class: 'btn ghost', html: 'Keep it', onclick: function () { m.close(); } }),
        confirmBtn
      ]
    });
  }

  document.addEventListener('click', function (ev) {
    if (!ready()) return;
    var b = deleteControl(ev.target);
    if (!b) return;
    if (b.__cdcConfirmed) { b.__cdcConfirmed = false; return; }
    var record = isRecord(b);
    var wantConfirm = record ? CONFIG.confirmRecords : CONFIG.confirmOperational;
    if (record && CONFIG.recordsManagerOnly && !mgr()) {
      ev.preventDefault(); ev.stopImmediatePropagation();
      if (typeof toast === 'function') toast('Only a manager can remove a safety record', 'warn');
      return;
    }
    if (!wantConfirm) return;
    ev.preventDefault();
    ev.stopImmediatePropagation();
    var what = labelFor(b);
    var snapshot = clone(STATE);
    askConfirm({
      title: record ? 'Void this record?' : 'Delete?',
      message: record
        ? 'Remove the record "' + what + '"? Food-safety records are normally kept for inspection. This will be logged in the audit trail.'
        : 'Delete "' + what + '"? You can undo this for a few seconds.',
      confirmLabel: record ? 'Void record' : 'Delete',
      reason: record
    }, function (reason) {
      b.__cdcConfirmed = true;
      try { b.click(); } catch (e) { b.__cdcConfirmed = false; return; }
      setTimeout(function () {
        var undoOps = [];
        try { undoOps = buildUndoOps(snapshot, STATE); } catch (e) {}
        if (record && typeof audit === 'function') {
          try { audit('record_voided', what + (reason ? ' — ' + reason : '')); save('audit void'); } catch (e) {}
        }
        showUndo(undoOps, record ? 'record' : (what.length > 24 ? 'item' : what), record);
      }, 30);
    });
  }, true);

  console.info('[Command de Cuisine] safe delete + targeted undo active');
})();
