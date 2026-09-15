from pathlib import Path
import shutil

app_dir = Path('app')

# Install the manager-only browser controls.
shutil.copyfile('manager_remove_controls.js', app_dir / 'manager_remove_controls.js')

index = app_dir / 'index.html'
html = index.read_text(encoding='utf-8')
tag = '<script src="manager_remove_controls.js"></script>'
if tag not in html:
    marker = '</body>'
    if marker not in html:
        raise SystemExit('Could not locate </body> in index.html')
    html = html.replace(marker, tag + '\n' + marker, 1)
index.write_text(html, encoding='utf-8')

# Serve the new static JS asset.
server = app_dir / 'server.py'
server_text = server.read_text(encoding='utf-8')
runtime_marker = 'RUNTIME_FILES = (\n'
asset_line = "    '/manager_remove_controls.js',\n"
if asset_line not in server_text:
    if runtime_marker not in server_text:
        raise SystemExit('RUNTIME_FILES marker not found in server.py')
    server_text = server_text.replace(runtime_marker, runtime_marker + asset_line, 1)
server.write_text(server_text, encoding='utf-8')

# Extend the existing manager account endpoint so a manager can truly remove
# a staff account while keeping historic operational records and audit trails.
auth = app_dir / 'auth_controls.py'
auth_text = auth.read_text(encoding='utf-8')
start_marker = '\ndef manage_user(handler, payload):\n'
end_marker = '\ndef save_state(handler, payload):\n'
start = auth_text.find(start_marker)
end = auth_text.find(end_marker, start + 1)
if start < 0 or end < 0:
    raise SystemExit('Could not locate manage_user/save_state block in auth_controls.py')

replacement = r'''
def manage_user(handler, payload):
    stored, manager = handler.require_user()
    if not stored: return
    if manager.get('role') != 'manager': handler.send_json({'error':'Manager access required.'},403); return
    username=str(payload.get('username','')).strip().lower(); venue_id=manager['tenantId']
    delete_requested=bool(payload.get('delete') or payload.get('remove'))
    with app.connect() as conn:
        try:
            current=_read_venue_state(venue_id,conn=conn,for_update=True); state=current['state']
            users=state.get('users',[]) if isinstance(state.get('users',[]),list) else []
            target=next((u for u in users if str(u.get('username','')).lower()==username),None)
            if not target: conn.rollback(); handler.send_json({'error':'Account not found.'},404); return

            if delete_requested:
                if username == str(manager.get('username','')).lower():
                    conn.rollback(); handler.send_json({'error':'You cannot remove the account you are currently signed in with.'},400); return
                remaining=[u for u in users if str(u.get('username','')).lower()!=username]
                if not any(u.get('role')=='manager' and u.get('active',True) for u in remaining):
                    conn.rollback(); handler.send_json({'error':'There must always be at least one active manager.'},400); return
                state['users']=remaining
                revision=current['revision']+1
                with conn.cursor() as cur:
                    cur.execute('DELETE FROM user_accounts WHERE username=%s AND venue_id=%s',(username,venue_id))
                    cur.execute('UPDATE venue_states SET state=%s::jsonb,revision=%s,updated_at=NOW(),updated_by=%s WHERE venue_id=%s',
                                (json.dumps(state,ensure_ascii=False,separators=(',',':')),revision,manager['username'],venue_id))
                    cur.execute('INSERT INTO server_audit(username,action,revision,details) VALUES(%s,%s,%s,%s::jsonb)',
                                (manager['username'],'delete_user',revision,json.dumps({'venueId':venue_id,'account':username,'name':target.get('name'),'historicalRecordsPreserved':True})))
                conn.commit()
                handler.send_json({'ok':True,'removed':username,**_public_state(_read_venue_state(venue_id))})
                return

            if 'name' in payload: target['name']=str(payload.get('name') or target.get('name') or username).strip()
            if 'jobTitle' in payload: target['jobTitle']=str(payload.get('jobTitle') or '').strip()
            if 'role' in payload:
                role=str(payload.get('role') or 'staff')
                if role not in ('staff','manager'): conn.rollback(); handler.send_json({'error':'Invalid role.'},400); return
                target['role']=role
            if 'active' in payload: target['active']=bool(payload.get('active'))
            new_password=payload.get('newPassword')
            if new_password is not None and not _password_ok(str(new_password)):
                conn.rollback(); handler.send_json({'error':'Temporary password must be at least 10 characters.'},400); return
            if not any(u.get('role')=='manager' and u.get('active',True) for u in users):
                conn.rollback(); handler.send_json({'error':'There must always be at least one active manager.'},400); return
            revision=current['revision']+1
            fields=[target.get('name',''),target.get('role','staff'),target.get('jobTitle',''),bool(target.get('active',True)),username,venue_id]
            with conn.cursor() as cur:
                cur.execute('UPDATE user_accounts SET name=%s,role=%s,job_title=%s,active=%s WHERE username=%s AND venue_id=%s', fields)
                if new_password is not None:
                    cur.execute('UPDATE user_accounts SET password=%s,must_change_password=TRUE WHERE username=%s AND venue_id=%s',
                                (app.hash_password(str(new_password)),username,venue_id))
                    target['mustChangePassword']=True
                cur.execute('UPDATE venue_states SET state=%s::jsonb,revision=%s,updated_at=NOW(),updated_by=%s WHERE venue_id=%s',
                            (json.dumps(state,ensure_ascii=False,separators=(',',':')),revision,manager['username'],venue_id))
                cur.execute('INSERT INTO server_audit(username,action,revision,details) VALUES(%s,%s,%s,%s::jsonb)',
                            (manager['username'],'manage_user',revision,json.dumps({'venueId':venue_id,'account':username})))
            conn.commit()
        except Exception:
            conn.rollback(); raise
    handler.send_json({'ok':True,**_public_state(_read_venue_state(venue_id))})
'''

auth_text = auth_text[:start] + replacement + auth_text[end:]
auth.write_text(auth_text, encoding='utf-8')

# Self-check the build patch before Render continues.
final_html = index.read_text(encoding='utf-8')
final_server = server.read_text(encoding='utf-8')
final_auth = auth.read_text(encoding='utf-8')
if final_html.count(tag) != 1:
    raise SystemExit('Manager removal script tag was not installed exactly once')
if "'/manager_remove_controls.js'" not in final_server:
    raise SystemExit('Manager removal static route was not installed')
if "'delete_user'" not in final_auth or 'delete_requested' not in final_auth:
    raise SystemExit('Staff deletion backend patch was not installed')

print('Manager removal controls installed')
