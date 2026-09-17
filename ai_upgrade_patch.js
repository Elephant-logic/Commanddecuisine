/* ============================================================================
   ai_upgrade_patch.js  —  Command de Cuisine  ·  "Chef Pro"
   ----------------------------------------------------------------------------
   Turns the built-in assistant from a search box into a real kitchen assistant
   that understands the live kitchen AND can carry out actions safely.

   It replaces two globals from index.html (aiContext, askAI) and wraps
   handleCommand. If the base app isn't present it no-ops.

   How it works:
     • Deterministic commands in index.html (log fridge one at four, what's due,
       mark opening checks done, read the probes…) keep working untouched.
     • Anything else goes to the model with a rich, structured live context and
       real UK food-safety rules, and the model must answer with STRICT JSON:
           {"action":"answer","say":"..."}                       (a spoken reply)
         or a WRITE action, e.g.
           {"action":"log_temperature","args":{"unit":"Fridge 1","celsius":4},"say":"..."}
     • Every WRITE is shown to the chef for one-tap confirmation before it
       touches the record — because an AI mishearing "forty" for "four" must
       never silently write a false safety record. Reads/answers just speak.

   Actions supported: answer, log_temperature, complete_checks, log_waste,
   receive_stock, log_corrective_action.
   ========================================================================== */
(function () {
  'use strict';
  if (window.__cdcAIPro) return;
  window.__cdcAIPro = true;

  function ready() {
    return typeof STATE !== 'undefined' && typeof askAI === 'function' &&
           typeof aiContext === 'function' && typeof chefSay === 'function' && typeof el === 'function';
  }
  var num = function (v) { return (v === '' || v == null || isNaN(+v)) ? null : +v; };
  var lc = function (v) { return String(v || '').toLowerCase(); };
  var WORD2NUM = { one:1, two:2, three:3, four:4, five:5, six:6, seven:7, eight:8, nine:9, ten:10, minus:'-', 'negative':'-' };
  function normUnitName(s) { return lc(s).replace(/\b(one|two|three|four|five|six|seven|eight|nine|ten)\b/g, function (w) { return WORD2NUM[w]; }); }

  function richContext() {
    var S = STATE, out = [];
    try {
      var biz = (S.settings && S.settings.businessName) || 'the kitchen';
      out.push(biz + '. ' + new Date().toLocaleString('en-GB', { weekday: 'long', hour: '2-digit', minute: '2-digit' }) + '.');
      var units = (S.appliances || []).map(function (a) {
        var r = (typeof latestReading === 'function') ? latestReading(a.id) : null;
        var v = r ? +r.value : null;
        var st = (typeof tempStatus === 'function' && v != null) ? tempStatus(a, v) : 'none';
        return a.name + ' ' + (v == null ? 'no reading' : v + '°C' + (a.target != null ? ' (≤' + a.target + ')' : '') + (st === 'danger' ? ' BREACH' : ''));
      });
      if (units.length) out.push('Units: ' + units.join('; ') + '.');
      var low = (S.stock || []).filter(function (s) { return num(s.qty) != null && num(s.par) != null && +s.qty < +s.par; })
        .map(function (s) { return (s.item || s.name) + ' ' + s.qty + '/' + s.par + (s.unit || ''); });
      out.push(low.length ? 'Below par: ' + low.slice(0, 15).join(', ') + '.' : 'Stock at/above par.');
      if (typeof checksProgress === 'function') out.push('Checks ' + checksProgress() + '% done.');
      if (typeof complianceToday === 'function') out.push('Compliance ' + complianceToday() + '%.');
      var soon = Date.now() + 30 * 864e5;
      var exp = (S.training || []).filter(function (t) { return t.expiry && new Date(t.expiry).getTime() <= soon; })
        .map(function (t) { return (t.name || '') + ' ' + (t.course || '') + ' by ' + t.expiry; });
      if (exp.length) out.push('Training expiring: ' + exp.slice(0, 8).join('; ') + '.');
      var today = new Date().toISOString().slice(0, 10);
      var fns = (S.functions || []).filter(function (f) { return !f.date || f.date >= today; })
        .map(function (f) { return (f.name || 'function') + (f.date ? ' ' + f.date : '') + ' (' + (f.guests || '?') + ')'; });
      if (fns.length) out.push('Functions: ' + fns.slice(0, 6).join('; ') + '.');
      out.push('Known units: ' + (S.appliances || []).map(function (a) { return a.name; }).join(', ') + '.');
    } catch (e) {}
    return out.join(' ');
  }

  var SYSTEM = [
    'You are "Chef", the assistant inside Command de Cuisine, an operations app for a professional UK kitchen.',
    'Use LIVE DATA as the only source of truth. Never invent temperatures, stock, or records. If the data does not say, tell the chef to check.',
    'Food-safety rules to apply: cold storage ≤8°C (aim 1–5°C), freezers ≤−18°C, hot-hold ≥63°C, cook/reheat to 75°C core (or 70°C for 2 min), cool 63°C→8°C within ~90 min, anyone with vomiting/diarrhoea stays off until 48h clear.',
    '',
    'You MUST reply with a single JSON object and nothing else (no markdown, no prose outside JSON). Shape:',
    '{"action": ACTION, "args": {...}, "say": "one or two short spoken sentences for a busy chef"}',
    'ACTION is one of:',
    '  "answer"                — just answer/explain. Put the reply in "say".',
    '  "log_temperature"       — args {"unit": exact unit name from LIVE DATA, "celsius": number}',
    '  "complete_checks"       — args {"period": "open" | "close"}',
    '  "log_waste"             — args {"item": string, "qty": number, "unit": string, "reason": string}',
    '  "receive_stock"         — args {"item": string, "qty": number}',
    '  "log_corrective_action" — args {"units": string, "action": string}',
    'Only choose a WRITE action when the chef clearly asks to record/log/do it. Otherwise use "answer". Match unit names to the exact names in LIVE DATA.'
  ].join('\n');

  var memory = [];

  function parseOutput(r) {
    var out = '';
    try { out = (r.output || []).flatMap(function (o) { return o.content || []; }).map(function (c) { return c.text || ''; }).join(' ').trim(); } catch (e) {}
    if (!out && r.output_text) out = r.output_text;
    return out;
  }
  function parseJSON(text) {
    if (!text) return null;
    var t = String(text).replace(/```json/gi, '').replace(/```/g, '').trim();
    var a = t.indexOf('{'), b = t.lastIndexOf('}');
    if (a >= 0 && b > a) t = t.slice(a, b + 1);
    try { return JSON.parse(t); } catch (e) { return null; }
  }

  function confirmWrite(summary, run, spoken) {
    if (typeof modal !== 'function') { if (window.confirm(summary)) { run(); chefSay(spoken); } return; }
    var body = el('div', {});
    body.innerHTML = '<p style="margin:0;font-size:14px;line-height:1.5">' + summary.replace(/</g, '&lt;') + '</p>';
    var m = modal({
      title: 'Confirm', body: body, footer: [
        el('button', { class: 'btn ghost', html: 'Cancel', onclick: function () { m.close(); chefSay('Cancelled.'); } }),
        el('button', {
          class: 'btn primary', html: 'Do it', onclick: function () {
            m.close();
            try { run(); chefSay(spoken); } catch (e) { chefSay('Sorry — I could not do that: ' + (e.message || 'error')); }
          }
        })
      ]
    });
  }

  function execute(cmd) {
    var action = cmd && cmd.action, args = (cmd && cmd.args) || {}, say = (cmd && cmd.say) || '';
    if (action === 'answer' || !action) { chefSay(say || 'Okay.'); if (say) memory.push({ role: 'assistant', content: say }); return; }

    if (action === 'log_temperature') {
      var want = normUnitName(args.unit);
      var app = (STATE.appliances || []).find(function (a) { return normUnitName(a.name) === want; }) ||
                (STATE.appliances || []).find(function (a) { return normUnitName(a.name).indexOf(want) >= 0 || want.indexOf(normUnitName(a.name)) >= 0; });
      var c = num(args.celsius);
      if (!app || c == null) { chefSay('I could not match that unit or temperature — say it like "log Fridge 1 at 4 degrees".'); return; }
      var st = (typeof tempStatus === 'function') ? tempStatus(app, c) : 'none';
      confirmWrite('Log ' + app.name + ' at ' + c + '°C' + (st === 'danger' ? ' — this is a BREACH.' : '?'), function () {
        STATE.tempReadings.push({ id: uid('t'), appId: app.id, value: c, ts: nowISO(), by: ME ? ME.username : 'chef', source: 'manual', photo: null });
        if (typeof audit === 'function') audit('temp_ai', app.name + ' ' + c);
        save('ai temp');
        if (st === 'danger' && typeof breachModal === 'function') breachModal([app]);
        if (typeof ROUTE !== 'undefined' && (ROUTE === 'temps' || ROUTE === 'pass')) rerender();
      }, say || (app.name + ' logged at ' + c + '°C' + (st === 'danger' ? '. That is a breach — record what you did.' : '.')));
      return;
    }

    if (action === 'complete_checks') {
      var period = lc(args.period).indexOf('clos') >= 0 ? 'close' : 'open';
      confirmWrite('Mark all ' + period + 'ing checks as done?', function () {
        if (typeof markAllChecks === 'function') markAllChecks(period);
      }, say || ('All ' + period + 'ing checks marked done.'));
      return;
    }

    if (action === 'log_waste') {
      var item = String(args.item || '').trim(), q = num(args.qty) || 0, unit = args.unit || 'kg', reason = args.reason || 'Spoilage';
      if (!item) { chefSay('What was wasted?'); return; }
      confirmWrite('Log waste: ' + q + unit + ' ' + item + ' (' + reason + ')?', function () {
        STATE.waste = STATE.waste || [];
        STATE.waste.unshift({ id: uid('w'), ts: nowISO(), item: item, qty: q, unit: unit, reason: reason, cost: 0, by: ME ? ME.username : 'chef' });
        if (typeof stockMoveByName === 'function') stockMoveByName(item, -q, 'waste', reason);
        if (typeof audit === 'function') audit('waste', item);
        save('ai waste'); if (typeof ROUTE !== 'undefined' && ROUTE === 'waste') rerender();
      }, say || ('Logged ' + q + unit + ' ' + item + ' as waste.'));
      return;
    }

    if (action === 'receive_stock') {
      var name = String(args.item || '').trim(), q2 = num(args.qty) || 0;
      var s = (typeof stockByName === 'function') ? stockByName(name) : null;
      if (!s) { chefSay('I could not find "' + name + '" in stock — add it once, then I can top it up.'); return; }
      confirmWrite('Add ' + q2 + ' to ' + (s.item || s.name) + '?', function () {
        if (typeof stockMove === 'function') stockMove(s.id, q2, 'received', 'ai');
        save('ai receive'); if (typeof ROUTE !== 'undefined' && ROUTE === 'stock') rerender();
      }, say || ('Added ' + q2 + ' to ' + (s.item || s.name) + '.'));
      return;
    }

    if (action === 'log_corrective_action') {
      var units = String(args.units || '').trim(), act = String(args.action || '').trim();
      if (!act) { chefSay('What action did you take?'); return; }
      confirmWrite('Log corrective action for ' + (units || 'the kitchen') + ': "' + act + '"?', function () {
        STATE.paperwork.unshift({ id: uid('pw'), type: 'Corrective action', ts: nowISO(), by: ME ? ME.username : 'chef', units: units, note: act, photo: null });
        if (typeof audit === 'function') audit('corrective_action', units);
        save('ai corrective');
      }, say || 'Corrective action recorded.');
      return;
    }
    chefSay(say || 'I understood, but that action is not available.');
  }

  function newAskAI(question) {
    chefSay('Let me check…', false);
    memory.push({ role: 'user', content: String(question || '') });
    var input = [{ role: 'system', content: SYSTEM }, { role: 'system', content: 'LIVE DATA: ' + richContext() }].concat(memory.slice(-8));
    api('/api/openai/responses', {
      method: 'POST',
      body: JSON.stringify({ model: 'gpt-4o-mini', input: input, max_output_tokens: 500, temperature: 0.2 })
    }).then(function (r) {
      var raw = parseOutput(r);
      var cmd = parseJSON(raw);
      if (cmd && cmd.action) execute(cmd);
      else if (raw) { chefSay(raw); }
      else chefSay('I couldn’t get a clear answer — try rephrasing.');
    }).catch(function (err) {
      var msg = (err && err.data && err.data.error && err.data.error.message) || (err && err.message) || '';
      if (/429|too many/i.test(msg)) chefSay('Too many AI questions just now — give it a minute.');
      else if (/api key|not configured|503/i.test(msg)) chefSay('The AI key isn’t set up on the server yet, but I can still run kitchen commands.');
      else chefSay('The AI service isn’t reachable right now, but I can still run kitchen commands.');
    });
  }

  function install() {
    if (!ready()) return setTimeout(install, 200);
    window.aiContext = richContext;
    window.askAI = newAskAI;
    console.info('[Command de Cuisine] Chef Pro active — rich context, memory, food-safety rules, confirmed actions');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();
})();
