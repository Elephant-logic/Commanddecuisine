from pathlib import Path
import shutil

app_dir = Path('app')
shutil.copyfile('manager_console.html', app_dir / 'manager_console.html')

# Honour contextual links such as ?tab=checks and ?tab=cleaning.
console = app_dir / 'manager_console.html'
console_html = console.read_text(encoding='utf-8')
old = "let session=null, state=null, revision=0, tab='cleaning';"
new = "const _requestedTab=new URLSearchParams(location.search).get('tab'); let session=null, state=null, revision=0, tab=['cleaning','checks','staff'].includes(_requestedTab)?_requestedTab:'cleaning';"
if old in console_html:
    console_html = console_html.replace(old, new, 1)
console.write_text(console_html, encoding='utf-8')

server = app_dir / 'server.py'
text = server.read_text(encoding='utf-8')
marker = 'RUNTIME_FILES = (\n'
line = "    '/manager_console.html',\n"
if line not in text:
    if marker not in text:
        raise SystemExit('RUNTIME_FILES marker not found in server.py')
    text = text.replace(marker, marker + line, 1)
server.write_text(text, encoding='utf-8')

# Ensure manager/admin state-definition changes remain server-protected.
auth = app_dir / 'auth_controls.py'
auth_text = auth.read_text(encoding='utf-8')
needle = "    incoming=json.loads(json.dumps(incoming)); expected=int(payload.get('revision') or 0); venue_id=user['tenantId']\n"
if 'protected_changed=any(incoming.get(k)' not in auth_text:
    insert = needle + "    manager_role=str(user.get('role','')).lower() in ('manager','admin','administrator')\n    protected_keys=('cleaningTasks','cleaningSchedules','checks')\n    protected_changed=any(incoming.get(k)!=stored['state'].get(k) for k in protected_keys)\n    if protected_changed and not manager_role:\n        handler.send_json({'error':'Manager access required to change cleaning tasks or daily checks.'},403); return\n"
    if needle not in auth_text:
        raise SystemExit('save_state insertion point not found')
    auth_text = auth_text.replace(needle, insert, 1)
    auth.write_text(auth_text, encoding='utf-8')

# Make admin/administrator aliases manager-equivalent in the staff endpoint.
auth_text = auth.read_text(encoding='utf-8')
auth_text = auth_text.replace("if manager.get('role') != 'manager': handler.send_json({'error':'Manager access required.'},403); return",
                              "if str(manager.get('role','')).lower() not in ('manager','admin','administrator'): handler.send_json({'error':'Manager access required.'},403); return")
auth_text = auth_text.replace("if manager.get('role') != 'manager': handler.send_json({'error':'Admin access required.'},403); return",
                              "if str(manager.get('role','')).lower() not in ('manager','admin','administrator'): handler.send_json({'error':'Admin access required.'},403); return")
auth.write_text(auth_text, encoding='utf-8')

if "'/manager_console.html'" not in server.read_text(encoding='utf-8'):
    raise SystemExit('Manager console static route missing')
if not (app_dir / 'manager_console.html').exists():
    raise SystemExit('Manager console file missing')
print('Standalone manager console installed at /manager_console.html with contextual tab selection')
