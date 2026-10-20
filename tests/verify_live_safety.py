"""Read-only verification that the safety/recipe client reached Render."""
import time
from urllib.request import Request,urlopen

HOST="https://command-de-cuisine.onrender.com"
CHECKS=(
    ("/api/health",None),
    ("/","main_app.js?v=20261020-dual-delivery-temp1"),
    ("/main_app.js?v=20261020-dual-delivery-temp1","const isNew=!r, original=r;"),
    ("/main_app.js?v=20261020-dual-delivery-temp1",
     "const known=s.qtyKnown===true,step=stockUnitStep(s.unit)"),
    ("/main_app.js?v=20261020-dual-delivery-temp1",
     "cdc-mobile-temp-history"),
    ("/main_app.js?v=20261020-dual-delivery-temp1",
     'if(tempTab==="repairs")return VIEWS.maintenance(v);'),
    ("/main_app.js?v=20261020-dual-delivery-temp1","cdc-delivery-chilled"),
    ("/main_app.js?v=20261020-dual-delivery-temp1","cdc-delivery-frozen"),
    ("/main_app.js?v=20261020-dual-delivery-temp1","function cdcSupplierNames(){"),
    ("/allergen_matrix_safety.js?v=20261020-kitchen-safety1",
     "Only a manager can edit and verify ingredient allergens.")
)
for attempt in range(1,25):
    missing=[]
    for path,marker in CHECKS:
        try:
            req=Request(HOST+path,headers={"User-Agent":"Command-de-Cuisine-Safety-Release-Check/1.0",
                                            "Cache-Control":"no-cache"})
            with urlopen(req,timeout=20) as response:
                raw=response.read(1_000_000).decode("utf-8",errors="replace")
                if response.status!=200 or (marker and marker not in raw):
                    missing.append(path+" lacks current release marker")
        except Exception as exc:
            missing.append(path+": "+str(exc))
    if not missing:
        print("PASS: Render is healthy and serves the new kitchen safety and mobile operational UI")
        break
    print("Deploy probe "+str(attempt)+"/24: "+"; ".join(missing),flush=True)
    if attempt==24:raise SystemExit("Live safety release not verified")
    time.sleep(20)
