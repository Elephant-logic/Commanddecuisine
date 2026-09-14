import base64
import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
import app

_LOCK=threading.Lock()
_LAST_BACKUP_DATE={}

def _url(): return os.environ.get('SUPABASE_URL','').strip().rstrip('/')
def _key(): return os.environ.get('SUPABASE_SERVICE_ROLE_KEY','').strip()
def _bucket(): return os.environ.get('SUPABASE_STORAGE_BUCKET','command-de-cuisine').strip() or 'command-de-cuisine'
def configured(): return bool(_url() and _key() and _bucket())

def _safe_component(value):
    value=str(value or '').strip()
    return ''.join(c if c.isalnum() or c in '-_.' else '_' for c in value)[:160] or 'item'

def _venue_prefix(user=None,state=None):
    venue_id = (user or {}).get('tenantId') if isinstance(user,dict) else None
    if not venue_id and isinstance(state,dict):
        venue_id=(state.get('settings') or {}).get('venueId')
    if not venue_id: raise RuntimeError('Venue context is missing')
    return 'venues/' + _safe_component(venue_id)

def _upload(path,data,mime_type='application/octet-stream'):
    if not configured(): raise RuntimeError('Supabase Storage is not configured')
    safe_path='/'.join(urllib.parse.quote(part,safe='') for part in path.split('/'))
    endpoint=f"{_url()}/storage/v1/object/{urllib.parse.quote(_bucket(),safe='')}/{safe_path}"
    req=urllib.request.Request(endpoint,data=data,method='POST',headers={
        'Authorization':'Bearer '+_key(),'apikey':_key(),'Content-Type':mime_type or 'application/octet-stream','x-upsert':'true'})
    try:
        with urllib.request.urlopen(req,timeout=60) as resp:
            raw=resp.read().decode('utf-8','replace'); payload=json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail=exc.read().decode('utf-8','replace')[:500]
        raise RuntimeError(f'Supabase Storage upload failed ({exc.code}): {detail}') from exc
    return {'bucket':_bucket(),'path':path,**(payload if isinstance(payload,dict) else {})}

def status(handler):
    stored,user=handler.require_user()
    if not stored:return
    handler.send_json({'ok':True,'configured':configured(),'urlConfigured':bool(_url()),'secretConfigured':bool(_key()),
                       'bucket':_bucket(),'role':user.get('role'),'tenantId':user.get('tenantId')})

def upload_from_json(handler,payload):
    stored,user=handler.require_user()
    if not stored:return
    try:
        name=_safe_component(str(payload.get('name') or 'document').strip()[:180])
        mime_type=str(payload.get('mimeType') or 'application/octet-stream').strip()[:120]
        data_b64=str(payload.get('dataBase64') or '')
        if ',' in data_b64 and data_b64.lstrip().startswith('data:'):data_b64=data_b64.split(',',1)[1]
        data=base64.b64decode(data_b64,validate=True)
        if not data:raise ValueError('File is empty')
        if len(data)>12*1024*1024:raise ValueError('Uploads are limited to 12 MB per file on this build')
        stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        result=_upload(f"{_venue_prefix(user=user)}/Documents/{stamp}-{name}",data,mime_type)
        handler.send_json({'ok':True,'file':result})
    except Exception as exc:handler.send_json({'error':str(exc)},400)

def _backup_payload(state,revision):
    return json.dumps({'product':'Command de Cuisine','revision':revision,'exportedAt':datetime.now(timezone.utc).isoformat(),'state':state},ensure_ascii=False,indent=2).encode()

def maybe_daily_backup(state,revision):
    if not configured():return None
    prefix=_venue_prefix(state=state); today=datetime.now(timezone.utc).date().isoformat()
    with _LOCK:
        if _LAST_BACKUP_DATE.get(prefix)==today:return None
        result=_upload(f'{prefix}/Backups/command-de-cuisine-{today}.json',_backup_payload(state,revision),'application/json')
        _LAST_BACKUP_DATE[prefix]=today
        return result

def backup_now(handler):
    stored,user=handler.require_user()
    if not stored:return
    if user.get('role')!='manager':handler.send_json({'error':'Admin access required.'},403);return
    try:
        stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        result=_upload(f"{_venue_prefix(user=user)}/Backups/command-de-cuisine-{stamp}.json",_backup_payload(stored['state'],stored['revision']),'application/json')
        handler.send_json({'ok':True,'file':result})
    except Exception as exc:handler.send_json({'error':str(exc)},400)
