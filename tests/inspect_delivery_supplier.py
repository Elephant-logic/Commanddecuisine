"""Inspect exact supplier editor and nav entries in assembled release (read-only)."""
from pathlib import Path
import re
p=Path("app/main_app.js")
text=p.read_text(encoding="utf-8")
patterns=[
 "VIEWS.settings=function(v){",
 "VIEWS.deliveries=function(v){",
 "STATE.suppliers.forEach",
 "STATE.suppliers.map",
 "function openContacts(",
 "contacts_directory.js",
 'title:"Suppliers"',
 'label:"Suppliers"',
 'Suppliers', 'Contact directory', 'Contacts & important numbers',
 "function renderSuppliers",
 "function suppliers",
 "function supplier",
 'VIEWS.suppliers',
 'showSuppliers',
 'VIEWS.contacts',
 'state.suppliers',
 'STATE.contacts',
]
for pat in patterns:
 ms=list(re.finditer(re.escape(pat),text,re.I))
 if not ms:continue
 print("TERM",pat,"COUNT",len(ms))
 for m in ms[:5]:
  a=max(0,m.start()-600);b=min(len(text),m.end()+(2500 if "suppliers" in pat.lower() or pat.startswith("VIEWS.") else 800))
  print("AT",m.start(),repr(text[a:b]))
print("CONTACT DIRECTORY")
p=Path("app/contacts_directory.js")
text=p.read_text(encoding="utf-8")
for pat in ['function install(', 'function open(', 'function openDirectory(', 'Add contact',
            'Add supplier','Contacts','More','VIEWS.', 'window.CDCContacts']:
 ms=list(re.finditer(re.escape(pat),text,re.I))
 print("TERM",pat,"COUNT",len(ms))
 for m in ms[:2]:
  print("AT",m.start(),repr(text[max(0,m.start()-200):m.end()+800]))
