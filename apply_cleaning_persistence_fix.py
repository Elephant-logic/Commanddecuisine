from pathlib import Path
import re

path = Path('app/auth_controls.py')
text = path.read_text(encoding='utf-8')

pattern = re.compile(r"def _merge_conflict_append_only\(current_state, incoming_state\):\n.*?\n\ndef _merge_rolling_audit", re.S)
replacement = r'''def _clean_task_marker(item):
    if not isinstance(item, dict):
        return ''
    if item.get('id') is not None:
        return 'id:' + str(item.get('id'))
    return 'task:' + str(item.get('area') or '').strip().lower() + '|' + str(item.get('task') or '').strip().lower()


def _time_key(value):
    value = str(value or '').strip()
    if not value:
        return ''
    if len(value) == 10:
        return value + 'T00:00:00Z'
    return value.replace('+00:00', 'Z')


def _merge_cleaning_task_updates(current_state, incoming_state, merged):
    current = current_state.get('cleaningTasks', [])
    incoming = incoming_state.get('cleaningTasks', [])
    if not isinstance(current, list) or not isinstance(incoming, list):
        return False
    out = json.loads(json.dumps(current))
    positions = {_clean_task_marker(item): idx for idx, item in enumerate(out) if _clean_task_marker(item)}
    changed = False
    for item in incoming:
        marker = _clean_task_marker(item)
        if not marker or marker not in positions or not isinstance(item, dict):
            continue
        target = out[positions[marker]]
        new_done = _time_key(item.get('lastDone'))
        old_done = _time_key(target.get('lastDone'))
        if new_done and (not old_done or new_done > old_done):
            target['lastDone'] = item.get('lastDone')
            if 'by' in item:
                target['by'] = item.get('by')
            for key in ('lastDoneBy','completedBy','completedAt'):
                if key in item:
                    target[key] = item.get(key)
            changed = True
    if changed:
        merged['cleaningTasks'] = out
    return changed


def _merge_conflict_append_only(current_state, incoming_state):
    merged = json.loads(json.dumps(current_state))
    changed = False
    for key in ('tempReadings','audit','scheduleCompletions'):
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
    if _merge_cleaning_task_updates(current_state, incoming_state, merged):
        changed = True
    return merged if changed else None


def _ensure_cleaning_history(before_state, incoming_state, user):
    before = before_state.get('cleaningTasks', [])
    after = incoming_state.get('cleaningTasks', [])
    if not isinstance(before, list) or not isinstance(after, list):
        return
    before_map = {_clean_task_marker(item): item for item in before if _clean_task_marker(item)}
    schedules = incoming_state.get('cleaningSchedules', []) if isinstance(incoming_state.get('cleaningSchedules', []), list) else []
    completions = incoming_state.get('scheduleCompletions', []) if isinstance(incoming_state.get('scheduleCompletions', []), list) else []
    existing = set()
    for row in completions:
        if not isinstance(row, dict):
            continue
        existing.add((str(row.get('scheduleId') or ''), str(row.get('completedAt') or ''), str(row.get('area') or '').strip().lower(), str(row.get('task') or '').strip().lower()))
    added = False
    for item in after:
        if not isinstance(item, dict):
            continue
        marker = _clean_task_marker(item)
        old = before_map.get(marker, {})
        new_done = _time_key(item.get('lastDone'))
        old_done = _time_key(old.get('lastDone'))
        if not new_done or (old_done and new_done <= old_done):
            continue
        area = str(item.get('area') or '').strip()
        task = str(item.get('task') or '').strip()
        schedule = next((s for s in schedules if isinstance(s, dict) and str(s.get('area') or '').strip().lower() == area.lower() and str(s.get('task') or '').strip().lower() == task.lower()), {})
        schedule_id = str(schedule.get('id') or '')
        completed_at = str(item.get('lastDone') or '')
        dedupe = (schedule_id, completed_at, area.lower(), task.lower())
        if dedupe in existing:
            continue
        frequency = str(schedule.get('frequency') or item.get('frequency') or item.get('freq') or '').strip()
        by = str(item.get('by') or user.get('username') or user.get('name') or '').strip()
        completions.append({
            'id': 'live-clean-completion-' + app.secrets.token_hex(8),
            'scheduleId': schedule_id,
            'area': area,
            'task': task,
            'frequency': frequency,
            'freq': frequency.lower(),
            'date': completed_at[:10],
            'completedAt': completed_at,
            'completedBy': by,
            'by': by,
            'status': 'Completed',
            'source': 'live_app',
            'timePrecision': 'timestamp'
        })
        existing.add(dedupe)
        added = True
    if added:
        incoming_state['scheduleCompletions'] = completions


def _merge_rolling_audit'''

text2, n = pattern.subn(replacement, text, count=1)
if n != 1:
    raise SystemExit('Cleaning conflict merge marker not found in app/auth_controls.py')
text = text2

needle = "            incoming['users']=current['state'].get('users',[])\n            if user.get('role') != 'manager':"
replace = "            incoming['users']=current['state'].get('users',[])\n            if str(payload.get('reason','')).strip().lower() == 'cleaning':\n                _ensure_cleaning_history(current['state'], incoming, user)\n            if user.get('role') != 'manager':"
if needle not in text:
    raise SystemExit('Cleaning history insertion marker not found in app/auth_controls.py')
text = text.replace(needle, replace, 1)

path.write_text(text, encoding='utf-8')
print('Applied cleaning persistence fix')
