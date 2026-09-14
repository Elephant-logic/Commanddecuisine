from pathlib import Path
import shutil

app_dir = Path('app')
for src, dest in (
    ('auth_controls_override.py', 'auth_controls.py'),
    ('temperature_store_override.py', 'temperature_store.py'),
    ('supabase_storage_override_mt.py', 'drive_storage.py'),
):
    shutil.copyfile(src, app_dir / dest)

index = app_dir / 'index.html'
text = index.read_text(encoding='utf-8')
text = text.replace('<div class="tag-line">First-time Admin setup</div>', '<div class="tag-line">Create your venue & Admin</div>')
text = text.replace('${icon("ok")}Create Admin & start', '${icon("ok")}Create venue & start')
old_hint = '<div class="demo-hint">Staff accounts are created and managed by an Admin.</div>`;'
new_hint = '<div class="demo-hint">Staff accounts are created and managed by an Admin.</div><button class="btn ghost" id="newVenueBtn" style="width:100%;margin-top:12px">Create a new venue</button>`;'
if old_hint not in text:
    raise SystemExit('Login hint marker not found in index.html')
text = text.replace(old_hint, new_hint, 1)
old_events = '$("#lbtn").addEventListener("click",go);\n  $("#lp").addEventListener("keydown",e=>{if(e.key==="Enter")go();});\n  $("#lu").focus();'
new_events = '$("#lbtn").addEventListener("click",go);\n  $("#lp").addEventListener("keydown",e=>{if(e.key==="Enter")go();});\n  $("#newVenueBtn").addEventListener("click",renderSetup);\n  $("#lu").focus();'
if old_events not in text:
    raise SystemExit('Login event marker not found in index.html')
text = text.replace(old_events, new_events, 1)

old_reports_head = '  const comp=complianceToday();\n  const breaches=STATE.tempReadings.filter(r=>{const a=appById(r.appId);return a&&tempStatus(a,r.value)==="danger";}).sort((a,b)=>b.ts.localeCompare(a.ts));'
new_reports_head = '  const reportTemps=STATE.tempReadings.filter(r=>String(r.ts||"").slice(0,10)===todayISO());\n  const reportTempOk=reportTemps.filter(r=>{const a=appById(r.appId);return a&&tempStatus(a,r.value)!=="danger";}).length;\n  const comp=reportTemps.length?Math.round(reportTempOk/reportTemps.length*100):0;\n  const breaches=STATE.tempReadings.filter(r=>{const a=appById(r.appId);return a&&tempStatus(a,r.value)==="danger";}).sort((a,b)=>b.ts.localeCompare(a.ts));'
if old_reports_head not in text:
    raise SystemExit('Cold chain report metric marker not found in index.html')
text = text.replace(old_reports_head, new_reports_head, 1)

old_cold_chain = '  d1.insertAdjacentHTML("beforeend",donut(comp,comp>=95?"var(--ok)":comp>=80?"var(--warn)":"var(--danger)","In range"));'
new_cold_chain = '  if(reportTemps.length)d1.insertAdjacentHTML("beforeend",donut(comp,comp>=95?"var(--ok)":comp>=80?"var(--warn)":"var(--danger)","In range")); else d1.append(el("div",{class:"empty",html:icon("temp")+"<h4>No temperature data yet</h4><div>Cold-chain percentages will appear after this venue records temperatures.</div>"}));'
if old_cold_chain not in text:
    raise SystemExit('Cold chain report display marker not found in index.html')
text = text.replace(old_cold_chain, new_cold_chain, 1)

old_delivery = 'd3.insertAdjacentHTML("beforeend",donut(STATE.deliveries.length?acc/STATE.deliveries.length*100:100,"var(--cold)","Accepted"));'
new_delivery = 'd3.insertAdjacentHTML("beforeend",donut(STATE.deliveries.length?acc/STATE.deliveries.length*100:0,STATE.deliveries.length?"var(--cold)":"var(--faint)",STATE.deliveries.length?"Accepted":"No records"));'
if old_delivery not in text:
    raise SystemExit('Delivery report marker not found in index.html')
text = text.replace(old_delivery, new_delivery, 1)

old_week = 'wk.insertAdjacentHTML("beforeend",bars(weekCompliance())); v.append(wk);'
new_week = 'const weekData=weekCompliance(); const hasWeekData=weekData.some(x=>x&&x.hasData!==false&&x.value>0)||STATE.tempReadings.some(r=>{const t=new Date(r.ts).getTime();return Number.isFinite(t)&&t>=Date.now()-7*864e5;}); if(hasWeekData)wk.insertAdjacentHTML("beforeend",bars(weekData)); else wk.append(el("div",{class:"empty",html:icon("history")+"<h4>No compliance history yet</h4><div>Percentages will appear after this venue starts recording its required checks.</div>"})); v.append(wk);'
if old_week not in text:
    raise SystemExit('Weekly compliance report marker not found in index.html')
text = text.replace(old_week, new_week, 1)
index.write_text(text, encoding='utf-8')

fixes = app_dir / 'kitchen_fixes_20260810.js'
js = fixes.read_text(encoding='utf-8')
old_pct = "const pct=expected?Math.round(good/expected*100):100;\n      out.push({label:dayName(day),value:pct,color:pct>=95?'var(--ok)':pct>=80?'var(--warn)':'var(--danger)'});"
new_pct = "const hasData=expected>0;\n      const pct=hasData?Math.round(good/expected*100):0;\n      out.push({label:dayName(day),value:pct,hasData,color:hasData?(pct>=95?'var(--ok)':pct>=80?'var(--warn)':'var(--danger)'):'var(--faint)'});"
if old_pct not in js:
    raise SystemExit('Weekly compliance empty-state marker not found in kitchen fixes')
js = js.replace(old_pct, new_pct, 1)
fixes.write_text(js, encoding='utf-8')
