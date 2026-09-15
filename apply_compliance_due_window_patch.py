from pathlib import Path
import re

index = Path('app/index.html')
text = index.read_text(encoding='utf-8')

# A probe calibration that is merely due later this week should remain visibly
# pending/upcoming, but it must not reduce the separate "Compliance Today"
# percentage until it is actually due.  Do NOT change its task state to done;
# the task state controls the green/amber card styling.
label = re.search(r'label\s*:\s*["\']Probe calibration["\']', text)
if not label:
    raise SystemExit('Probe calibration task marker not found')

push_start = text.rfind('t.push(', 0, label.start())
if push_start < 0:
    raise SystemExit('Probe calibration t.push(...) call not found')

open_idx = push_start + len('t.push')
depth = 0
quote = None
escaped = False
close_idx = None
for i in range(open_idx, len(text)):
    ch = text[i]
    if quote:
        if escaped:
            escaped = False
        elif ch == '\\':
            escaped = True
        elif ch == quote:
            quote = None
        continue
    if ch in ('"', "'", '`'):
        quote = ch
        continue
    if ch == '(':
        depth += 1
    elif ch == ')':
        depth -= 1
        if depth == 0:
            close_idx = i
            break
if close_idx is None:
    raise SystemExit('Could not find end of probe calibration push call')

insert_at = close_idx + 1
while insert_at < len(text) and text[insert_at] in ' \t':
    insert_at += 1
if insert_at < len(text) and text[insert_at] == ';':
    insert_at += 1

marker = '/* cdc-compliance-future-calibration-neutral */'
patch = '''\n  /* cdc-compliance-future-calibration-neutral */\n  {\n    const _cal=t[t.length-1];\n    if(_cal&&_cal.label==="Probe calibration"&&/\\bdue this week\\b/i.test(String(_cal.detail||""))){\n      _cal.complianceNeutral=true;\n    }\n  }'''
text = text[:insert_at] + patch + text[insert_at:]

# Wherever the dashboard counts completed task states for its percentage,
# treat a future calibration as neutral for that count without turning its
# visual state into "done". This intentionally leaves the row amber/pending.
pat = re.compile(r'\.filter\(\s*([A-Za-z_$][\w$]*)\s*=>\s*\1\.state\s*===\s*(["\'])done\2\s*\)')

def repl(m):
    var = m.group(1)
    return f'.filter({var}=>{var}.state==="done"||{var}.complianceNeutral)'

text, count = pat.subn(repl, text)
if count == 0:
    # Support parenthesised arrow parameters as well.
    pat2 = re.compile(r'\.filter\(\s*\(\s*([A-Za-z_$][\w$]*)\s*\)\s*=>\s*\1\.state\s*===\s*(["\'])done\2\s*\)')
    text, count = pat2.subn(repl, text)

index.write_text(text, encoding='utf-8')
print(f'Future probe calibration stays pending visually and is neutral in Compliance Today; adjusted {count} done-count filter(s)')
