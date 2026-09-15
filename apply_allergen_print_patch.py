from pathlib import Path
import shutil

app_dir = Path('app')

# Copy the allergen print helper into the built application.
shutil.copyfile('allergen_print_patch.js', app_dir / 'allergen_print_patch.js')

# Add the allergen helper to the page if it is not already present.
index = app_dir / 'index.html'
text = index.read_text(encoding='utf-8')
marker = '</body>'
script = '<script src="/allergen_print_patch.js"></script>\n'
if script not in text:
    if marker not in text:
        raise SystemExit('Expected </body> marker not found in index.html')
    text = text.replace(marker, script + marker, 1)
    index.write_text(text, encoding='utf-8')

# main_app.js is created earlier in the build by externalize_main_script.py.
# The production HTTP server only serves JavaScript files explicitly listed in
# RUNTIME_FILES, so make both external scripts first-class runtime assets here.
server = app_dir / 'server.py'
server_text = server.read_text(encoding='utf-8')
runtime_marker = 'RUNTIME_FILES = (\n'
if runtime_marker not in server_text:
    raise SystemExit('RUNTIME_FILES marker not found in server.py')

routes = ('/main_app.js', '/allergen_print_patch.js')
for route in routes:
    literal = f"    '{route}',\n"
    if literal not in server_text:
        server_text = server_text.replace(runtime_marker, runtime_marker + literal, 1)

server.write_text(server_text, encoding='utf-8')

for route in routes:
    if f"'{route}'" not in server_text:
        raise SystemExit(f'Failed to enable runtime route {route}')

if not (app_dir / 'main_app.js').exists():
    raise SystemExit('main_app.js was not created before static route setup')

print('Enabled /main_app.js and /allergen_print_patch.js runtime routes')
