from pathlib import Path

index = Path('app/index.html')
text = index.read_text(encoding='utf-8')

old = 'kitchen_fixes_20260810.js?v=20260812c'
new = 'kitchen_fixes_20260810.js?v=20260915-offline2'
if old not in text and new not in text:
    raise SystemExit('Expected kitchen fixes script URL not found in index.html')
text = text.replace(old, new)

index.write_text(text, encoding='utf-8')
print('Bumped kitchen compliance asset version for offline-unit rules')
