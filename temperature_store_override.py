import json
from datetime import datetime
import app


def _init():
    with app.connect() as conn:
        with conn.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS tenant_temperature_readings (
                venue_id TEXT NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
                id TEXT NOT NULL,
                app_id TEXT NOT NULL,
                value DOUBLE PRECISION NOT NULL,
                ts TIMESTAMPTZ NOT NULL,
                period TEXT NOT NULL,
                recorded_by TEXT NOT NULL,
                source TEXT NOT NULL,
                payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                PRIMARY KEY (venue_id,id)
            )''')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_tenant_temp_venue_ts ON tenant_temperature_readings(venue_id,ts)')
        conn.commit()


def _public_row(row):
    payload=row.get('payload') if isinstance(row.get('payload'),dict) else {}
    out=dict(payload)
    out.update({'id':row['id'],'appId':row['app_id'],'value':float(row['value']),
                'ts':row['ts'].isoformat() if hasattr(row['ts'],'isoformat') else str(row['ts']),
                'period':row['period'],'by':row['recorded_by'],'source':row['source']})
    return out


def list_readings(handler):
    stored,user=handler.require_user()
    if not stored:return
    venue_id=user['tenantId']
    with app.connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id,app_id,value,ts,period,recorded_by,source,payload FROM tenant_temperature_readings WHERE venue_id=%s ORDER BY ts ASC,id ASC',(venue_id,))
            rows=cur.fetchall()
    handler.send_json({'ok':True,'readings':[_public_row(r) for r in rows]})


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
        try:value=float(row.get('value'))
        except Exception:handler.send_json({'error':'Temperature must be numeric.'},400);return
        if not row_id or app_id not in valid_apps or value < -60 or value > 120:
            handler.send_json({'error':'Temperature reading is incomplete or invalid.'},400);return
        item=dict(row);item.update({'id':row_id,'appId':app_id,'value':value,'period':period,
                                    'by':str(row.get('by') or user.get('username') or '')[:80],
                                    'source':str(row.get('source') or 'manual')[:80]})
        cleaned.append(item)
    inserted=[]; venue_id=user['tenantId']
    with app.connect() as conn:
        with conn.cursor() as cur:
            for item in cleaned:
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

_init()
