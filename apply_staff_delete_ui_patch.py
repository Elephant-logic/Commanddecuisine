from pathlib import Path
import re

app = Path('app')
controls = app / 'account_controls.js'
js = controls.read_text(encoding='utf-8')

# Add a real destructive delete control beside the existing role/active/reset controls.
# The backend /api/users/manage endpoint already enforces: no self-delete and at least
# one active manager must remain. Historic operational/audit records are preserved.
if 'Delete account' not in js:
    pattern = re.compile(
        r"(const\s+reset\s*=\s*el\('button',\{class:'btn sm ghost',html:'Reset password'\}\);\s*"
        r"reset\.addEventListener\('click',\(\)=>resetPassword\(u\)\);\s*)"
        r"row\.append\(info,role,active,reset\);card\.append\(row\);"
    )
    replacement = r"""\1const remove=u.username!==ME.username?el('button',{class:'btn sm danger',html:'Delete account'}):null;
        if(remove)remove.addEventListener('click',async()=>{
          if(!confirm('Delete '+(u.name||u.username)+' from this venue?\n\nTheir login account will be permanently removed. Historic kitchen records and audit entries will remain.'))return;
          remove.disabled=true;
          try{
            await api('/api/users/manage',{method:'POST',body:JSON.stringify({username:u.username,delete:true})});
            await refreshSharedState();toast('Staff account deleted','ok');rerender();
          }catch(err){remove.disabled=false;toast(err.message||'Could not delete account','bad');}
        });
        row.append(info,role,active,reset);if(remove)row.append(remove);card.append(row);"""
    js, n = pattern.subn(replacement, js, count=1)
    if n != 1:
        raise SystemExit('Could not locate Team account action row in account_controls.js')

controls.write_text(js, encoding='utf-8')

# Force browsers to fetch the corrected Team controls rather than the old cached JS.
for path in (app / 'index.html', app / 'server.py'):
    if not path.exists():
        continue
    text = path.read_text(encoding='utf-8')
    text = re.sub(r'account_controls\.js(?:\?[^\"\']*)?', 'account_controls.js?v=20260915-delete2', text)
    path.write_text(text, encoding='utf-8')

print('Team UI now includes Delete account and is cache-busted')
