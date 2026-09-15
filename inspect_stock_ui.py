from pathlib import Path
import re

p = Path('app/index.html')
text = p.read_text(encoding='utf-8')
terms = ['par','stock','inventory','below par','Stock','Par']
seen=[]
for term in terms:
    for m in re.finditer(re.escape(term), text, re.I):
        a=max(0,m.start()-450); b=min(len(text),m.end()+900)
        snippet=text[a:b].replace('\n',' ')
        key=snippet[:180]
        if key in seen: continue
        seen.append(key)
        print('STOCK_INSPECT:', snippet)
        if len(seen)>=18: break
    if len(seen)>=18: break
print('STOCK_INSPECT_COUNT', len(seen))
