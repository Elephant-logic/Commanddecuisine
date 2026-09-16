from pathlib import Path

main = Path('app/main_app.js')
text = main.read_text(encoding='utf-8')

# Temperature records already carry an explicit AM/PM period. Always prefer it.
# Only fall back to converting the timestamp in the browser's local timezone for
# legacy records that pre-date the period field.
marker = 'function tempStatusNeedsAction(k){return k==="out_of_order"||k==="awaiting_repair";}'
helper = marker + r'''
function tempRecordPeriod(r){
  const p=String(r&&r.period||"").trim().toLowerCase();
  if(p==="am"||p==="pm")return p;
  const d=new Date(r&&r.ts||"");
  if(!Number.isNaN(d.getTime()))return d.getHours()<12?"am":"pm";
  const h=+String(r&&r.ts||"").slice(11,13);
  return Number.isFinite(h)?(h<12?"am":"pm"):"";
}
function tempRecordLocalDay(r){
  const d=new Date(r&&r.ts||"");
  if(!Number.isNaN(d.getTime())){
    return [d.getFullYear(),String(d.getMonth()+1).padStart(2,"0"),String(d.getDate()).padStart(2,"0")].join("-");
  }
  return String(r&&r.ts||"").slice(0,10);
}'''
if 'function tempRecordPeriod(r)' not in text:
    if marker not in text:
        raise SystemExit('Temperature helper marker not found')
    text = text.replace(marker, helper, 1)

old_slot = 'const slotCount=period=>coldUnits.filter(a=>STATE.tempReadings.some(r=>r.appId===a.id&&tempRecordHasValue(r)&&String(r.ts||"").slice(0,10)===today&&(period==="am"?+String(r.ts).slice(11,13)<12:+String(r.ts).slice(11,13)>=12))).length;'
new_slot = 'const slotCount=period=>coldUnits.filter(a=>STATE.tempReadings.some(r=>r.appId===a.id&&tempRecordHasValue(r)&&tempRecordLocalDay(r)===today&&tempRecordPeriod(r)===period)).length;'
if old_slot not in text:
    raise SystemExit('Compliance temperature slot marker not found')
text = text.replace(old_slot, new_slot, 1)

old_done = 'const doneNow=!isOffline&&STATE.tempReadings.some(x=>x.appId===a.id&&tempRecordHasValue(x)&&x.ts.slice(0,10)===today&&(period==="am"?+x.ts.slice(11,13)<12:+x.ts.slice(11,13)>=12));'
new_done = 'const doneNow=!isOffline&&STATE.tempReadings.some(x=>x.appId===a.id&&tempRecordHasValue(x)&&tempRecordLocalDay(x)===today&&tempRecordPeriod(x)===period);'
if old_done not in text:
    raise SystemExit('Temperature round done marker not found')
text = text.replace(old_done, new_done, 1)
main.write_text(text, encoding='utf-8')

fixes = Path('app/kitchen_fixes_20260810.js')
js = fixes.read_text(encoding='utf-8')

old_slot_helper = """  const slotForReading=r=>{
    if(r&&r.period)return String(r.period).toLowerCase()==='pm'?'pm':'am';
    const h=+(String(r&&r.ts||'').slice(11,13)||0);
    return h>=12?'pm':'am';
  };"""
new_slot_helper = """  const slotForReading=r=>{
    if(typeof tempRecordPeriod==='function')return tempRecordPeriod(r);
    if(r&&r.period)return String(r.period).toLowerCase()==='pm'?'pm':'am';
    const d=new Date(r&&r.ts||'');
    return !Number.isNaN(d.getTime())&&d.getHours()>=12?'pm':'am';
  };"""
if old_slot_helper not in js:
    raise SystemExit('Coverage slotForReading marker not found')
js = js.replace(old_slot_helper, new_slot_helper, 1)

old_reading = "return (STATE.tempReadings||[]).filter(r=>r.appId===appId&&String(r.ts||'').slice(0,10)===ds&&slotForReading(r)===period)"
new_reading = "return (STATE.tempReadings||[]).filter(r=>r.appId===appId&&(typeof tempRecordLocalDay==='function'?tempRecordLocalDay(r):String(r.ts||'').slice(0,10))===ds&&slotForReading(r)===period)"
if old_reading not in js:
    raise SystemExit('Coverage readingFor marker not found')
js = js.replace(old_reading, new_reading, 1)

# Historic/back-filled readings were previously pushed only into STATE and then
# sent through /api/state. Production stores temperatures in a normalized table,
# so those entries could appear immediately and then vanish/not count on reload.
# Save backfills through the real temperature endpoint first, then mirror the
# server-confirmed rows into STATE for immediate UI feedback.
old_click = "el('button',{class:'btn primary',html:icon('save')+'Save historic readings',onclick:()=>{"
new_click = "el('button',{class:'btn primary',html:icon('save')+'Save historic readings',onclick:async()=>{"
if old_click not in js:
    raise SystemExit('Backfill save button marker not found')
js = js.replace(old_click, new_click, 1)

if 'let added=0;' not in js:
    raise SystemExit('Backfill added counter marker not found')
js = js.replace('        let added=0;', '        let added=0,pending=[];', 1)

old_push = "STATE.tempReadings.push({id:uid('t'),appId:a.id,value:val,ts:ds+'T'+(p==='am'?'09:00:00':'17:00:00'),period:p,by:ME.username,source:'manager-backfill',backfilled:true,enteredAt:nowISO(),photo:null});"
new_push = "pending.push({id:uid('t'),appId:a.id,value:val,equipmentStatus:'reading',ts:ds+'T'+(p==='am'?'09:00:00':'17:00:00'),period:p,by:ME.username,source:'manager-backfill',backfilled:true,enteredAt:nowISO(),photo:null});"
if old_push not in js:
    raise SystemExit('Backfill STATE push marker not found')
js = js.replace(old_push, new_push, 1)

old_tail = """        if(!added){toast('Enter at least one missing reading','warn');return;}
        audit('temp_backfill',ds+' '+p.toUpperCase()+' · '+added+' readings entered later');
        save('historic temperature backfill'); m.close(); toast(added+' historic reading'+(added===1?'':'s')+' added','ok'); rerender();"""
new_tail = """        if(!added){toast('Enter at least one missing reading','warn');return;}
        try{
          let savedRows=pending;
          if(serverMode){
            const res=await api('/api/temperature-readings',{method:'POST',body:JSON.stringify({readings:pending})});
            if(!res||res.ok!==true)throw new Error((res&&res.error)||'Temperature save failed');
            savedRows=Array.isArray(res.readings)&&res.readings.length?res.readings:pending;
          }
          savedRows.forEach(r=>{if(!STATE.tempReadings.some(x=>x.id===r.id))STATE.tempReadings.push(r);});
          audit('temp_backfill',ds+' '+p.toUpperCase()+' · '+added+' readings entered later');
          save('historic temperature backfill'); m.close(); toast(added+' historic reading'+(added===1?'':'s')+' added','ok'); rerender();
        }catch(err){
          toast('Historic temperatures were not saved — please try again','bad');
          console.error('temperature backfill save failed',err);
        }"""
if old_tail not in js:
    raise SystemExit('Backfill save tail marker not found')
js = js.replace(old_tail, new_tail, 1)

fixes.write_text(js, encoding='utf-8')
print('Temperature rounds now respect explicit AM/PM periods and historic backfills persist through the normalized temperature store')
