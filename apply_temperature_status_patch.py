from pathlib import Path

app_dir = Path('app')
index = app_dir / 'index.html'
text = index.read_text(encoding='utf-8')

marker = 'function latestReading(appId){ return STATE.tempReadings.filter(r=>r.appId===appId).sort((a,b)=>b.ts.localeCompare(a.ts))[0]; }'
helper = marker + '''\nconst TEMP_EQUIPMENT_STATUSES={reading:"Reading",out_of_order:"Out of order",not_in_use:"Not in use",defrosting:"Defrosting",awaiting_repair:"Awaiting repair"};\nfunction tempRecordHasValue(r){return !!r&&r.value!==null&&r.value!==""&&Number.isFinite(Number(r.value));}\nfunction tempRecordStatusLabel(r){if(!r)return"";return TEMP_EQUIPMENT_STATUSES[r.equipmentStatus]||r.statusLabel||"";}\nfunction tempReadingDisplay(r){if(!r)return"—";return tempRecordHasValue(r)?Number(r.value).toFixed(1)+"°C":(tempRecordStatusLabel(r)||"No temperature");}\nfunction tempRecordResult(a,r){if(!r)return"none";if(!tempRecordHasValue(r))return"status";return tempStatus(a,Number(r.value));}\nfunction tempStatusNeedsAction(k){return k==="out_of_order"||k==="awaiting_repair";}'''
if marker not in text:
    raise SystemExit('latestReading marker not found')
text = text.replace(marker, helper, 1)

start = text.index('function tempRound(v){')
end = text.index('function breachModal(apps){', start)
new_round = r'''function tempRound(v){
  const card=el("div",{class:"card"});
  card.append(el("div",{class:"card-head"},el("h3",{},"Temperature round"),el("div",{class:"spacer"}),
    el("span",{class:"chip",html:icon("clock")+new Date().toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit"})})));
  const grid=el("div",{class:"grid g2"});
  const draft={};
  const period=new Date().getHours()<12?"am":"pm";
  const today=todayISO();
  const coldUnits=STATE.appliances.filter(a=>a.type==="fridge"||a.type==="freezer");
  coldUnits.forEach(a=>{
    const r=latestReading(a.id);
    const doneNow=STATE.tempReadings.some(x=>x.appId===a.id&&x.ts.slice(0,10)===today&&(period==="am"?+x.ts.slice(11,13)<12:+x.ts.slice(11,13)>=12));
    const wrap=el("div",{class:"card",style:"background:var(--bg2);padding:14px"});
    const head=el("div",{style:"display:flex;align-items:center;gap:10px;margin-bottom:10px"});
    head.innerHTML=`<div style="flex:1"><b>${esc(a.name)}</b><div class="muted" style="font-size:12px">Target ≤ ${a.target}°C · limit ${a.critical}°C · last ${r?esc(tempReadingDisplay(r))+" "+fmtTime(r.ts):"—"}</div></div>`;
    const statusTag=el("span",{class:"tag "+(doneNow?"ok":"dim")},doneNow?"Done "+period.toUpperCase():"Due");
    head.append(statusTag);
    const line=el("div",{style:"display:grid;grid-template-columns:minmax(110px,1fr) minmax(110px,1fr);gap:8px"});
    const mode=el("select",{class:"inp"});
    Object.entries(TEMP_EQUIPMENT_STATUSES).forEach(([k,l])=>mode.append(el("option",{value:k},l)));
    const inp=el("input",{class:"inp num mono",type:"number",step:"0.1",placeholder:"°C",style:"text-align:right;font-size:18px"});
    const notes=el("textarea",{class:"inp",rows:"2",placeholder:"Fault / action / note",style:"grid-column:1/-1;display:none"});
    draft[a.id]={status:"reading",value:null,notes:""};
    function paint(){
      const d=draft[a.id];
      if(d.status!=="reading"){
        inp.disabled=true; inp.value=""; notes.style.display="block";
        statusTag.className="tag warn"; statusTag.textContent=TEMP_EQUIPMENT_STATUSES[d.status]; return;
      }
      inp.disabled=false; notes.style.display="none";
      const val=inp.value===""?null:+inp.value; d.value=val; const st=tempStatus(a,val);
      statusTag.className="tag "+(st==="ok"?"cold":st==="warn"?"warn":st==="danger"?"danger":"dim");
      statusTag.textContent=val==null?"—":st==="ok"?"In range":st==="warn"?"High":"BREACH";
    }
    mode.addEventListener("change",()=>{draft[a.id].status=mode.value;paint();});
    inp.addEventListener("input",paint);
    notes.addEventListener("input",()=>draft[a.id].notes=notes.value.trim());
    line.append(mode,inp,notes);
    const probe=STATE.probes.find(p=>p.appId===a.id&&p.type==="wifi");
    if(probe){ line.append(el("button",{class:"btn ghost icon",title:"Read "+probe.name,style:"grid-column:1/-1;justify-self:end",html:icon("probe"),onclick:()=>{
      if(serverMode){toast("Sensor integration not connected yet","warn");return;}
      mode.value="reading"; draft[a.id].status="reading";
      const val=+((a.type==="freezer"?-19:4)+(Math.random()*1.6-0.8)).toFixed(1);
      inp.value=val;paint();toast("Preview reading: "+val+"°C","ok");}})); }
    wrap.append(head,line); grid.append(wrap);
  });
  card.append(grid);
  const foot=el("div",{style:"display:flex;gap:10px;margin-top:16px;justify-content:flex-end"});
  foot.append(el("button",{class:"btn primary",html:icon("save")+"Save round",onclick:()=>{
    let n=0,breach=[],missingAction=[];
    coldUnits.forEach(a=>{
      const d=draft[a.id]||{};
      if(d.status==="reading"){
        if(d.value==null||!Number.isFinite(Number(d.value)))return;
        const val=Number(d.value);
        STATE.tempReadings.push({id:uid("t"),appId:a.id,value:val,equipmentStatus:"reading",ts:nowISO(),period,by:ME.username,source:"manual",notes:d.notes||"",photo:null});n++;
        if(tempStatus(a,val)==="danger")breach.push(a);
      }else if(d.status){
        if(tempStatusNeedsAction(d.status)&&!String(d.notes||"").trim()){missingAction.push(a.name);return;}
        STATE.tempReadings.push({id:uid("t"),appId:a.id,value:null,equipmentStatus:d.status,statusLabel:TEMP_EQUIPMENT_STATUSES[d.status],ts:nowISO(),period,by:ME.username,source:"manual-status",notes:String(d.notes||"").trim(),photo:null});n++;
      }
    });
    if(missingAction.length){toast("Add a fault/action note for "+missingAction.join(", "),"warn");return;}
    if(!n){toast("Enter at least one reading or equipment status","warn");return;}
    audit("temp_round",n+" temperature/status records");save("temp round");
    if(breach.length){ toast(breach.length+" breach logged — add corrective action","bad"); breachModal(breach); }
    else toast(n+" temperature/status records saved","ok");
    tempTab="round";rerender();
  }}));
  card.append(foot); v.append(card);
}
'''
text = text[:start] + new_round + text[end:]

start = text.index('function tempHistory(v){')
end = text.index('function tempTrends(v){', start)
new_history = r'''function tempHistory(v){
  const rows=STATE.tempReadings.slice().sort((a,b)=>b.ts.localeCompare(a.ts)).slice(0,120);
  v.append(sheet(
    [{key:"ts",label:"When",render:r=>`<span class="cell readonly mono">${fmtDate(r.ts)} ${fmtTime(r.ts)}</span>`,w:"120px"},
     {key:"appId",label:"Unit",render:r=>`<span class="cell readonly">${esc(appById(r.appId)?.name||"?")}</span>`},
     {key:"reading",label:"Reading / status",render:r=>`<span class="cell readonly">${esc(tempReadingDisplay(r))}</span>`},
     {key:"status",label:"Result",render:r=>{const a=appById(r.appId),st=a?tempRecordResult(a,r):"none";const label=st==="ok"?"In range":st==="warn"?"High":st==="danger"?"Breach":tempRecordStatusLabel(r)||"—";return `<div style="padding:8px 12px"><span class="tag ${st==="ok"?"cold":st==="warn"?"warn":st==="danger"?"danger":st==="status"?"warn":"dim"}">${esc(label)}</span></div>`;}},
     {key:"notes",label:"Notes",render:r=>`<span class="cell readonly">${esc(r.notes||"")}</span>`},
     {key:"source",label:"By",render:r=>`<span class="cell readonly">${esc(r.by||"")} · ${r.source==="probe"?"probe":r.source==="manual-status"?"status":"manual"}</span>`}],
    rows,{title:"Reading history",addable:false,
      onDelete:row=>{STATE.tempReadings=STATE.tempReadings.filter(x=>x.id!==row.id);save("delete reading");rerender();toast("Record removed","ok");}}));
}
'''
text = text[:start] + new_history + text[end:]

old = 'function readingSeries(appId){ return STATE.tempReadings.filter(r=>r.appId===appId).sort((a,b)=>a.ts.localeCompare(b.ts)).slice(-28).map(r=>({ts:r.ts,value:r.value})); }'
new = 'function readingSeries(appId){ return STATE.tempReadings.filter(r=>r.appId===appId&&tempRecordHasValue(r)).sort((a,b)=>a.ts.localeCompare(b.ts)).slice(-28).map(r=>({ts:r.ts,value:Number(r.value)})); }'
if old not in text: raise SystemExit('readingSeries marker not found')
text = text.replace(old,new,1)

text = text.replace('const temps=STATE.appliances.map(a=>{const r=latestReading(a.id);return a.name+": "+(r?r.value+"C":"no reading");}).join("; ");', 'const temps=STATE.appliances.map(a=>{const r=latestReading(a.id);return a.name+": "+(r?tempReadingDisplay(r):"no reading");}).join("; ");', 1)

old_gauge = '''    const r=latestReading(a.id); const st=r?tempStatus(a,r.value):"none";\n    const cls=st==="danger"?"danger":st==="warn"?"warn":"ok";\n    rail.append(el("div",{class:"gauge "+cls,html:`\n      <div class="gl">${esc(a.name)}</div>\n      <div class="gv">${r?r.value.toFixed(1):"—"}<small>°C</small></div>\n      <div class="gs" style="color:var(--${st==="danger"?"danger":st==="warn"?"warn":"cold"})">${st==="danger"?icon("alert"):icon("ok")} ${r?fmtTime(r.ts):"no reading"}</div>`}));'''
new_gauge = '''    const r=latestReading(a.id); const st=r?tempRecordResult(a,r):"none";\n    const cls=st==="danger"?"danger":st==="warn"||st==="status"?"warn":"ok";\n    const shown=r?tempReadingDisplay(r):"—";\n    rail.append(el("div",{class:"gauge "+cls,html:`\n      <div class="gl">${esc(a.name)}</div>\n      <div class="gv" style="font-size:${r&&!tempRecordHasValue(r)?'17px':'inherit'}">${esc(shown)}</div>\n      <div class="gs" style="color:var(--${st==="danger"?"danger":st==="warn"||st==="status"?"warn":"cold"})">${st==="danger"||st==="status"?icon("alert"):icon("ok")} ${r?fmtTime(r.ts):"no reading"}</div>`}));'''
if old_gauge not in text: raise SystemExit('dashboard gauge marker not found')
text = text.replace(old_gauge,new_gauge,1)

text = text.replace('const reportTemps=STATE.tempReadings.filter(r=>String(r.ts||"").slice(0,10)===todayISO());', 'const reportTemps=STATE.tempReadings.filter(r=>String(r.ts||"").slice(0,10)===todayISO()&&tempRecordHasValue(r));', 1)

old_pack = 'return `<tr><td>${fmtDate(r.ts)} ${fmtTime(r.ts)}</td><td>${esc(a?.name||"")}</td><td style="text-align:right">${r.value}°C</td><td>${st==="danger"?"<b style=\'color:#b3261e\'>BREACH</b>":st==="warn"?"High":"OK"}</td><td>${esc(r.by||"")}</td></tr>`;'
new_pack = 'const reading=tempRecordHasValue(r)?Number(r.value).toFixed(1)+"°C":tempRecordStatusLabel(r)||"No temperature"; const result=tempRecordHasValue(r)?(st==="danger"?"<b style=\'color:#b3261e\'>BREACH</b>":st==="warn"?"High":"OK"):esc(tempRecordStatusLabel(r)||"Status recorded"); return `<tr><td>${fmtDate(r.ts)} ${fmtTime(r.ts)}</td><td>${esc(a?.name||"")}</td><td style="text-align:right">${reading}</td><td>${result}${r.notes?" — "+esc(r.notes):""}</td><td>${esc(r.by||"")}</td></tr>`;'
if old_pack not in text: raise SystemExit('inspection pack row marker not found')
text = text.replace(old_pack,new_pack,1)

old_csv = 'const rows=[["Date","Time","Unit","Type","Reading_C","Status","LoggedBy","Source"]];'
new_csv = 'const rows=[["Date","Time","Unit","Type","Reading_C","EquipmentStatus","Result","Notes","LoggedBy","Source"]];'
if old_csv not in text: raise SystemExit('CSV header marker not found')
text = text.replace(old_csv,new_csv,1)
old_csv_row = 'rows.push([r.ts.slice(0,10),fmtTime(r.ts),a?.name||"",a?.type||"",r.value,st,r.by||"",r.source||""]);});'
new_csv_row = 'rows.push([r.ts.slice(0,10),fmtTime(r.ts),a?.name||"",a?.type||"",tempRecordHasValue(r)?r.value:"",tempRecordStatusLabel(r)||"Reading",tempRecordHasValue(r)?st:"status",r.notes||"",r.by||"",r.source||""]);});'
if old_csv_row not in text: raise SystemExit('CSV row marker not found')
text = text.replace(old_csv_row,new_csv_row,1)

index.write_text(text,encoding='utf-8')

fixes = app_dir / 'kitchen_fixes_20260810.js'
js = fixes.read_text(encoding='utf-8')
js = js.replace("const safe=logged.filter(x=>tempStatus(x.app,x.reading.value)!=='danger');", "const safe=logged.filter(x=>typeof tempRecordHasValue==='function'&&tempRecordHasValue(x.reading)&&tempStatus(x.app,x.reading.value)!=='danger');")
js = js.replace("if(r&&tempStatus(a,r.value)!=='danger')good++;", "if(r&&typeof tempRecordHasValue==='function'&&tempRecordHasValue(r)&&tempStatus(a,r.value)!=='danger')good++;")
fixes.write_text(js,encoding='utf-8')
