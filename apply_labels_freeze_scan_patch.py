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
    const wanted=['qr_code','ean_13','ean_8','code_128','upc_a','upc_e','data_matrix','itf','codabar'];
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
VIEWS.labels=function(v){
  STATE.settings=STATE.settings||{};
  STATE.settings.labelCodes=STATE.settings.labelCodes||{};
  const card=el("div",{class:"card"});
  card.append(el("div",{class:"card-head"},el("h3",{},"Print a label")));
  card.insertAdjacentHTML("beforeend",`<p class="muted" style="font-size:12.5px;margin:-6px 0 12px">Date &amp; use-by labels for prepped, opened, chilled or frozen food. Frozen defaults to 3 months and can be adjusted if the product needs a different shelf life.</p>`);
  const dish=el("select",{class:"inp"},el("option",{value:""},"— choose a dish —"),...STATE.recipes.map(r=>el("option",{value:r.id},r.name)));
  const name=el("input",{class:"inp",placeholder:"Or type an item name"});
  const life=el("input",{class:"inp num",type:"number",min:"1",value:"2",style:"max-width:90px"});
  const unit=el("select",{class:"inp",style:"max-width:130px"},el("option",{value:"days"},"days"),el("option",{value:"months"},"months"));
  const kind=el("select",{class:"inp"},...["Prepped","Opened","Defrosted","Cooked & chilled","Frozen"].map(k=>el("option",{},k)));
  const code=el("input",{class:"inp mono",placeholder:"Barcode / QR code (optional)"});
  const scan=el("button",{class:"btn ghost",type:"button",html:icon("label")+"Scan barcode / QR"});
  const resolveCode=raw=>{
    raw=String(raw||'').trim(); if(!raw)return;
    code.value=raw;
    const mapped=STATE.settings.labelCodes[raw];
    const byCode=x=>x&&[x.barcode,x.qr,x.code,x.sku,x.id].some(v=>v!=null&&String(v)===raw);
    const recipe=STATE.recipes.find(byCode);
    const stock=STATE.stock.find(byCode);
    if(mapped){
      name.value=mapped.name||name.value;
      if(mapped.recipeId&&STATE.recipes.some(r=>r.id===mapped.recipeId)){dish.value=mapped.recipeId;}
      toast("Code recognised — label details filled in","ok");
    }else if(recipe){
      dish.value=recipe.id; name.value=recipe.name||name.value; toast("Recipe recognised","ok");
    }else if(stock){
      name.value=stock.item||stock.name||name.value; toast("Stock item recognised","ok");
    }else{
      toast("Code captured — enter the item name once and it will be remembered","ok");
    }
  };
  scan.addEventListener("click",()=>scanLabelCode(resolveCode));
  dish.addEventListener("change",()=>{const r=STATE.recipes.find(x=>x.id===dish.value);if(r)name.value=r.name;});
  kind.addEventListener("change",()=>{
    if(kind.value==="Frozen"){life.value="3";unit.value="months";}
    else if(unit.value==="months"){life.value="2";unit.value="days";}
  });
  const lifeRow=el("div",{style:"display:flex;gap:8px;align-items:center"},life,unit);
  const codeRow=el("div",{style:"display:flex;gap:8px;align-items:center;flex-wrap:wrap"}); codeRow.append(code,scan);
  card.append(el("div",{class:"grid g2"},lf("Dish (optional)",dish),lf("Item name",name)),
    el("div",{class:"grid g2",style:"margin-top:2px"},lf("Label type",kind),lf("Use within",lifeRow)),
    el("div",{style:"margin-top:10px"},lf("Barcode / QR (optional)",codeRow)));
  card.append(el("div",{style:"display:flex;justify-content:flex-end;margin-top:12px"},el("button",{class:"btn primary",html:icon("print")+"Preview & print",onclick:()=>{
    const nm=name.value.trim()||"(item)"; const r=STATE.recipes.find(x=>x.id===dish.value); const raw=code.value.trim();
    if(raw&&nm!=="(item)"){
      STATE.settings.labelCodes[raw]={name:nm,recipeId:dish.value||"",updatedAt:nowISO()};
      save("label code mapping");
    }
    printLabel(nm,kind.value,+life.value||1,r?r.allergens:"",unit.value,raw);
  }})));
  v.append(card);
};
function printLabel(name,kind,days,allergens,expiryUnit="days",code=""){'''

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

# Add the captured code as traceability text on the printed label, without changing
# the existing allergen/date layout.
needle = '    <div class="k">${esc(kind)}</div><h1>${esc(name)}</h1>'
replacement2 = '    <div class="k">${esc(kind)}</div><h1>${esc(name)}</h1>${code?`<div class="k" style="margin-bottom:4px">Code: ${esc(code)}</div>`:""}'
if needle not in text:
    raise SystemExit('Could not locate printed label heading')
text = text.replace(needle, replacement2, 1)

path.write_text(text, encoding='utf-8')
print('Labels upgraded: Frozen defaults to 3 months; barcode/QR camera scanning and remembered code mappings enabled')
