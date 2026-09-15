from pathlib import Path

index = Path('app/index.html')
text = index.read_text(encoding='utf-8')
old = '<script src="manager_remove_controls.js"></script>'
new = '<script src="manager_remove_controls.js?v=20260915-staff-delete"></script>'
if old not in text:
    raise SystemExit('manager removal script tag not found')
text = text.replace(old, new, 1)
index.write_text(text, encoding='utf-8')
print('Manager removal controls cache-busted')
