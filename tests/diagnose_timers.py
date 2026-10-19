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

print("\n================ GENERATED APP ================\n")
for filename in sorted(Path('app').rglob('*.js'))+[Path('app/index.html')]:
 if not filename.is_file():continue
 s=filename.read_text(encoding='utf-8',errors='replace')
 pat=re.compile(r'VIEWS\.timers|VIEWS\[.timers|function\s+[A-Za-z0-9_$]*timer[A-Za-z0-9_$]*\s*\(|timerPreset|[Tt]imers|timer.*(?:pause|start|reset|stop|button|click)',re.I)
 hits=list(pat.finditer(s))
 if hits:
  print(f'\n========== {filename} ({len(s)} chars; {len(hits)} matches) =========')
  spans=[]
  for match in hits[:30]:
   a=max(0,match.start()-650);b=min(len(s),match.end()+1600)
   if spans and a<=spans[-1][1]:spans[-1]=(spans[-1][0],max(spans[-1][1],b))
   else:spans.append((a,b))
  for a,b in spans[:8]:
   print(f'\n OFFSET {a}-{b}\n'+s[a:b][:12000])

print("\n========== FOCUSED V2 TIMER SOURCE ==========")
v2=Path("app/kitchen_tools_v2.js").read_text()
for startlabel,endlabel in [
 ("function panelHtml(){","function durationFromText"),
 ("function bindPanel(){","function durationFromText"),
 ("function addTimer(","function serviceData"),
 ("function openSheet","function durationFromText")
]:
 a=v2.find(startlabel);b=v2.find(endlabel,a+1)
 print("FOCUS",startlabel,a,endlabel,b)
 if a>=0: print(v2[a:(b if b>a else a+10500)][:11000])

print("\n========== V2 BOTTOM TICK AND INSTALL ==========")
print(v2[v2.find("function durationFromText"):][-6000:])
