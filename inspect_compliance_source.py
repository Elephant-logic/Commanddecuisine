from pathlib import Path
text=Path('app/index.html').read_text(encoding='utf-8')
for needle in ['Probe calibration','COMPLIANCE TODAY','Compliance Today','compliance']:
    print('\n=== INSPECT',needle,'===')
    start=0
    found=0
    while True:
        i=text.find(needle,start)
        if i<0 or found>=4: break
        print(text[max(0,i-1800):min(len(text),i+2600)])
        print('\n---END SNIP---\n')
        start=i+len(needle); found+=1
