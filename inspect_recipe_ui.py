from pathlib import Path
import re
p=Path('app/index.html')
text=p.read_text(encoding='utf-8')
needles=['VIEWS.recipes','function editRecipe','Import','recipe','AI','menuImports','photoInput']
for needle in needles:
    print(f'=== NEEDLE {needle} ===')
    start=0
    hits=0
    while True:
        i=text.find(needle,start)
        if i<0 or hits>=8: break
        a=max(0,i-1800); b=min(len(text),i+4200)
        print(text[a:b])
        print('\n---\n')
        hits+=1; start=i+len(needle)
print('RECIPE_INSPECT_DONE')
