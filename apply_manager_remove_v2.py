from pathlib import Path
import re
import shutil

app_dir = Path('app')
shutil.copyfile('manager_remove_controls_v2.js', app_dir / 'manager_remove_controls_v2.js')

index = app_dir / 'index.html'
html = index.read_text(encoding='utf-8')
html = re.sub(r'\s*<script src="manager_remove_controls(?:_v2)?\.js(?:\?[^\"]*)?"></script>\s*', '\n', html)
tag = '<script src="manager_remove_controls_v2.js"></script>'
marker = '</body>'
if marker not in html:
    raise SystemExit('Could not locate </body> in index.html')
html = html.replace(marker, tag + '\n' + marker, 1)
index.write_text(html, encoding='utf-8')

server = app_dir / 'server.py'
text = server.read_text(encoding='utf-8')
runtime_marker = 'RUNTIME_FILES = (\n'
asset_line = "    '/manager_remove_controls_v2.js',\n"
if asset_line not in text:
    if runtime_marker not in text:
        raise SystemExit('RUNTIME_FILES marker not found in server.py')
    text = text.replace(runtime_marker, runtime_marker + asset_line, 1)
server.write_text(text, encoding='utf-8')

final_html = index.read_text(encoding='utf-8')
if final_html.count(tag) != 1:
    raise SystemExit('Cache-busted manager removal script not installed exactly once')
print('Cache-busted manager removal UI installed')
