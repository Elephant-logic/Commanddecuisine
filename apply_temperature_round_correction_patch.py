from pathlib import Path
import re

app = Path('app')
store = app / 'temperature_store.py'
server = app / 'server.py'
fixes = app / 'kitchen_fixes_20260810.js'
gap = app / 'temperature_gap_fill.js'

for required in (store, server, fixes):
    if not required.exists():
        raise SystemExit(f'Temperature round correction target missing: {required}')

# Atomic manager correction endpoint. Existing rows are snapshotted into the
# server audit before replacement/removal, so correcting a mistake does not
# erase the history of what was changed.
st = store.read_text(encoding='utf-8')
if 'def correct_round(handler, payload):' not in st:
    st += r'''


def correct_round(handler, payload):
    stored,user=handler.require_user()
    if not stored:return
    if user.get('role') != 'manager':
        handler.send_json({'error':'Manager access required.'},403);return
    operations=payload.get('operations') if isinstance(payload,dict) else None
    if not isinstance(operations,list) or not operations:
        handler.send_json({'error':'No temperature changes supplied.'},400);return
    if len(operations)>64:
        handler.send_json({'error':'Too many temperature changes in one save.'},400);return

    valid_apps={str(a.get('id')) for a in stored['state'].get('appliances',[]) if isinstance(a,dict) and a.get('id')}
    cleaned=[]; seen_remove=set()
    for op in operations:
        if not isinstance(op,dict):
            handler.send_json({'error':'Invalid temperature change.'},400);return
        app_id=str(op.get('appId') or '').strip()
        if app_id not in valid_apps:
            handler.send_json({'error':'Temperature change refers to an unknown appliance.'},400);return
        remove_ids=[str(x).strip() for x in (op.get('removeIds') or []) if str(x).strip()]
        if len(remove_ids)>8:
            handler.send_json({'error':'Too many existing records selected for one appliance/round.'},400);return
        for rid in remove_ids:
            if rid in seen_remove:
                handler.send_json({'error':'A temperature record was selected more than once.'},400);return
            seen_remove.add(rid)

        record=op.get('record')
        item=None
        if record is not None:
            if not isinstance(record,dict):
                handler.send_json({'error':'Replacement temperature record is invalid.'},400);return
            row_id=str(record.get('id') or '').strip()
            ts=str(record.get('ts') or '').strip()
            try: parsed=datetime.fromisoformat(ts.replace('Z','+00:00'))
            except Exception:
                handler.send_json({'error':'Temperature timestamp is invalid.'},400);return
            period=str(record.get('period') or '').upper().strip()
            if period not in ('AM','PM'): period='AM' if parsed.hour<12 else 'PM'
            equipment_status=str(record.get('equipmentStatus') or 'reading').strip().lower()
            if equipment_status not in VALID_EQUIPMENT_STATUSES:
                handler.send_json({'error':'Equipment status is invalid.'},400);return
            value=None
            if equipment_status == 'reading':
                try:value=float(record.get('value'))
                except Exception:
                    handler.send_json({'error':'Temperature must be numeric for a reading.'},400);return
                if value < -60 or value > 120:
                    handler.send_json({'error':'Temperature reading is outside the supported range.'},400);return
            notes=str(record.get('notes') or '').strip()
            if equipment_status in ('out_of_order','awaiting_repair') and not notes:
                handler.send_json({'error':'A fault/action note is required for this equipment status.'},400);return
            if not row_id:
                handler.send_json({'error':'Replacement temperature record needs an id.'},400);return
            item=dict(record)
            item.update({
                'id':row_id,'appId':app_id,'value':value,'equipmentStatus':equipment_status,'period':period,
                'by':str(user.get('username') or record.get('by') or '')[:80],
                'source':'manager-backfill-status' if equipment_status!='reading' else 'manager-backfill',
                'notes':notes,'corrected':True
            })
        if not remove_ids and item is None:
            handler.send_json({'error':'Temperature change contains nothing to update.'},400);return
        cleaned.append({'appId':app_id,'removeIds':remove_ids,'record':item})

    removed_ids=[]; inserted=[]; previous=[]; venue_id=user['tenantId']
    with app.connect() as conn:
        try:
            with conn.cursor() as cur:
                for op in cleaned:
                    ids=op['removeIds']
                    if ids:
                        cur.execute("""SELECT id,app_id,value,ts,period,recorded_by,source,payload
                                       FROM tenant_temperature_readings
                                       WHERE venue_id=%s AND id = ANY(%s)
                                       FOR UPDATE""",(venue_id,ids))
                        old_rows=cur.fetchall()
                        found={str(r['id']) for r in old_rows}
                        if found != set(ids):
                            conn.rollback();handler.send_json({'error':'One of the temperature records changed or was already removed. Reopen the round and try again.'},409);return
                        if any(str(r['app_id'])!=op['appId'] for r in old_rows):
                            conn.rollback();handler.send_json({'error':'Temperature correction did not match the selected appliance.'},400);return
                        previous.extend([_public_row(r) for r in old_rows])
                        cur.execute('DELETE FROM tenant_temperature_readings WHERE venue_id=%s AND id = ANY(%s)',(venue_id,ids))
                        removed_ids.extend(ids)

                    item=op['record']
                    if item is not None:
                        cur.execute("""INSERT INTO tenant_temperature_readings(venue_id,id,app_id,value,ts,period,recorded_by,source,payload)
                                       VALUES(%s,%s,%s,%s,%s::timestamptz,%s,%s,%s,%s::jsonb)
                                       RETURNING id,app_id,value,ts,period,recorded_by,source,payload""",
                                    (venue_id,item['id'],item['appId'],item['value'],item['ts'],item['period'],item['by'],item['source'],
                                     json.dumps(item,ensure_ascii=False,separators=(',',':'))))
                        inserted.append(_public_row(cur.fetchone()))

                cur.execute('INSERT INTO server_audit(username,action,revision,details) VALUES(%s,%s,%s,%s::jsonb)',
                            (user['username'],'correct_temperature_round',stored['revision'],
                             json.dumps({'venueId':venue_id,'removedIds':removed_ids,'previous':previous,'replacement':inserted,
                                         'reason':str(payload.get('reason') or 'manager temperature correction')[:200]},
                                        ensure_ascii=False,separators=(',',':'))))
            conn.commit()
        except Exception:
            conn.rollback();raise

    handler.send_json({'ok':True,'removedIds':removed_ids,'readings':inserted})
'''
    store.write_text(st, encoding='utf-8')

# Wire the atomic correction endpoint into the live server.
sv = server.read_text(encoding='utf-8')
if "path == '/api/temperature-round/correct'" not in sv:
    marker = """        if path == '/api/temperature-readings':
            try:
                payload = self.read_json()
            except Exception as exc:
                self.send_json({'error': str(exc)}, 400)
                return
            temperature_store.append_readings(self, payload)
            return
"""
    insert = """        if path == '/api/temperature-round/correct':
            try:
                payload = self.read_json()
            except Exception as exc:
                self.send_json({'error': str(exc)}, 400)
                return
            temperature_store.correct_round(self, payload)
            return
""" + marker
    if marker not in sv:
        raise SystemExit('Temperature POST route marker not found while adding round correction endpoint')
    sv = sv.replace(marker, insert, 1)
server.write_text(sv, encoding='utf-8')

# Replace the historic round editor with a single correction-aware workflow.
js = fixes.read_text(encoding='utf-8')
start = js.find('  function backfillRound(date,period){')
end = js.find('\n  const originalTempHistory=tempHistory;', start)
if start < 0 or end < 0:
    raise SystemExit('Could not locate historic temperature round editor')

new_func = r'''  function backfillRound(date,period){
    if(!isMgr()){toast('Managers can update a historic temperature round','warn');return;}
    const units=coldUnits();
    const labels=(typeof TEMP_EQUIPMENT_STATUSES!=='undefined'?TEMP_EQUIPMENT_STATUSES:{reading:'Reading',out_of_order:'Out of order',not_in_use:'Not in use',defrosting:'Defrosting',awaiting_repair:'Awaiting repair'});
    const actionStatuses=new Set(['out_of_order','awaiting_repair']);
    const b=el('div',{});
    const dateInp=el('input',{class:'inp',type:'date',value:date,max:todayISO()});
    const periodInp=el('select',{class:'inp'},el('option',{value:'am'},'Morning (AM)'),el('option',{value:'pm'},'Evening (PM)'));
    periodInp.value=period;
    b.append(el('div',{class:'grid g2'},lf('Date',dateInp),lf('Round',periodInp)));
    const progress=el('div',{class:'muted',style:'font-size:13px;margin:10px 0 4px'});
    b.append(progress);
    b.append(el('p',{class:'muted',style:'font-size:12.5px;margin-top:6px'},
      'Use the actual reading or equipment status that applied to that round. If you do not know it, leave it missing. Existing records can be corrected here; unchanged rows are left alone.'));
    const values={};
    const host=el('div',{}); b.append(host);

    const slotRecords=(appId,ds,p)=>(STATE.tempReadings||[]).filter(r=>r&&r.appId===appId&&String(r.ts||'').slice(0,10)===ds&&slotForReading(r)===p);
    const displayRecord=r=>typeof tempReadingDisplay==='function'?tempReadingDisplay(r):(r&&r.value!=null?r.value+'°C':(r&&r.equipmentStatus)||'status');
    const hasValue=r=>typeof tempRecordHasValue==='function'?tempRecordHasValue(r):!!(r&&r.value!==null&&r.value!==''&&Number.isFinite(Number(r.value)));

    function draw(){
      host.innerHTML='';
      Object.keys(values).forEach(k=>delete values[k]);
      let recorded=0;
      units.forEach(a=>{
        const existingRows=slotRecords(a.id,dateInp.value,periodInp.value);
        const existing=existingRows.length?existingRows[existingRows.length-1]:null;
        if(existing)recorded++;

        const row=el('div',{class:'card',style:'background:var(--bg2);padding:10px;margin:8px 0'});
        row.append(el('div',{class:'dk-t',style:'margin-bottom:7px'},a.name));
        if(existing){
          row.append(el('div',{class:'muted',style:'font-size:12px;margin:-2px 0 7px'},
            'Recorded: '+displayRecord(existing)+' · change it below only if it is wrong'));
        }

        const mode=el('select',{class:'inp'});
        mode.append(el('option',{value:''},'Leave missing'));
        Object.entries(labels).forEach(([k,l])=>mode.append(el('option',{value:k},l)));
        const inp=el('input',{class:'inp num mono',type:'number',step:'0.1',placeholder:'°C'});
        const note=el('input',{class:'inp',type:'text',placeholder:'Fault / action / note',style:'display:none;grid-column:1/-1'});
        const controls=el('div',{style:'display:grid;grid-template-columns:minmax(145px,1fr) minmax(90px,110px);gap:8px'});
        controls.append(mode,inp,note);

        const initialStatus=existing?(hasValue(existing)?'reading':String(existing.equipmentStatus||'')):'';
        mode.value=initialStatus;
        if(existing&&initialStatus==='reading')inp.value=Number(existing.value);
        if(existing&&initialStatus!=='reading')note.value=String(existing.notes||'');

        const paint=()=>{
          const status=mode.value;
          inp.disabled=status!=='reading';
          if(status!=='reading')inp.value='';
          note.style.display=status&&status!=='reading'?'block':'none';
        };
        mode.addEventListener('change',paint);
        paint();

        values[a.id]={existingRows,existing,mode,inp,note};
        row.append(controls); host.append(row);
      });
      progress.textContent=(dateInp.value||'')+' '+String(periodInp.value||'').toUpperCase()+' · '+recorded+'/'+units.length+' recorded. Update only the rows that need correcting.';
      if(typeof window.CDCTemperatureSignControl==='object'&&window.CDCTemperatureSignControl&&typeof window.CDCTemperatureSignControl.refresh==='function'){
        setTimeout(()=>window.CDCTemperatureSignControl.refresh(),0);
      }
    }

    dateInp.addEventListener('change',draw);periodInp.addEventListener('change',draw);draw();

    const m=modal({title:'Update temperature round',body:b,footer:[
      el('button',{class:'btn ghost',html:'Cancel',onclick:()=>m.close()}),
      el('button',{class:'btn primary',html:icon('save')+'Save changes',onclick:async()=>{
        const ds=dateInp.value,p=periodInp.value;
        if(!ds||ds>todayISO()){toast('Choose a valid past date','warn');return;}

        const operations=[];
        const sameText=(a,b)=>String(a||'').trim()===String(b||'').trim();

        for(const a of units){
          const d=values[a.id]; if(!d)continue;
          const existing=d.existing;
          const existingRows=d.existingRows||[];
          const status=String(d.mode.value||'');
          const note=String(d.note.value||'').trim();
          const existingStatus=existing?(hasValue(existing)?'reading':String(existing.equipmentStatus||'')):'';
          const existingNote=existing?String(existing.notes||'').trim():'';
          const existingValue=existing&&hasValue(existing)?Number(existing.value):null;
          const value=status==='reading'&&d.inp.value!==''?Number(String(d.inp.value).replace(',','.')):null;

          if(status==='reading'&&(value==null||!Number.isFinite(value))){
            toast('Enter a temperature for '+a.name+' or choose another status','warn');return;
          }
          if(actionStatuses.has(status)&&!note){
            toast('Add a fault/action note for '+a.name,'warn');return;
          }

          let changed=false;
          if(existing){
            if(status!==existingStatus)changed=true;
            else if(status==='reading'&&Number(value)!==Number(existingValue))changed=true;
            else if(status&&status!=='reading'&&!sameText(note,existingNote))changed=true;
            else if(!status)changed=true;
          }else if(status){
            changed=true;
          }
          if(!changed)continue;

          let record=null;
          if(status){
            record=status==='reading'
              ?{id:uid('t'),appId:a.id,value:Number(value),equipmentStatus:'reading',ts:ds+'T'+(p==='am'?'09:00:00':'17:00:00'),period:p,by:ME.username,source:'manager-backfill',backfilled:true,enteredAt:nowISO(),enteredVia:'historic-round-update',notes:'',photo:null}
              :{id:uid('t'),appId:a.id,value:null,equipmentStatus:status,statusLabel:labels[status]||status,ts:ds+'T'+(p==='am'?'09:00:00':'17:00:00'),period:p,by:ME.username,source:'manager-backfill-status',backfilled:true,enteredAt:nowISO(),enteredVia:'historic-round-update',notes:note,photo:null};
          }
          operations.push({appId:a.id,removeIds:existingRows.map(r=>r.id).filter(Boolean),record});
        }

        if(!operations.length){toast('No changes to save','warn');return;}

        try{
          let removedIds=[],savedRows=[];
          if(serverMode){
            const res=await api('/api/temperature-round/correct',{method:'POST',body:JSON.stringify({operations,reason:'temperature round updated'})});
            if(!res||res.ok!==true)throw new Error((res&&res.error)||'Temperature update failed');
            removedIds=Array.isArray(res.removedIds)?res.removedIds:[];
            savedRows=Array.isArray(res.readings)?res.readings:[];
          }else{
            removedIds=operations.flatMap(op=>op.removeIds||[]);
            savedRows=operations.map(op=>op.record).filter(Boolean);
          }

          const removed=new Set(removedIds);
          STATE.tempReadings=(STATE.tempReadings||[]).filter(r=>!removed.has(r.id));
          savedRows.forEach(r=>{if(!STATE.tempReadings.some(x=>x.id===r.id))STATE.tempReadings.push(r);});

          if(typeof audit==='function')audit('temp_record_updated',ds+' '+p.toUpperCase()+' · '+operations.length+' temperature record change'+(operations.length===1?'':'s'));
          if(typeof save==='function')save('temperature round update');
          if(typeof persist==='function')await persist('temperature round update');

          m.close();
          toast(operations.length+' temperature record change'+(operations.length===1?'':'s')+' saved','ok');
          rerender();
        }catch(err){
          console.error('temperature round update failed',err);
          toast((err&&err.message)||'Temperature changes were not saved','bad');
        }
      }})
    ]});
  }
'''
js = js[:start] + new_func + js[end:]
fixes.write_text(js, encoding='utf-8')

# Make the History gap action use the same authoritative round editor rather
# than a second, slightly different backfill form.
if gap.exists():
    gj = gap.read_text(encoding='utf-8')
    gs = gj.find('    function fillGap(gap){')
    ge = gj.find('\n\n    function gapCard(){', gs)
    if gs >= 0 and ge >= 0:
        gj = gj[:gs] + r'''    function fillGap(gap){
      if(typeof backfillRound==='function')return backfillRound(gap.date,String(gap.period||'AM').toLowerCase());
      return toast('Temperature round editor is not available','bad');
    }''' + gj[ge:]
        gap.write_text(gj, encoding='utf-8')

# Cache-bust both historical temperature scripts in every place the server or
# HTML may reference them.
sv = server.read_text(encoding='utf-8')
sv = re.sub(r'kitchen_fixes_20260810\.js\?v=[^"\']+', 'kitchen_fixes_20260810.js?v=20260923-roundfix2', sv)
sv = re.sub(r'temperature_gap_fill\.js\?v=[^"\']+', 'temperature_gap_fill.js?v=20260923-roundfix2', sv)
server.write_text(sv, encoding='utf-8')

index = app / 'index.html'
if index.exists():
    ht = index.read_text(encoding='utf-8')
    ht = re.sub(r'kitchen_fixes_20260810\.js\?v=[^"\']+', 'kitchen_fixes_20260810.js?v=20260923-roundfix2', ht)
    ht = re.sub(r'temperature_gap_fill\.js\?v=[^"\']+', 'temperature_gap_fill.js?v=20260923-roundfix2', ht)
    index.write_text(ht, encoding='utf-8')

# The app's runtime loader appends its own cache key to modules. Bust that too;
# otherwise a phone can keep the old "Fill missed temperature round" code even
# though the corrected script exists on the server.
runtime_loader = app / 'runtime_loader.js'
if runtime_loader.exists():
    rt = runtime_loader.read_text(encoding='utf-8')
    rt = re.sub(r'kitchen_fixes_20260810\.js\?v=[^"\']+', 'kitchen_fixes_20260810.js?v=20260923-roundfix2', rt)
    rt = re.sub(r'temperature_gap_fill\.js\?v=[^"\']+', 'temperature_gap_fill.js?v=20260923-roundfix2', rt)
    rt = re.sub(r"\?runtime=[^'\"]+", '?runtime=20260923-roundfix2', rt)
    runtime_loader.write_text(rt, encoding='utf-8')

for guard_name in ('temperature_reset_guard.js','runtime_guard.js'):
    guard = app / guard_name
    if guard.exists():
        gt = guard.read_text(encoding='utf-8')
        gt = re.sub(r"runtime_loader\.js\?v=[^'\"]+", 'runtime_loader.js?v=20260923-roundfix2', gt)
        guard.write_text(gt, encoding='utf-8')

# Build-time checks: fail rather than deploy a UI that can appear editable but
# has no atomic correction endpoint behind it.
final_store = store.read_text(encoding='utf-8')
final_server = server.read_text(encoding='utf-8')
final_fixes = fixes.read_text(encoding='utf-8')
if 'def correct_round(handler, payload):' not in final_store:
    raise SystemExit('Temperature round correction backend missing')
if "path == '/api/temperature-round/correct'" not in final_server:
    raise SystemExit('Temperature round correction route missing')
if "modal({title:'Update temperature round'" not in final_fixes or "api('/api/temperature-round/correct'" not in final_fixes:
    raise SystemExit('Temperature round correction UI missing')
if runtime_loader.exists() and '?runtime=20260923-roundfix2' not in runtime_loader.read_text(encoding='utf-8'):
    raise SystemExit('Temperature round correction runtime cache-bust missing')
print('Temperature historic rounds are editable/correctable, atomically saved and cache-busted')
