from pathlib import Path
import re
import shutil

app_dir = Path('app')
source = Path('manager_controls_v5.js').read_text(encoding='utf-8')
shutil.copyfile('manager_controls_v5.js', app_dir / 'manager_controls_v5.js')

# Put the control code directly in index.html. This avoids a second cached asset
# being able to hide the manager UI.
index = app_dir / 'index.html'
html = index.read_text(encoding='utf-8')
html = re.sub(r'\s*<script src="manager_(?:remove_controls(?:_v2)?|controls_v[345])\.js(?:\?[^\"]*)?"></script>\s*', '\n', html)
html = re.sub(r'\s*<script id="cdc-manager-v5-inline">.*?</script>\s*', '\n', html, flags=re.S)
inline = '<script id="cdc-manager-v5-inline">\n' + source + '\n</script>'
if '</body>' not in html:
    raise SystemExit('Could not locate </body> in index.html')
html = html.replace('</body>', inline + '\n</body>', 1)
index.write_text(html, encoding='utf-8')

# Keep an external route too for diagnostics/future use.
server = app_dir / 'server.py'
server_text = server.read_text(encoding='utf-8')
marker = 'RUNTIME_FILES = (\n'
line = "    '/manager_controls_v5.js',\n"
if line not in server_text and marker in server_text:
    server_text = server_text.replace(marker, marker + line, 1)
server.write_text(server_text, encoding='utf-8')

# Existing installed/PWA copies can keep serving an old cached index even after a
# successful Render deploy. Force any packaged service worker to activate now,
# delete its old Cache Storage entries, and claim the current page.
sw_patch = r'''
/* CDC UI refresh 2026-09-15 v5: discard stale application-shell caches. */
self.addEventListener('install', function(){ try { self.skipWaiting(); } catch(e) {} });
self.addEventListener('activate', function(event){
  event.waitUntil((async function(){
    try {
      var keys = await caches.keys();
      await Promise.all(keys.map(function(k){ return caches.delete(k); }));
    } catch(e) {}
    try { await self.clients.claim(); } catch(e) {}
  })());
});
'''
patched_sw = 0
for p in app_dir.rglob('*.js'):
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        continue
    low = text.lower()
    if ('self.addeventlistener' in low and 'fetch' in low and ('caches.' in low or 'service worker' in low)):
        if 'CDC UI refresh 2026-09-15 v5' not in text:
            p.write_text(text + '\n' + sw_patch, encoding='utf-8')
            patched_sw += 1

# One-time browser-cache flush on the session endpoint. The marker cookie means
# it runs once per browser, not on every request. It does not clear auth cookies.
auth = app_dir / 'auth_controls.py'
auth_text = auth.read_text(encoding='utf-8')
if 'cdc_ui_v5=1' not in auth_text:
    start = auth_text.find('\ndef send_session(handler):\n')
    end = auth_text.find('\ndef send_export(handler):\n', start)
    if start < 0 or end < 0:
        raise SystemExit('send_session block not found')
    block = auth_text[start:end]
    block = block.replace(
        'def send_session(handler):\n',
        'def send_session(handler):\n'
        "    _cookie_header = handler.headers.get('Cookie') or ''\n"
        "    _ui_refresh_headers = {}\n"
        "    if 'cdc_ui_v5=1' not in _cookie_header:\n"
        "        _ui_refresh_headers = {'Clear-Site-Data':'\\\"cache\\\"','Set-Cookie':'cdc_ui_v5=1; Path=/; Secure; SameSite=Lax; Max-Age=604800'}\n",
        1,
    )
    # Only the two send_json calls inside send_session are modified.
    block = block.replace("handler.send_json({'authenticated':False,'initialised':True,'needsSetup':needs_setup,'canCreateVenue':True})",
                          "handler.send_json({'authenticated':False,'initialised':True,'needsSetup':needs_setup,'canCreateVenue':True}, extra_headers=_ui_refresh_headers)")
    block = block.replace("handler.send_json({'authenticated':True,'needsSetup':False,'canCreateVenue':True,'user':_safe_user(account),**_public_state(stored)})",
                          "handler.send_json({'authenticated':True,'needsSetup':False,'canCreateVenue':True,'user':_safe_user(account),**_public_state(stored)}, extra_headers=_ui_refresh_headers)")
    auth_text = auth_text[:start] + block + auth_text[end:]
    auth.write_text(auth_text, encoding='utf-8')

final_html = index.read_text(encoding='utf-8')
if final_html.count('id="cdc-manager-v5-inline"') != 1:
    raise SystemExit('v5 manager control was not inlined exactly once')
if 'MANAGE TASKS' not in final_html or 'MANAGE CHECKS' not in final_html:
    raise SystemExit('v5 visible manager labels missing from index')
print('Manager controls v5 installed; service workers patched:', patched_sw)
