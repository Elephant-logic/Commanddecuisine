"""Read-only live check of the original missed-round workflow after deploy."""
import time
from urllib.request import Request,urlopen

host="https://command-de-cuisine.onrender.com"
expect={
  "/":'temperature_gap_fill.js?v=20261101-staticroute1',
  "/temperature_gap_fill.js?v=20261101-staticroute1":"Temperature gaps",
  "/kitchen_fixes_20260810.js?v=20261013-pmdue1":"Temperature coverage — last 7 days"
}
for attempt in range(1,25):
    missing=[]
    for route,needle in expect.items():
        try:
            req=Request(host+route,headers={
                "Cache-Control":"no-cache",
                "User-Agent":"CDC-original-temperature-gaps-live-verification/1.0"
            })
            with urlopen(req,timeout=20) as response:
                body=response.read(400000).decode("utf-8",errors="replace")
                if response.status!=200 or needle not in body:
                    missing.append(route+" not ready")
                if route.startswith("/temperature_gap_fill.js") and "Fill missing" not in body:
                    missing.append(route+" lacks original Fill missing button")
        except Exception as exc:
            missing.append(route+": "+str(exc))
    if not missing:
        print("PASS: Live Render serves original Temperature gaps and Fill missing controls")
        break
    print("Deployment check "+str(attempt)+"/24: "+"; ".join(missing),flush=True)
    if attempt==24:raise SystemExit("Original missed-round controls not verified live")
    time.sleep(20)
