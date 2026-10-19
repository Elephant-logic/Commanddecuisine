"""Read-only confirmation that the fixed Kitchen Tools script reached Render."""
from __future__ import annotations
import time
from urllib.request import Request, urlopen

HOST="https://command-de-cuisine.onrender.com"
MARKER="const before=timers.map(t=>t.id+':'+t.status).join('|')"
KEY="/kitchen_tools_v2.js?v=20261019-timer-controls1"
for attempt in range(1,25):
    problems=[]
    for path,marker in (("/api/health",None),(KEY,MARKER)):
        try:
            request=Request(HOST+path,headers={"User-Agent":"Command-de-Cuisine-Timer-Release-Check/1.0"})
            with urlopen(request,timeout=20) as response:
                body=response.read(60_000).decode("utf-8",errors="replace")
                if response.status!=200 or (marker is not None and marker not in body):
                    problems.append(path+" missing new timer fix")
        except Exception as exc:
            problems.append(path+" "+str(exc))
    if not problems:
        print("PASS: Live Render website is serving the corrected timer controls")
        break
    print(f"Deploy probe {attempt}/24: "+"; ".join(problems),flush=True)
    if attempt==24:
        raise SystemExit("Live timer asset was not verified")
    time.sleep(20)
