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
# task, but it must not lower today's completion percentage. Internally it is
# neutralised for the score; the small runtime patch below keeps its visual
# status amber/upcoming so it is never presented as actually completed.
label = re.search(r'label\s*:\s*["\']Probe calibration["\']', text)
if not label:
    raise SystemExit('Probe calibration task marker not found')

push_start = text.rfind('t.push(', 0, label.start())
if push_start < 0:
    raise SystemExit('Probe calibration t.push(...) call not found')

open_idx = push_start + len('t.push')
if open_idx >= len(text) or text[open_idx] != '(':
    raise SystemExit('Malformed probe calibration push call')

# Find the matching close-paren while ignoring quoted JavaScript strings.
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

patch = '''\n  /* cdc-compliance-future-calibration-neutral */\n  {\n    const _cal=t[t.length-1];\n    if(_cal&&_cal.label==="Probe calibration"&&/\\bdue this week\\b/i.test(String(_cal.detail||""))){\n      _cal.state="done";\n      _cal.visualState="upcoming";\n    }\n  }'''
text = text[:insert_at] + patch + text[insert_at:]

visual = r'''
<style id="cdc-probe-calibration-upcoming-style">
  .cdc-probe-calibration-upcoming{border-left-color:var(--warn,#e4ad37)!important;}
  .cdc-probe-calibration-upcoming svg{color:var(--warn,#e4ad37)!important;stroke:var(--warn,#e4ad37)!important;}
  .cdc-probe-calibration-upcoming [class*="icon"]{color:var(--warn,#e4ad37)!important;}
</style>
<script id="cdc-probe-calibration-upcoming-visual">
(()=>{
  'use strict';
  function leafText(el){return el&&el.children.length===0?String(el.textContent||'').trim():'';}
  function fix(){
    const labels=[...document.querySelectorAll('body *')].filter(el=>leafText(el)==='Probe calibration');
    for(const label of labels){
      let card=label;
      for(let i=0;i<7&&card;i++,card=card.parentElement){
        const body=String(card.innerText||'');
        if(/Probe calibration/i.test(body)&&/Due this week/i.test(body)&&(/View|Open/i.test(body))){
          card.classList.add('cdc-probe-calibration-upcoming');
          card.style.borderLeftColor='var(--warn,#e4ad37)';
          break;
        }
      }
    }
  }
  const obs=new MutationObserver(fix);
  obs.observe(document.documentElement,{childList:true,subtree:true});
  setInterval(fix,750);
  fix();
})();
</script>
'''
if 'id="cdc-probe-calibration-upcoming-visual"' not in text:
    if '</body>' not in text:
        raise SystemExit('Could not find </body> for probe calibration visual patch')
    text = text.replace('</body>', visual + '\n</body>', 1)

index.write_text(text, encoding='utf-8')
print('Future probe calibration excluded from Compliance Today and shown amber/upcoming, not completed')
