from pathlib import Path
from zipfile import ZipFile
import re
z=ZipFile('Command-de-Cuisine-clean-production.zip')
print("ZIP JS FILES",len([p for p in z.namelist() if p.endswith('.js')]))
for filename in z.namelist():
 if not (filename.endswith('.js') or filename.endswith('index.html')):continue
 s=z.read(filename).decode('utf-8')
 pat=re.compile(r'VIEWS\.timers|function\s+[A-Za-z0-9_$]*timer[A-Za-z0-9_$]*\s*\(|timerPreset|timer.*[Pp]reset|timer.*[Pp]ause|timer.*[Ss]tart|[Tt]imers',re.I)
 hits=list(pat.finditer(s))
 if hits:
  print(f'\n========== {filename} ({len(s)} chars; {len(hits)} matches) =========')
  spans=[]
  for match in hits[:23]:
   a=max(0,match.start()-750);b=min(len(s),match.end()+1500)
   if spans and a<=spans[-1][1]:spans[-1]=(spans[-1][0],max(spans[-1][1],b))
   else:spans.append((a,b))
  for a,b in spans[:12]:
   print(f'\n OFFSET {a}-{b}\n'+s[a:b][:14500])
