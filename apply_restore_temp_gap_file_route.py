"""Restore the existing missing-temperature-log feature's static file route.

Do not alter UI logic, round calculations, backfill buttons, kitchen records,
credentials or historical readings. The original JS file is already shipped
in the release, but was accidentally omitted from server.py RUNTIME_FILES.
"""
from pathlib import Path

server=Path("app/server.py")
existing=Path("app/temperature_gap_fill.js")
if not server.is_file() or not existing.is_file():
    raise SystemExit("Missing server or original temperature_gap_fill.js")

source=server.read_text(encoding="utf-8")
start=source.find("RUNTIME_FILES = (")
end=source.find("\n)",start)
if start<0 or end<start:
    raise SystemExit("Static file whitelist has changed; cannot safely patch")
allowed=source[start:end]
target="'/temperature_gap_fill.js'"
if target in allowed:
    raise SystemExit("Original temperature gap file is already whitelisted")

needle="'/kitchen_fixes_20260810.js',"
if allowed.count(needle)!=1:
    raise SystemExit("Expected legacy temperature scripts whitelist marker missing")
allowed=allowed.replace(needle,needle+" '/temperature_gap_fill.js',",1)
source=source[:start]+allowed+source[end:]

# This original feature was being requested by the index page with a stale
# query string and 404 response. Bump only its script version so phones retry.
old='temperature_gap_fill.js?v=20261013-pmdue1'
new='temperature_gap_fill.js?v=20261101-staticroute1'
if source.count(old)!=1:
    raise SystemExit("Expected temperature-gap script tag has changed")
source=source.replace(old,new,1)
server.write_text(source,encoding="utf-8")
print("PASS: restored the original temperature gaps static route; no UI or data changes")
