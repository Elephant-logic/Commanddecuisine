from pathlib import Path

server = Path('app/server.py')
text = server.read_text(encoding='utf-8')

marker = "RUNTIME_FILES = (\n"
if marker not in text:
    raise SystemExit('RUNTIME_FILES marker not found in server.py')

wanted = ["'/main_app.js',", "'/allergen_print_patch.js',"]
insert = ''.join(f'    {item}\n' for item in wanted if item not in text)
if insert:
    text = text.replace(marker, marker + insert, 1)

for route in ('/main_app.js', '/allergen_print_patch.js'):
    if repr(route) not in text and f"'{route}'" not in text:
        raise SystemExit(f'Failed to add static route for {route}')

server.write_text(text, encoding='utf-8')
print('Static routes enabled for external application scripts')
