from pathlib import Path
import re

app = Path('app')
server = app / 'server.py'
server_text = server.read_text(encoding='utf-8')

# Discover the existing authenticated password-change endpoint from production.
idx = server_text.find('change_password')
if idx < 0:
    raise SystemExit('Could not find change_password route in server.py')
window = server_text[max(0, idx - 700): idx + 500]
routes = re.findall(r"['\"](/api/[^'\"]+)['\"]", window)
if not routes:
    raise SystemExit('Could not identify API route for change_password')
password_route = routes[-1]

# Discover the existing logout/sign-out route when present. The client also has safe
# fallbacks for older bundles where logout is exposed only as a global app function.
logout_route = ''
low = server_text.lower()
for marker in ('logout', 'signout', 'sign_out', 'log_out'):
    pos = low.find(marker)
    if pos >= 0:
        w = server_text[max(0, pos - 800): pos + 800]
        candidates = re.findall(r"['\"](/api/[^'\"]+)['\"]", w)
        preferred = [r for r in candidates if 'logout' in r.lower() or 'sign' in r.lower()]
        if preferred:
            logout_route = preferred[-1]
            break
        if candidates:
            logout_route = candidates[-1]
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
tag = '<script src="/self_password_change.js?v=20260915-account2"></script>'
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
