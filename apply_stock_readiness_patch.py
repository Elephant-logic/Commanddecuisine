"""Repair Stock quantity controls and show accurate catalogue readiness."""
from pathlib import Path
main=Path("app/main_app.js")
idx=Path("app/index.html")
s=main.read_text(encoding="utf-8")
def once(old,new,label):
 global s
 if s.count(old)!=1:raise SystemExit(label+" marker count "+str(s.count(old)))
 s=s.replace(old,new,1)
once('VIEWS.stock=function(v){\n  const low=STATE.stock.filter(s=>s.qtyKnown!==false && +s.qty< +s.par);',
 'VIEWS.stock=function(v){\n  const low=STATE.stock.filter(s=>s.qtyKnown===true && +s.par>0 && +s.qty< +s.par);',
 'Stock low count')
once('function stockRow(s){\n  const short=+s.par-+s.qty, lowr=short>0, out=+s.qty<=0;',
 'function stockRow(s){\n  const known=s.qtyKnown===true,step=stockUnitStep(s.unit);\n  const short=known?+s.par-+s.qty:0, lowr=known&&+s.par>0&&short>0, out=known&&+s.qty<=0;',
 'Stock row input step')
once('const pct=+s.par?clamp(+s.qty/+s.par*100,0,100):100;',
 'const pct=known&&+s.par?clamp(+s.qty/+s.par*100,0,100):0;',
 'Progress reflects count')
tick=chr(96)
opening='$'+'{'
once(opening+'out?'+tick+'<span class="tag danger">Out</span>'+tick+':lowr?',
 opening+'!known?'+tick+'<span class="tag dim">Not counted</span>'+tick+':out?'+tick+'<span class="tag danger">Out</span>'+tick+':lowr?',
 'Stock uncounted badge')
once('s.qty=+e.target.value||0;save("stock");rerender();',
 'if(e.target.value.trim()==="")return;s.qty=+e.target.value||0;s.qtyKnown=true;save("stock");rerender();',
 'Stock entered quantity')
once('const lowr=+s.qty< +s.par;return',
 'const known=s.qtyKnown===true,lowr=known&&+s.par>0&&+s.qty< +s.par;return',
 'Stock sheet status')
once(opening+'lowr?"warn":"ok"}',opening+'!known?"dim":lowr?"warn":"ok"}','Stock sheet status CSS')
once(opening+'lowr?"Low":"OK"}',opening+'!known?"Not counted":lowr?"Low":"OK"}','Stock sheet status text')
once('onEdit:(row,k,val)=>{row[k]=val;save("stock");if(k==="qty"||k==="par"||k==="cat")rerender();}',
 'onEdit:(row,k,val)=>{row[k]=val;if(k==="qty"&&String(val).trim()!==""&&Number.isFinite(Number(val)))row.qtyKnown=true;save("stock");if(k==="qty"||k==="par"||k==="cat")rerender();}',
 'Stock sheet counted flag')
once('STATE.stock.push({id:uid("s"),item:"New item",cat:"Other",unit:"each",par:1,qty:0,supplier:""});',
 'STATE.stock.push({id:uid("s"),item:"New item",cat:"Other",unit:"each",par:0,qty:0,qtyKnown:false,supplier:""});',
 'New stock remains uncounted')
once('const low=STATE.stock.filter(s=>+s.qty< +s.par).length;',
 'const low=STATE.stock.filter(s=>s.qtyKnown===true&&+s.par>0&&+s.qty< +s.par).length;',
 'Home stock warnings')
anchor='VIEWS.stock=function(v){\n'
banner='''VIEWS.stock=function(v){
  const total=STATE.stock.length,counted=STATE.stock.filter(x=>x.qtyKnown===true).length;
  const suppliers=STATE.stock.filter(x=>String(x.supplier||"").trim()).length;
  const note=el("div",{class:"card cdc-stock-readiness",style:"margin:0 0 14px;padding:13px;border-left:4px solid var(--brass,#e3a72c)"});
  note.append(el("strong",{},"Stock catalogue readiness"));
  note.append(el("div",{class:"muted",style:"margin-top:5px;font-size:13px;line-height:1.5"},
    "Counted "+counted+"/"+total+" items · Supplier assigned "+suppliers+"/"+total+". "+
    (counted===0?"Your Stock list is a catalogue, not a physical stock count yet.":"Only counted lines are labelled low or out of stock.")));
  note.append(el("div",{class:"muted",style:"font-size:12px;margin-top:5px"},
    "Tap an item to enter a genuine quantity, minimum and supplier. Unknown quantities are not zero."));
  v.append(note);
'''
once(anchor,banner,'Stock overview')
once('low.length?"Reorder soon":"All stocked"',
 'low.length?"Reorder soon":STATE.stock.some(x=>x.qtyKnown===true)?"No low counted lines":"Nothing counted yet"',
 'Stock summary')
main.write_text(s,encoding="utf-8")
html=idx.read_text(encoding="utf-8")
old="main_app.js?v=20261020-kitchen-safety1"
if html.count(old)!=1:raise SystemExit("Cache version missing")
idx.write_text(html.replace(old,"main_app.js?v=20261020-kitchen-stock1",1),encoding="utf-8")
print("PASS: Stock stepper, count provenance, catalogue progress, honest low-stock warnings")
