from pathlib import Path
import re
import shutil

app_dir = Path('app')
shutil.copyfile('manager_controls_v3.js', app_dir / 'manager_controls_v3.js')

# Load only the v3 controls so old DOM-patching experiments cannot interfere.
index = app_dir / 'index.html'
html = index.read_text(encoding='utf-8')
html = re.sub(r'\s*<script src="manager_(?:remove_controls(?:_v2)?|controls_v3)\.js(?:\?[^\"]*)?"></script>\s*', '\n', html)
tag = '<script src="manager_controls_v3.js?v=20260915-1"></script>'
if '</body>' not in html:
    raise SystemExit('Could not locate </body> in index.html')
html = html.replace('</body>', tag + '\n</body>', 1)
index.write_text(html, encoding='utf-8')

# Serve the new browser asset.
server = app_dir / 'server.py'
server_text = server.read_text(encoding='utf-8')
marker = 'RUNTIME_FILES = (\n'
line = "    '/manager_controls_v3.js',\n"
if line not in server_text:
    if marker not in server_text:
        raise SystemExit('RUNTIME_FILES marker not found in server.py')
    server_text = server_text.replace(marker, marker + line, 1)
server.write_text(server_text, encoding='utf-8')

# Treat legacy admin/administrator roles as manager-equivalent for manager endpoints.
auth = app_dir / 'auth_controls.py'
text = auth.read_text(encoding='utf-8')
text = text.replace("if manager.get('role') != 'manager': handler.send_json({'error':'Manager access required.'},403); return",
                    "if str(manager.get('role','')).lower() not in ('manager','admin','administrator'): handler.send_json({'error':'Manager access required.'},403); return")
text = text.replace("if manager.get('role') != 'manager': handler.send_json({'error':'Admin access required.'},403); return",
                    "if str(manager.get('role','')).lower() not in ('manager','admin','administrator'): handler.send_json({'error':'Admin access required.'},403); return")
text = text.replace("u.get('role')=='manager' and u.get('active',True)",
                    "str(u.get('role','')).lower() in ('manager','admin','administrator') and u.get('active',True)")
auth.write_text(text, encoding='utf-8')

# Build self-checks.
final_html = index.read_text(encoding='utf-8')
final_server = server.read_text(encoding='utf-8')
if final_html.count(tag) != 1:
    raise SystemExit('manager_controls_v3 script tag not installed exactly once')
if "'/manager_controls_v3.js'" not in final_server:
    raise SystemExit('manager_controls_v3 static route missing')
print('Manager edit/remove controls v3 installed')
