from pathlib import Path
import re

p = Path('app/index.html')
text = p.read_text(encoding='utf-8')

patterns = [
    r'function\s+[A-Za-z0-9_]*stock[A-Za-z0-9_]*\s*\([^)]*\)\s*\{',
    r'function\s+[A-Za-z0-9_]*inventory[A-Za-z0-9_]*\s*\([^)]*\)\s*\{',
    r'label\s*:\s*["\']Par["\']',
    r'label\s*:\s*["\']Qty["\']',
    r'Below par',
    r'par level',
    r'STATE\.stock'
]
seen=set(); n=0
for pat in patterns:
    for m in re.finditer(pat, text, re.I):
        a=max(0,m.start()-700); b=min(len(text),m.start()+4200)
        snippet=text[a:b].replace('\n',' ')
        key=(m.start()//1000,pat)
        if key in seen: continue
        seen.add(key); n+=1
        print(f'STOCK_TARGET_{n}:', snippet)
        if n>=20: break
    if n>=20: break
print('STOCK_TARGET_COUNT', n)
