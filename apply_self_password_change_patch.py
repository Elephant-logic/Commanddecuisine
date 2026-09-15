from pathlib import Path
import re

app = Path('app')
server = app / 'server.py'
server_text = server.read_text(encoding='utf-8')

# Find the actual route-dispatch call, not an import/reference near the top of server.py.
call_positions = [m.start() for m in re.finditer(r'(?:auth_controls\.)?change_password\s*\(', server_text)]
if not call_positions:
    raise SystemExit('Could not find change_password route call in server.py')
idx = call_positions[-1]
route_hits = [(m.start(), m.group(1)) for m in re.finditer(r"['\"](/api/[^'\"]+)['\"]", server_text[:idx])]
if not route_hits:
    raise SystemExit('Could not identify API route for change_password')
pos, password_route = route_hits[-1]
if idx - pos > 1200:
    raise SystemExit('Password route candidate is too far from change_password call')

# Discover a logout/sign-out route only when it is genuinely associated with a logout marker.
logout_route = ''
low = server_text.lower()
route_matches = list(re.finditer(r"['\"](/api/[^'\"]+)['\"]", server_text))
for marker in ('logout', 'signout', 'sign_out', 'log_out'):
    for mm in re.finditer(marker, low):
        before = [r for r in route_matches if r.start() <= mm.start() and mm.start() - r.start() <= 1000]
        if not before:
            continue
        cand = before[-1].group(1)
        if 'logout' in cand.lower() or 'sign' in cand.lower() or mm.start() - before[-1].start() < 350:
            logout_route = cand
            break
    if logout_route:
        break

src = Path('self_password_change.js')
js = src.read_text(encoding='utf-8')
js = js.replace('__PASSWORD_ROUTE__', password_route).replace('__LOGOUT_ROUTE__', logout_route)
(app / 'self_password_change.js').write_text(js, encoding='utf-8')

# Serve the script as a runtime asset.
marker = 'RUNTIME_FILES = (\n'
asset = "    '/self_password_change.js',\n"
if asset not in server_text:
    if marker not in server_text:
        raise SystemExit('RUNTIME_FILES marker not found in server.py')
    server_text = server_text.replace(marker, marker + asset, 1)
server.write_text(server_text, encoding='utf-8')

# Load after manager/team UI patches so the account buttons survive DOM/script cleanup.
index = app / 'index.html'
html = index.read_text(encoding='utf-8')
tag = '<script src="/self_password_change.js?v=20260915-account4"></script>'
html = re.sub(r'\s*<script[^>]+src=["\']/?self_password_change\.js(?:\?[^"\']*)?["\'][^>]*></script>\s*', '\n', html, flags=re.I)
if '</body>' not in html:
    raise SystemExit('Could not locate </body> in index.html')
html = html.replace('</body>', tag + '\n</body>', 1)
index.write_text(html, encoding='utf-8')

# Self-check final build artifacts.
final_server = server.read_text(encoding='utf-8')
final_html = index.read_text(encoding='utf-8')
final_js = (app / 'self_password_change.js').read_text(encoding='utf-8')
if "'/self_password_change.js'" not in final_server:
    raise SystemExit('Self account script route missing')
if final_html.count(tag) != 1:
    raise SystemExit('Self account script tag not installed exactly once')
if '__PASSWORD_ROUTE__' in final_js or password_route not in final_js:
    raise SystemExit('Password API route was not wired into client script')
if '__LOGOUT_ROUTE__' in final_js:
    raise SystemExit('Logout placeholder was not resolved')

print(f'Self account controls restored: password={password_route}, logout={logout_route or "client fallback"}')
