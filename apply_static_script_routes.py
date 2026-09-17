from pathlib import Path
import re
import shutil

app = Path('app')
server = app / 'server.py'
loader = app / 'runtime_loader.js'

# These files live at repository root and are copied into the built app.
review_assets = [
    'safe_delete_patch.js',
    'ai_upgrade_patch.js',
    'compliance_pro.js',
    'integration_bridge.js',
]

for name in review_assets:
    src = Path(name)
    if not src.exists():
        raise SystemExit(f'Missing staged review asset: {name}')
    shutil.copy2(src, app / name)

# Keep existing external application scripts and expose the review modules.
text = server.read_text(encoding='utf-8')
marker = "RUNTIME_FILES = (\n"
if marker not in text:
    raise SystemExit('RUNTIME_FILES marker not found in server.py')

routes = ['/main_app.js', '/allergen_print_patch.js'] + ['/' + name for name in review_assets]
insert = ''.join(f"    {route!r},\n" for route in routes if route not in text)
if insert:
    text = text.replace(marker, marker + insert, 1)

for route in routes:
    if route not in text:
        raise SystemExit(f'Failed to add static route for {route}')
server.write_text(text, encoding='utf-8')

# Load the review modules last, after the base globals and all earlier patches.
loader_text = loader.read_text(encoding='utf-8')
match = re.search(r"(const\s+modules\s*=\s*\[)(.*?)(\n\s*\];)", loader_text, re.S)
if not match:
    raise SystemExit('runtime_loader.js modules array not found')
body = match.group(2)
missing = [name for name in review_assets if ("'" + name + "'") not in body and ('"' + name + '"') not in body]
if missing:
    addition = ''.join(",\n    " + repr(name) for name in missing)
    body = body.rstrip() + addition
    loader_text = loader_text[:match.start(2)] + body + loader_text[match.end(2):]
loader.write_text(loader_text, encoding='utf-8')

# Build-time self-check: one route and one module entry per asset.
server_check = server.read_text(encoding='utf-8')
loader_check = loader.read_text(encoding='utf-8')
for name in review_assets:
    route = '/' + name
    if server_check.count(repr(route)) != 1 and server_check.count('"' + route + '"') != 1:
        raise SystemExit(f'Runtime route not installed exactly once: {route}')
    if loader_check.count("'" + name + "'") + loader_check.count('"' + name + '"') != 1:
        raise SystemExit(f'Runtime module not installed exactly once: {name}')
    if not (app / name).exists():
        raise SystemExit(f'Built runtime asset missing: {name}')

print('Static routes enabled; safety, Chef Pro, Compliance Pro and integration bridge installed')
