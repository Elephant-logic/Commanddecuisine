import json
import re
import contextvars
from datetime import datetime
from zoneinfo import ZoneInfo
import app
import drive_storage

_TENANT = contextvars.ContextVar('cdc_tenant_id', default=None)
_LEGACY_READ_STATE = app.read_state


_LONDON = ZoneInfo('Europe/London')


def _temp_dt(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value or '').replace('Z','+00:00'))
    except Exception:
        return None


def _temp_slot_day(value):
    dt=_temp_dt(value)
    if not dt:
        return str(value or '')[:10]
    if dt.tzinfo is None:
        return dt.date().isoformat()
    return dt.astimezone(_LONDON).date().isoformat()


def _temp_winner_key(item):
    entered=_temp_dt(item.get('enteredAt'))
    ts=_temp_dt(item.get('ts'))
    return (
        entered.timestamp() if entered else float('-inf'),
        ts.timestamp() if ts else float('-inf'),
        str(item.get('id') or ''),
    )


def _authoritative_temperature_rows(venue_id):
    if not venue_id:
        return None
    try:
        with app.connect() as conn:
            with conn.cursor() as cur:
                cur.execute('''SELECT id,app_id,value,ts,period,recorded_by,source,payload
                               FROM tenant_temperature_readings
                               WHERE venue_id=%s ORDER BY ts ASC,id ASC''',(venue_id,))
                rows=cur.fetchall()
        current={}
        for row in rows:
            payload=row.get('payload') if isinstance(row.get('payload'),dict) else {}
            item=dict(payload)
            value=row.get('value')
            item.update({
                'id':row['id'],
                'appId':row['app_id'],
                'value':float(value) if value is not None else None,
                'ts':row['ts'].isoformat() if hasattr(row['ts'],'isoformat') else str(row['ts']),
                'period':row['period'],
                'by':row['recorded_by'],
                'source':row['source'],
            })
            key=(str(item.get('appId') or ''),_temp_slot_day(item.get('ts')),str(item.get('period') or '').upper())
            prev=current.get(key)
            if prev is None or _temp_winner_key(item) > _temp_winner_key(prev):
                current[key]=item
        return sorted(current.values(),key=lambda x:(str(x.get('ts') or ''),str(x.get('id') or '')))
    except Exception:
        # During first boot the normalized table may not exist yet. In that
        # narrow case, keep the state copy rather than breaking sign-in.
        return None


def _public_state(stored):
    if not stored:
        return stored
    out = dict(stored)
    state = json.loads(json.dumps(stored['state']))
    authoritative_temps=_authoritative_temperature_rows(stored.get('tenantId'))
    if authoritative_temps is not None:
        state['tempReadings']=authoritative_temps
    for user in state.get('users', []):
        user.pop('password', None)
    out['state'] = state
    return out


def _safe_user(user):
    return {k: user.get(k) for k in ('id','username','name','role','jobTitle','email','phone','active','tenantId','venueName')}


def _password_ok(value):
    return isinstance(value, str) and len(value) >= 10


def _canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _append_only_additions(base_state, incoming_state, key):
    base = base_state.get(key, [])
    new = incoming_state.get(key, [])
    if not isinstance(base, list) or not isinstance(new, list):
        return None
    base_ids = {str(x.get('id')) for x in base if isinstance(x, dict) and x.get('id') is not None}
    base_exact = {_canon(x) for x in base}
    additions = []
    for item in new:
        if isinstance(item, dict) and item.get('id') is not None:
            if str(item.get('id')) not in base_ids:
                additions.append(item)
        elif _canon(item) not in base_exact:
            additions.append(item)
    return additions


def _merge_conflict_append_only(current_state, incoming_state):
    merged = json.loads(json.dumps(current_state))
    changed = False
    for key in ('tempReadings','audit'):
        additions = _append_only_additions(current_state, incoming_state, key)
        if additions is None:
            return None
        existing = merged.get(key, [])
        existing_ids = {str(x.get('id')) for x in existing if isinstance(x, dict) and x.get('id') is not None}
        existing_exact = {_canon(x) for x in existing}
        for item in additions:
            if isinstance(item, dict) and item.get('id') is not None:
                marker = str(item.get('id'))
                if marker in existing_ids:
                    continue
                existing.append(item); existing_ids.add(marker); changed = True
            elif _canon(item) not in existing_exact:
                existing.append(item); existing_exact.add(_canon(item)); changed = True
        merged[key] = existing
    return merged if changed else None


def _merge_rolling_audit(current_state, incoming_state):
    current = current_state.get('audit', []) if isinstance(current_state.get('audit', []), list) else []
    additions = _append_only_additions(current_state, incoming_state, 'audit') or []
    merged, seen_ids, seen_exact = [], set(), set()
    for item in list(additions) + list(current):
        if isinstance(item, dict) and item.get('id') is not None:
            marker = str(item.get('id'))
            if marker in seen_ids: continue
            seen_ids.add(marker)
        else:
            marker = _canon(item)
            if marker in seen_exact: continue
            seen_exact.add(marker)
        merged.append(item)
    return merged[:400]


def init_multitenant_db():
    with app.connect() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS venues (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    active BOOLEAN NOT NULL DEFAULT TRUE
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS venue_states (
                    venue_id TEXT PRIMARY KEY REFERENCES venues(id) ON DELETE CASCADE,
                    state JSONB NOT NULL,
                    revision BIGINT NOT NULL DEFAULT 1,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_by TEXT NOT NULL DEFAULT 'bootstrap'
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS user_accounts (
                    username TEXT PRIMARY KEY,
                    venue_id TEXT NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('staff','manager')),
                    job_title TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    phone TEXT NOT NULL DEFAULT '',
                    password TEXT NOT NULL,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            ''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_user_accounts_venue ON user_accounts(venue_id)')
        conn.commit()


def _account(username, conn=None):
    username = str(username or '').strip().lower()
    if not username:
        return None
    owns = conn is None
    if owns: conn = app.connect()
    try:
        with conn.cursor() as cur:
            cur.execute('''SELECT u.username,u.venue_id,u.user_id,u.name,u.role,u.job_title,u.email,u.phone,u.password,u.active,u.must_change_password,v.name AS venue_name
                           FROM user_accounts u JOIN venues v ON v.id=u.venue_id
                           WHERE u.username=%s AND v.active=TRUE''', (username,))
            row = cur.fetchone()
        if not row: return None
        return {
            'id': row['user_id'], 'username': row['username'], 'name': row['name'], 'role': row['role'],
            'jobTitle': row['job_title'], 'email': row['email'], 'phone': row['phone'], 'password': row['password'],
            'active': row['active'], 'mustChangePassword': row['must_change_password'],
            'tenantId': row['venue_id'], 'venueName': row['venue_name'],
        }
    finally:
        if owns: conn.close()


def _read_venue_state(venue_id, conn=None, for_update=False):
    owns = conn is None
    if owns: conn = app.connect()
    try:
        with conn.cursor() as cur:
            sql = 'SELECT state,revision,updated_at,updated_by FROM venue_states WHERE venue_id=%s'
            if for_update: sql += ' FOR UPDATE'
            cur.execute(sql, (venue_id,))
            row = cur.fetchone()
        if not row: return None
        return {'state': row['state'], 'revision': int(row['revision']),
                'updated_at': row['updated_at'].isoformat() if hasattr(row['updated_at'],'isoformat') else str(row['updated_at']),
                'updated_by': row['updated_by'], 'tenantId': venue_id}
    finally:
        if owns: conn.close()


def tenant_read_state(conn=None, for_update=False):
    venue_id = _TENANT.get()
    if venue_id:
        return _read_venue_state(venue_id, conn=conn, for_update=for_update)
    return _LEGACY_READ_STATE(conn=conn, for_update=for_update)


def _require_user(handler):
    username = app.parse_session(handler.headers.get('Cookie'))
    account = _account(username)
    if not account or not account.get('active', True):
        handler.send_json({'error':'Sign in required.'},401)
        return None, None
    _TENANT.set(account['tenantId'])
    stored = _read_venue_state(account['tenantId'])
    if not stored:
        handler.send_json({'error':'Venue storage is not initialised.'},409)
        return None, None
    state_user = next((u for u in stored['state'].get('users',[]) if str(u.get('username','')).lower()==account['username']), None)
    if state_user:
        merged = dict(state_user); merged.update(account); account = merged
    return stored, account


init_multitenant_db()
app.read_state = tenant_read_state
app.Handler.require_user = _require_user


def send_session(handler):
    username = app.parse_session(handler.headers.get('Cookie'))
    account = _account(username)
    if not account or not account.get('active', True):
        with app.connect() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT COUNT(*) AS n FROM venues WHERE active=TRUE')
                row = cur.fetchone()
        needs_setup = int(row['n'] if row else 0) == 0
        handler.send_json({'authenticated':False,'initialised':True,'needsSetup':needs_setup,'canCreateVenue':True})
        return
    _TENANT.set(account['tenantId'])
    stored = _read_venue_state(account['tenantId'])
    handler.send_json({'authenticated':True,'needsSetup':False,'canCreateVenue':True,'user':_safe_user(account),**_public_state(stored)})


def send_export(handler):
    stored, _ = handler.require_user()
    if stored: handler.send_json(_public_state(stored))


def login(handler, payload):
    username = str(payload.get('username','')).strip().lower()
    password = str(payload.get('password',''))
    account = _account(username)
    if not account or not account.get('active', True) or not app.verify_password(password, account.get('password','')):
        handler.send_json({'error':'Wrong username or password.'},401); return
    _TENANT.set(account['tenantId'])
    stored = _read_venue_state(account['tenantId'])
    cookie = f"{app.SESSION_COOKIE}={app.make_session(account['username'])}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=43200"
    handler.send_json({'ok':True,'user':_safe_user(account),**_public_state(stored)}, extra_headers={'Set-Cookie':cookie})


def bootstrap_admin(handler, payload):
    business = str(payload.get('businessName','')).strip()
    name = str(payload.get('name','')).strip()
    username = str(payload.get('username','')).strip().lower()
    password = str(payload.get('password',''))
    if not business or not name or not username:
        handler.send_json({'error':'Business name, Admin name and username are required.'},400); return
    if not re.fullmatch(r'[a-z0-9._-]{3,40}', username):
        handler.send_json({'error':'Username must be 3–40 characters using letters, numbers, dot, dash or underscore.'},400); return
    if not _password_ok(password):
        handler.send_json({'error':'Use at least 10 characters for the Admin password.'},400); return
    venue_id = 'v_' + app.secrets.token_hex(8)
    user_id = 'u_' + app.secrets.token_hex(8)
    state = app.default_state()
    admin = {'id':user_id,'username':username,'name':name,'role':'manager','jobTitle':'Administrator','active':True,'createdAt':app.utcnow()}
    state['users'] = [admin]
    settings = state.setdefault('settings',{})
    settings.update({'businessName':business,'setupDone':True,'firstAdminCreatedAt':app.utcnow(),'venueId':venue_id})
    with app.connect() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT 1 FROM user_accounts WHERE username=%s', (username,))
                if cur.fetchone():
                    conn.rollback(); handler.send_json({'error':'That username already exists. Choose another username.'},409); return
                cur.execute('INSERT INTO venues(id,name) VALUES(%s,%s)', (venue_id,business))
                cur.execute('INSERT INTO venue_states(venue_id,state,revision,updated_at,updated_by) VALUES(%s,%s::jsonb,1,NOW(),%s)',
                            (venue_id,json.dumps(state,ensure_ascii=False,separators=(',',':')),username))
                cur.execute('''INSERT INTO user_accounts(username,venue_id,user_id,name,role,job_title,password,active)
                               VALUES(%s,%s,%s,%s,'manager','Administrator',%s,TRUE)''',
                            (username,venue_id,user_id,name,app.hash_password(password)))
                cur.execute('INSERT INTO server_audit(username,action,revision,details) VALUES(%s,%s,%s,%s::jsonb)',
                            (username,'create_venue',1,json.dumps({'venueId':venue_id,'businessName':business})))
            conn.commit()
        except Exception:
            conn.rollback(); raise
    _TENANT.set(venue_id)
    account = _account(username)
    try: drive_storage.maybe_daily_backup(state,1)
    except Exception: pass
    cookie = f"{app.SESSION_COOKIE}={app.make_session(username)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=43200"
    handler.send_json({'ok':True,'user':_safe_user(account),**_public_state(_read_venue_state(venue_id))}, extra_headers={'Set-Cookie':cookie})


def create_user(handler, payload):
    stored, manager = handler.require_user()
    if not stored: return
    if manager.get('role') != 'manager': handler.send_json({'error':'Admin access required.'},403); return
    name = str(payload.get('name','')).strip(); username = str(payload.get('username','')).strip().lower()
    password = str(payload.get('password','')); job_title = str(payload.get('jobTitle','')).strip(); role = str(payload.get('role','staff')).lower()
    if not name or not username: handler.send_json({'error':'Name and username are required.'},400); return
    if role not in ('staff','manager'): handler.send_json({'error':'Invalid role.'},400); return
    if not re.fullmatch(r'[a-z0-9._-]{3,40}', username): handler.send_json({'error':'Username must be 3–40 characters using letters, numbers, dot, dash or underscore.'},400); return
    if not _password_ok(password): handler.send_json({'error':'Temporary password must be at least 10 characters.'},400); return
    venue_id = manager['tenantId']; user_id = 'u_' + app.secrets.token_hex(8)
    with app.connect() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute('SELECT 1 FROM user_accounts WHERE username=%s',(username,))
                if cur.fetchone(): conn.rollback(); handler.send_json({'error':'That username already exists.'},409); return
                current = _read_venue_state(venue_id, conn=conn, for_update=True); state=current['state']
                public_user={'id':user_id,'username':username,'name':name,'role':role,'jobTitle':job_title,'active':True,'mustChangePassword':True,'createdAt':app.utcnow()}
                state.setdefault('users',[]).append(public_user)
                revision=current['revision']+1
                cur.execute('''INSERT INTO user_accounts(username,venue_id,user_id,name,role,job_title,password,active,must_change_password)
                               VALUES(%s,%s,%s,%s,%s,%s,%s,TRUE,TRUE)''',
                            (username,venue_id,user_id,name,role,job_title,app.hash_password(password)))
                cur.execute('UPDATE venue_states SET state=%s::jsonb,revision=%s,updated_at=NOW(),updated_by=%s WHERE venue_id=%s',
                            (json.dumps(state,ensure_ascii=False,separators=(',',':')),revision,manager['username'],venue_id))
                cur.execute('INSERT INTO server_audit(username,action,revision,details) VALUES(%s,%s,%s,%s::jsonb)',
                            (manager['username'],'create_user',revision,json.dumps({'venueId':venue_id,'account':username,'role':role})))
            conn.commit()
        except Exception:
            conn.rollback(); raise
    handler.send_json({'ok':True,**_public_state(_read_venue_state(venue_id))})


def change_password(handler, payload):
    stored, user = handler.require_user()
    if not stored: return
    current_password=str(payload.get('currentPassword','')); new_password=str(payload.get('newPassword',''))
    if not app.verify_password(current_password,user.get('password','')): handler.send_json({'error':'Your current password is not correct.'},400); return
    if not _password_ok(new_password): handler.send_json({'error':'Use at least 10 characters for the new password.'},400); return
    if current_password == new_password: handler.send_json({'error':'Choose a different password.'},400); return
    with app.connect() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE user_accounts SET password=%s,must_change_password=FALSE WHERE username=%s AND venue_id=%s',
                        (app.hash_password(new_password),user['username'],user['tenantId']))
        conn.commit()
    handler.send_json({'ok':True,'revision':stored['revision'],'message':'Password changed.'})


def manage_user(handler, payload):
    stored, manager = handler.require_user()
    if not stored: return
    if manager.get('role') != 'manager': handler.send_json({'error':'Manager access required.'},403); return
    username=str(payload.get('username','')).strip().lower(); venue_id=manager['tenantId']
    with app.connect() as conn:
        try:
            current=_read_venue_state(venue_id,conn=conn,for_update=True); state=current['state']
            target=next((u for u in state.get('users',[]) if str(u.get('username','')).lower()==username),None)
            if not target: conn.rollback(); handler.send_json({'error':'Account not found.'},404); return
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
            if not any(u.get('role')=='manager' and u.get('active',True) for u in state.get('users',[])):
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
            conn.commit()
        except Exception:
            conn.rollback(); raise
    handler.send_json({'ok':True,**_public_state(_read_venue_state(venue_id))})




_BACKDATED_TEMP_SOURCES = {
    'manager-backfill', 'manager-backfill-status',
    'paper-log', 'paper-log-status',
    'temp-record-added', 'temperature-record',
}

def _is_backdated_temp_candidate(row):
    if not isinstance(row, dict):
        return False
    if row.get('backfilled') is True:
        return True
    source=str(row.get('source') or '').strip().lower().replace('_','-')
    return source in _BACKDATED_TEMP_SOURCES or 'backfill' in source or source.startswith('paper-log')

def _sync_backdated_temperature_candidates(conn, venue_id, incoming_state, user):
    rows=incoming_state.get('tempReadings', []) if isinstance(incoming_state,dict) else []
    if not isinstance(rows,list):
        return 0
    appliances=incoming_state.get('appliances', []) if isinstance(incoming_state.get('appliances', []),list) else []
    valid_apps={str(a.get('id')) for a in appliances if isinstance(a,dict) and a.get('id')}
    inserted=0
    with conn.cursor() as cur:
        for row in rows:
            if not _is_backdated_temp_candidate(row):
                continue
            row_id=str(row.get('id') or '').strip()
            app_id=str(row.get('appId') or '').strip()
            ts=str(row.get('ts') or '').strip()
            if not row_id or app_id not in valid_apps or not ts:
                raise ValueError('Back-dated temperature record is incomplete.')
            try:
                parsed=datetime.fromisoformat(ts.replace('Z','+00:00'))
            except Exception as exc:
                raise ValueError('Back-dated temperature timestamp is invalid.') from exc
            period=str(row.get('period') or '').strip().upper()
            if period not in ('AM','PM'):
                period='AM' if parsed.hour < 12 else 'PM'
            equipment_status=str(row.get('equipmentStatus') or 'reading').strip().lower()
            if equipment_status not in ('reading','out_of_order','not_in_use','defrosting','awaiting_repair'):
                raise ValueError('Back-dated equipment status is invalid.')
            value=None
            if equipment_status == 'reading':
                try:
                    value=float(row.get('value'))
                except Exception as exc:
                    raise ValueError('Back-dated temperature must be numeric.') from exc
                if value < -60 or value > 120:
                    raise ValueError('Back-dated temperature is outside the supported range.')
            notes=str(row.get('notes') or '').strip()
            if equipment_status in ('out_of_order','awaiting_repair') and not notes:
                raise ValueError('A fault/action note is required for an out-of-order or awaiting-repair back-dated record.')
            recorded_by=str(row.get('by') or user.get('username') or '')[:80]
            source=str(row.get('source') or ('manager-backfill' if equipment_status=='reading' else 'manager-backfill-status'))[:80]
            payload=dict(row)
            payload.update({
                'id':row_id,'appId':app_id,'value':value,'equipmentStatus':equipment_status,
                'period':period,'by':recorded_by,'source':source,'notes':notes
            })
            cur.execute(
                '''INSERT INTO tenant_temperature_readings
                   (venue_id,id,app_id,value,ts,period,recorded_by,source,payload)
                   VALUES(%s,%s,%s,%s,%s::timestamptz,%s,%s,%s,%s::jsonb)
                   ON CONFLICT (venue_id,id) DO NOTHING
                   RETURNING id''',
                (venue_id,row_id,app_id,value,ts,period,recorded_by,source,
                 json.dumps(payload,ensure_ascii=False,separators=(',',':')))
            )
            if cur.fetchone():
                inserted += 1
    return inserted

def save_state(handler, payload):
    stored,user=handler.require_user()
    if not stored: return
    incoming=payload.get('state')
    if not isinstance(incoming,dict): handler.send_json({'error':'A valid state is required.'},400); return
    incoming=json.loads(json.dumps(incoming)); expected=int(payload.get('revision') or 0); venue_id=user['tenantId']
    with app.connect() as conn:
        try:
            current=_read_venue_state(venue_id,conn=conn,for_update=True)
            if not current: conn.rollback(); handler.send_json({'error':'Venue is not initialised.'},409); return
            conflict_merge=False
            if expected != current['revision']:
                merged=_merge_conflict_append_only(current['state'],incoming)
                if merged is None:
                    conn.rollback(); handler.send_json({'error':'Another user saved changes first. Latest shared data has been returned.','conflict':True,**_public_state(current)},409); return
                incoming=merged; conflict_merge=True
            backdated_inserted=_sync_backdated_temperature_candidates(conn,venue_id,incoming,user)
            incoming['tempReadings']=current['state'].get('tempReadings',[])
            incoming['audit']=_merge_rolling_audit(current['state'],incoming)
            incoming['users']=current['state'].get('users',[])
            if user.get('role') != 'manager':
                incoming['settings']=current['state'].get('settings',{})
            else:
                incoming.setdefault('settings',{})['venueId']=venue_id
            raw=json.dumps(incoming,ensure_ascii=False,separators=(',',':'))
            if len(raw.encode()) > app.MAX_STATE_BYTES: conn.rollback(); handler.send_json({'error':'State is too large.'},413); return
            revision=current['revision']+1
            with conn.cursor() as cur:
                cur.execute('UPDATE venue_states SET state=%s::jsonb,revision=%s,updated_at=NOW(),updated_by=%s WHERE venue_id=%s',
                            (raw,revision,user['username'],venue_id))
                cur.execute('INSERT INTO server_audit(username,action,revision,details) VALUES(%s,%s,%s,%s::jsonb)',
                            (user['username'],'save_state',revision,json.dumps({'venueId':venue_id,'reason':str(payload.get('reason','client save')),'conflict_append_merge':conflict_merge,'backdated_temperature_inserted':backdated_inserted})))
            conn.commit()
        except Exception:
            conn.rollback(); raise
    try: drive_storage.maybe_daily_backup(incoming,revision)
    except Exception as exc: print('Supabase Storage daily backup skipped:',exc)
    handler.send_json({'ok':True,'revision':revision,'conflictAppendMerge':conflict_merge,'backdatedTemperatureInserted':backdated_inserted})
