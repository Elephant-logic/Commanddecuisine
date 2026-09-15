from pathlib import Path

index = Path('app/index.html')
patch = Path('recipe_import_patch.js')
text = index.read_text(encoding='utf-8')
js = patch.read_text(encoding='utf-8')
marker = 'id="cdc-recipe-import-patch"'
if marker in text:
    print('Recipe import patch already present')
else:
    tag = f'\n<script id="cdc-recipe-import-patch">\n{js}\n</script>\n'
    if '</body>' not in text:
        raise SystemExit('Could not find </body> in app/index.html')
    text = text.replace('</body>', tag + '</body>', 1)
    index.write_text(text, encoding='utf-8')
    print('Recipe photo/notes import + update controls installed')
