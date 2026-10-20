"""Read-only inspect delivery/supplier entry points from the assembled release."""
from pathlib import Path
import re
files=("app/main_app.js","app/index.html","app/operations_upgrade.js","app/contacts_directory.js")
terms=[
 "VIEWS.deliveries=function(v){","VIEWS.suppliers=function(v){",
 "VIEWS.contacts=function(v){","VIEWS.delivery=function(v){",
 "function editDelivery(","function editSupplier(","function editStock(",
 "VIEWS.stock=function(v){", "STATE.suppliers",
 "chilledTemp","frozenTemp","frozenTemperature",
 "chilledTemperature","deliveryTemp","temperature",
 "supplier","contact","Receiving"
]
for name in files:
 p=Path(name)
 if not p.exists():continue
 s=p.read_text(encoding="utf-8")
 print("SOURCE",name,"SIZE",len(s))
 for t in terms:
  indices=[m.start() for m in re.finditer(re.escape(t),s,re.IGNORECASE)]
  if not indices:continue
  print("  TERM",t,"MATCHES",len(indices))
  for ix in indices[:4 if t in ("supplier","contact","temperature") else 7]:
   lo=max(0,ix-280);hi=min(len(s),ix+(4200 if t.startswith(("VIEWS.","function edit")) else 500))
   text=s[lo:hi].replace("\n","\\n")
   print("  OFFSET",ix,"SNIPPET",text)
