from pathlib import Path

p=Path('app/main_app.js')
text=p.read_text(encoding='utf-8')

old_display='if(sh){const s=el("div",{class:"shift",onclick:()=>editShift(u,d,row),html:`<div class="st">${sh.start}–${sh.end}</div><div class="sr">${esc(sh.role||"")}</div>`});td.append(s);}'
new_display='if(sh){const split=(sh.start2&&sh.end2)?`<br>${sh.start2}–${sh.end2}`:"";const s=el("div",{class:"shift",onclick:()=>editShift(u,d,row),html:`<div class="st">${sh.start}–${sh.end}${split}</div><div class="sr">${esc(sh.role||"")}</div>`});td.append(s);}'
if old_display not in text:
    raise SystemExit('Rota display marker not found')
text=text.replace(old_display,new_display,1)

old_hours='function shiftHours(sh){const[a,b]=[sh.start,sh.end].map(t=>{const[h,m]=t.split(":");return +h+ (+m)/60;});return Math.max(0,b-a);}'
new_hours='function shiftHours(sh){const hours=(a,b)=>{if(!a||!b)return 0;const x=a.split(":"),y=b.split(":");const s=+x[0]+(+x[1])/60,e=+y[0]+(+y[1])/60;return Math.max(0,e-s);};return hours(sh.start,sh.end)+hours(sh.start2,sh.end2);}'
if old_hours not in text:
    raise SystemExit('Rota hours marker not found')
text=text.replace(old_hours,new_hours,1)

old_form='''  b.innerHTML=`<div class="frow"><label class="f"><span class="lab">Start</span><input class="inp mono" id="ss" type="time" value="${sh.start}"></label>\n    <label class="f"><span class="lab">End</span><input class="inp mono" id="se" type="time" value="${sh.end}"></label></div>\n    <label class="f"><span class="lab">Station / role</span><input class="inp" id="sr" value="${esc(sh.role||"")}" placeholder="e.g. Grill, Prep, Pass"></label>`;'''
new_form='''  b.innerHTML=`<div class="frow"><label class="f"><span class="lab">Start 1</span><input class="inp mono" id="ss" type="time" value="${sh.start||""}"></label>\n    <label class="f"><span class="lab">End 1</span><input class="inp mono" id="se" type="time" value="${sh.end||""}"></label></div>\n    <div style="margin:2px 0 10px;color:var(--muted);font-size:12px">Split shift (optional)</div>\n    <div class="frow"><label class="f"><span class="lab">Start 2</span><input class="inp mono" id="ss2" type="time" value="${sh.start2||""}"></label>\n    <label class="f"><span class="lab">End 2</span><input class="inp mono" id="se2" type="time" value="${sh.end2||""}"></label></div>\n    <label class="f"><span class="lab">Station / role</span><input class="inp" id="sr" value="${esc(sh.role||"")}" placeholder="e.g. Grill, Prep, Pass"></label>`;'''
if old_form not in text:
    raise SystemExit('Rota edit form marker not found')
text=text.replace(old_form,new_form,1)

old_save='el("button",{class:"btn primary",html:icon("save")+"Save",onclick:()=>{row.shifts[d]={start:$("#ss").value,end:$("#se").value,role:$("#sr").value};save("rota");m.close();rerender();}})]});'
new_save='el("button",{class:"btn primary",html:icon("save")+"Save",onclick:()=>{const s1=$("#ss").value,e1=$("#se").value,s2=$("#ss2").value,e2=$("#se2").value;if(!s1||!e1){toast("Start 1 and End 1 are required","warn");return;}if((s2&&!e2)||(!s2&&e2)){toast("Enter both Start 2 and End 2 for a split shift","warn");return;}row.shifts[d]={start:s1,end:e1,start2:s2||"",end2:e2||"",role:$("#sr").value};save("rota");m.close();rerender();}})]});'
if old_save not in text:
    raise SystemExit('Rota save marker not found')
text=text.replace(old_save,new_save,1)

p.write_text(text,encoding='utf-8')
print('Rota split shifts enabled with optional second start/end and combined hours')

print('=== TEMP BACKFILL DIAGNOSTIC ===')
for path in [Path('app/main_app.js'), Path('app/kitchen_fixes_20260810.js')]:
    if not path.exists():
        continue
    src=path.read_text(encoding='utf-8')
    print('FILE',path)
    for needle in ['historic temperature backfill','backfill','function readingFor','/api/temperature','temperature-readings','append_temperature','period===','period===']:
        start=0;shown=0
        while shown<8:
            i=src.lower().find(needle.lower(),start)
            if i<0: break
            print(f'--- {needle} @ {i} ---')
            print(src[max(0,i-1800):min(len(src),i+3400)])
            print('--- END ---')
            shown+=1
            start=i+max(1,len(needle))
