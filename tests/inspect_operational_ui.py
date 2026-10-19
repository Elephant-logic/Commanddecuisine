"""Read-only locate stock, repair and temperature-history views in release."""
from pathlib import Path
import re
for path in ["app/main_app.js","app/index.html","app/operations_upgrade.js"]:
    p=Path(path)
    if not p.exists():continue
    s=p.read_text(encoding="utf-8")
    print("#####",path,len(s))
    patterns=(
      "VIEWS.stock=function(v){",
      "function stockRow(s){",
      "function tempHistory(v){",
      "VIEWS.temps=function(v){",
      "function tempRound(v){",
      "VIEWS.home=function(v){",
      "VIEWS.daily=function(v){",
      "VIEWS.maintenance=function(v){",
      "function editMaintenance(",
      "function editMaint(",
      "STATE.maintenance",
      "maintenance",
      "function save(reason)",
      "const stock"
    )
    for pat in patterns:
        matches=[m.start() for m in re.finditer(re.escape(pat),s,re.I)]
        if matches:
            print("MATCH",repr(pat),"count",len(matches))
            for x in matches[:2]:
                size=8500 if pat.startswith("VIEWS.stock") or pat.startswith("function tempHistory") else 3000
                print(s[max(0,x-180):x+size].replace("\n","\n  ")[:size+180])
