from pathlib import Path

p = Path('app/index.html')
text = p.read_text(encoding='utf-8')

# Stock should be shown as real quantities (g, kg, oz, ml, L, packs, etc.)
# rather than exposing the internal "par" terminology. The internal `par`
# field remains the minimum/target so existing data and ordering logic remain
# compatible.
text = text.replace('stock:"Inventory & par levels"', 'stock:"Inventory quantities & ordering"')
text = text.replace('kpis.append(kpi("Below par",al.stock,al.stock?"Reorder soon":"Stocked","",al.stock?"down":"up","stock"));',
                    'kpis.append(kpi("Low stock",al.stock,al.stock?"Reorder soon":"Stocked","",al.stock?"down":"up","stock"));')

old = 'const STOCK_CATS=["Meat","Frozen","Dairy","Veg","Bakery","Ambient","Drinks","Other"]; let stockView="list", stockSearch="", stockCat="all";'
new = '''const STOCK_CATS=["Meat","Frozen","Dairy","Veg","Bakery","Ambient","Drinks","Other"];
const STOCK_UNITS=["g","kg","oz","ml","L","each","pack","case","box","tin","bottle","tray","bag","bunch"];
function stockUnitLabel(unit){const u=String(unit||"each").trim();return u==="ea"?"each":u;}
function stockUnitStep(unit){const u=stockUnitLabel(unit);return (u==="kg"||u==="L")?0.1:1;}
function stockFmtQty(n){const v=Math.round((Number(n)||0)*100)/100;return Number.isInteger(v)?String(v):String(v).replace(/0+$/,"").replace(/\\.$/,"");}
function stockQtyText(n,unit){
  const v=Number(n)||0,u=stockUnitLabel(unit);
  const plurals={pack:"packs",case:"cases",box:"boxes",tin:"tins",bottle:"bottles",tray:"trays",bag:"bags",bunch:"bunches"};
  return stockFmtQty(v)+" "+((v===1||!plurals[u])?u:plurals[u]);
}
function stockShortfallSummary(items){
  const by={};(items||[]).forEach(s=>{const u=stockUnitLabel(s.unit),q=Math.max(0,(+s.par||0)-(+s.qty||0));by[u]=(by[u]||0)+q;});
  return Object.entries(by).filter(([,q])=>q>0).map(([u,q])=>stockQtyText(q,u)).join(" · ")||"Nothing to order";
}
let stockView="list", stockSearch="", stockCat="all";'''
if old not in text:
    raise SystemExit('STOCK_CATS marker not found')
text = text.replace(old, new, 1)

# Normalise legacy "ea" units and present the stock overview in quantity terms.
text = text.replace('VIEWS.stock=function(v){   const low=STATE.stock.filter(s=>+s.qty< +s.par);',
'''VIEWS.stock=function(v){
  let stockUnitsChanged=false;
  STATE.stock.forEach(s=>{if(!s.unit||s.unit==="ea"){s.unit="each";stockUnitsChanged=true;}});
  if(stockUnitsChanged)save("normalise stock units");
  const low=STATE.stock.filter(s=>+s.qty< +s.par);''', 1)
text = text.replace('bar.append(kpi("Below par",low.length,low.length?"Reorder soon":"All stocked",low.length?"down":"up","","alert"));',
                    'bar.append(kpi("Low stock",low.length,low.length?"Reorder soon":"All stocked",low.length?"down":"up","","alert"));', 1)
text = text.replace('bar.append(kpi("To order",low.reduce((n,s)=>n+Math.max(0,Math.ceil(+s.par-+s.qty)),0),"units short","",""));',
                    'bar.append(kpi("To order",low.length,stockShortfallSummary(low),"",""));', 1)
text = text.replace('el("h3",{style:"color:var(--warn)"},"Below par")',
                    'el("h3",{style:"color:var(--warn)"},"Low stock — amounts to order")', 1)
text = text.replace('html:`${esc(s.item)} <b class="mono" style="color:var(--warn)">+${Math.ceil(+s.par-+s.qty)} ${esc(s.unit||"")}</b>`',
                    'html:`${esc(s.item)} <b class="mono" style="color:var(--warn)">+${esc(stockQtyText(Math.max(0,(+s.par||0)-(+s.qty||0)),s.unit))}</b>`', 1)

# List rows: show the actual amount first, then the minimum amount, both with units.
text = text.replace('${Math.ceil(short)} short</span>', '${esc(stockQtyText(short,s.unit))} short</span>', 1)
text = text.replace('<div class="muted" style="font-size:11.5px;margin-top:2px">par ${s.par} ${esc(s.unit||"")}${s.supplier?" · "+esc(s.supplier):""}</div>',
                    '<div class="muted" style="font-size:11.5px;margin-top:2px"><b style="color:var(--ink)">Actual: ${esc(stockQtyText(s.qty,s.unit))}</b> · Minimum: ${esc(stockQtyText(s.par,s.unit))}${s.supplier?" · "+esc(s.supplier):""}</div>', 1)
text = text.replace('function stockRow(s){   const short=+s.par-+s.qty, lowr=short>0, out=+s.qty<=0;',
                    'function stockRow(s){   const short=+s.par-+s.qty, lowr=short>0, out=+s.qty<=0, step=stockUnitStep(s.unit);', 1)
text = text.replace('s.qty=Math.max(0,Math.round((+s.qty-1)*10)/10);', 's.qty=Math.max(0,Math.round((+s.qty-step)*100)/100);', 1)
text = text.replace('type:"number",step:"0.1",value:s.qty,style:"width:64px;text-align:center;padding:8px"',
                    'type:"number",step:String(step),value:s.qty,style:"width:74px;text-align:center;padding:8px"', 1)
text = text.replace('s.qty=Math.round((+s.qty+1)*10)/10;', 's.qty=Math.round((+s.qty+step)*100)/100;', 1)
text = text.replace('row.append(info,stepper);', 'stepper.append(el("span",{class:"muted",style:"min-width:34px;font-size:12px"},stockUnitLabel(s.unit))); row.append(info,stepper);', 1)

# Sheet view: unit is a controlled list and "Par" is called Minimum stock.
text = text.replace('{key:"unit",label:"Unit",w:"80px"},{key:"par",label:"Par",type:"number",w:"70px"},{key:"qty",label:"In stock",type:"number",w:"90px"},',
                    '{key:"unit",label:"Unit",type:"select",opts:STOCK_UNITS,w:"90px"},{key:"par",label:"Minimum stock",type:"number",w:"110px"},{key:"qty",label:"Actual stock",type:"number",w:"100px"},', 1)
text = text.replace('unit:"ea",par:1,qty:0,supplier:""', 'unit:"each",par:1,qty:0,supplier:""')

# Stock editor: unit selector, clear quantity labels, and real unit examples.
old_unit = '<label class="f"><span class="lab">Unit</span><input class="inp" id="su" value="${esc(s.unit||"")}" placeholder="kg, box, pack…"></label>'
new_unit = '<label class="f"><span class="lab">Unit</span><select class="inp" id="su">${[...new Set([stockUnitLabel(s.unit),...STOCK_UNITS])].map(u=>`<option value="${esc(u)}"${stockUnitLabel(s.unit)===u?" selected":""}>${esc(u)}</option>`).join("")}</select></label>'
if old_unit not in text:
    raise SystemExit('stock unit editor marker not found')
text = text.replace(old_unit, new_unit, 1)
text = text.replace('<span class="lab">Par level (target)</span>', '<span class="lab">Minimum stock amount</span>', 1)
text = text.replace('<span class="lab">In stock now</span>', '<span class="lab">Actual amount in stock</span>', 1)

# Supplier orders and delivery copy should also use quantity language.
text = text.replace('Suggested order to bring every line back to par:', 'Suggested order to bring each item back to its minimum stock amount:')
text = text.replace('Restock below-par', 'Restock low stock')
text = text.replace('fill everything to par.', 'bring each item back to its minimum stock amount.')
text = text.replace('Stock is at par — check what you actually need', 'Stock is above minimum — check what you actually need')

# User-facing dashboard/compliance/voice wording: keep "below par" as a voice synonym,
# but never make staff learn that term in the UI.
text = text.replace('item"+(low>1?"s":"")+" below par"', 'low-stock item"+(low>1?"s":"")')
text = text.replace('" below par — raise the order"', '" low-stock item"+(low.length>1?"s":"")+" — raise the order"')
text = text.replace('" line"+(low.length>1?"s":"")+" below par: "', '" low-stock line"+(low.length>1?"s":"")+": "')
text = text.replace('"Stock is fine — nothing below par."', '"Stock is fine — nothing is below its minimum amount."')
text = text.replace('Below par: ${low.join(", ")||"none"}.', 'Low stock: ${low.join(", ")||"none"}.')
text = text.replace("tell you what's due or below par", "tell you what's due or low on stock")

p.write_text(text, encoding='utf-8')
print('Stock quantity/unit UI applied: actual amounts, minimums and order shortfalls now show g/kg/oz/ml/L/count units')
