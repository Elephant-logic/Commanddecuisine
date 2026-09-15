from pathlib import Path

p=Path('app/main_app.js')
text=p.read_text(encoding='utf-8')
print('=== GRAPH DIAGNOSTIC ===')
needles=['Compliance — last 7 days','Compliance — Last 7 Days','Compliance — Last 7 Days','COMPLIANCE — LAST 7 DAYS','bars(','donut(','lineChart(']
seen=[]
for needle in needles:
    start=0
    count=0
    while True:
        i=text.find(needle,start)
        if i<0 or count>=8: break
        # Skip helper function definitions for chart primitives.
        prefix=text[max(0,i-30):i]
        if needle in ('bars(','donut(','lineChart(') and ('function '+needle[:-1]) in prefix:
            start=i+len(needle); continue
        key=(needle,i)
        if key not in seen:
            print(f'--- {needle} @ {i} ---')
            print(text[max(0,i-900):min(len(text),i+1800)])
            print('--- END GRAPH SNIP ---')
            seen.append(key)
        start=i+len(needle); count+=1
