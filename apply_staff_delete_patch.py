from pathlib import Path

app = Path('app')

auth = app / 'auth_controls.py'
text = auth.read_text(encoding='utf-8')
marker = "            target=next((u for u in state.get('users',[]) if str(u.get('username','')).lower()==username),None)\n            if not target: conn.rollback(); handler.send_json({'error':'Account not found.'},404); return\n"
insert = marker + "            if bool(payload.get('delete')):\n                if username == str(manager.get('username','')).lower():\n                    conn.rollback(); handler.send_json({'error':'You cannot delete the account you are currently signed in with.'},400); return\n                remaining=[u for u in state.get('users',[]) if str(u.get('username','')).lower()!=username]\n                if not any(u.get('role')=='manager' and u.get('active',True) for u in remaining):\n                    conn.rollback(); handler.send_json({'error':'There must always be at least one active manager.'},400); return\n                state['users']=remaining\n                revision=current['revision']+1\n                with conn.cursor() as cur:\n                    cur.execute('DELETE FROM user_accounts WHERE username=%s AND venue_id=%s',(username,venue_id))\n                    cur.execute('UPDATE venue_states SET state=%s::jsonb,revision=%s,updated_at=NOW(),updated_by=%s WHERE venue_id=%s',\n                                (json.dumps(state,ensure_ascii=False,separators=(',',':')),revision,manager['username'],venue_id))\n                    cur.execute('INSERT INTO server_audit(username,action,revision,details) VALUES(%s,%s,%s,%s::jsonb)',\n                                (manager['username'],'delete_user',revision,json.dumps({'venueId':venue_id,'account':username})))\n                conn.commit()\n                handler.send_json({'ok':True,**_public_state(_read_venue_state(venue_id))})\n                return\n"
if marker not in text:
    raise SystemExit('manage_user target marker not found')
text = text.replace(marker, insert, 1)
auth.write_text(text, encoding='utf-8')

controls = app / 'account_controls.js'
js = controls.read_text(encoding='utf-8')
old = "        const reset=el('button',{class:'btn sm ghost',html:'Reset password'});\n        reset.addEventListener('click',()=>resetPassword(u));\n        row.append(info,role,active,reset);card.append(row);"
new = "        const reset=el('button',{class:'btn sm ghost',html:'Reset password'});\n        reset.addEventListener('click',()=>resetPassword(u));\n        const remove=u.username!==ME.username?el('button',{class:'btn sm danger',html:'Remove'}):null;\n        if(remove)remove.addEventListener('click',async()=>{\n          if(!confirm('Remove '+(u.name||u.username)+' from this venue? They will no longer be able to sign in.'))return;\n          remove.disabled=true;\n          try{\n            await api('/api/users/manage',{method:'POST',body:JSON.stringify({username:u.username,delete:true})});\n            await refreshSharedState();toast('Staff account removed','ok');rerender();\n          }catch(err){remove.disabled=false;toast(err.message||'Could not remove account','bad');}\n        });\n        row.append(info,role,active,reset);if(remove)row.append(remove);card.append(row);"
if old not in js:
    raise SystemExit('account controls row marker not found')
js = js.replace(old, new, 1)
controls.write_text(js, encoding='utf-8')

server = app / 'server.py'
s = server.read_text(encoding='utf-8')
s = s.replace('/account_controls.js?v=20260812c', '/account_controls.js?v=20260915-delete')
server.write_text(s, encoding='utf-8')

print('Staff deletion enabled')
