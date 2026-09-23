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


# 2026-09-21 neutral historic-entry presentation.
# Keep immutable entry timestamps/backfill metadata for auditability, but do not
# stigmatise normal retrospective entry in the everyday kitchen UI.
fixes_path = app / 'kitchen_fixes_20260810.js'
if not fixes_path.exists():
    raise SystemExit('Historic entry presentation target missing: app/kitchen_fixes_20260810.js')
fx = fixes_path.read_text(encoding='utf-8')
presentation_replacements = {
    "Fill missing temperature round": "Add missing temperature record",
    "Save historic readings": "Save records",
    "Save historic records": "Save records",
    "Enter at least one missing reading": "Add at least one record or leave this round incomplete",
    "Enter at least one missing record": "Add at least one record or leave this round incomplete",
    "readings entered later": "records added",
    "records entered later": "records added",
    "historic temperature backfill": "temperature record",
    "Historic temperature backfill": "Temperature record",
    "Historic temperatures were not saved": "Records were not saved",
    "historic reading": "record",
    "Historic reading": "Record",
    "audit('temp_backfill'": "audit('temp_record_added'",
}
changed = 0
for old, new in presentation_replacements.items():
    if old in fx:
        changed += fx.count(old)
        fx = fx.replace(old, new)
# Keep source:'manager-backfill', backfilled:true and enteredAt untouched.
# Those fields are the quiet audit trail showing when the digital entry was made.
if changed == 0:
    raise SystemExit('Historic entry presentation markers not found; refusing silent no-op')
fixes_path.write_text(fx, encoding='utf-8')

# Make the primary temperature history wording neutral if a later patch exposes
# source text directly. Internal audit/source metadata remains unchanged.
main_path = app / 'main_app.js'
if main_path.exists():
    mj = main_path.read_text(encoding='utf-8')
    for old, new in {
        "entered later": "record",
        "Backfill": "Record",
        "backfill": "record",
    }.items():
        # Only replace user-facing phrases already containing temperature/history
        # by targeted known strings rather than changing identifiers globally.
        mj = mj.replace("temperature " + old, "temperature " + new)
        mj = mj.replace("Temperature " + old, "Temperature " + new)
    main_path.write_text(mj, encoding='utf-8')

# Cache-bust again so kitchen devices see the neutral wording promptly.
if runtime_loader.exists():
    rt = runtime_loader.read_text(encoding='utf-8')
    rt = re.sub(r"\?runtime=[^'\"]+", '?runtime=20260921-paperlike1', rt)
    runtime_loader.write_text(rt, encoding='utf-8')
if guard.exists():
    gt = guard.read_text(encoding='utf-8')
    gt = re.sub(r"runtime_loader\.js\?v=[^'\"]+", 'runtime_loader.js?v=20260921-paperlike1', gt)
    guard.write_text(gt, encoding='utf-8')
print(f'Applied paper-like temperature record presentation ({changed} wording updates); audit timestamps preserved')


# 2026-09-21 Kitchen Tools: persistent multi-timers and quick calculations.
# Timers are device-local operational helpers; they do not write compliance/state data.
tools_payload = Path('cdc_kitchen_tools.js.b64')
if not tools_payload.exists():
    raise SystemExit('Missing Kitchen Tools payload: cdc_kitchen_tools.js.b64')
try:
    tools_raw = zlib.decompress(base64.b64decode(tools_payload.read_text(encoding='utf-8').strip()))
except Exception as exc:
    raise SystemExit(f'Could not decode Kitchen Tools payload: {exc}')
tools_sha = hashlib.sha256(tools_raw).hexdigest()
expected_tools_sha = 'f18e7828c1cf7e557d6ae81e36cc02fadb12b2312ca1bf8e98a1795b8b555b28'
if tools_sha != expected_tools_sha:
    raise SystemExit(f'Kitchen Tools checksum mismatch: {tools_sha}')
tools_target = app / 'kitchen_tools.js'
tools_target.write_bytes(tools_raw)
if hashlib.sha256(tools_target.read_bytes()).hexdigest() != expected_tools_sha:
    raise SystemExit('Kitchen Tools write verification failed')


# On mobile, keep the floating timer button above the fixed bottom navigation
# so it never covers More (where History is reached).
tools_text = tools_target.read_text(encoding='utf-8')
mobile_timer_old = "@media(max-width:620px){.cdc-kt-grid{grid-template-columns:1fr 1fr}.cdc-kt-grid .name{grid-column:1/-1}.cdc-kt-grid .add{grid-column:1/-1}.cdc-kt-toolgrid{grid-template-columns:1fr}.cdc-kt-time{font-size:24px}#${FAB}{right:12px;bottom:12px}}"
mobile_timer_new = "@media(max-width:900px){#${FAB}{right:12px;bottom:calc(82px + env(safe-area-inset-bottom));max-width:calc(100vw - 24px)}}@media(max-width:620px){.cdc-kt-grid{grid-template-columns:1fr 1fr}.cdc-kt-grid .name{grid-column:1/-1}.cdc-kt-grid .add{grid-column:1/-1}.cdc-kt-toolgrid{grid-template-columns:1fr}.cdc-kt-time{font-size:24px}}"
if mobile_timer_old not in tools_text:
    raise SystemExit('Kitchen Tools mobile FAB marker not found')
tools_text = tools_text.replace(mobile_timer_old, mobile_timer_new, 1)
tools_target.write_text(tools_text, encoding='utf-8')

# Serve the runtime file.
srv = server.read_text(encoding='utf-8')
runtime_marker = "RUNTIME_FILES = (\n"
tools_route = "    '/kitchen_tools.js',\n"
if tools_route not in srv:
    if runtime_marker not in srv:
        raise SystemExit('RUNTIME_FILES marker missing while adding Kitchen Tools')
    srv = srv.replace(runtime_marker, runtime_marker + tools_route, 1)
server.write_text(srv, encoding='utf-8')

# Load Kitchen Tools after Chef Pro so timer voice/text commands can wrap askAI.
if not runtime_loader.exists():
    raise SystemExit('runtime_loader.js missing while adding Kitchen Tools')
rt = runtime_loader.read_text(encoding='utf-8')
m = re.search(r"(const\s+modules\s*=\s*\[)(.*?)(\n\s*\];)", rt, re.S)
if not m:
    raise SystemExit('runtime_loader.js modules array not found for Kitchen Tools')
body = m.group(2)
if "'kitchen_tools.js'" not in body and '"kitchen_tools.js"' not in body:
    body = body.rstrip() + ",\n    'kitchen_tools.js'"
    rt = rt[:m.start(2)] + body + rt[m.end(2):]
rt = re.sub(r"\?runtime=[^'\"]+", '?runtime=20260921-historynav1', rt)
runtime_loader.write_text(rt, encoding='utf-8')

if guard.exists():
    gt = guard.read_text(encoding='utf-8')
    gt = re.sub(r"runtime_loader\.js\?v=[^'\"]+", 'runtime_loader.js?v=20260921-historynav1', gt)
    guard.write_text(gt, encoding='utf-8')

# Build-time wiring checks.
srv_check = server.read_text(encoding='utf-8')
rt_check = runtime_loader.read_text(encoding='utf-8')
if srv_check.count("'/kitchen_tools.js'") + srv_check.count('"/kitchen_tools.js"') != 1:
    raise SystemExit('Kitchen Tools runtime route not installed exactly once')
if rt_check.count("'kitchen_tools.js'") + rt_check.count('"kitchen_tools.js"') != 1:
    raise SystemExit('Kitchen Tools module not installed exactly once')
print('Applied Kitchen Tools: multi-timers, Chef timer commands, converter and portion scaler')


# Keep normal History presentation paper-like and neutral. Internal provenance
# fields/source IDs remain untouched; only user-facing wording is changed.
history_targets = [
    app / 'kitchen_fixes_20260810.js',
    app / 'history_truth_fix.js',
    app / 'temperature_history_reconcile.js',
    app / 'manager_ai_temp_backfill.js',
    app / 'paper_import_undo.js',
]
history_replacements = [
    ('Historic entries are marked as back-filled so the audit trail stays clear.',
     'Records are shown under the date and round they relate to.'),
    ('Historic entries are marked as back-filled so the audit trail stays clear',
     'Records are shown under the date and round they relate to'),
    ('Manager back-fill', 'Recorded'),
    ('Manager back-fill status', 'Recorded'),
    ('manager back-fill', 'temperature record'),
    ('manager back-fills', 'temperature records'),
    ('manager historic backfills', 'manually added temperature records'),
    ('Entered later', ''),
    ('entered later', ''),
]
history_changes = 0
for hp in history_targets:
    if not hp.exists():
        continue
    ht = hp.read_text(encoding='utf-8')
    before = ht
    for old, new in history_replacements:
        ht = ht.replace(old, new)
    # Keep the action obvious without using retrospective/audit jargon.
    ht = ht.replace("html:'Fill in'", "html:'Add record'")
    ht = ht.replace('html:"Fill in"', 'html:"Add record"')
    if ht != before:
        history_changes += 1
        hp.write_text(ht, encoding='utf-8')

# Final cache-bust after both the navigation and History presentation fix.
if runtime_loader.exists():
    rt = runtime_loader.read_text(encoding='utf-8')
    rt = re.sub(r"\?runtime=[^'\"]+", '?runtime=20260921-historynav1', rt)
    runtime_loader.write_text(rt, encoding='utf-8')
if guard.exists():
    gt = guard.read_text(encoding='utf-8')
    gt = re.sub(r"runtime_loader\.js\?v=[^'\"]+", 'runtime_loader.js?v=20260921-historynav1', gt)
    guard.write_text(gt, encoding='utf-8')
print(f'History/navigation repair applied; {history_changes} history modules updated')


# 2026-09-21 Kitchen Tools v2.
# Replaces the first floating timer UI with a left-docked service timer system,
# recipe-step timer buttons and Chef "what's next?" support.
tools_v2_parts = [Path('cdc_kitchen_tools_v2.part1'), Path('cdc_kitchen_tools_v2.part2'), Path('cdc_kitchen_tools_v2.part3')]
if not all(p.exists() for p in tools_v2_parts):
    raise SystemExit('Missing one or more Kitchen Tools v2 payload parts')
try:
    tools_v2_b64 = ''.join(p.read_text(encoding='utf-8').strip() for p in tools_v2_parts)
    if hashlib.sha256(tools_v2_b64.encode('utf-8')).hexdigest() != '244c9a4a23d635366b977f7a06ad3ce5be4d73618dcd451369006a47f29992a9':
        raise ValueError('payload text checksum mismatch')
    tools_v2_raw = zlib.decompress(base64.b64decode(tools_v2_b64))
except Exception as exc:
    raise SystemExit(f'Could not decode Kitchen Tools v2 payload parts: {exc}')
tools_v2_sha = hashlib.sha256(tools_v2_raw).hexdigest()
expected_tools_v2_sha = '20ff802da431f705695bea8915bb69e1e658051ad97da0339279e71ef45f9090'
if tools_v2_sha != expected_tools_v2_sha:
    raise SystemExit(f'Kitchen Tools v2 checksum mismatch: {tools_v2_sha}')
tools_v2_target = app / 'kitchen_tools_v2.js'
tools_v2_target.write_bytes(tools_v2_raw)
if hashlib.sha256(tools_v2_target.read_bytes()).hexdigest() != expected_tools_v2_sha:
    raise SystemExit('Kitchen Tools v2 write verification failed')

# Serve v2.
srv = server.read_text(encoding='utf-8')
runtime_marker = "RUNTIME_FILES = (\n"
v2_route = "    '/kitchen_tools_v2.js',\n"
if v2_route not in srv:
    if runtime_marker not in srv:
        raise SystemExit('RUNTIME_FILES marker missing while adding Kitchen Tools v2')
    srv = srv.replace(runtime_marker, runtime_marker + v2_route, 1)
server.write_text(srv, encoding='utf-8')

# Disable the old timer module and load v2 last so it can wrap Chef safely.
rt = runtime_loader.read_text(encoding='utf-8')
m = re.search(r"(const\s+modules\s*=\s*\[)(.*?)(\n\s*\];)", rt, re.S)
if not m:
    raise SystemExit('runtime_loader.js modules array not found for Kitchen Tools v2')
body = m.group(2)
body = body.replace(",\n    'kitchen_tools.js'", "")
body = body.replace(",\n    \"kitchen_tools.js\"", "")
body = body.replace("'kitchen_tools.js',\n", "")
body = body.replace('"kitchen_tools.js",\n', "")
body = body.replace(",\n    'kitchen_tools_v2.js'", "")
body = body.replace(",\n    \"kitchen_tools_v2.js\"", "")
body = body.rstrip() + ",\n    'kitchen_tools_v2.js'"
rt = rt[:m.start(2)] + body + rt[m.end(2):]
rt = re.sub(r"\?runtime=[^'\"]+", '?runtime=20260921-tools-v2', rt)
runtime_loader.write_text(rt, encoding='utf-8')

if guard.exists():
    gt = guard.read_text(encoding='utf-8')
    gt = re.sub(r"runtime_loader\.js\?v=[^'\"]+", 'runtime_loader.js?v=20260921-tools-v2', gt)
    guard.write_text(gt, encoding='utf-8')

# Build-time wiring checks.
srv_check = server.read_text(encoding='utf-8')
rt_check = runtime_loader.read_text(encoding='utf-8')
if srv_check.count("'/kitchen_tools_v2.js'") + srv_check.count('"/kitchen_tools_v2.js"') != 1:
    raise SystemExit('Kitchen Tools v2 runtime route not installed exactly once')
if rt_check.count("'kitchen_tools_v2.js'") + rt_check.count('"kitchen_tools_v2.js"') != 1:
    raise SystemExit('Kitchen Tools v2 module not installed exactly once')
if "'kitchen_tools.js'" in rt_check or '"kitchen_tools.js"' in rt_check:
    raise SystemExit('Legacy Kitchen Tools module is still active')
print('Applied Kitchen Tools v2: left-docked multi-timers, recipe timers, service view, Chef commands and quick calculations')


# 2026-09-21 Recipe dependency sync.
# Recipe edits now reconcile verified supplier allergen declarations, allergen
# matrix data and ingredient->stock links. Physical stock quantities are never
# changed by this overlay.
recipe_sync_parts = [
    Path('cdc_recipe_sync.part1'),
    Path('cdc_recipe_sync.part2'),
    Path('cdc_recipe_sync.part3'),
    Path('cdc_recipe_sync.part4'),
]
if not all(p.exists() for p in recipe_sync_parts):
    raise SystemExit('Missing one or more recipe dependency sync payload parts')
try:
    recipe_sync_b64 = ''.join(p.read_text(encoding='utf-8').strip() for p in recipe_sync_parts)
    recipe_sync_b64_sha = hashlib.sha256(recipe_sync_b64.encode('utf-8')).hexdigest()
    if recipe_sync_b64_sha != '526b707d5c2ee05ed770e691a3ec404f8931f00b0bbe1288bff946b444a2be38':
        raise ValueError(f'payload text checksum mismatch: {recipe_sync_b64_sha}')
    recipe_sync_raw = zlib.decompress(base64.b64decode(recipe_sync_b64))
except Exception as exc:
    raise SystemExit(f'Could not decode recipe dependency sync payload: {exc}')
recipe_sync_sha = hashlib.sha256(recipe_sync_raw).hexdigest()
expected_recipe_sync_sha = 'bc90e4df12c281ebc6df257c5b6d0593c1fc8b4aa05305f5b48f378d4fe7f9c5'
if recipe_sync_sha != expected_recipe_sync_sha:
    raise SystemExit(f'Recipe dependency sync checksum mismatch: {recipe_sync_sha}')
recipe_sync_target = app / 'recipe_dependency_sync.js'
recipe_sync_target.write_bytes(recipe_sync_raw)
if hashlib.sha256(recipe_sync_target.read_bytes()).hexdigest() != expected_recipe_sync_sha:
    raise SystemExit('Recipe dependency sync write verification failed')

# Serve the sync runtime.
srv = server.read_text(encoding='utf-8')
runtime_marker = "RUNTIME_FILES = (\n"
recipe_sync_route = "    '/recipe_dependency_sync.js',\n"
if recipe_sync_route not in srv:
    if runtime_marker not in srv:
        raise SystemExit('RUNTIME_FILES marker missing while adding recipe dependency sync')
    srv = srv.replace(runtime_marker, runtime_marker + recipe_sync_route, 1)
server.write_text(srv, encoding='utf-8')

# Load it last, after integration bridge, recipe imports and Kitchen Tools.
rt = runtime_loader.read_text(encoding='utf-8')
m = re.search(r"(const\s+modules\s*=\s*\[)(.*?)(\n\s*\];)", rt, re.S)
if not m:
    raise SystemExit('runtime_loader.js modules array not found for recipe dependency sync')
body = m.group(2)
body = body.replace(",\n    'recipe_dependency_sync.js'", "")
body = body.replace(",\n    \"recipe_dependency_sync.js\"", "")
body = body.replace("'recipe_dependency_sync.js',\n", "")
body = body.replace('"recipe_dependency_sync.js",\n', "")
body = body.rstrip() + ",\n    'recipe_dependency_sync.js'"
rt = rt[:m.start(2)] + body + rt[m.end(2):]
rt = re.sub(r"\?runtime=[^'\"]+", '?runtime=20260921-recipe-sync1', rt)
runtime_loader.write_text(rt, encoding='utf-8')

if guard.exists():
    gt = guard.read_text(encoding='utf-8')
    gt = re.sub(r"runtime_loader\.js\?v=[^'\"]+", 'runtime_loader.js?v=20260921-recipe-sync1', gt)
    guard.write_text(gt, encoding='utf-8')

srv_check = server.read_text(encoding='utf-8')
rt_check = runtime_loader.read_text(encoding='utf-8')
if srv_check.count("'/recipe_dependency_sync.js'") + srv_check.count('"/recipe_dependency_sync.js"') != 1:
    raise SystemExit('Recipe dependency sync runtime route not installed exactly once')
if rt_check.count("'recipe_dependency_sync.js'") + rt_check.count('"recipe_dependency_sync.js"') != 1:
    raise SystemExit('Recipe dependency sync module not installed exactly once')
print('Applied recipe dependency sync: verified supplier allergens, allergen matrix and stock-link reconciliation')


# 2026-09-21 Operations upgrade.
# Adds service mode, live supplier-based recipe costing, recipe version history,
# supplier/spec review and yield-aware menu/function stock requirements.
# It is browser-side only and does not alter auth, environment or database schema.
operations_parts = [
    Path('cdc_operations_upgrade.part1'),
    Path('cdc_operations_upgrade.part2'),
    Path('cdc_operations_upgrade.part3'),
    Path('cdc_operations_upgrade.part4'),
    Path('cdc_operations_upgrade.part5'),
]
if not all(p.exists() for p in operations_parts):
    raise SystemExit('Missing one or more operations upgrade payload parts')
try:
    operations_b64 = ''.join(p.read_text(encoding='utf-8').strip() for p in operations_parts)
    operations_b64_sha = hashlib.sha256(operations_b64.encode('utf-8')).hexdigest()
    if operations_b64_sha != '9027078a787b8fcb1303f7f514d6326d04a49d66328df502cfa20441f6b23f53':
        raise ValueError(f'payload text checksum mismatch: {operations_b64_sha}')
    operations_raw = zlib.decompress(base64.b64decode(operations_b64))
except Exception as exc:
    raise SystemExit(f'Could not decode operations upgrade payload: {exc}')
operations_sha = hashlib.sha256(operations_raw).hexdigest()
expected_operations_sha = '6a393751e6423bfcb5589f17a93e53b28b29c47f2b95e9376068e81fce1d3c2b'
if operations_sha != expected_operations_sha:
    raise SystemExit(f'Operations upgrade checksum mismatch: {operations_sha}')
operations_target = app / 'operations_upgrade.js'
operations_target.write_bytes(operations_raw)
if hashlib.sha256(operations_target.read_bytes()).hexdigest() != expected_operations_sha:
    raise SystemExit('Operations upgrade write verification failed')

# Serve the final operations runtime.
srv = server.read_text(encoding='utf-8')
runtime_marker = "RUNTIME_FILES = (\n"
operations_route = "    '/operations_upgrade.js',\n"
if operations_route not in srv:
    if runtime_marker not in srv:
        raise SystemExit('RUNTIME_FILES marker missing while adding operations upgrade')
    srv = srv.replace(runtime_marker, runtime_marker + operations_route, 1)
server.write_text(srv, encoding='utf-8')

# Load last so it can unify the already-installed recipe, stock, timer and
# allergen modules without replacing them.
rt = runtime_loader.read_text(encoding='utf-8')
m = re.search(r"(const\s+modules\s*=\s*\[)(.*?)(\n\s*\];)", rt, re.S)
if not m:
    raise SystemExit('runtime_loader.js modules array not found for operations upgrade')
body = m.group(2)
body = body.replace(",\n    'operations_upgrade.js'", "")
body = body.replace(",\n    \"operations_upgrade.js\"", "")
body = body.replace("'operations_upgrade.js',\n", "")
body = body.replace('"operations_upgrade.js",\n', "")
body = body.rstrip() + ",\n    'operations_upgrade.js'"
rt = rt[:m.start(2)] + body + rt[m.end(2):]
rt = re.sub(r"\?runtime=[^'\"]+", '?runtime=20260921-ops1', rt)
runtime_loader.write_text(rt, encoding='utf-8')

if guard.exists():
    gt = guard.read_text(encoding='utf-8')
    gt = re.sub(r"runtime_loader\.js\?v=[^'\"]+", 'runtime_loader.js?v=20260921-ops1', gt)
    guard.write_text(gt, encoding='utf-8')

srv_check = server.read_text(encoding='utf-8')
rt_check = runtime_loader.read_text(encoding='utf-8')
if srv_check.count("'/operations_upgrade.js'") + srv_check.count('"/operations_upgrade.js"') != 1:
    raise SystemExit('Operations upgrade runtime route not installed exactly once')
if rt_check.count("'operations_upgrade.js'") + rt_check.count('"operations_upgrade.js"') != 1:
    raise SystemExit('Operations upgrade module not installed exactly once')
print('Applied Operations upgrade: service mode, live costing, supplier specs, recipe versions and yield-aware requirements')


# 2026-09-21 Contacts & important numbers.
# Adds a connected kitchen directory for suppliers, engineers and priority
# contacts. Data is only created when a user adds/edits a contact.
contacts_parts = [
    Path('cdc_contacts.part1'),
    Path('cdc_contacts.part2'),
    Path('cdc_contacts.part3'),
]
if not all(p.exists() for p in contacts_parts):
    raise SystemExit('Missing one or more contacts directory payload parts')
try:
    contacts_b64 = ''.join(p.read_text(encoding='utf-8').strip() for p in contacts_parts)
    contacts_b64_sha = hashlib.sha256(contacts_b64.encode('utf-8')).hexdigest()
    if contacts_b64_sha != '0ef632c97b336214b66355adc7d7b4adfa8fd9380923703fc580af5da58890d1':
        raise ValueError(f'payload text checksum mismatch: {contacts_b64_sha}')
    contacts_raw = zlib.decompress(base64.b64decode(contacts_b64))
except Exception as exc:
    raise SystemExit(f'Could not decode contacts directory payload: {exc}')
contacts_sha = hashlib.sha256(contacts_raw).hexdigest()
expected_contacts_sha = '9f5fef5559e5b390a504ce36b840168e258509be5a75c948f399e2807ad71888'
if contacts_sha != expected_contacts_sha:
    raise SystemExit(f'Contacts directory checksum mismatch: {contacts_sha}')
contacts_target = app / 'contacts_directory.js'
contacts_target.write_bytes(contacts_raw)
if hashlib.sha256(contacts_target.read_bytes()).hexdigest() != expected_contacts_sha:
    raise SystemExit('Contacts directory write verification failed')

# Serve and load the directory last, after Operations and Chef, so it can
# connect to Service Mode, Stock and Chef contact queries.
srv = server.read_text(encoding='utf-8')
runtime_marker = "RUNTIME_FILES = (\n"
contacts_route = "    '/contacts_directory.js',\n"
if contacts_route not in srv:
    if runtime_marker not in srv:
        raise SystemExit('RUNTIME_FILES marker missing while adding contacts directory')
    srv = srv.replace(runtime_marker, runtime_marker + contacts_route, 1)
server.write_text(srv, encoding='utf-8')

rt = runtime_loader.read_text(encoding='utf-8')
m = re.search(r"(const\s+modules\s*=\s*\[)(.*?)(\n\s*\];)", rt, re.S)
if not m:
    raise SystemExit('runtime_loader.js modules array not found for contacts directory')
body = m.group(2)
body = body.replace(",\n    'contacts_directory.js'", "")
body = body.replace(",\n    \"contacts_directory.js\"", "")
body = body.replace("'contacts_directory.js',\n", "")
body = body.replace('"contacts_directory.js",\n', "")
body = body.rstrip() + ",\n    'contacts_directory.js'"
rt = rt[:m.start(2)] + body + rt[m.end(2):]
rt = re.sub(r"\?runtime=[^'\"]+", '?runtime=20260921-contacts1', rt)
runtime_loader.write_text(rt, encoding='utf-8')

if guard.exists():
    gt = guard.read_text(encoding='utf-8')
    gt = re.sub(r"runtime_loader\.js\?v=[^'\"]+", 'runtime_loader.js?v=20260921-contacts1', gt)
    guard.write_text(gt, encoding='utf-8')

srv_check = server.read_text(encoding='utf-8')
rt_check = runtime_loader.read_text(encoding='utf-8')
if srv_check.count("'/contacts_directory.js'") + srv_check.count('"/contacts_directory.js"') != 1:
    raise SystemExit('Contacts directory runtime route not installed exactly once')
if rt_check.count("'contacts_directory.js'") + rt_check.count('"contacts_directory.js"') != 1:
    raise SystemExit('Contacts directory module not installed exactly once')
print('Applied Contacts directory: suppliers, engineers, priority numbers, Service Mode and Chef lookup')


# 2026-09-21 Mobile freezer temperature sign control.
# Some phone numeric keyboards omit a minus key, making freezer readings
# impossible to enter. Add a visible +/- control without changing stored data.
import hashlib
temp_sign_src = Path('temperature_negative_input.js')
if not temp_sign_src.exists():
    raise SystemExit('Missing mobile temperature sign control asset')
temp_sign_raw = temp_sign_src.read_bytes()
expected_temp_sign_sha = '8ecaf8b71e9d87d9645007943c79ebce07d9736b5861559f8dc25cfa8f9edf78'
if hashlib.sha256(temp_sign_raw).hexdigest() != expected_temp_sign_sha:
    raise SystemExit('Mobile temperature sign control checksum mismatch')
temp_sign_target = app / 'temperature_negative_input.js'
temp_sign_target.write_bytes(temp_sign_raw)

srv = server.read_text(encoding='utf-8')
runtime_marker = "RUNTIME_FILES = (\n"
temp_sign_route = "    '/temperature_negative_input.js',\n"
if temp_sign_route not in srv:
    if runtime_marker not in srv:
        raise SystemExit('RUNTIME_FILES marker missing while adding mobile temperature sign control')
    srv = srv.replace(runtime_marker, runtime_marker + temp_sign_route, 1)
server.write_text(srv, encoding='utf-8')

rt = runtime_loader.read_text(encoding='utf-8')
m = re.search(r"(const\s+modules\s*=\s*\[)(.*?)(\n\s*\];)", rt, re.S)
if not m:
    raise SystemExit('runtime_loader.js modules array not found for mobile temperature sign control')
body = m.group(2)
body = body.replace(",\n    'temperature_negative_input.js'", "")
body = body.replace(",\n    \"temperature_negative_input.js\"", "")
body = body.replace("'temperature_negative_input.js',\n", "")
body = body.replace('"temperature_negative_input.js",\n', "")
body = body.rstrip() + ",\n    'temperature_negative_input.js'"
rt = rt[:m.start(2)] + body + rt[m.end(2):]
rt = re.sub(r"\?runtime=[^'\"]+", '?runtime=20260921-tempminus2', rt)
runtime_loader.write_text(rt, encoding='utf-8')

if guard.exists():
    gt = guard.read_text(encoding='utf-8')
    gt = re.sub(r"runtime_loader\.js\?v=[^'\"]+", 'runtime_loader.js?v=20260921-tempminus2', gt)
    guard.write_text(gt, encoding='utf-8')

srv_check = server.read_text(encoding='utf-8')
rt_check = runtime_loader.read_text(encoding='utf-8')
if srv_check.count("'/temperature_negative_input.js'") + srv_check.count('"/temperature_negative_input.js"') != 1:
    raise SystemExit('Mobile temperature sign route not installed exactly once')
if rt_check.count("'temperature_negative_input.js'") + rt_check.count('"temperature_negative_input.js"') != 1:
    raise SystemExit('Mobile temperature sign module not installed exactly once')
print('Applied mobile temperature +/- entry control for freezer readings')


# 2026-09-23 Team login/password repair.
# Keep Team profiles and real sign-in accounts together. New people require an
# initial temporary password; existing profile-only rows can be provisioned with
# a login by setting a password. Existing passwords are never changed unless a
# manager explicitly submits a new one.
team_src = Path('team_login_accounts.js')
if not team_src.exists():
    raise SystemExit('Missing Team login accounts runtime')
team_target = app / 'team_login_accounts.js'
team_target.write_bytes(team_src.read_bytes())

auth_path = app / 'auth_controls.py'
auth_text = auth_path.read_text(encoding='utf-8')

# If an older UI created a Team profile without a user_accounts row, let the
# normal create-user endpoint adopt that profile instead of appending a duplicate.
create_old = """                current = _read_venue_state(venue_id, conn=conn, for_update=True); state=current['state']
                public_user={'id':user_id,'username':username,'name':name,'role':role,'jobTitle':job_title,'active':True,'mustChangePassword':True,'createdAt':app.utcnow()}
                state.setdefault('users',[]).append(public_user)
                revision=current['revision']+1
"""
create_new = """                current = _read_venue_state(venue_id, conn=conn, for_update=True); state=current['state']
                existing_profile=next((u for u in state.setdefault('users',[]) if str(u.get('username','')).lower()==username),None)
                if existing_profile:
                    public_user=existing_profile
                    user_id=str(public_user.get('id') or user_id)
                    public_user.update({'id':user_id,'username':username,'name':name,'role':role,'jobTitle':job_title,'active':True,'mustChangePassword':True})
                    public_user.setdefault('createdAt',app.utcnow())
                else:
                    public_user={'id':user_id,'username':username,'name':name,'role':role,'jobTitle':job_title,'active':True,'mustChangePassword':True,'createdAt':app.utcnow()}
                    state.setdefault('users',[]).append(public_user)
                revision=current['revision']+1
"""
if 'existing_profile=next((u for u in state.setdefault' not in auth_text:
    if create_old not in auth_text:
        raise SystemExit('Could not locate create_user profile block for Team login repair')
    auth_text = auth_text.replace(create_old, create_new, 1)

# The manager password action also repairs a legacy profile-only person. Query
# the real account table first; if no account exists for this venue and the
# manager supplied a password, create the account using the existing profile id.
manage_probe_old = """            new_password=payload.get('newPassword')
            if new_password is not None and not _password_ok(str(new_password)):
                conn.rollback(); handler.send_json({'error':'Temporary password must be at least 10 characters.'},400); return
"""
manage_probe_new = manage_probe_old + """            account_exists_here=False; account_taken_elsewhere=False
            with conn.cursor() as cur:
                cur.execute('SELECT venue_id FROM user_accounts WHERE username=%s',(username,))
                account_row=cur.fetchone()
            if account_row:
                account_exists_here=str(account_row['venue_id'])==str(venue_id)
                account_taken_elsewhere=not account_exists_here
            if new_password is not None and account_taken_elsewhere:
                conn.rollback(); handler.send_json({'error':'That username belongs to a different venue. Choose a different username for this person.'},409); return
"""
if 'account_exists_here=False; account_taken_elsewhere=False' not in auth_text:
    if manage_probe_old not in auth_text:
        raise SystemExit('Could not locate manage_user password validation for Team login repair')
    auth_text = auth_text.replace(manage_probe_old, manage_probe_new, 1)

manage_write_old = """            with conn.cursor() as cur:
                cur.execute('UPDATE user_accounts SET name=%s,role=%s,job_title=%s,active=%s WHERE username=%s AND venue_id=%s', fields)
                if new_password is not None:
                    cur.execute('UPDATE user_accounts SET password=%s,must_change_password=TRUE WHERE username=%s AND venue_id=%s',
                                (app.hash_password(str(new_password)),username,venue_id))
                    target['mustChangePassword']=True
                cur.execute('UPDATE venue_states SET state=%s::jsonb,revision=%s,updated_at=NOW(),updated_by=%s WHERE venue_id=%s',
"""
manage_write_new = """            with conn.cursor() as cur:
                if account_exists_here:
                    cur.execute('UPDATE user_accounts SET name=%s,role=%s,job_title=%s,active=%s WHERE username=%s AND venue_id=%s', fields)
                    if new_password is not None:
                        cur.execute('UPDATE user_accounts SET password=%s,must_change_password=TRUE WHERE username=%s AND venue_id=%s',
                                    (app.hash_password(str(new_password)),username,venue_id))
                        target['mustChangePassword']=True
                elif new_password is not None:
                    account_user_id=str(target.get('id') or ('u_'+app.secrets.token_hex(8)))
                    target['id']=account_user_id; target['mustChangePassword']=True
                    cur.execute('''INSERT INTO user_accounts(username,venue_id,user_id,name,role,job_title,password,active,must_change_password)
                                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,TRUE)''',
                                (username,venue_id,account_user_id,target.get('name') or username,target.get('role') or 'staff',
                                 target.get('jobTitle') or '',app.hash_password(str(new_password)),bool(target.get('active',True))))
                cur.execute('UPDATE venue_states SET state=%s::jsonb,revision=%s,updated_at=NOW(),updated_by=%s WHERE venue_id=%s',
"""
if "account_user_id=str(target.get('id')" not in auth_text:
    if manage_write_old not in auth_text:
        raise SystemExit('Could not locate manage_user account write block for Team login repair')
    auth_text = auth_text.replace(manage_write_old, manage_write_new, 1)

auth_path.write_text(auth_text, encoding='utf-8')

# Serve the Team runtime and load it last so it replaces the old profile-only
# Team editor while remaining compatible with the self-service password button.
srv = server.read_text(encoding='utf-8')
runtime_marker = "RUNTIME_FILES = (\n"
team_route = "    '/team_login_accounts.js',\n"
if team_route not in srv:
    if runtime_marker not in srv:
        raise SystemExit('RUNTIME_FILES marker missing while adding Team login accounts')
    srv = srv.replace(runtime_marker, runtime_marker + team_route, 1)
server.write_text(srv, encoding='utf-8')

runtime_loader = app / 'runtime_loader.js'
rt = runtime_loader.read_text(encoding='utf-8')
m = re.search(r"(const\s+modules\s*=\s*\[)(.*?)(\n\s*\];)", rt, re.S)
if not m:
    raise SystemExit('runtime_loader.js modules array not found for Team login accounts')
body = m.group(2)
body = body.replace(",\n    'team_login_accounts.js'", "")
body = body.replace(",\n    \"team_login_accounts.js\"", "")
body = body.replace("'team_login_accounts.js',\n", "")
body = body.replace('"team_login_accounts.js",\n', "")
body = body.rstrip() + ",\n    'team_login_accounts.js'"
rt = rt[:m.start(2)] + body + rt[m.end(2):]
rt = re.sub(r"\?runtime=[^'\"]+", '?runtime=20260923-teamlogin1', rt)
runtime_loader.write_text(rt, encoding='utf-8')

guard = app / 'temperature_reset_guard.js'
if guard.exists():
    gt = guard.read_text(encoding='utf-8')
    gt = re.sub(r"runtime_loader\.js\?v=[^'\"]+", 'runtime_loader.js?v=20260923-teamlogin1', gt)
    guard.write_text(gt, encoding='utf-8')

srv_check = server.read_text(encoding='utf-8')
rt_check = runtime_loader.read_text(encoding='utf-8')
auth_check = auth_path.read_text(encoding='utf-8')
if srv_check.count("'/team_login_accounts.js'") + srv_check.count('"/team_login_accounts.js"') != 1:
    raise SystemExit('Team login accounts route not installed exactly once')
if rt_check.count("'team_login_accounts.js'") + rt_check.count('"team_login_accounts.js"') != 1:
    raise SystemExit('Team login accounts module not installed exactly once')
if 'account_exists_here=False; account_taken_elsewhere=False' not in auth_check or 'existing_profile=next((u for u in state.setdefault' not in auth_check:
    raise SystemExit('Team login backend repair did not install')
print('Applied Team login repair: Add person requires password; existing profiles can be provisioned/reset safely')

# Force the repaired Team login UI to load directly after all other page scripts.
# This avoids stale/runtime-loader ordering leaving the older profile-only Team view active.
index = app / 'index.html'
team_html = index.read_text(encoding='utf-8')
team_html = re.sub(r'\s*<script[^>]+src=["\']/?team_login_accounts\.js(?:\?[^"\']*)?["\'][^>]*></script>\s*', '\n', team_html, flags=re.I)
team_tag = '<script src="/team_login_accounts.js?v=20260923-teamlogin2"></script>'
if '</body>' not in team_html:
    raise SystemExit('Could not locate </body> while installing direct Team login UI')
team_html = team_html.replace('</body>', team_tag + '\n</body>', 1)
index.write_text(team_html, encoding='utf-8')

final_team_html = index.read_text(encoding='utf-8')
if final_team_html.count(team_tag) != 1:
    raise SystemExit('Direct Team login UI tag not installed exactly once')
print('Forced Team login UI to load directly after other page scripts')

