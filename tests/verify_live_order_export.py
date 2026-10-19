"""Read-only live release check for the new public static ordering assets."""
from __future__ import annotations
import time
from urllib.request import Request, urlopen

BASE = "https://command-de-cuisine.onrender.com"
CHECKS = (
    ("/api/health", None),
    ("/full_stock_html_export.js?v=20261019-full-list1", "Download full ordering sheet"),
    ("/full_stock_order_template.html?v=20261019-full1", 'id="selectedOrderPanel"'),
    ("/full_stock_order_template.html?v=20261019-full1", "function saveSelectedHtml()"),
)
MAX_ATTEMPTS = 24
for attempt in range(1, MAX_ATTEMPTS + 1):
    failed = []
    for path, marker in CHECKS:
        try:
            req = Request(BASE + path, headers={"User-Agent": "Command-de-Cuisine-release-check/1.0"})
            with urlopen(req, timeout=25) as response:
                body = response.read(240_000).decode("utf-8", errors="replace")
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}")
                if marker and marker not in body:
                    raise RuntimeError("Expected ordering feature is not served")
        except Exception as exc:
            failed.append(f"{path}: {exc}")
    if not failed:
        print("PASS: Live Render health and complete ordering exporter assets verified")
        break
    print(f"Deployment check {attempt}/{MAX_ATTEMPTS}: " + "; ".join(failed), flush=True)
    if attempt == MAX_ATTEMPTS:
        raise SystemExit("Live ordering asset verification failed; inspect Render deployment")
    time.sleep(20)
