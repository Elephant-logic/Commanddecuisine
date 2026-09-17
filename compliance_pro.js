/* ============================================================================
   compliance_pro.js  —  Command de Cuisine
   ----------------------------------------------------------------------------
   Sharpens the compliance edges that matter for a real EHO inspection.

     1. OPEN-BREACH REGISTER — a temperature breach isn't "closed" until a
        corrective action is recorded. This surfaces every unit currently in
        breach with no corrective action logged after it, on the Reports page,
        with a one-tap "Record action" button. Nothing slips through.
     2. OVERDUE FLAGS — probe calibration older than 30 days (or never done),
        and expired staff training, are shown in the same "Action needed" card.
     3. INSPECTION PACK v2 — pick the date range (7 / 14 / 28 / 90 days),
        includes a "Deletions & voids" section (so removed records are still
        transparent to an inspector) and a signed declaration block.

   Additive: overrides window.inspectionPack and wraps VIEWS.reports. No-ops if
   the base app isn't loaded.
   ========================================================================== */
(function () {
  'use strict';
  if (window.__cdcCompliancePro) return;
  window.__cdcCompliancePro = true;

  function ready() { return typeof STATE !== 'undefined' && typeof VIEWS !== 'undefined' && typeof el === 'function'; }
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };

  function openBreaches() {
    var res = [];
    var actions = (STATE.paperwork || []).filter(function (p) { return p && p.type === 'Corrective action'; });
    var norm = function (v) { return String(v == null ? '' : v).toLowerCase().trim().replace(/\s+/g, ' '); };
    var stamp = function (v) { var n = new Date(v).getTime(); return isFinite(n) ? n : 0; };

    function actionCoversApp(p, a) {
      if (!p || !a) return false;
      if (p.appId != null && String(p.appId) === String(a.id)) return true;
      if (Array.isArray(p.appIds) && p.appIds.some(function (id) { return String(id) === String(a.id); })) return true;
      var target = norm(a.name);
      if (!target) return false;
      return String(p.units || '').split(',').some(function (name) { return norm(name) === target; });
    }

    (STATE.appliances || []).forEach(function (a) {
      if (!a || typeof tempStatus !== 'function') return;
      var breaches = (STATE.tempReadings || []).filter(function (r) {
        return r && String(r.appId) === String(a.id) && tempStatus(a, r.value) === 'danger';
      }).sort(function (x, y) { return stamp(y.ts) - stamp(x.ts); });

      var unresolved = breaches.find(function (r) {
        var rt = stamp(r.ts);
        return !actions.some(function (p) { return actionCoversApp(p, a) && stamp(p.ts) >= rt; });
      });
      if (unresolved) res.push({ app: a, reading: unresolved });
    });
    return res;
  }

  function calibrationOverdue() {
    var last = (STATE.calibrations || []).slice().sort(function (a, b) { return String(b.ts).localeCompare(String(a.ts)); })[0];
    if (!last) return { overdue: true, last: null };
    var days = (Date.now() - new Date(last.ts).getTime()) / 864e5;
    return { overdue: days > 30, last: last.ts, days: Math.round(days) };
  }

  function expiredTraining() {
    var today = new Date().toISOString().slice(0, 10);
    return (STATE.training || []).filter(function (t) { return t.expiry && t.expiry < today; });
  }

  function actionCard() {
    var breaches = openBreaches(), cal = calibrationOverdue(), exp = expiredTraining();
    if (!breaches.length && !cal.overdue && !exp.length) return null;
    var card = el('div', { class: 'card', style: 'margin-bottom:16px;border:1px solid var(--danger)' });
    card.append(el('div', { class: 'card-head' },
      el('h3', { html: (typeof icon === 'function' ? icon('alert') : '') + 'Action needed' }),
      el('div', { class: 'spacer' }),
      el('span', { class: 'chip mono' }, String(breaches.length + (cal.overdue ? 1 : 0) + exp.length))));

    breaches.forEach(function (b) {
      var row = el('div', { class: 'docket over', style: 'margin-bottom:6px' });
      row.innerHTML = '<div class="dk-ic" style="color:var(--danger)">' + (typeof icon === 'function' ? icon('alert') : '') + '</div>' +
        '<div style="flex:1"><div class="dk-t">' + esc(b.app.name) + ' — <span class="mono">' + b.reading.value + '°C</span> · breach with no corrective action</div>' +
        '<div class="dk-s">' + (typeof fmtDate === 'function' ? fmtDate(b.reading.ts) + ' ' + fmtTime(b.reading.ts) : '') + '</div></div>';
      row.append(el('button', {
        class: 'btn primary sm', html: 'Record action',
        onclick: function () { if (typeof breachModal === 'function') breachModal([b.app]); }
      }));
      card.append(row);
    });

    if (cal.overdue) {
      card.append(el('div', {
        class: 'docket due', style: 'margin-bottom:6px',
        html: '<div class="dk-ic" style="color:var(--warn)">' + (typeof icon === 'function' ? icon('alert') : '') + '</div>' +
          '<div><div class="dk-t">Probe calibration ' + (cal.last ? 'overdue (' + cal.days + ' days)' : 'never recorded') + '</div>' +
          '<div class="dk-s">Calibrate against iced water (0°C) and boiling water (100°C) in Safety records.</div></div>'
      }));
    }

    exp.forEach(function (t) {
      card.append(el('div', {
        class: 'docket due', style: 'margin-bottom:6px',
        html: '<div class="dk-ic" style="color:var(--warn)">' + (typeof icon === 'function' ? icon('cap') : '') + '</div>' +
          '<div><div class="dk-t">' + esc(t.name) + ' — ' + esc(t.course) + ' expired</div>' +
          '<div class="dk-s">Expired ' + (typeof fmtDate === 'function' ? fmtDate(t.expiry) : esc(t.expiry)) + '</div></div>'
      }));
    });
    return card;
  }

  function wrapReports() {
    if (window.__cdcReportsWrapped || typeof VIEWS.reports !== 'function') return;
    window.__cdcReportsWrapped = true;
    var orig = VIEWS.reports;
    VIEWS.reports = function (v) { orig(v); try { var c = actionCard(); if (c) v.prepend(c); } catch (e) {} };
  }

  function generatePack(days) {
    var S = STATE, since = Date.now() - days * 864e5;
    var appById = function (id) { return (S.appliances || []).find(function (a) { return a.id === id; }); };
    var st = function (a, v) { return (typeof tempStatus === 'function') ? tempStatus(a, v) : 'none'; };
    var d = function (ts) { return typeof fmtDate === 'function' ? fmtDate(ts) : String(ts).slice(0, 10); };
    var tm = function (ts) { return typeof fmtTime === 'function' ? fmtTime(ts) : ''; };
    var inRange = function (ts) { return new Date(ts).getTime() >= since; };
    var ALL = (typeof ALLERGENS !== 'undefined') ? ALLERGENS : [];
    var rHas = (typeof recipeHas === 'function') ? recipeHas : function () { return false; };

    var reads = (S.tempReadings || []).filter(function (r) { return inRange(r.ts); }).sort(function (a, b) { return a.ts.localeCompare(b.ts); });
    var breachN = reads.filter(function (r) { var a = appById(r.appId); return a && st(a, r.value) === 'danger'; }).length;
    var rows = reads.map(function (r) { var a = appById(r.appId); var s = a ? st(a, r.value) : 'none';
      return '<tr><td>' + d(r.ts) + ' ' + tm(r.ts) + '</td><td>' + esc(a && a.name) + '</td><td style="text-align:right">' + r.value + '°C</td><td>' + (s === 'danger' ? "<b style='color:#b3261e'>BREACH</b>" : s === 'warn' ? 'High' : 'OK') + '</td><td>' + esc(r.by) + '</td></tr>'; }).join('');
    var cor = (S.paperwork || []).filter(function (p) { return p.type === 'Corrective action' && inRange(p.ts); }).map(function (p) {
      return '<tr><td>' + d(p.ts) + '</td><td>' + esc(p.units) + '</td><td>' + esc(p.note) + '</td><td>' + esc(p.by || '') + '</td></tr>'; }).join('');
    var cook = (S.cookLogs || []).filter(function (c) { return inRange(c.ts); }).map(function (c) { var ok = c.kind === 'hothold' ? c.temp >= 63 : c.temp >= 75;
      return '<tr><td>' + d(c.ts) + ' ' + tm(c.ts) + '</td><td>' + esc(c.dish) + '</td><td>' + esc(c.kind) + '</td><td style="text-align:right">' + c.temp + '°C</td><td>' + (ok ? 'OK' : "<b style='color:#b3261e'>FAIL</b>") + '</td><td>' + esc(c.by) + '</td></tr>'; }).join('');
    var cool = (S.coolingLogs || []).filter(function (c) { return inRange(c.ts); }).map(function (c) { var ok = c.endTemp <= 8 && c.minutes <= 90;
      return '<tr><td>' + d(c.ts) + '</td><td>' + esc(c.item) + '</td><td>' + (c.startTemp == null ? '—' : c.startTemp) + '° → ' + c.endTemp + '°</td><td>' + c.minutes + ' min</td><td>' + (ok ? 'OK' : 'REVIEW') + '</td></tr>'; }).join('');
    var cal = (S.calibrations || []).filter(function (c) { return inRange(c.ts); }).map(function (c) { var ok = (c.ice == null || Math.abs(c.ice) <= 1) && (c.boil == null || Math.abs(c.boil - 100) <= 1);
      return '<tr><td>' + d(c.ts) + '</td><td>' + (c.ice == null ? '—' : c.ice) + '°</td><td>' + (c.boil == null ? '—' : c.boil) + '°</td><td>' + (ok ? 'In tolerance' : 'Adjusted') + '</td><td>' + esc(c.by) + '</td></tr>'; }).join('');
    var clean = (S.cleaningTasks || []).map(function (t) { return '<tr><td>' + esc(t.task) + '</td><td>' + esc(t.area) + '</td><td>' + esc(t.freq) + '</td><td>' + (t.lastDone ? d(t.lastDone) : '—') + '</td><td>' + esc(t.by) + '</td></tr>'; }).join('');
    var amx = (S.recipes || []).map(function (r) { return '<tr><td>' + esc(r.name) + '</td>' + ALL.map(function (a) { return '<td style="text-align:center">' + (rHas(r, a) ? '●' : '') + '</td>'; }).join('') + '</tr>'; }).join('');
    var fit = (S.fitness || []).filter(function (f) { return inRange(f.ts); }).map(function (f) { return '<tr><td>' + d(f.ts) + '</td><td>' + esc(f.name) + '</td><td>' + (f.kind === 'return' ? 'Fit to return' : 'Illness') + '</td><td>' + esc(f.note) + '</td></tr>'; }).join('');
    var pest = (S.pestChecks || []).filter(function (p) { return inRange(p.ts); }).map(function (p) { return '<tr><td>' + d(p.ts) + '</td><td>' + esc(p.area) + '</td><td>' + esc(p.findings) + '</td><td>' + esc(p.action) + '</td></tr>'; }).join('');
    var fry = (S.fryerLogs || []).filter(function (f) { return inRange(f.ts); }).map(function (f) { return '<tr><td>' + d(f.ts) + '</td><td>' + esc(f.fryer) + '</td><td>' + (f.tpm == null ? '—' : f.tpm + '%') + '</td><td>' + (f.tpm != null && f.tpm >= 24 ? 'CHANGE' : 'OK') + '</td><td>' + esc(f.action) + '</td></tr>'; }).join('');
    var train = (S.training || []).map(function (t) { return '<tr><td>' + esc(t.name) + '</td><td>' + esc(t.course) + '</td><td>' + (t.date ? d(t.date) : '—') + '</td><td>' + (t.expiry ? d(t.expiry) : '—') + '</td></tr>'; }).join('');
    var maint = (S.maintenance || []).filter(function (m) { return inRange(m.ts); }).map(function (m) { return '<tr><td>' + d(m.ts) + '</td><td>' + esc(m.item) + '</td><td>' + esc(m.issue) + '</td><td>' + esc(m.action) + '</td><td>' + esc(m.status) + '</td></tr>'; }).join('');
    var waste = (S.waste || []).filter(function (w) { return inRange(w.ts); }).map(function (w) { return '<tr><td>' + d(w.ts) + '</td><td>' + esc(w.item) + '</td><td>' + w.qty + ' ' + esc(w.unit) + '</td><td>' + esc(w.reason) + '</td><td>£' + (+w.cost || 0).toFixed(2) + '</td></tr>'; }).join('');
    var voids = (S.audit || []).filter(function (x) { return x.action === 'record_voided' && inRange(x.ts); }).map(function (x) { return '<tr><td>' + d(x.ts) + ' ' + tm(x.ts) + '</td><td>' + esc(x.user) + '</td><td>' + esc(x.detail) + '</td></tr>'; }).join('');
    var equip = (S.appliances || []).map(function (a) { return '<tr><td>' + esc(a.name) + '</td><td>' + esc(a.type) + '</td><td>≤ ' + a.target + '°C</td><td>' + a.critical + '°C</td></tr>'; }).join('');

    var biz = esc(S.settings && S.settings.businessName);
    var who = esc((typeof ME !== 'undefined' && ME && ME.name) || '');
    function sec(title, head, body, span) { return '<h2>' + title + '</h2><table><thead><tr>' + head + '</tr></thead><tbody>' + (body || '<tr><td colspan="' + span + '">None recorded</td></tr>') + '</tbody></table>'; }

    var html = '<html><head><title>Inspection pack — ' + biz + '</title><style>' +
      'body{font-family:Arial,sans-serif;color:#111;margin:32px;font-size:12px}h1{font-size:20px;margin:0}h2{font-size:14px;border-bottom:2px solid #111;padding-bottom:4px;margin-top:26px}.sub{color:#555;margin:4px 0 0}table{width:100%;border-collapse:collapse;margin-top:8px}td,th{border:1px solid #bbb;padding:5px 7px;text-align:left}th{background:#eee}.meta{display:flex;gap:24px;margin-top:10px;color:#333}.decl{margin-top:30px;border:1px solid #111;padding:14px;font-size:12px}.sign{margin-top:26px;display:flex;gap:40px}.sign div{border-top:1px solid #111;padding-top:5px;min-width:200px;color:#333}@media print{h2{page-break-after:avoid}}' +
      '</style></head><body>' +
      '<h1>' + biz + '</h1><div class="sub">Food safety records — last ' + days + ' days · generated ' + new Date().toLocaleString('en-GB') + ' by ' + who + '</div>' +
      '<div class="meta"><div><b>Readings:</b> ' + reads.length + '</div><div><b>Breaches:</b> ' + breachN + '</div><div><b>Corrective actions:</b> ' + (S.paperwork || []).filter(function (p) { return p.type === 'Corrective action' && inRange(p.ts); }).length + '</div><div><b>Open breaches now:</b> ' + openBreaches().length + '</div></div>' +
      sec('Temperature log', '<th>When</th><th>Unit</th><th>Reading</th><th>Status</th><th>By</th>', rows, 5) +
      sec('Corrective actions', '<th>Date</th><th>Unit(s)</th><th>Action taken</th><th>By</th>', cor, 4) +
      sec('Cooking &amp; reheating', '<th>When</th><th>Item</th><th>Type</th><th>Core</th><th>Result</th><th>By</th>', cook, 6) +
      sec('Cooling records', '<th>Date</th><th>Item</th><th>Temp change</th><th>Time</th><th>Result</th>', cool, 5) +
      sec('Probe calibration', '<th>Date</th><th>Ice</th><th>Boiling</th><th>Result</th><th>By</th>', cal, 5) +
      sec('Cleaning schedule', '<th>Task</th><th>Area</th><th>Frequency</th><th>Last done</th><th>By</th>', clean, 5) +
      '<h2>Allergen matrix</h2><table style="font-size:9px"><thead><tr><th>Dish</th>' + ALL.map(function (a) { return '<th>' + a + '</th>'; }).join('') + '</tr></thead><tbody>' + (amx || '<tr><td colspan="15">No dishes</td></tr>') + '</tbody></table>' +
      sec('Fitness to work', '<th>Date</th><th>Person</th><th>Type</th><th>Notes</th>', fit, 4) +
      sec('Pest control', '<th>Date</th><th>Area</th><th>Findings</th><th>Action</th>', pest, 4) +
      sec('Fryer oil (TPM)', '<th>Date</th><th>Fryer</th><th>TPM</th><th>Result</th><th>Action</th>', fry, 5) +
      sec('Staff training', '<th>Person</th><th>Course</th><th>Completed</th><th>Expires</th>', train, 4) +
      sec('Equipment maintenance', '<th>Date</th><th>Item</th><th>Issue</th><th>Action</th><th>Status</th>', maint, 5) +
      sec('Food waste', '<th>Date</th><th>Item</th><th>Qty</th><th>Reason</th><th>Cost</th>', waste, 5) +
      sec('Deletions &amp; voided records', '<th>When</th><th>By</th><th>Record &amp; reason</th>', voids, 3) +
      sec('Equipment &amp; limits', '<th>Unit</th><th>Type</th><th>Target</th><th>Critical</th>', equip, 4) +
      '<div class="decl"><b>Declaration.</b> I confirm that the records in this pack are a true and accurate account of the food-safety management activity for the period stated, kept as part of our documented food-safety management system.' +
      '<div class="sign"><div>Signed</div><div>Name &amp; role</div><div>Date</div></div></div>' +
      '<script>setTimeout(function(){window.print();},400);<\/script></body></html>';

    var w = window.open('', '_blank');
    if (!w) { if (typeof toast === 'function') toast('Allow pop-ups to print', 'warn'); return; }
    w.document.write(html); w.document.close();
  }

  function packV2() {
    if (typeof modal !== 'function') { generatePack(14); return; }
    var body = el('div', {});
    body.innerHTML = '<p class="muted" style="margin:0 0 12px;font-size:13px">Choose the period to include. The pack prints all food-safety records for that range, plus any voided records and a signed declaration.</p>';
    var wrap = el('div', { style: 'display:flex;gap:8px;flex-wrap:wrap' });
    [[7, 'Last 7 days'], [14, 'Last 14 days'], [28, 'Last 28 days'], [90, 'Last 90 days']].forEach(function (o) {
      wrap.append(el('button', { class: 'btn ghost', html: o[1], onclick: function () { m.close(); generatePack(o[0]); } }));
    });
    body.append(wrap);
    var m = modal({ title: 'Inspection pack', body: body, footer: [el('button', { class: 'btn ghost', html: 'Close', onclick: function () { m.close(); } })] });
  }

  function install() {
    if (!ready()) return setTimeout(install, 200);
    window.inspectionPack = packV2;
    window.openBreaches = openBreaches;
    wrapReports();
    console.info('[Command de Cuisine] Compliance Pro active — open-breach register, richer inspection pack');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();
})();
