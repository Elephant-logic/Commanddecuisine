"""Desktop/phone browser regression for dual goods-in temperatures and suppliers.

Runs only against isolated sample data and the real assembled production
Deliveries function. Never uses kitchen credentials or the live database.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from functools import partial
import http.server
import json
from playwright.sync_api import sync_playwright

INITIAL={
    "suppliers":[],
    "contacts":[{"id":"ct1","category":"Supplier","company":"Cornwall Chilled","name":"Office"}],
    "stock":[
        {"id":"s1","item":"Butter","supplier":"Cornwall Chilled","qty":3,"par":8,"unit":"kg","qtyKnown":True},
        {"id":"s2","item":"Peas","supplier":"Frozen Choice","qty":0,"par":20,"unit":"kg","qtyKnown":False}
    ],
    "deliveries":[{"id":"old1","ts":"2026-10-10T10:00:00Z","supplier":"Older supplier",
                   "temp":2.8,"status":"accepted","items":[],"note":""}]
}
HTML='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font:16px system-ui;background:#141924;color:white;padding:10px}
.card{background:#202833;padding:12px;margin-bottom:10px;border:1px solid #506071;border-radius:10px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:650px){.grid{grid-template-columns:1fr}}
.btn,.inp,button,input,select{background:#253449;color:white;border:1px solid #667c94;border-radius:8px;padding:10px}
.f{display:block}.lab{display:block}.modal{position:fixed;inset:4%;background:#192231;padding:18px;border:2px solid #718496;z-index:100;overflow:auto}</style>
</head><body><main id="view"></main><div id="overlays"></div>
<script>
const STATE=__STATE__, ME={username:"chef",role:"manager"};
const VIEWS={};let saves=0;window.errorsCaptured=[];window.stockMoves=[];window.auditCalls=[];
function icon(){return ''}
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function uid(t){return t+'_'+Math.random().toString(36).slice(2)}
function nowISO(){return new Date().toISOString()}
function audit(...args){window.auditCalls.push(args)}
function save(reason){saves++}
function toast(msg,type){window.errorsCaptured.push({msg,type})}
function rerender(){}
function stockById(id){return STATE.stock.find(s=>s.id===id)}
function stockMove(id,qty,type,supplier){
 const s=stockById(id); if(!s)return false;
 s.qty+=qty;window.stockMoves.push({id,qty,type,supplier});return true;
}
function photoInput(handler){const e=document.createElement('input');e.type='file';e.style.display='none';return e}
function el(tag,attributes,...children){
 const e=document.createElement(tag);
 Object.entries(attributes||{}).forEach(([k,v])=>{
  if(k==='html')e.innerHTML=v;
  else if(k==='class')e.className=v;
  else if(k==='style')e.style.cssText=v;
  else if(k.startsWith('on')&&typeof v==='function')e.addEventListener(k.slice(2),v);
  else e.setAttribute(k,String(v))
 });
 children.forEach(child=>{if(child instanceof Node)e.appendChild(child);else if(child!=null&&child!=='')e.appendChild(document.createTextNode(String(child)))});
 return e;
}
function lf(title,node){return el('label',{class:'f'},el('span',{class:'lab'},title),node)}
function modal(args){
 const wrap=el('section',{class:'modal',role:'dialog'});
 wrap.append(el('h2',{},args.title),args.body);
 const actions=el('div',{class:'actions'});
 (args.footer||[]).forEach(e=>{if(e instanceof Node)actions.append(e)});
 wrap.append(actions);document.getElementById('overlays').append(wrap);
 return {close(){wrap.remove()}};
}
function sheet(cols,rows,opts){
 window.deliveryCols=cols;
 return el('div',{class:'sheet'},'Goods-in log '+rows.length+' records');
}
function fmtDate(ts){return String(ts).slice(0,10)}
function fmtTime(ts){return String(ts).slice(11,16)}
</script>
<script>__DELIVERIES__</script>
<script>VIEWS.deliveries(document.getElementById('view'))</script>
</body></html>'''

def run_case(browser,url,mobile=False):
    ctx=browser.new_context(viewport={"width":390,"height":844} if mobile else {"width":1180,"height":825},
                            is_mobile=mobile,has_touch=mobile)
    page=ctx.new_page()
    errors=[]
    page.on("pageerror",lambda x:errors.append(str(x)))
    page.goto(url)
    host=page.locator("#view")
    assert host.get_by_text("Log a delivery").count()==1
    assert host.locator("#cdc-delivery-chilled").count()==1
    assert host.locator("#cdc-delivery-frozen").count()==1
    assert host.get_by_role("button",name="Add supplier").count()==1
    opts=host.locator("select").first.locator("option")
    assert opts.count()==4,opts.all_text_contents()
    assert "Cornwall Chilled" in opts.all_text_contents()
    assert "Frozen Choice" in opts.all_text_contents()
    # Legacy one-temperature record stays unclassified, not silently 'chilled'.
    legacy=page.evaluate("""window.deliveryCols.find(x=>x.key==='temp').render(STATE.deliveries[0])""")
    assert "Earlier reading (type unspecified): 2.8°C" in legacy,legacy
    assert page.evaluate("saves")==0

    # Supplier Add saves only directory entries, does not log a delivery.
    host.get_by_role("button",name="Add supplier").click()
    dialog=page.get_by_role("dialog")
    dialog.get_by_placeholder("e.g. your food wholesaler").fill("New Food Wholesaler")
    dialog.get_by_role("button",name="Save supplier").click()
    assert dialog.count()==0
    assert page.evaluate("STATE.suppliers[0].name")=="New Food Wholesaler"
    assert page.evaluate("STATE.contacts.filter(x=>x.category==='Supplier').length")==2
    assert page.evaluate("STATE.deliveries.length")==1
    assert page.evaluate("window.stockMoves.length")==0
    assert page.evaluate("saves")==1
    assert host.locator("select").first.input_value()=="New Food Wholesaler"

    # No duplicate supplier entries if the spelling differs only by case.
    host.get_by_role("button",name="Add supplier").click()
    dialog=page.get_by_role("dialog")
    dialog.get_by_placeholder("e.g. your food wholesaler").fill("new food wholesaler")
    dialog.get_by_role("button",name="Save supplier").click()
    assert page.evaluate("STATE.suppliers.length")==1
    assert page.evaluate("STATE.contacts.length")==2
    assert page.evaluate("saves")==1

    host.locator("#cdc-delivery-chilled").fill("4.3")
    host.locator("#cdc-delivery-frozen").fill("-18.7")
    # Fill real goods-in stock line but do not post until Accept.
    host.locator("select").nth(1).select_option("s1")
    host.locator("input[type=number]").last.fill("2")
    host.get_by_role("button",name="Restock low stock").click()
    assert page.evaluate("STATE.stock[0].qty")==3
    assert page.evaluate("STATE.stock[1].qty")==0
    host.get_by_role("button",name="Accept delivery").click()
    assert page.evaluate("STATE.deliveries.length")==2
    d=page.evaluate("STATE.deliveries[0]")
    assert d["supplier"]=="New Food Wholesaler"
    assert d["chilledTemp"]==4.3 and d["frozenTemp"]==-18.7,d
    assert d["temp"] is None
    assert d["status"]=="accepted"
    assert d["by"]=="chef"
    assert len(page.evaluate("window.stockMoves"))==1
    assert page.evaluate("STATE.stock[0].qty")==8
    rendered=page.evaluate("""window.deliveryCols.find(x=>x.key==='temp').render(STATE.deliveries[0])""")
    assert "Chilled: 4.3°C" in rendered and "Frozen: -18.7°C" in rendered,rendered

    # A frozen-only or chilled-only delivery retains a truly empty second field.
    page.evaluate("document.getElementById('view').replaceChildren();VIEWS.deliveries(document.getElementById('view'))")
    host=page.locator("#view")
    host.locator("select").first.select_option("Cornwall Chilled")
    host.locator("#cdc-delivery-frozen").fill("-19.0")
    host.get_by_role("button",name="Reject").click()
    latest=page.evaluate("STATE.deliveries[0]")
    assert latest["chilledTemp"] is None and latest["frozenTemp"]==-19.0
    assert latest["status"]=="rejected"
    assert len(page.evaluate("window.stockMoves"))==1,"Rejected delivery changed stock"
    assert not errors,errors
    ctx.close()
    print("PASS "+("touchscreen phone" if mobile else "desktop")+
          ": supplier Contacts+Stock picker, add/dedup, separate chilled+frozen temps, goods-in audit, legacy entries")

def main():
    source=Path("app/main_app.js").read_text(encoding="utf-8")
    helper=source[source.index("function cdcSupplierNames(){"):source.index("VIEWS.deliveries=function(v){")]
    func=source[source.index("VIEWS.deliveries=function(v){"):source.index("\nfunction lf(label,node)",source.index("VIEWS.deliveries=function(v){"))]
    with TemporaryDirectory() as tmp:
        path=Path(tmp)
        html=HTML.replace("__STATE__",json.dumps(INITIAL)).replace("__DELIVERIES__",helper+func)
        (path/"index.html").write_text(html,encoding="utf-8")
        server=http.server.ThreadingHTTPServer(("127.0.0.1",0),partial(http.server.SimpleHTTPRequestHandler,directory=tmp))
        Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
                url=f"http://127.0.0.1:{server.server_port}/index.html"
                run_case(browser,url,False)
                run_case(browser,url,True)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

if __name__=="__main__":
    main()
