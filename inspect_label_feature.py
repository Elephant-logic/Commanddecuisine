from pathlib import Path
import re

print('=== LABEL FEATURE INSPECTION START ===')
for name in ('main_app.js','index.html'):
    p=Path('app')/name
    if not p.exists():
        continue
    text=p.read_text(encoding='utf-8')
    pats=[r'VIEWS\.labels\s*=',r'labels?\b',r'barcode',r'qr\b',r'freez',r'frozen',r'useBy',r'use[ -]?by',r'best[ -]?before']
    seen=[]
    for pat in pats:
        for m in re.finditer(pat,text,re.I):
            if any(abs(m.start()-x)<500 for x in seen):
                continue
            seen.append(m.start())
            lo=max(0,m.start()-1200); hi=min(len(text),m.end()+2500)
            print(f'--- {name} @ {m.start()} / {pat} ---')
            print(text[lo:hi].replace('\n','\\n'))
            print('<<<SNIP>>>')
            if len(seen)>=30: break
        if len(seen)>=30: break
print('=== LABEL FEATURE INSPECTION END ===')
