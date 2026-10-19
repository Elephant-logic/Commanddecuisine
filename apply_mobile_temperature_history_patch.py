"""Show readable, status-aware temperature history cards on small phones.

This is a presentation-only change. Desktop retains the original table and
the existing manager correction tools remain installed after the renderer.
"""
from pathlib import Path
p=Path("app/main_app.js")
index=Path("app/index.html")
s=p.read_text(encoding="utf-8")
anchor='''  function tempHistory(v){
    const rows=STATE.tempReadings.slice().sort((a,b)=>b.ts.localeCompare(a.ts)).slice(0,120);
'''
mobile='''  function tempHistory(v){
    const rows=STATE.tempReadings.slice().sort((a,b)=>b.ts.localeCompare(a.ts)).slice(0,120);
    if(typeof window!=="undefined"&&window.matchMedia&&window.matchMedia("(max-width: 650px)").matches){
      const list=el("div",{class:"cdc-mobile-temp-history",style:"display:grid;gap:9px"});
      list.append(el("h3",{style:"font-size:16px;margin:0 0 5px"},"Reading history"));
      if(!rows.length)list.append(el("div",{class:"card muted"},"No recorded temperatures or equipment statuses yet."));
      rows.forEach(r=>{
        const a=appById(r.appId),st=a?tempRecordResult(a,r):"none";
        const result=st==="ok"?"In range":st==="warn"?"High":st==="danger"?"Breach":tempRecordStatusLabel(r)||"Status";
        const cls=st==="ok"?"cold":st==="warn"||st==="status"?"warn":st==="danger"?"danger":"dim";
        const card=el("div",{class:"card",style:"padding:12px 14px;min-width:0"});
        const top=el("div",{style:"display:flex;gap:9px;justify-content:space-between;align-items:flex-start;flex-wrap:wrap"});
        top.append(el("strong",{style:"font-size:15px"},a?a.name:"Unknown unit"));
        top.append(el("span",{class:"tag "+cls},tempReadingDisplay(r)));
        card.append(top);
        card.append(el("div",{class:"muted",style:"font-size:12px;margin-top:6px"},
          fmtDate(r.ts)+" "+fmtTime(r.ts)+" · "+result));
        if(String(r.notes||"").trim())card.append(el("div",{style:"font-size:12px;margin-top:6px;white-space:pre-wrap;overflow-wrap:anywhere"},"Note: "+r.notes));
        card.append(el("div",{class:"muted",style:"font-size:11px;margin-top:4px"},"By "+(r.by||"—")));
        list.append(card);
      });
      v.append(list);
      return;
    }
'''
if s.count(anchor)!=1:raise SystemExit("Cannot uniquely locate temperature history renderer")
p.write_text(s.replace(anchor,mobile,1),encoding="utf-8")
html=index.read_text(encoding="utf-8")
old='main_app.js?v=20261020-kitchen-stock1'
if html.count(old)!=1:raise SystemExit("Expected Stock patch cache marker missing")
index.write_text(html.replace(old,"main_app.js?v=20261020-stock-mobile1",1),encoding="utf-8")
print("PASS: compact phone temperatures display measurement, equipment status and notes without editing data")
