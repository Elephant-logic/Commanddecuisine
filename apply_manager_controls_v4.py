from pathlib import Path
import re
import shutil

app_dir = Path('app')
shutil.copyfile('manager_controls_v4.js', app_dir / 'manager_controls_v4.js')

# Load only the v4 manager UI and cache-bust it aggressively.
index = app_dir / 'index.html'
html = index.read_text(encoding='utf-8')
html = re.sub(r'\s*<script src="manager_(?:remove_controls(?:_v2)?|controls_v3|controls_v4)\.js(?:\?[^\"]*)?"></script>\s*', '\n', html)
tag = '<script src="manager_controls_v4.js?v=20260915-0340"></script>'
if '</body>' not in html:
    raise SystemExit('Could not locate </body> in index.html')
html = html.replace('</body>', tag + '\n</body>', 1)
index.write_text(html, encoding='utf-8')

# Serve the v4 static asset.
server = app_dir / 'server.py'
server_text = server.read_text(encoding='utf-8')
marker = 'RUNTIME_FILES = (\n'
line = "    '/manager_controls_v4.js',\n"
if line not in server_text:
    if marker not in server_text:
        raise SystemExit('RUNTIME_FILES marker not found in server.py')
    server_text = server_text.replace(marker, marker + line, 1)
server.write_text(server_text, encoding='utf-8')

# Protect definition changes server-side. Managers/admins may edit/remove active
# cleaning tasks and daily-check definitions; staff can still save routine records.
auth = app_dir / 'auth_controls.py'
auth_text = auth.read_text(encoding='utf-8')
needle = "    incoming=json.loads(json.dumps(incoming)); expected=int(payload.get('revision') or 0); venue_id=user['tenantId']\n"
insert = needle + "    manager_role=str(user.get('role','')).lower() in ('manager','admin','administrator')\n    protected_keys=('cleaningTasks','cleaningSchedules','checks')\n    protected_changed=any(incoming.get(k)!=stored['state'].get(k) for k in protected_keys)\n    if protected_changed and not manager_role:\n        handler.send_json({'error':'Manager access required to change cleaning tasks or daily checks.'},403); return\n"
if 'protected_changed=any(incoming.get(k)' not in auth_text:
    if needle not in auth_text:
        raise SystemExit('save_state insertion point not found')
    auth_text = auth_text.replace(needle, insert, 1)
auth.write_text(auth_text, encoding='utf-8')

final_html = index.read_text(encoding='utf-8')
final_server = server.read_text(encoding='utf-8')
final_auth = auth.read_text(encoding='utf-8')
if final_html.count(tag) != 1:
    raise SystemExit('manager_controls_v4 script tag not installed exactly once')
if "'/manager_controls_v4.js'" not in final_server:
    raise SystemExit('manager_controls_v4 static route missing')
if 'protected_changed=any(incoming.get(k)' not in final_auth:
    raise SystemExit('manager-only state protection missing')
print('Manager controls v4 installed: STATE-aware edit/remove UI')
