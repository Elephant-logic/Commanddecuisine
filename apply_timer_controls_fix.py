"""Keep Kitchen Tools v2 form controls mounted while countdown text updates.

The original 500ms tick replaced .cdc-ktv2-body.innerHTML on EVERY tick.
On touchscreen browsers that destroys focused inputs and button elements
between pointerdown and click. Never modify persisted kitchen data/auth.
"""
from pathlib import Path

path=Path("app/kitchen_tools_v2.js")
if not path.is_file():
    raise SystemExit("Kitchen Tools v2 runtime missing")
text=path.read_text(encoding="utf-8")
original="""  function tick(){updateExpired();renderDock();if(document.getElementById(PANEL))renderPanelBody();injectRecipeTimers();hideOldTimerUI();wrapChef();}"""
corrected="""  function tick(){
    const before=timers.map(t=>t.id+':'+t.status).join('|');
    updateExpired();
    renderDock();
    const panel=document.getElementById(PANEL);
    if(panel){
      const after=timers.map(t=>t.id+':'+t.status).join('|');
      const rows=[...panel.querySelectorAll('.cdc-ktv2-timer')];
      const byId=new Map(timers.map(t=>[String(t.id),t]));
      // Rerender only when a timer actually changes state (e.g. finishes).
      // Never replace inputs or action buttons at 500ms intervals.
      if(before!==after || rows.length!==timers.length || rows.some(row=>!byId.has(row.dataset.id))){
        renderPanelBody();
      }else{
        rows.forEach(row=>{
          const t=byId.get(row.dataset.id);
          const time=row.querySelector('.cdc-ktv2-time');
          if(t&&time){
            const label=t.status==='done'?'DONE':fmt(remaining(t));
            if(time.textContent!==label)time.textContent=label;
          }
        });
      }
    }
    injectRecipeTimers();hideOldTimerUI();wrapChef();
  }"""
if original not in text:
    if corrected in text:
        print("Timer fix already installed")
        raise SystemExit(0)
    raise SystemExit("Kitchen Tools v2 tick marker changed — refusing unverified timer patch")
if text.count(original)!=1:
    raise SystemExit("Expected exactly one timer tick function")
text=text.replace(original,corrected,1)
if original in text or text.count("const before=timers.map(t=>t.id+':'+t.status)")!=1:
    raise SystemExit("Timer tick patch failed verification")
path.write_text(text,encoding="utf-8")
print("Kitchen Tools v2 timer controls fixed: 500ms tick updates countdown text without unmounting inputs/buttons")
