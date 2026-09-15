from pathlib import Path
import re

p = Path('app/index.html')
text = p.read_text(encoding='utf-8')

# Stock should be recorded and displayed as real quantities (g, kg, oz, ml, L,
# packs, cases, each, etc.) rather than exposing the internal "par" term. The
# internal `par` field remains the minimum/target for backwards compatibility
# with existing records and ordering logic.
text = text.replace('stock:"Inventory & par levels"', 'stock:"Inventory quantities & ordering"')
text = text.replace('kpis.append(kpi("Below par",al.stock,al.stock?"Reorder soon":"Stocked","",al.stock?"down":"up","stock"));',
                    'kpis.append(kpi("Low stock",al.stock,al.stock?"Reorder soon":"Stocked","",al.stock?"down":"up","stock"));')

new_stock_header = '''const STOCK_CATS=["Meat","Frozen","Dairy","Veg","Bakery","Ambient","Drinks","Other"];
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
stock_header_pattern = r'const\s+STOCK_CATS\s*=\s*\["Meat","Frozen","Dairy","Veg","Bakery","Ambient","Drinks","Other"\]\s*;\s*let\s+stockView\s*=\s*"list"\s*,\s*stockSearch\s*=\s*""\s*,\s*stockCat\s*=\s*"all"\s*;'
text, stock_header_count = re.subn(stock_header_pattern, lambda m: new_stock_header, text, count=1)
if stock_header_count != 1:
    raise SystemExit(f'STOCK_CATS marker not found or ambiguous: {stock_header_count}')

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

# List rows: show actual amount first, then minimum amount, both with units.
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

# Stock editor: unit selector plus clear quantity labels.
old_unit = '<label class="f"><span class="lab">Unit</span><input class="inp" id="su" value="${esc(s.unit||"")}" placeholder="kg, box, pack…"></label>'
new_unit = '<label class="f"><span class="lab">Unit</span><select class="inp" id="su">${[...new Set([stockUnitLabel(s.unit),...STOCK_UNITS])].map(u=>`<option value="${esc(u)}"${stockUnitLabel(s.unit)===u?" selected":""}>${esc(u)}</option>`).join("")}</select></label>'
if old_unit not in text:
    raise SystemExit('stock unit editor marker not found')
text = text.replace(old_unit, new_unit, 1)
text = text.replace('<span class="lab">Par level (target)</span>', '<span class="lab">Minimum stock amount</span>', 1)
text = text.replace('<span class="lab">In stock now</span>', '<span class="lab">Actual amount in stock</span>', 1)

# Menu stock calculations should show units in Need, Actual and To buy columns.
text = text.replace('<td class="mono" style="padding:9px 11px;text-align:right">${round1(r.have)}</td>',
                    '<td class="mono" style="padding:9px 11px;text-align:right">${round1(r.have)} ${esc(r.unit||"")}</td>', 1)
text = text.replace('<td class="mono" style="padding:9px 11px;text-align:right;color:var(--${r.buy>0?"warn":"ok"})">${r.buy>0?"+"+round1(r.buy):"✓"}</td>',
                    '<td class="mono" style="padding:9px 11px;text-align:right;color:var(--${r.buy>0?"warn":"ok"})">${r.buy>0?"+"+round1(r.buy)+" "+esc(r.unit||""):"✓"}</td>', 1)

# Movement history also shows the unit when the stock line still exists.
text = text.replace('{key:"delta",label:"Change",render:m=>`<span class="cell readonly mono" style="color:var(--${m.delta>=0?"ok":"danger"})">${m.delta>=0?"+":""}${m.delta}</span>`,w:"90px"},',
                    '{key:"delta",label:"Change",render:m=>{const s=stockById(m.stockId)||stockByName(m.item);return `<span class="cell readonly mono" style="color:var(--${m.delta>=0?"ok":"danger"})">${m.delta>=0?"+":""}${stockQtyText(m.delta,s&&s.unit)}</span>`;},w:"110px"},', 1)
text = text.replace('{key:"after",label:"→ Now",render:m=>`<span class="cell readonly mono">${m.after}</span>`,w:"80px"},',
                    '{key:"after",label:"→ Now",render:m=>{const s=stockById(m.stockId)||stockByName(m.item);return `<span class="cell readonly mono">${stockQtyText(m.after,s&&s.unit)}</span>`;},w:"100px"},', 1)

# Supplier orders and delivery copy should use quantity language.
text = text.replace('Suggested order to bring every line back to par:', 'Suggested order to bring each item back to its minimum stock amount:')
text = text.replace('Restock below-par', 'Restock low stock')
text = text.replace('fill everything to par.', 'bring each item back to its minimum stock amount.')
text = text.replace('Stock is at par — check what you actually need', 'Stock is above minimum — check what you actually need')

# User-facing dashboard/compliance/voice wording. Voice still accepts the phrase
# "below par" as an input synonym, but staff-facing output uses plain language.
text = text.replace('item"+(low>1?"s":"")+" below par"', 'low-stock item"+(low>1?"s":"")')
text = text.replace('low.length+" item"+(low.length>1?"s":"")+" below par — raise the order"',
                    'low.length+" low-stock item"+(low.length>1?"s":"")+" — raise the order"')
text = text.replace('" line"+(low.length>1?"s":"")+" below par: "', '" low-stock line"+(low.length>1?"s":"")+": "')
text = text.replace('"Stock is fine — nothing below par."', '"Stock is fine — nothing is below its minimum amount."')
text = text.replace('Below par: ${low.join(", ")||"none"}.', 'Low stock: ${low.join(", ")||"none"}.')
text = text.replace("tell you what's due or below par", "tell you what's due or low on stock")

# Fail the build rather than silently shipping the old terminology/UI again.
required = [
    'const STOCK_UNITS=[',
    'Minimum stock amount',
    'Actual amount in stock',
    'Low stock — amounts to order',
    'stockShortfallSummary(low)',
]
missing = [x for x in required if x not in text]
forbidden = [
    'stock:"Inventory & par levels"',
    'kpi("Below par"',
    '<span class="lab">Par level (target)</span>',
    '"units short"',
    'Suggested order to bring every line back to par:',
]
left = [x for x in forbidden if x in text]
if missing or left:
    raise SystemExit(f'Stock quantity patch verification failed; missing={missing}, old_markers={left}')

p.write_text(text, encoding='utf-8')
print('Stock quantity/unit UI applied: actual amounts, minimums and order shortfalls now show g/kg/oz/ml/L/count units')
