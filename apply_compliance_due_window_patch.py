from pathlib import Path
import re

index = Path('app/index.html')
text = index.read_text(encoding='utf-8')

marker = '/* cdc-compliance-future-calibration-neutral */'
if marker in text:
    print('Compliance due-window patch already present')
    raise SystemExit(0)

# "Compliance today" should measure work that is due now/overdue. A probe
# calibration that is merely due later this week stays visible as an upcoming
# task, but it must not lower today's completion percentage.
label = re.search(r'label\s*:\s*["\']Probe calibration["\']', text)
if not label:
    raise SystemExit('Probe calibration task marker not found')

push_start = text.rfind('t.push(', 0, label.start())
if push_start < 0:
    raise SystemExit('Probe calibration t.push(...) call not found')

open_idx = push_start + len('t.push')
if open_idx >= len(text) or text[open_idx] != '(':
    raise SystemExit('Malformed probe calibration push call')

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

patch = '''\n  /* cdc-compliance-future-calibration-neutral */\n  {\n    const _cal=t[t.length-1];\n    if(_cal&&_cal.label==="Probe calibration"&&/\\bdue this week\\b/i.test(String(_cal.detail||""))){\n      _cal.state="done";\n    }\n  }'''
text = text[:insert_at] + patch + text[insert_at:]

index.write_text(text, encoding='utf-8')
print('Future probe calibration no longer reduces Compliance Today')
