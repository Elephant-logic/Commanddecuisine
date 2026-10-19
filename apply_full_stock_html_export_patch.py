"""Last-stage, additive offline full Stock HTML export. Does not touch stored kitchen data."""
from pathlib import Path
import re
import shutil

app = Path('app')
server = app / 'server.py'
index = app / 'index.html'
assets = ('full_stock_html_export.js', 'full_stock_order_template.html')
for name in assets:
    src = Path(name)
    if not src.exists():
        raise SystemExit('Missing complete Stock exporter asset: ' + name)
    shutil.copy2(src, app / name)

server_text = server.read_text(encoding='utf-8')
marker = 'RUNTIME_FILES = (\n'
if marker not in server_text:
    raise SystemExit('Missing runtime route marker for Stock exporter')
for name in assets:
    line = "    '/" + name + "',\n"
    if line not in server_text:
        server_text = server_text.replace(marker, marker + line, 1)
server.write_text(server_text, encoding='utf-8')

# Reliable photo-menu imports have an explicit successful-save point. Emit a
# browser-only signal so the ordering action is contextual immediately afterwards.
# No extra app-state write and no change to menu or recipe persistence.
reliable = app / 'reliable_menu_import.js'
if not reliable.exists():
    raise SystemExit('Reliable menu importer missing while linking ordering sheet')
reliable_text = reliable.read_text(encoding='utf-8')
saved_marker = "setStatus('Saved: '+savedMenu.dishIds.length+' dishes and recipes.');"
event_marker = "window.dispatchEvent(new CustomEvent('cdc:menu-saved'"
if event_marker not in reliable_text:
    if reliable_text.count(saved_marker) != 1:
        raise SystemExit('Could not locate unique successful menu-save confirmation')
    signal = (
        "try{window.dispatchEvent(new CustomEvent('cdc:menu-saved',"
        "{detail:{menuId:savedMenu.id,name:savedMenu.name}}));}catch(_){ }\n"
        "        "
    )
    reliable_text = reliable_text.replace(saved_marker, signal + saved_marker, 1)
    reliable.write_text(reliable_text, encoding='utf-8')

html = index.read_text(encoding='utf-8')
html = re.sub(r'\s*<script[^>]+src=["\']/?full_stock_html_export\.js(?:\?[^"\']*)?["\'][^>]*></script>\s*', '\n', html, flags=re.I)
tag = '<script src="/full_stock_html_export.js?v=20261019-full-list1"></script>'
if '</body>' not in html:
    raise SystemExit('Cannot locate closing body tag for Stock exporter')
html = html.replace('</body>', tag + '\n</body>', 1)
index.write_text(html, encoding='utf-8')

if index.read_text(encoding='utf-8').count(tag) != 1:
    raise SystemExit('Stock exporter was not installed exactly once')
if any(server.read_text(encoding='utf-8').count("'/" + name + "'") != 1 for name in assets):
    raise SystemExit('One or more Stock HTML static routes are missing or duplicated')
print('Complete standalone Stock ordering HTML installed (no stock-level filtering or data writes)')