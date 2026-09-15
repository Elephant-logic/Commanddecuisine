from pathlib import Path
import shutil

app_dir = Path('app')
shutil.copyfile('allergen_print_patch.js', app_dir / 'allergen_print_patch.js')
index = app_dir / 'index.html'
text = index.read_text(encoding='utf-8')
marker = '</body>'
script = '<script src="allergen_print_patch.js"></script>\n'
if script in text:
    raise SystemExit(0)
if marker not in text:
    raise SystemExit('Expected </body> marker not found in index.html')
index.write_text(text.replace(marker, script + marker, 1), encoding='utf-8')
