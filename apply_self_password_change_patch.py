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

# 2026-09-17 safety overlay. This deliberately changes only three browser-side
# runtime files; auth, Supabase configuration and persisted data are untouched.
import base64
import hashlib
import zlib

overlays = [
    ('compliance_pro.js', 'cdc_overlay_compliance_pro.js.b64', '7570dac36d6f4d4a2f67dc0c938aa13dcc0f585ba4a96092a8f29957eaf07674'),
    ('integration_bridge.js', 'cdc_overlay_integration_bridge.js.b64', '7b1e5e71ef08c632c47fb7589610e42acbf88b7886e7702673457a046519ef70'),
    ('safe_delete_patch.js', 'cdc_overlay_safe_delete_patch.js.b64', '7342d07dd6c9094535a17658b15ce31ce9c571b41f907652c5807d2abfc46f11'),
]

for target_name, payload_name, expected_sha in overlays:
    payload_path = Path(payload_name)
    if not payload_path.exists():
        raise SystemExit(f'Missing safety overlay payload: {payload_name}')
    try:
        raw = zlib.decompress(base64.b64decode(payload_path.read_text(encoding='utf-8').strip()))
    except Exception as exc:
        raise SystemExit(f'Could not decode safety overlay {payload_name}: {exc}')
    got = hashlib.sha256(raw).hexdigest()
    if got != expected_sha:
        raise SystemExit(f'Safety overlay checksum mismatch for {target_name}: {got}')
    target = app / target_name
    if not target.exists():
        raise SystemExit(f'Safety overlay target missing: {target}')
    target.write_bytes(raw)
    verify = hashlib.sha256(target.read_bytes()).hexdigest()
    if verify != expected_sha:
        raise SystemExit(f'Safety overlay write verification failed for {target_name}: {verify}')

# Force browsers/service workers to request the corrected runtime modules.
runtime_loader = app / 'runtime_loader.js'
if runtime_loader.exists():
    rt = runtime_loader.read_text(encoding='utf-8')
    rt2 = re.sub(r"\?runtime=[^'\"]+", '?runtime=20260917-safety2', rt)
    runtime_loader.write_text(rt2, encoding='utf-8')

guard = app / 'temperature_reset_guard.js'
if guard.exists():
    gt = guard.read_text(encoding='utf-8')
    gt2 = re.sub(r"runtime_loader\.js\?v=[^'\"]+", 'runtime_loader.js?v=20260917-safety2', gt)
    guard.write_text(gt2, encoding='utf-8')

print('Applied 2026-09-17 compliance, stock-link and targeted-delete safety fixes')

# 2026-09-17 historic temperature/status consistency overlay. It runs last so
# earlier build patches cannot reintroduce numeric-only historical workflows.
historic_payload = Path('cdc_historic_status_patch.py.b64')
if not historic_payload.exists():
    raise SystemExit('Missing historic status patch payload: cdc_historic_status_patch.py.b64')
try:
    historic_raw = zlib.decompress(base64.b64decode(historic_payload.read_text(encoding='utf-8').strip()))
except Exception as exc:
    raise SystemExit(f'Could not decode historic status patch payload: {exc}')
historic_sha = hashlib.sha256(historic_raw).hexdigest()
expected_historic_sha = '93af4cafd6da8505b2b8e7cc35e11ed1a1f679d4dfde963a3ed5c3df8b81cc0b'
if historic_sha != expected_historic_sha:
    raise SystemExit(f'Historic status patch checksum mismatch: {historic_sha}')
exec(compile(historic_raw, 'cdc_historic_status_patch.py', 'exec'), {'__name__': '__main__'})
print('Applied historic temperature/status consistency fixes')

# Chef Pro v2: replace only the browser-side Chef assistant after all earlier
# build patches. This does not change auth, Supabase configuration or stored data.
chef_payload = Path('cdc_chef_pro_v2.js.b64')
if not chef_payload.exists():
    raise SystemExit('Missing Chef Pro v2 payload: cdc_chef_pro_v2.js.b64')
try:
    chef_raw = zlib.decompress(base64.b64decode(chef_payload.read_text(encoding='utf-8').strip()))
except Exception as exc:
    raise SystemExit(f'Could not decode Chef Pro v2 payload: {exc}')
chef_sha = hashlib.sha256(chef_raw).hexdigest()
expected_chef_sha = '76c89a2251d24ff1f421bfae933b2eaab57d0a43d031754617d75611d20fb0c2'
if chef_sha != expected_chef_sha:
    raise SystemExit(f'Chef Pro v2 checksum mismatch: {chef_sha}')
chef_target = app / 'ai_upgrade_patch.js'
if not chef_target.exists():
    raise SystemExit('Chef Pro runtime target missing: app/ai_upgrade_patch.js')
chef_target.write_bytes(chef_raw)
if hashlib.sha256(chef_target.read_bytes()).hexdigest() != expected_chef_sha:
    raise SystemExit('Chef Pro v2 write verification failed')

# Cache-bust the runtime loader so active kitchen devices fetch the new Chef brain.
if runtime_loader.exists():
    rt = runtime_loader.read_text(encoding='utf-8')
    rt = re.sub(r"\?runtime=[^'\"]+", '?runtime=20260917-chef2', rt)
    runtime_loader.write_text(rt, encoding='utf-8')
if guard.exists():
    gt = guard.read_text(encoding='utf-8')
    gt = re.sub(r"runtime_loader\.js\?v=[^'\"]+", 'runtime_loader.js?v=20260917-chef2', gt)
    guard.write_text(gt, encoding='utf-8')
print('Applied Chef Pro v2 culinary reasoning and recipe knowledge upgrade')
