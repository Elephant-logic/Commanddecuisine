from pathlib import Path
import re

root = Path('app')
keywords = re.compile(r'labels?|barcode|qr\b|use[ -]?by|best[ -]?before|freez|frozen|shelf[ -]?life', re.I)
print('=== LABEL FEATURE INSPECTION START ===')
shown = 0
for p in sorted(root.rglob('*')):
    if not p.is_file() or p.suffix.lower() not in {'.html','.js','.py','.css'}:
        continue
    try:
        text = p.read_text(encoding='utf-8')
    except Exception:
        continue
    matches = list(keywords.finditer(text))
    if not matches:
        continue
    print(f'--- {p} ({len(matches)} matches) ---')
    for m in matches[:20]:
        lo = max(0, m.start()-350)
        hi = min(len(text), m.end()+550)
        snippet = text[lo:hi].replace('\n','\\n')
        print(snippet)
        print('<<<SNIP>>>')
        shown += 1
        if shown >= 80:
            break
    if shown >= 80:
        break
print('=== LABEL FEATURE INSPECTION END ===')
