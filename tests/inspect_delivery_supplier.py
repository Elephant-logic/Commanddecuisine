from pathlib import Path
import re
s=Path("app/contacts_directory.js").read_text(encoding="utf-8")
for pat in ["function contacts()", "function contacts(", "function openEditor(", "function saveState(", "function renderDirectory(", "c.category", "state.contacts", "STATE.contacts", "contactsDirectory", "contactDirectory"]:
 ms=list(re.finditer(re.escape(pat),s,re.I))
 print("MATCH",pat,len(ms))
 for m in ms[:3]:print("AT",m.start(),"DATA",repr(s[max(0,m.start()-100):m.start()+1700]))
s=Path("app/main_app.js").read_text(encoding="utf-8")
start=s.find("VIEWS.deliveries=function(v){")
end=s.find("/* ----------",start+1)
print("DELIVERY VIEW",start,end,repr(s[start:end if end>0 else start+8200]))
