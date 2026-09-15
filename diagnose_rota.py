from pathlib import Path
import re

for name in ('app/main_app.js','app/index.html'):
    p=Path(name)
    if not p.exists():
        continue
    text=p.read_text(encoding='utf-8')
    print(f'=== ROTA DIAGNOSTIC {name} ===')
    seen=[]
    for pat in (r'rota', r'shift'):
        for m in re.finditer(pat,text,re.I):
            s=max(0,m.start()-1200); e=min(len(text),m.start()+2200)
            key=(s//500,e//500)
            if key in seen: continue
            seen.append(key)
            print(f'--- {pat} @{m.start()} ---')
            print(text[s:e].replace('\n','\\n'))
            if len(seen)>=12: break
        if len(seen)>=12: break
