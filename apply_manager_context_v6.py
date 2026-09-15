from pathlib import Path
import re
import shutil

app_dir = Path('app')

# Install the contextual in-app manager controls. The standalone console remains
# available as a fallback/debug page, but normal buttons no longer navigate to it.
shutil.copyfile('manager_console.html', app_dir / 'manager_console.html')
shutil.copyfile('manager_context_controls_v6.js', app_dir / 'manager_context_controls_v6.js')

# Let the fallback console open the requested tab when visited directly.
console = app_dir / 'manager_console.html'
console_html = console.read_text(encoding='utf-8')
old = "let session=null, state=null, revision=0, tab='cleaning';"
new = "const _requestedTab=new URLSearchParams(location.search).get('tab'); let session=null, state=null, revision=0, tab=['cleaning','checks','staff'].includes(_requestedTab)?_requestedTab:'cleaning';"
if old in console_html:
    console_html = console_html.replace(old, new, 1)
console.write_text(console_html, encoding='utf-8')

# Remove every previous manager UI experiment from index.html and load only the
# contextual in-app manager controls.
index = app_dir / 'index.html'
html = index.read_text(encoding='utf-8')
html = re.sub(
    r'\s*<script[^>]+src=["\']/?manager_(?:remove_controls(?:_v2)?|controls_v[3456]|context_controls_v6)\.js(?:\?[^"\']*)?["\'][^>]*></script>\s*',
    '\n', html, flags=re.I
)
html = re.sub(r'\s*<script id=["\']cdc-manager-v5-inline["\']>.*?</script>\s*', '\n', html, flags=re.S|re.I)
html = re.sub(r'\s*<script[^>]*id=["\']cdc-manager-v[34][^"\']*["\'][^>]*>.*?</script>\s*', '\n', html, flags=re.S|re.I)

tag = '<script src="/manager_context_controls_v6.js?v=20260915-0412"></script>'
if '</body>' not in html:
    raise SystemExit('Could not locate </body> in index.html')
html = html.replace('</body>', tag + '\n</body>', 1)
if 'http-equiv="Cache-Control"' not in html and '<head>' in html:
    html = html.replace('<head>', '<head>\n<meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0">\n<meta http-equiv="Pragma" content="no-cache">', 1)
index.write_text(html, encoding='utf-8')

# Serve both resources.
server = app_dir / 'server.py'
server_text = server.read_text(encoding='utf-8')
marker = 'RUNTIME_FILES = (\n'
for route in ("'/manager_console.html',", "'/manager_context_controls_v6.js',"):
    line = '    ' + route + '\n'
    if line not in server_text:
        if marker not in server_text:
            raise SystemExit('RUNTIME_FILES marker not found in server.py')
        server_text = server_text.replace(marker, marker + line, 1)
server.write_text(server_text, encoding='utf-8')

# Keep definition changes manager-only and accept manager/admin/administrator aliases.
auth = app_dir / 'auth_controls.py'
auth_text = auth.read_text(encoding='utf-8')
needle = "    incoming=json.loads(json.dumps(incoming)); expected=int(payload.get('revision') or 0); venue_id=user['tenantId']\n"
if 'protected_changed=any(incoming.get(k)' not in auth_text:
    insert = needle + "    manager_role=str(user.get('role','')).lower() in ('manager','admin','administrator')\n    protected_keys=('cleaningTasks','cleaningSchedules','checks')\n    protected_changed=any(incoming.get(k)!=stored['state'].get(k) for k in protected_keys)\n    if protected_changed and not manager_role:\n        handler.send_json({'error':'Manager access required to change cleaning tasks or daily checks.'},403); return\n"
    if needle not in auth_text:
        raise SystemExit('save_state insertion point not found')
    auth_text = auth_text.replace(needle, insert, 1)
auth_text = auth_text.replace("if manager.get('role') != 'manager': handler.send_json({'error':'Manager access required.'},403); return",
                              "if str(manager.get('role','')).lower() not in ('manager','admin','administrator'): handler.send_json({'error':'Manager access required.'},403); return")
auth_text = auth_text.replace("if manager.get('role') != 'manager': handler.send_json({'error':'Admin access required.'},403); return",
                              "if str(manager.get('role','')).lower() not in ('manager','admin','administrator'): handler.send_json({'error':'Admin access required.'},403); return")
auth_text = auth_text.replace("u.get('role')=='manager' and u.get('active',True)",
                              "str(u.get('role','')).lower() in ('manager','admin','administrator') and u.get('active',True)")
auth.write_text(auth_text, encoding='utf-8')

final_html = index.read_text(encoding='utf-8')
if final_html.count(tag) != 1:
    raise SystemExit('contextual manager launcher not installed exactly once')
legacy = re.findall(r'<script[^>]+src=["\']/?manager_(?:remove_controls(?:_v2)?|controls_v[345])\.js', final_html, flags=re.I)
if legacy:
    raise SystemExit('Legacy manager UI scripts still present: ' + ','.join(legacy))
if 'cdc-manager-v5-inline' in final_html:
    raise SystemExit('Legacy v5 inline manager UI still present')
if "'/manager_context_controls_v6.js'" not in server.read_text(encoding='utf-8'):
    raise SystemExit('Manager context route missing')
print('Manager controls v8 installed: Cleaning/Daily add-edit-remove actions save through live state API')
