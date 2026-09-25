import json
from datetime import datetime
from zoneinfo import ZoneInfo
import app


VALID_EQUIPMENT_STATUSES = {'reading', 'out_of_order', 'not_in_use', 'defrosting', 'awaiting_repair'}


def _init():
    with app.connect() as conn:
        with conn.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS tenant_temperature_readings (
                venue_id TEXT NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
                id TEXT NOT NULL,
                app_id TEXT NOT NULL,
                value DOUBLE PRECISION,
                ts TIMESTAMPTZ NOT NULL,
                period TEXT NOT NULL,
                recorded_by TEXT NOT NULL,
                source TEXT NOT NULL,
                payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                PRIMARY KEY (venue_id,id)
            )''')
            # Existing installations originally required a numeric value. Operational
            # status records (out of order, defrosting, etc.) intentionally have no
            # temperature, so allow NULL for value.
            cur.execute('ALTER TABLE tenant_temperature_readings ALTER COLUMN value DROP NOT NULL')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_tenant_temp_venue_ts ON tenant_temperature_readings(venue_id,ts)')
        conn.commit()


def _public_row(row):
    payload=row.get('payload') if isinstance(row.get('payload'),dict) else {}
    out=dict(payload)
    value=row.get('value')
    out.update({'id':row['id'],'appId':row['app_id'],'value':float(value) if value is not None else None,
                'ts':row['ts'].isoformat() if hasattr(row['ts'],'isoformat') else str(row['ts']),
                'period':row['period'],'by':row['recorded_by'],'source':row['source']})
    return out



_LONDON = ZoneInfo('Europe/London')


def _parse_dt(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value or '').replace('Z','+00:00'))
    except Exception:
        return None


def _slot_day(value):
    dt=_parse_dt(value)
    if not dt:
        return str(value or '')[:10]
    if dt.tzinfo is None:
        return dt.date().isoformat()
    return dt.astimezone(_LONDON).date().isoformat()


def _winner_key(item):
    entered=_parse_dt(item.get('enteredAt'))
    ts=_parse_dt(item.get('ts'))
    return (
        entered.timestamp() if entered else float('-inf'),
        ts.timestamp() if ts else float('-inf'),
        str(item.get('id') or ''),
    )


def _current_rows(rows):
    current={}
    for raw in rows:
        item=_public_row(raw) if 'app_id' in raw else dict(raw)
        key=(str(item.get('appId') or ''), _slot_day(item.get('ts')), str(item.get('period') or '').upper())
        prev=current.get(key)
        if prev is None or _winner_key(item) > _winner_key(prev):
            current[key]=item
    return sorted(current.values(), key=lambda x: (str(x.get('ts') or ''), str(x.get('id') or '')))


def list_readings(handler):
    stored,user=handler.require_user()
    if not stored:return
    venue_id=user['tenantId']
    with app.connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id,app_id,value,ts,period,recorded_by,source,payload FROM tenant_temperature_readings WHERE venue_id=%s ORDER BY ts ASC,id ASC',(venue_id,))
            rows=cur.fetchall()
    handler.send_json({'ok':True,'readings':_current_rows(rows)})


def append_readings(handler,payload):
    stored,user=handler.require_user()
    if not stored:return
    rows=payload.get('readings')
    if not isinstance(rows,list) or not rows:
        handler.send_json({'error':'No temperature readings supplied.'},400);return
    if len(rows)>64:
        handler.send_json({'error':'Too many temperature readings in one save.'},400);return
    valid_apps={str(a.get('id')) for a in stored['state'].get('appliances',[]) if isinstance(a,dict) and a.get('id')}
    cleaned=[]
    for row in rows:
        if not isinstance(row,dict):handler.send_json({'error':'Invalid temperature reading.'},400);return
        row_id=str(row.get('id') or '').strip(); app_id=str(row.get('appId') or '').strip(); ts=str(row.get('ts') or '').strip()
        try: parsed=datetime.fromisoformat(ts.replace('Z','+00:00'))
        except Exception: handler.send_json({'error':'Temperature timestamp is invalid.'},400);return
        period=str(row.get('period') or '').upper().strip()
        if period not in ('AM','PM'): period='AM' if parsed.hour<12 else 'PM'
        equipment_status=str(row.get('equipmentStatus') or 'reading').strip().lower()
        if equipment_status not in VALID_EQUIPMENT_STATUSES:
            handler.send_json({'error':'Equipment status is invalid.'},400);return
        value=None
        if equipment_status == 'reading':
            try:value=float(row.get('value'))
            except Exception:handler.send_json({'error':'Temperature must be numeric for a reading.'},400);return
            if value < -60 or value > 120:
                handler.send_json({'error':'Temperature reading is outside the supported range.'},400);return
        if not row_id or app_id not in valid_apps:
            handler.send_json({'error':'Temperature reading is incomplete or invalid.'},400);return
        notes=str(row.get('notes') or '').strip()
        if equipment_status in ('out_of_order','awaiting_repair') and not notes:
            handler.send_json({'error':'A fault/action note is required for this equipment status.'},400);return
        item=dict(row);item.update({'id':row_id,'appId':app_id,'value':value,'equipmentStatus':equipment_status,'period':period,
                                    'by':str(row.get('by') or user.get('username') or '')[:80],
                                    'source':str(row.get('source') or ('manual' if equipment_status == 'reading' else 'manual-status'))[:80],
                                    'notes':notes,'slotDate':_slot_day(parsed)})
        cleaned.append(item)
    slot_keys=[(item['appId'],item['slotDate'],item['period']) for item in cleaned]
    if len(slot_keys) != len(set(slot_keys)):
        handler.send_json({'error':'This temperature round contains the same appliance more than once.'},400);return

    inserted=[]; venue_id=user['tenantId']
    with app.connect() as conn:
        with conn.cursor() as cur:
            for item in cleaned:
                cur.execute("""SELECT id FROM tenant_temperature_readings
                               WHERE venue_id=%s AND app_id=%s AND upper(period)=%s
                                 AND (ts AT TIME ZONE 'Europe/London')::date=%s::date
                               LIMIT 1""",
                            (venue_id,item['appId'],item['period'],item['slotDate']))
                if cur.fetchone():
                    conn.rollback()
                    handler.send_json({'error':f"{item['slotDate']} {item['period']} is already recorded for this appliance. Use Update temperature round to change it."},409);return
                cur.execute('''INSERT INTO tenant_temperature_readings(venue_id,id,app_id,value,ts,period,recorded_by,source,payload)
                               VALUES(%s,%s,%s,%s,%s::timestamptz,%s,%s,%s,%s::jsonb)
                               ON CONFLICT (venue_id,id) DO NOTHING
                               RETURNING id,app_id,value,ts,period,recorded_by,source,payload''',
                            (venue_id,item['id'],item['appId'],item['value'],item['ts'],item['period'],item['by'],item['source'],json.dumps(item,ensure_ascii=False,separators=(',',':'))))
                saved=cur.fetchone()
                if saved: inserted.append(_public_row(saved))
            cur.execute('INSERT INTO server_audit(username,action,revision,details) VALUES(%s,%s,%s,%s::jsonb)',
                        (user['username'],'append_temperature_readings',stored['revision'],json.dumps({'venueId':venue_id,'requested':len(cleaned),'inserted':len(inserted)})))
        conn.commit()
    handler.send_json({'ok':True,'inserted':len(inserted),'readings':inserted})


def delete_reading(handler,payload):
    stored,user=handler.require_user()
    if not stored:return
    row_id=str(payload.get('id') or '').strip() if isinstance(payload,dict) else ''
    if not row_id:
        handler.send_json({'error':'Temperature record id is required.'},400);return
    venue_id=user['tenantId']
    with app.connect() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM tenant_temperature_readings WHERE venue_id=%s AND id=%s RETURNING id',(venue_id,row_id))
            deleted=cur.fetchone()
            cur.execute('INSERT INTO server_audit(username,action,revision,details) VALUES(%s,%s,%s,%s::jsonb)',
                        (user['username'],'delete_temperature_reading',stored['revision'],json.dumps({'venueId':venue_id,'id':row_id,'deleted':bool(deleted)})))
        conn.commit()
    handler.send_json({'ok':True,'deleted':bool(deleted),'id':row_id})


_init()