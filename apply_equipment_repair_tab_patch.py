"""Expose existing Maintenance register from Temperatures without creating records.

No temperature, incident or maintenance records are inserted automatically.
Staff can report equipment faults; managers close/reopen repair tickets.
"""
from pathlib import Path
p=Path("app/main_app.js")
idx=Path("app/index.html")
s=p.read_text(encoding="utf-8")
old='[["round","Log round"],["history","History"],["trends","Trends"],["probes","Probes"]]'
new='[["round","Log round"],["history","History"],["trends","Trends"],["repairs","Repairs"],["probes","Probes"]]'
if s.count(old)!=1:raise SystemExit("Unexpected Temperature navigation shape")
s=s.replace(old,new,1)
marker='if(tempTab==="probes")return tempProbes(v);'
start=s.find(new)
stop=s.find(marker,start)
if start<0 or stop<0:raise SystemExit("Cannot locate Temperature tab switch")
s=s[:stop]+'if(tempTab==="repairs")return VIEWS.maintenance(v);'+chr(10)+'    '+s[stop:]
# Existing maintenance log allows any staff member to close a repair job.
# Reporting a fault remains available, completion needs manager confirmation.
old='row.append(el("button",{class:"btn sm ghost",html:m.status==="closed"?"Reopen":"Close"'
new='if(isMgr())row.append(el("button",{class:"btn sm ghost",html:m.status==="closed"?"Reopen":"Close"'
if s.count(old)!=1:raise SystemExit("Cannot locate maintenance job close control")
s=s.replace(old,new,1)
p.write_text(s,encoding="utf-8")
html=idx.read_text(encoding="utf-8")
old='main_app.js?v=20261020-stock-mobile1'
if html.count(old)!=1:raise SystemExit("Expected mobile release cache marker")
idx.write_text(html.replace(old,'main_app.js?v=20261020-stock-mobile-repairs1',1),encoding="utf-8")
print("PASS: Existing maintenance register now accessible as Repairs in Temperatures, with manager-only closure")
