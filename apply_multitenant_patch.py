from pathlib import Path
import shutil

app_dir = Path('app')
for src, dest in (
    ('auth_controls_override.py', 'auth_controls.py'),
    ('temperature_store_override.py', 'temperature_store.py'),
    ('supabase_storage_override_mt.py', 'drive_storage.py'),
):
    shutil.copyfile(src, app_dir / dest)

index = app_dir / 'index.html'
text = index.read_text(encoding='utf-8')
text = text.replace('<div class="tag-line">First-time Admin setup</div>', '<div class="tag-line">Create your venue & Admin</div>')
text = text.replace('${icon("ok")}Create Admin & start', '${icon("ok")}Create venue & start')
old_hint = '<div class="demo-hint">Staff accounts are created and managed by an Admin.</div>`;'
new_hint = '<div class="demo-hint">Staff accounts are created and managed by an Admin.</div><button class="btn ghost" id="newVenueBtn" style="width:100%;margin-top:12px">Create a new venue</button>`;'
if old_hint not in text:
    raise SystemExit('Login hint marker not found in index.html')
text = text.replace(old_hint, new_hint, 1)
old_events = '$("#lbtn").addEventListener("click",go);\n  $("#lp").addEventListener("keydown",e=>{if(e.key==="Enter")go();});\n  $("#lu").focus();'
new_events = '$("#lbtn").addEventListener("click",go);\n  $("#lp").addEventListener("keydown",e=>{if(e.key==="Enter")go();});\n  $("#newVenueBtn").addEventListener("click",renderSetup);\n  $("#lu").focus();'
if old_events not in text:
    raise SystemExit('Login event marker not found in index.html')
text = text.replace(old_events, new_events, 1)
index.write_text(text, encoding='utf-8')
