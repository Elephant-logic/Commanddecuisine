from pathlib import Path

app = Path('app')
index = app / 'index.html'
text = index.read_text(encoding='utf-8')

# A non-reading equipment status persists until a later numeric reading brings
# the unit back online. Offline units remain auditable but are excluded from
# required temperature-round/compliance denominators.
marker = 'function tempStatusNeedsAction(k){return k==="out_of_order"||k==="awaiting_repair";}'
helper = marker + '''\nconst TEMP_OFFLINE_STATUSES=new Set(["out_of_order","awaiting_repair","not_in_use","defrosting"]);\nfunction tempUnitRecordAt(appId,ds){\n  return (STATE.tempReadings||[]).filter(r=>r.appId===appId&&String(r.ts||"").slice(0,10)<=ds).sort((a,b)=>String(b.ts||"").localeCompare(String(a.ts||"")))[0]||null;\n}\nfunction tempUnitOfflineOn(appId,ds){\n  const r=tempUnitRecordAt(appId,ds);\n  return !!(r&&!tempRecordHasValue(r)&&TEMP_OFFLINE_STATUSES.has(r.equipmentStatus));\n}\nfunction tempUnitOffline(appId){return tempUnitOfflineOn(appId,todayISO());}\nfunction tempOfflineLabel(appId,ds=todayISO()){const r=tempUnitRecordAt(appId,ds);return r&&!tempRecordHasValue(r)?(tempRecordStatusLabel(r)||"Offline"):"";}'''
if marker not in text:
    raise SystemExit('temperature status helper marker not found')
text = text.replace(marker, helper, 1)

old = '''  const coldUnits=STATE.appliances.filter(a=>a.type==="fridge"||a.type==="freezer");
  const slotCount=period=>coldUnits.filter(a=>STATE.tempReadings.some(r=>r.appId===a.id&&r.ts.slice(0,10)===today&&(period==="am"?+r.ts.slice(11,13)<12:+r.ts.slice(11,13)>=12))).length;
  const amCount=slotCount("am"), pmCount=slotCount("pm");
  const amDone=coldUnits.length>0&&amCount===coldUnits.length, pmDone=coldUnits.length>0&&pmCount===coldUnits.length;
  const breaches=coldUnits.filter(a=>{const r=latestReading(a.id);return r&&tempStatus(a,r.value)==="danger";}).length;
  t.push({id:"temp_am",label:"Morning temperature round",route:"temps",icon:"temp",state:amDone?"done":(h>=11?"over":"due"),detail:amCount+"/"+coldUnits.length+" units"});
  t.push({id:"temp_pm",label:"Evening temperature round",route:"temps",icon:"temp",state:pmDone?"done":(h>=18?"over":h>=15?"due":"ok"),detail:pmCount+"/"+coldUnits.length+" units"});'''
new = '''  const allColdUnits=STATE.appliances.filter(a=>a.type==="fridge"||a.type==="freezer");
  const offlineUnits=allColdUnits.filter(a=>tempUnitOfflineOn(a.id,today));
  const coldUnits=allColdUnits.filter(a=>!tempUnitOfflineOn(a.id,today));
  const slotCount=period=>coldUnits.filter(a=>STATE.tempReadings.some(r=>r.appId===a.id&&tempRecordHasValue(r)&&String(r.ts||"").slice(0,10)===today&&(period==="am"?+String(r.ts).slice(11,13)<12:+String(r.ts).slice(11,13)>=12))).length;
  const amCount=slotCount("am"), pmCount=slotCount("pm");
  const amDone=coldUnits.length===0||amCount===coldUnits.length, pmDone=coldUnits.length===0||pmCount===coldUnits.length;
  const breaches=coldUnits.filter(a=>{const r=latestReading(a.id);return r&&tempRecordHasValue(r)&&tempStatus(a,Number(r.value))==="danger";}).length;
  const roundDetail=count=>count+"/"+coldUnits.length+" active"+(offlineUnits.length?" · "+offlineUnits.length+" offline":"");
  t.push({id:"temp_am",label:"Morning temperature round",route:"temps",icon:"temp",state:amDone?"done":(h>=11?"over":"due"),detail:roundDetail(amCount)});
  t.push({id:"temp_pm",label:"Evening temperature round",route:"temps",icon:"temp",state:pmDone?"done":(h>=18?"over":h>=15?"due":"ok"),detail:roundDetail(pmCount)});'''
if old not in text:
    raise SystemExit('compliance temperature block not found')
text = text.replace(old, new, 1)

# Make the round card reflect a persistent offline state. Selecting Reading and
# saving a numeric value automatically returns the unit to service.
round_start = text.index('function tempRound(v){')
round_end = text.index('function breachModal(apps){', round_start)
round_text = text[round_start:round_end]
round_text = round_text.replace(
    '    const r=latestReading(a.id);\n    const doneNow=STATE.tempReadings.some(x=>x.appId===a.id&&x.ts.slice(0,10)===today&&(period==="am"?+x.ts.slice(11,13)<12:+x.ts.slice(11,13)>=12));',
    '    const r=latestReading(a.id);\n    const isOffline=tempUnitOfflineOn(a.id,today);\n    const doneNow=!isOffline&&STATE.tempReadings.some(x=>x.appId===a.id&&tempRecordHasValue(x)&&x.ts.slice(0,10)===today&&(period==="am"?+x.ts.slice(11,13)<12:+x.ts.slice(11,13)>=12));'
)
round_text = round_text.replace(
    '    const statusTag=el("span",{class:"tag "+(doneNow?"ok":"dim")},doneNow?"Done "+period.toUpperCase():"Due");',
    '    const statusTag=el("span",{class:"tag "+(isOffline?"warn":doneNow?"ok":"dim")},isOffline?"Offline · "+tempOfflineLabel(a.id,today):(doneNow?"Done "+period.toUpperCase():"Due"));'
)
round_text = round_text.replace(
    '    draft[a.id]={status:"reading",value:null,notes:""};',
    '    draft[a.id]={status:isOffline&&r&&r.equipmentStatus?r.equipmentStatus:"reading",value:null,notes:isOffline&&r?(r.notes||""):""};\n    if(isOffline&&r&&r.equipmentStatus){mode.value=r.equipmentStatus;notes.value=r.notes||"";}'
)
round_text = round_text.replace(
    '    notes.addEventListener("input",()=>draft[a.id].notes=notes.value.trim());\n    line.append(mode,inp,notes);',
    '    notes.addEventListener("input",()=>draft[a.id].notes=notes.value.trim());\n    paint();\n    line.append(mode,inp,notes);'
)
text = text[:round_start] + round_text + text[round_end:]
index.write_text(text, encoding='utf-8')

# Historical coverage/compliance: an offline unit is not an expected slot for
# that day, and status-only records are not counted as numeric temperature reads.
fixes = app / 'kitchen_fixes_20260810.js'
js = fixes.read_text(encoding='utf-8')
old_cov = '''      duePeriods(ds).forEach(period=>units.forEach(a=>{
        const reading=readingFor(a.id,ds,period);
        slots.push({date:ds,period,app:a,reading,missing:!reading});
      }));'''
new_cov = '''      duePeriods(ds).forEach(period=>units.filter(a=>!(typeof tempUnitOfflineOn==='function'&&tempUnitOfflineOn(a.id,ds))).forEach(a=>{
        const reading=readingFor(a.id,ds,period);
        const numeric=reading&&(!window.tempRecordHasValue||tempRecordHasValue(reading));
        slots.push({date:ds,period,app:a,reading:numeric?reading:null,missing:!numeric});
      }));'''
if old_cov not in js:
    raise SystemExit('coverage slot block not found')
js = js.replace(old_cov, new_cov, 1)
old_week = '''      periods.forEach(period=>units.forEach(a=>{
        expected++;
        const r=readingFor(a.id,ds,period);
        if(r&&typeof tempRecordHasValue==='function'&&tempRecordHasValue(r)&&tempStatus(a,r.value)!=='danger')good++;
      }));'''
new_week = '''      periods.forEach(period=>units.filter(a=>!(typeof tempUnitOfflineOn==='function'&&tempUnitOfflineOn(a.id,ds))).forEach(a=>{
        expected++;
        const r=readingFor(a.id,ds,period);
        if(r&&typeof tempRecordHasValue==='function'&&tempRecordHasValue(r)&&tempStatus(a,r.value)!=='danger')good++;
      }));'''
if old_week not in js:
    # Support the unpatched source marker as a fallback.
    old_week = '''      periods.forEach(period=>units.forEach(a=>{
        expected++;
        const r=readingFor(a.id,ds,period);
        if(r&&tempStatus(a,r.value)!=='danger')good++;
      }));'''
if old_week not in js:
    raise SystemExit('weekly compliance block not found')
js = js.replace(old_week, new_week, 1)
fixes.write_text(js, encoding='utf-8')

print('Offline equipment compliance rules applied')
