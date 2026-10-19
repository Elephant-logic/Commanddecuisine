"""Last-stage, fail-closed app safety patch; changes no stored user data."""
from pathlib import Path
root=Path("app")
auth=root/"auth_controls.py"
temp=root/"temperature_store.py"
main=root/"main_app.js"
allergen=root/"allergen_matrix_safety.js"
index=root/"index.html"
for path in (auth,temp,main,allergen,index):
    if not path.exists(): raise SystemExit("Missing required production file: "+str(path))

s=auth.read_text(encoding="utf-8")
helper=r'''

def _cdc_protected_state_change(old_state, incoming_state):
    """Reject non-manager changes to safety attestations using locked server data."""
    if _canon(old_state.get('managerSignoffs', [])) != _canon(incoming_state.get('managerSignoffs', [])):
        return 'Only managers can edit or remove manager sign-offs.'
    def approvals(state):
        out=[]
        for r in state.get('recipes', []) or []:
            if not isinstance(r,dict):continue
            rid=str(r.get('id') or '')
            fields=('allergens','allergenVerified','allergenDrafts',
                    'allergenReviewRequired','allergenVerificationReason',
                    'ingredientAllergenAuthoritative','ingredientAllergensManaged')
            flags={k:r[k] for k in fields if k in r}
            if flags:out.append(['recipe',rid,flags])
            for ing in r.get('ingredients', []) or []:
                if not isinstance(ing,dict):continue
                if ing.get('allergenVerified') is True or str(ing.get('allergenSource') or '').lower() in ('manager-edit','user-confirmed'):
                    out.append(['verified-ingredient',rid,ing])
        for row in state.get('stock', []) or []:
            if isinstance(row,dict) and 'allergenVerified' in row:
                out.append(['stock-verification',str(row.get('id') or ''),row['allergenVerified']])
        return sorted(_canon(x) for x in out)
    if approvals(old_state)!=approvals(incoming_state):
        return 'Only managers can confirm or modify protected allergen information.'
    return ''

'''
marker="def save_state(handler, payload):"
if s.count(marker)!=1 or "_cdc_protected_state_change(" in s:
    raise SystemExit("Auth save-state marker unexpectedly changed")
s=s.replace(marker,helper+marker,1)
old="""                incoming=merged; conflict_merge=True
            backdated_inserted=_sync_backdated_temperature_candidates(conn,venue_id,incoming,user)"""
new="""                incoming=merged; conflict_merge=True
            if user.get('role') != 'manager':
                protected_error=_cdc_protected_state_change(current['state'], incoming)
                if protected_error:
                    conn.rollback()
                    handler.send_json({'error':protected_error},403)
                    return
            # Legacy back-dated temperature sync is manager-only.
            backdated_inserted=(_sync_backdated_temperature_candidates(conn,venue_id,incoming,user)
                                if user.get('role')=='manager' else 0)"""
if s.count(old)!=1:raise SystemExit("Auth conflict/backfill marker unexpectedly changed")
s=s.replace(old,new,1)
auth.write_text(s,encoding="utf-8")

# Atomic historic corrections are manager-only already. Secure the older delete
# endpoint and require today's local date for routine staff temperature entry.
t=temp.read_text(encoding="utf-8")
old="""def delete_reading(handler,payload):
    stored,user=handler.require_user()
    if not stored:return
    row_id="""
new="""def delete_reading(handler,payload):
    stored,user=handler.require_user()
    if not stored:return
    if user.get('role')!='manager':
        handler.send_json({'error':'Manager access required to delete a saved temperature record.'},403);return
    row_id="""
if t.count(old)!=1:raise SystemExit("Cannot find legacy temperature delete handler")
t=t.replace(old,new,1)
old="""        if not row_id or app_id not in valid_apps:
            handler.send_json({'error':'Temperature reading is incomplete or invalid.'},400);return
        notes="""
new="""        if not row_id or app_id not in valid_apps:
            handler.send_json({'error':'Temperature reading is incomplete or invalid.'},400);return
        if user.get('role')!='manager':
            local_ts=parsed.replace(tzinfo=_LONDON) if parsed.tzinfo is None else parsed.astimezone(_LONDON)
            local_now=datetime.now(_LONDON)
            if local_ts.date()!=local_now.date() or local_ts > local_now + __import__('datetime').timedelta(minutes=5):
                handler.send_json({'error':'Historic or future temperature entry requires manager access.'},403);return
        notes="""
if t.count(old)!=1:raise SystemExit("Cannot find temperature append validation")
t=t.replace(old,new,1)
old="""                                    'by':str(row.get('by') or user.get('username') or '')[:80],
                                    'source':str(row.get('source') or ('manual' if equipment_status == 'reading' else 'manual-status'))[:80],"""
new="""                                    'by':str(user.get('username') or '')[:80],
                                    'source':(str(row.get('source') or ('manual' if equipment_status == 'reading' else 'manual-status'))[:80]
                                              if user.get('role')=='manager' else
                                              ('manual' if equipment_status=='reading' else 'manual-status')),"""
if t.count(old)!=1:raise SystemExit("Cannot find temperature source attribution")
t=t.replace(old,new,1)
temp.write_text(t,encoding="utf-8")

# A cancelled recipe editor must leave the original untouched. Ingredient edits
# mutate a draft, with Save the only commit. Free-text allergen notes remain drafts.
s=main.read_text(encoding="utf-8")
start=s.find("function editRecipe(r){")
end=s.find("\n/* ---------- REPORTS ---------- */",start)
if start<0 or end<start:raise SystemExit("Cannot locate unique legacy recipe editor")
editor=s[start:end]
old='  const isNew=!r; r=r||{id:uid("r"),name:"",cat:"Mains",allergens:"",method:"",cost:0,price:0,yield:"1",ingredients:[]};\n  r.ingredients=r.ingredients||[];'
new='  const isNew=!r, original=r;\n  r=r?JSON.parse(JSON.stringify(r)):{id:uid("r"),name:"",cat:"Mains",allergens:"",method:"",cost:0,price:0,yield:"1",ingredients:[]};\n  r.ingredients=r.ingredients||[];'
if editor.count(old)!=1:raise SystemExit("Legacy recipe draft marker changed")
editor=editor.replace(old,new,1)
if editor.count('Allergens (comma separated)')!=1 or editor.count('esc(r.allergens)')!=1:
    raise SystemExit("Legacy recipe allergen editor changed")
editor=editor.replace('Allergens (comma separated)','Allergen notes (draft — confirm in ingredient editor)',1)
editor=editor.replace('esc(r.allergens)','esc(Array.isArray(r.allergenDrafts)?r.allergenDrafts.join(", "):(r.allergenDrafts||""))',1)
old='STATE.recipes=STATE.recipes.filter(x=>x.id!==r.id);save("del recipe");'
new='STATE.recipes=STATE.recipes.filter(x=>x.id!==original.id);save("del recipe");'
if editor.count(old)!=1:raise SystemExit("Legacy recipe delete marker changed")
editor=editor.replace(old,new,1)
old='allergens:$("#ra").value'
new='allergenDrafts:$("#ra").value.split(/[,;]+/).map(x=>x.trim()).filter(Boolean)'
if editor.count(old)!=1:raise SystemExit("Legacy recipe allergen commit marker changed")
editor=editor.replace(old,new,1)
old='if(isNew)STATE.recipes.push(r);save("save recipe");m.close();'
new='if(r.allergenDrafts.length){r.needsReview=true;r.allergenReviewRequired=true;}if(isNew)STATE.recipes.push(r);else Object.assign(original,r);save("save recipe");m.close();'
if editor.count(old)!=1:raise SystemExit("Legacy recipe Save target changed")
editor=editor.replace(old,new,1)
s=s[:start]+editor+s[end:]
main.write_text(s,encoding="utf-8")

# Staff can inspect the matrix, but managers alone edit/verify allergens.
s=allergen.read_text(encoding="utf-8")
old="  function openIngredient(recipe,index){"
new="""  function openIngredient(recipe,index){
    var manager=false;
    try{manager=typeof ME!=='undefined'&&ME&&['manager','admin','administrator'].indexOf(String(ME.role||'').toLowerCase())>=0;}catch(e){}
    if(!manager){notify('Only a manager can edit and verify ingredient allergens.',true);return;}"""
if s.count(old)!=1:raise SystemExit("Ingredient editor handler changed")
s=s.replace(old,new,1)
allergen.write_text(s,encoding="utf-8")

idx=index.read_text(encoding="utf-8")
old="main_app.js?v=20261019-recipes-unified1"
if idx.count(old)!=1:raise SystemExit("Expected Recipes cache marker")
index.write_text(idx.replace(old,"main_app.js?v=20261020-kitchen-safety1",1),encoding="utf-8")
print("PASS: manager verification/temperature guards, draft-only recipe editing and cache refresh installed")
