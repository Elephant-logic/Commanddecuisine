from pathlib import Path

print('=== TEMPERATURE REVIEW INSPECTION START ===')
for rel in ['app/main_app.js','app/kitchen_fixes_20260810.js','app/index.html']:
    p=Path(rel)
    if not p.exists():
        continue
    text=p.read_text(encoding='utf-8', errors='replace')
    print(f'--- {rel} ---')
    found=False
    for term in ['Needs review','New unit missing','Fill in','missing round','Missing round','temperature gaps','Temperature gaps']:
        start=0
        while True:
            i=text.find(term,start)
            if i<0: break
            found=True
            lo=max(0,i-2200); hi=min(len(text),i+3000)
            print(f'@@ {term!r} @ {i} @@')
            print(text[lo:hi])
            start=i+len(term)
    if not found:
        print('(no review markers found)')
print('=== TEMPERATURE REVIEW INSPECTION END ===')
