from pathlib import Path

for path in [Path('app/main_app.js'), Path('app/kitchen_fixes_20260810.js')]:
    if not path.exists():
        continue
    text = path.read_text(encoding='utf-8')
    print(f'=== TEMP BACKFILL DIAGNOSTIC {path} ===')
    needles = [
        'historic temperature backfill',
        'Historic temperature',
        'backfill',
        'function readingFor',
        '/api/temperature',
        'temperature-readings',
        'append_temperature',
        'period===',
        'period==='
    ]
    seen=[]
    for needle in needles:
        start=0
        shown=0
        while shown<8:
            i=text.lower().find(needle.lower(), start)
            if i<0: break
            if all(abs(i-j)>100 for j in seen):
                seen.append(i)
                print(f'--- {needle} @ {i} ---')
                print(text[max(0,i-2200):min(len(text),i+4200)])
                print('--- END ---')
                shown+=1
            start=i+max(1,len(needle))
