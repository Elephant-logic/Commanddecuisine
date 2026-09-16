from pathlib import Path

checks = {
    'app/main_app.js': ['function persist','async function persist','function save','markDirty','tempReadings','/api/','readings'],
    'app/server.py': ['temperature_store','append_readings','list_readings','temperature','/api/'],
    'app/app.py': ['temperature_store','append_readings','list_readings','temperature','/api/'],
    'app/kitchen_fixes_20260810.js': ['function readingFor','slotForReading','historic temperature backfill']
}
for name, needles in checks.items():
    path=Path(name)
    if not path.exists(): continue
    text=path.read_text(encoding='utf-8')
    print(f'=== TEMP PERSIST DIAGNOSTIC {name} ===')
    seen=[]
    for needle in needles:
        start=0; shown=0
        while shown<12:
            i=text.lower().find(needle.lower(),start)
            if i<0: break
            if all(abs(i-j)>120 for j in seen):
                seen.append(i)
                print(f'--- {needle} @ {i} ---')
                print(text[max(0,i-1800):min(len(text),i+3600)])
                print('--- END ---')
                shown+=1
            start=i+max(1,len(needle))
