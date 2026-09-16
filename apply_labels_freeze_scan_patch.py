from pathlib import Path
import re

path = Path('app/main_app.js')
text = path.read_text(encoding='utf-8')

pattern = re.compile(r'/\* ---------- LABELS \(print prep / use-by\) ---------- \*/\nVIEWS\.labels=function\(v\)\{.*?\n\};\nfunction printLabel\(name,kind,days,allergens\)\{', re.S)
replacement = r'''/* ---------- LABELS (print prep / use-by) ---------- */
async function scanLabelCode(onValue){
  if(!('BarcodeDetector' in window) || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){
    const manual=window.prompt('Camera barcode/QR scanning is not supported by this browser. Enter the code instead:','');
    if(manual&&manual.trim())onValue(manual.trim());
    return;
  }
  let stream=null, stopped=false, raf=0;
  const wrap=el("div",{});
  const video=el("video",{autoplay:true,playsinline:true,style:"width:100%;max-height:56vh;background:#000;border-radius:12px;object-fit:cover"});
  const status=el("div",{class:"muted",style:"margin-top:10px;font-size:13px"},"Point the camera at a barcode or QR code.");
  wrap.append(video,status);
  const m=modal({title:"Scan barcode / QR",body:wrap,onClose:()=>stop()});
  function stop(){
    if(stopped)return; stopped=true;
    if(raf)cancelAnimationFrame(raf);
    if(stream)stream.getTracks().forEach(t=>t.stop());
  }
  try{
    const supported=await BarcodeDetector.getSupportedFormats();
    const wanted=['qr_code','ean_13','ean_8','code_128','code_39','upc_a','upc_e','data_matrix','itf','codabar'];
    const formats=wanted.filter(x=>supported.includes(x));
    const detector=formats.length?new BarcodeDetector({formats}):new BarcodeDetector();
    stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});
    video.srcObject=stream;
    await video.play();
    const tick=async()=>{
      if(stopped)return;
      try{
        if(video.readyState>=2){
          const found=await detector.detect(video);
          if(found&&found.length&&found[0].rawValue){
            const raw=String(found[0].rawValue).trim();
            stop(); m.close(); onValue(raw); return;
          }
        }
      }catch(e){}
      raf=requestAnimationFrame(tick);
    };
    raf=requestAnimationFrame(tick);
  }catch(err){
    stop(); m.close();
    const manual=window.prompt('Camera could not start. Enter the barcode or QR code instead:','');
    if(manual&&manual.trim())onValue(manual.trim());
  }
}
function cdcStockCodeMatch(s,raw){
  if(!s||!raw)return false;
  const vals=[s.barcode,s.qr,s.code,s.sku,s.id,...(Array.isArray(s.barcodes)?s.barcodes:[])];
  return vals.some(v=>v!=null&&String(v)===String(raw));
}
function cdcStockByCode(raw){
  raw=String(raw||'').trim();
  if(!raw)return null;
  const direct=(STATE.stock||[]).find(s=>cdcStockCodeMatch(s,raw));
  if(direct)return direct;
  const mapped=STATE.settings&&STATE.settings.labelCodes&&STATE.settings.labelCodes[raw];
  if(mapped&&mapped.stockId)return (STATE.stock||[]).find(s=>s.id===mapped.stockId)||null;
  return null;
}
function cdcEnsureStockCode(s,preferred){
  if(!s)return String(preferred||'').trim();
  let raw=String(preferred||'').trim();
  if(!raw) raw=String(s.barcode||'').trim();
  if(!raw && Array.isArray(s.barcodes) && s.barcodes.length) raw=String(s.barcodes[0]||'').trim();
  if(!raw){
    const base=String(s.id||s.item||Date.now()).replace(/[^A-Za-z0-9._-]/g,'').slice(-28)||String(Date.now());
    raw='CDC-'+base;
  }
  s.barcodes=Array.isArray(s.barcodes)?s.barcodes:[];
  if(!s.barcodes.some(x=>String(x)===raw))s.barcodes.push(raw);
  if(!s.barcode)s.barcode=raw;
  return raw;
}
VIEWS.labels=function(v){
  STATE.settings=STATE.settings||{};
  STATE.settings.labelCodes=STATE.settings.labelCodes||{};
  const card=el("div",{class:"card"});
  card.append(el("div",{class:"card-head"},el("h3",{},"Print a label")));
  card.insertAdjacentHTML("beforeend",`<p class="muted" style="font-size:12.5px;margin:-6px 0 12px">Date &amp; use-by labels for prepped, opened, chilled or frozen food. Frozen defaults to 3 months. Link a stock item and the printed barcode will resolve back to that stock item.</p>`);
  const dish=el("select",{class:"inp"},el("option",{value:""},"— choose a dish —"),...STATE.recipes.map(r=>el("option",{value:r.id},r.name)));
  const stock=el("select",{class:"inp"},el("option",{value:""},"— choose a stock item —"),...(STATE.stock||[]).map(s=>el("option",{value:s.id},s.item||s.name||s.id)));
  const name=el("input",{class:"inp",placeholder:"Or type an item name"});
  const life=el("input",{class:"inp num",type:"number",min:"1",value:"2",style:"max-width:90px"});
  const unit=el("select",{class:"inp",style:"max-width:130px"},el("option",{value:"days"},"days"),el("option",{value:"months"},"months"));
  const kind=el("select",{class:"inp"},...["Prepped","Opened","Defrosted","Cooked & chilled","Frozen"].map(k=>el("option",{},k)));
  const code=el("input",{class:"inp mono",placeholder:"Barcode / QR code (optional)"});
  const scan=el("button",{class:"btn ghost",type:"button",html:icon("label")+"Scan barcode / QR"});
  const make=el("button",{class:"btn ghost",type:"button",html:icon("plus")+"Create stock barcode"});
  const resolveCode=raw=>{
    raw=String(raw||'').trim(); if(!raw)return;
    code.value=raw;
    const mapped=STATE.settings.labelCodes[raw];
    const recipe=STATE.recipes.find(r=>r&&[r.barcode,r.qr,r.code,r.sku,r.id].some(v=>v!=null&&String(v)===raw));
    const stockItem=cdcStockByCode(raw);
    if(mapped){
      name.value=mapped.name||name.value;
      if(mapped.recipeId&&STATE.recipes.some(r=>r.id===mapped.recipeId)){dish.value=mapped.recipeId;}
      if(mapped.stockId&&(STATE.stock||[]).some(s=>s.id===mapped.stockId)){stock.value=mapped.stockId;}
      toast("Code recognised — label details filled in","ok");
    }else if(recipe){
      dish.value=recipe.id; name.value=recipe.name||name.value; toast("Recipe recognised","ok");
    }else if(stockItem){
      stock.value=stockItem.id; name.value=stockItem.item||stockItem.name||name.value; toast("Stock item recognised","ok");
    }else{
      toast("Code captured — choose a stock item or enter the item name to link it","ok");
    }
  };
  scan.addEventListener("click",()=>scanLabelCode(resolveCode));
  make.addEventListener("click",()=>{
    const s=(STATE.stock||[]).find(x=>x.id===stock.value);
    if(!s){toast("Choose a stock item first","warn");return;}
    const raw=cdcEnsureStockCode(s,code.value.trim());
    code.value=raw;
    STATE.settings.labelCodes[raw]={name:s.item||s.name||"",stockId:s.id,recipeId:dish.value||"",updatedAt:nowISO()};
    save("stock barcode link");
    toast("Stock barcode created and linked","ok");
  });
  dish.addEventListener("change",()=>{const r=STATE.recipes.find(x=>x.id===dish.value);if(r)name.value=r.name;});
  stock.addEventListener("change",()=>{
    const s=(STATE.stock||[]).find(x=>x.id===stock.value);
    if(!s)return;
    name.value=s.item||s.name||name.value;
    const existing=String(s.barcode||((s.barcodes||[])[0])||'').trim();
    if(existing)code.value=existing;
  });
  kind.addEventListener("change",()=>{
    if(kind.value==="Frozen"){life.value="3";unit.value="months";}
    else if(unit.value==="months"){life.value="2";unit.value="days";}
  });
  const lifeRow=el("div",{style:"display:flex;gap:8px;align-items:center"},life,unit);
  const codeRow=el("div",{style:"display:flex;gap:8px;align-items:center;flex-wrap:wrap"}); codeRow.append(code,scan,make);
  card.append(el("div",{class:"grid g2"},lf("Dish (optional)",dish),lf("Stock item (optional)",stock)),
    el("div",{class:"grid g2",style:"margin-top:2px"},lf("Item name",name),lf("Label type",kind)),
    el("div",{class:"grid g2",style:"margin-top:2px"},lf("Use within",lifeRow),lf("Barcode / QR",codeRow)));
  card.append(el("div",{style:"display:flex;justify-content:flex-end;margin-top:12px"},el("button",{class:"btn primary",html:icon("print")+"Preview & print",onclick:()=>{
    const s=(STATE.stock||[]).find(x=>x.id===stock.value);
    const nm=name.value.trim()||(s&&(s.item||s.name))||"(item)";
    const r=STATE.recipes.find(x=>x.id===dish.value);
    let raw=code.value.trim();
    if(s)raw=cdcEnsureStockCode(s,raw);
    if(raw&&nm!=="(item)"){
      STATE.settings.labelCodes[raw]={name:nm,recipeId:dish.value||"",stockId:s?s.id:"",updatedAt:nowISO()};
      save(s?"label stock barcode mapping":"label code mapping");
    }
    printLabel(nm,kind.value,+life.value||1,r?r.allergens:"",unit.value,raw,s?s.id:"");
  }})));
  v.append(card);
};
function printLabel(name,kind,days,allergens,expiryUnit="days",code="",stockId=""){'''

text2, n = pattern.subn(replacement, text, count=1)
if n != 1:
    raise SystemExit('Could not locate Labels view in main_app.js')
text = text2

old = '  const made=new Date(); const use=new Date(Date.now()+days*864e5);'
new = '''  const made=new Date(); const use=new Date(made.getTime());
  if(expiryUnit==="months") use.setMonth(use.getMonth()+Math.max(1,+days||1));
  else use.setDate(use.getDate()+Math.max(1,+days||1));'''
if old not in text:
    raise SystemExit('Could not locate label expiry calculation')
text = text.replace(old, new, 1)

needle = '    <div class="k">${esc(kind)}</div><h1>${esc(name)}</h1>'
replacement2 = '''    <div class="k">${esc(kind)}</div><h1>${esc(name)}</h1>${code?`<div style="margin:4px 0 8px"><svg id="cdcBarcode" data-code="${esc(code)}"></svg></div><div class="k" style="margin-bottom:4px">Stock code: ${esc(code)}</div>`:""}'''
if needle not in text:
    raise SystemExit('Could not locate printed label heading')
text = text.replace(needle, replacement2, 1)

label_start = text.find('function printLabel(name,kind,days,allergens,expiryUnit=')
if label_start < 0:
    raise SystemExit('Could not locate patched printLabel function')
close_idx = text.find('w.document.close();', label_start)
if close_idx < 0:
    raise SystemExit('Could not locate label document close')
html_end = text.rfind('</body></html>', label_start, close_idx)
if html_end < 0:
    raise SystemExit('Could not locate label HTML end')
barcode_script = '${code?`<script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.12.3/dist/JsBarcode.all.min.js"></script><script>window.addEventListener("load",function(){try{var el=document.getElementById("cdcBarcode");if(el&&window.JsBarcode){JsBarcode(el,el.getAttribute("data-code"),{format:"CODE128",displayValue:false,height:46,margin:0,width:1.6});}}catch(e){}});</script>`:""}'
text = text[:html_end] + barcode_script + text[html_end:]
# Give the barcode library a little more time to render before the print dialog.
label_start = text.find('function printLabel(name,kind,days,allergens,expiryUnit=')
close_idx = text.find('w.document.close();', label_start)
print_end = text.find('}', close_idx)
segment = text[label_start:print_end+1]
segment = segment.replace('setTimeout(()=>w.print(),300)', 'setTimeout(()=>w.print(),700)', 1)
text = text[:label_start] + segment + text[print_end+1:]

stock_wrapper = r'''
/* ---------- STOCK BARCODE / QR LOOKUP ---------- */
(function(){
  const originalStockView=VIEWS.stock;
  if(typeof originalStockView!=="function" || VIEWS.stock._cdcScanWrapped)return;
  function renderStockScanCard(v){
    STATE.settings=STATE.settings||{};
    STATE.settings.labelCodes=STATE.settings.labelCodes||{};
    const card=el("div",{class:"card"});
    const result=el("div",{class:"muted",style:"margin-top:10px;font-size:13px"},"Scan a linked barcode or QR code to find a stock item.");
    const btn=el("button",{class:"btn primary",type:"button",html:icon("label")+"Scan stock barcode / QR"});
    const manual=el("input",{class:"inp mono",placeholder:"Or enter / scan code",style:"max-width:280px"});
    const go=raw=>{
      raw=String(raw||manual.value||'').trim();
      if(!raw)return;
      manual.value=raw;
      const s=cdcStockByCode(raw);
      result.innerHTML="";
      if(!s){
        const msg=el("div",{class:"docket due"});
        const body=el("div",{style:"flex:1"});
        body.append(el("div",{class:"dk-t"},"Code not linked"),el("div",{class:"dk-s"},raw+" — choose a stock item to link it."));
        const sel=el("select",{class:"inp",style:"margin-top:8px"},el("option",{value:""},"— choose stock item —"),...(STATE.stock||[]).map(x=>el("option",{value:x.id},x.item||x.name||x.id)));
        const link=el("button",{class:"btn sm primary",style:"margin-top:8px",html:"Link code",onclick:()=>{
          const item=(STATE.stock||[]).find(x=>x.id===sel.value);
          if(!item){toast("Choose a stock item","warn");return;}
          cdcEnsureStockCode(item,raw);
          STATE.settings.labelCodes[raw]={name:item.item||item.name||"",stockId:item.id,updatedAt:nowISO()};
          audit("stock_barcode_link",(item.item||item.name||item.id)+" · "+raw);
          save("stock barcode link");
          toast("Code linked to "+(item.item||item.name||"stock item"),"ok");
          go(raw);
        }});
        body.append(sel,link); msg.append(body); result.append(msg); return;
      }
      const box=el("div",{class:"docket done"});
      const info=el("div",{style:"flex:1"});
      info.append(el("div",{class:"dk-t"},s.item||s.name||"Stock item"));
      info.append(el("div",{class:"dk-s"},"Code "+raw+" · Current "+(+s.qty||0)+" "+(s.unit||"")));
      const q=el("input",{class:"inp num",type:"number",step:"any",value:String(s.qty==null?"":s.qty),style:"max-width:120px;margin-top:8px"});
      const saveBtn=el("button",{class:"btn sm primary",style:"margin-top:8px;margin-left:8px",html:"Save actual stock",onclick:()=>{
        const val=Number(q.value);
        if(!Number.isFinite(val)){toast("Enter a valid stock quantity","warn");return;}
        s.qty=val;
        cdcEnsureStockCode(s,raw);
        STATE.settings.labelCodes[raw]={name:s.item||s.name||"",stockId:s.id,updatedAt:nowISO()};
        audit("stock_barcode_count",(s.item||s.name||s.id)+" = "+val+" "+(s.unit||""));
        save("stock barcode count");
        toast("Actual stock updated","ok");
        rerender();
      }});
      info.append(q,saveBtn); box.append(info); result.append(box);
    };
    btn.addEventListener("click",()=>scanLabelCode(go));
    manual.addEventListener("keydown",e=>{if(e.key==="Enter")go(manual.value);});
    card.append(el("div",{class:"card-head"},el("h3",{},"Barcode / QR stock lookup")));
    card.append(el("div",{style:"display:flex;gap:8px;align-items:center;flex-wrap:wrap"},btn,manual),result);
    v.append(card);
  }
  VIEWS.stock=function(v){
    renderStockScanCard(v);
    originalStockView(v);
  };
  VIEWS.stock._cdcScanWrapped=true;
})();
'''
text += stock_wrapper

path.write_text(text, encoding='utf-8')
print('Labels upgraded: Frozen defaults to 3 months; printed CODE128 barcodes link to stock; Stock can scan barcode/QR and update actual quantity')
