"""Add separate chilled/frozen readings and a shared supplier picker.

No database mutations at build time. Existing single-temp delivery records stay
untouched and are clearly labelled as unspecified-type legacy readings.
"""
from pathlib import Path

main=Path("app/main_app.js")
index=Path("app/index.html")
s=main.read_text(encoding="utf-8")
start=s.find("VIEWS.deliveries=function(v){")
end=s.find("\nfunction lf(label,node)",start)
if start<0 or end<=start or s.count("VIEWS.deliveries=function(v){")!=1:
    raise SystemExit("Cannot uniquely locate original Deliveries view")

helper="""
function cdcSupplierNames(){
  const names=new Map();
  function add(raw){
    const value=String(raw||"").trim(),k=value.toLowerCase();
    if(value&&k!=="other"&&!names.has(k))names.set(k,value);
  }
  (STATE.suppliers||[]).forEach(x=>add(x&&x.name));
  (STATE.contacts||[]).filter(x=>String(x&&x.category||"").trim().toLowerCase()==="supplier")
    .forEach(x=>add(x.company||x.name));
  (STATE.stock||[]).forEach(x=>add(x&&x.supplier));
  return [...names.values()].sort((a,b)=>a.localeCompare(b));
}
"""
if "function cdcSupplierNames()" in s:raise SystemExit("Supplier helper already installed")
s=s[:start]+helper+s[start:]
start=s.index("VIEWS.deliveries=function(v){")
end=s.find("\nfunction lf(label,node)",start)
view=s[start:end]

def one(old,new,reason):
    global view
    if view.count(old)!=1:raise SystemExit(reason+": "+str(view.count(old)))
    view=view.replace(old,new,1)

old='''  const sup=el("select",{class:"inp"},...STATE.suppliers.map(s=>el("option",{},s.name)),el("option",{},"Other"));
  const temp=el("input",{class:"inp num mono",type:"number",step:"0.1",placeholder:"°C on arrival"});
  const note=el("input",{class:"inp",placeholder:"Notes (condition, damage…)"});'''
new='''  const sup=el("select",{class:"inp"});
  function refreshSupplierChoices(preferred){
    const keep=preferred||sup.value;
    sup.replaceChildren();
    const names=cdcSupplierNames();
    sup.append(el("option",{value:""},"Choose a supplier…"));
    names.forEach(name=>sup.append(el("option",{value:name},name)));
    sup.append(el("option",{value:"Other"},"Other / not listed"));
    sup.value=names.includes(keep)||keep==="Other"?keep:"";
  }
  refreshSupplierChoices("");
  const addSupplier=el("button",{class:"btn ghost sm",type:"button",html:icon("plus")+"Add supplier",onclick:()=>{
    const b=el("div",{});
    const name=el("input",{class:"inp",type:"text",placeholder:"e.g. your food wholesaler",maxlength:"120"});
    b.append(lf("Supplier company name",name));
    const m=modal({title:"Add a supplier",body:b,footer:[
      el("button",{class:"btn ghost",type:"button",html:"Cancel",onclick:()=>m.close()}),
      el("button",{class:"btn primary",type:"button",html:"Save supplier",onclick:()=>{
        const value=name.value.trim();
        if(!value){toast("Enter a supplier name","warn");name.focus();return;}
        const existing=cdcSupplierNames().find(x=>x.toLowerCase()===value.toLowerCase());
        if(existing){refreshSupplierChoices(existing);m.close();toast("Supplier already exists","ok");return;}
        if(!Array.isArray(STATE.suppliers))STATE.suppliers=[];
        STATE.suppliers.push({id:uid("sup"),name:value,contact:"",items:""});
        if(!Array.isArray(STATE.contacts))STATE.contacts=[];
        if(!STATE.contacts.some(c=>String(c.category||"").toLowerCase()==="supplier"&&String(c.company||c.name||"").trim().toLowerCase()===value.toLowerCase())){
          STATE.contacts.push({id:uid("ct"),name:"",company:value,category:"Supplier",phone:"",mobile:"",email:"",accountRef:"",notes:"",priority:false,stockIds:[],equipmentIds:[],createdAt:nowISO()});
        }
        save("add supplier");
        refreshSupplierChoices(value);
        m.close();
        toast("Supplier added for Deliveries, Stock and Contacts","ok");
      }})
    ]});
    name.focus();
  }});
  const supplierBox=el("div",{style:"display:flex;gap:8px;align-items:center;flex-wrap:wrap"});
  sup.style.flex="1 1 160px";
  supplierBox.append(sup,addSupplier);
  const chilledTemp=el("input",{class:"inp num mono",type:"number",step:"0.1",inputmode:"decimal",placeholder:"e.g. 3.8",id:"cdc-delivery-chilled"});
  const frozenTemp=el("input",{class:"inp num mono",type:"number",step:"0.1",inputmode:"decimal",placeholder:"e.g. -18.5",id:"cdc-delivery-frozen"});
  const note=el("input",{class:"inp",placeholder:"Notes (condition, damage…)"});'''
one(old,new,"Supplier and original Temperature fields")
one('''    lf("Supplier",sup),lf("Temperature",temp),lf("Notes",note),''',
    '''    lf("Supplier",supplierBox),lf("Chilled temperature (°C)",chilledTemp),
    lf("Frozen temperature (°C)",frozenTemp),lf("Notes",note),''',"Delivery fields")
one('''  card.append(form);
  // received items''',
    '''  card.append(form);
  card.append(el("div",{class:"muted",style:"font-size:12px;margin-top:8px;line-height:1.45"},
    "Record the actual chilled and/or frozen goods-in temperatures for this supplier. Leave either blank if it does not apply or was not measured."));
  // received items''',"Goods-in guidance")
one('''STATE.stock.filter(s=>+s.qty< +s.par).forEach(s=>{if(!lines.some(l=>l.stockId===s.id))lines.push({stockId:s.id,qty:Math.ceil(+s.par-+s.qty)});});''',
    '''STATE.stock.filter(s=>s.qtyKnown===true&&+s.par>0&&+s.qty< +s.par).forEach(s=>{if(!lines.some(l=>l.stockId===s.id))lines.push({stockId:s.id,qty:Math.ceil(+s.par-+s.qty)});});''',
    "Restrict quick restock to actually counted items")
one('''  function logDelivery(status){
    STATE.deliveries.unshift({id:uid("d"),ts:nowISO(),supplier:sup.value,temp:temp.value===""?null:+temp.value,status,by:ME.username,note:note.value,photo,items:lines.slice()});
    let added=0;''',
    '''  function logDelivery(status){
    if(!sup.value){toast("Choose or add a supplier first","warn");return;}
    function readTemperature(inp,label){
      if(inp.validity&&inp.validity.badInput)throw new Error(label+" must be a number");
      const raw=String(inp.value||"").trim();
      if(!raw)return null;
      const n=Number(raw);
      if(!Number.isFinite(n)||n < -60||n > 120)throw new Error(label+" must be a valid temperature");
      return Math.round(n*10)/10;
    }
    let chilled=null,frozen=null;
    try{
      chilled=readTemperature(chilledTemp,"Chilled temperature");
      frozen=readTemperature(frozenTemp,"Frozen temperature");
    }catch(e){toast(e.message,"warn");return;}
    STATE.deliveries.unshift({id:uid("d"),ts:nowISO(),supplier:sup.value,
      temp:null,chilledTemp:chilled,frozenTemp:frozen,status,by:ME.username,
      note:note.value,photo,items:lines.slice()});
    let added=0;''',
    "Dual temperature save")

# Replace only the Delivery-history temperature column. Older one-value
# records stay unclassified rather than being misidentified as chilled.
lines=view.splitlines(keepends=True)
positions=[i for i,line in enumerate(lines) if '{key:"temp",label:"°C",render:d=>' in line]
if len(positions)!=1:raise SystemExit("Delivery history old column not found once")
lines[positions[0]]='''     {key:"temp",label:"Chilled / Frozen",render:d=>{
       const hasDual=Object.prototype.hasOwnProperty.call(d,"chilledTemp")||Object.prototype.hasOwnProperty.call(d,"frozenTemp");
       const parts=[];
       if(hasDual){
         if(d.chilledTemp!=null)parts.push("Chilled: "+Number(d.chilledTemp).toFixed(1)+"°C");
         if(d.frozenTemp!=null)parts.push("Frozen: "+Number(d.frozenTemp).toFixed(1)+"°C");
       }else if(d.temp!=null){
         parts.push("Earlier reading (type unspecified): "+Number(d.temp).toFixed(1)+"°C");
       }
       return '<span class="cell readonly mono" style="white-space:normal;min-width:150px">'+esc(parts.join(" / ")||"—")+"</span>";
     },w:"230px"},\n'''
view=''.join(lines)
s=s[:start]+view+s[end:]

# Ensure supplier contacts are selectable from the Stock item editor as well.
needle='STATE.suppliers.map(x=>'
if s.count(needle)!=1:raise SystemExit("Stock supplier datalist changed")
pos=s.index(needle)
stop=s.find('.join("")',pos)
if stop<0 or stop-pos>240:raise SystemExit("Stock supplier datalist syntax changed")
sub=s[pos:stop]
sub=sub.replace('STATE.suppliers.map(x=>','cdcSupplierNames().map(name=>',1).replace('esc(x.name)','esc(name)',1)
s=s[:pos]+sub+s[stop:]

main.write_text(s,encoding="utf-8")
html=index.read_text(encoding="utf-8")
old='main_app.js?v=20261020-stock-mobile-repairs1'
if html.count(old)!=1:raise SystemExit("Expected production main app version absent")
index.write_text(html.replace(old,'main_app.js?v=20261020-dual-delivery-temp1',1),encoding="utf-8")
print("PASS: chilled/frozen deliveries and shared supplier picker installed")
