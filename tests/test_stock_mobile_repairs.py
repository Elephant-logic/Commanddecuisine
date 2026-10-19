"""Browser regression: Stock readiness, phone temperatures, and repair workflow.

Tests production-assembled JS excerpts in isolated fixtures; never changes
live stock, temperature or maintenance records.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from functools import partial
import json
import http.server
from playwright.sync_api import sync_playwright

FIXTURE='''<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font:16px system-ui;background:#12151b;color:white;padding:12px}
.card{background:#242936;padding:12px;margin:4px;border:1px solid #596477;border-radius:10px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:9px}
.btn,.inp,button{padding:6px;margin:3px;color:white;background:#39455a;border:1px solid #687993}
.muted{color:#b5bcc5}.tag{background:#31455d;padding:3px;border-radius:6px}</style></head>
<body><section id="host"></section>
<script>
const ME={username:"chef",role:"manager"};
const STATE=__STATE__;
const VIEWS={};
let stockView='list',stockSearch='',stockCat='all',tempTab='round',saves=0;
const STOCK_CATS=['Veg','Dairy','Other'];
function icon(){return ''}
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function el(tag,attrs,...children){
 const n=document.createElement(tag);
 for(const [k,v] of Object.entries(attrs||{})){
  if(k==='html')n.innerHTML=v;
  else if(k==='class')n.className=v;
  else if(k==='style')n.style.cssText=v;
  else if(['onclick','oninput','onchange'].includes(k))n.addEventListener(k.slice(2),v);
  else n.setAttribute(k,v);
 }
 children.forEach(c=>{
  if(c instanceof Node)n.appendChild(c);
  else if(c!=null&&c!=='')n.appendChild(document.createTextNode(String(c)));
 });
 return n;
}
function kpi(label,value,detail){return el('div',{class:'card'},label+': '+value+' '+(detail||''))}
function clamp(x,min,max){return Math.max(min,Math.min(max,x))}
function stockUnitLabel(u){return u||'each'}
function stockUnitStep(u){return ['kg','L'].includes(u)?0.1:1}
function stockFmtQty(n){return String(Number(n)||0)}
function stockQtyText(n,unit){return stockFmtQty(n)+' '+stockUnitLabel(unit)}
function stockShortfallSummary(items){return items.map(s=>s.item).join(',')||'Nothing to order'}
function stockById(id){return STATE.stock.find(x=>x.id===id)}
function stockByName(item){return STATE.stock.find(x=>x.item===item)}
function stockSheet(){return el('div',{},'SHEET_VIEW')}
function stockMovesView(){return el('div',{},'MOVES_VIEW')}
function draftOrder(){}
function editStock(){}
function sheet(){return el('div',{id:'desktop-temp-sheet'},'DESKTOP_TEMP_SHEET')}
function appById(id){return STATE.appliances.find(a=>a.id===id)}
function tempRecordResult(a,r){return r.equipmentStatus==='awaiting_repair'?'status':r.value>8?'danger':'ok'}
function tempReadingDisplay(r){return r.value==null?'Awaiting repair':r.value.toFixed(1)+'°C'}
function tempRecordStatusLabel(r){return r.equipmentStatus==='awaiting_repair'?'Awaiting repair':'Status'}
function fmtDate(ts){return String(ts).slice(0,10)}
function fmtTime(ts){return String(ts).slice(11,16)}
function save(){saves++}
function rerender(){const v=document.getElementById('host');if(!v)return;v.replaceChildren();if(window.currentView==='stock')VIEWS.stock(v);else if(window.currentView==='temps')VIEWS.temps(v);else if(window.currentView==='maintenance')VIEWS.maintenance(v);}
function toast(){}
function isMgr(){return ME.role==='manager'}
function uid(p){return p+'_test_'+Math.random().toString(36).slice(2)}
function nowISO(){return new Date().toISOString()}
function lf(label,node){return el('label',{},label,node)}
function tempRound(v){v.append(el('div',{},'TEMPERATURE ROUND'))}
function tempTrends(v){v.append(el('div',{},'TRENDS'))}
function tempProbes(v){v.append(el('div',{},'PROBES'))}
</script>
<script>__STOCK_VIEW__</script>
<script>__TEMP_HISTORY__</script>
<script>__TEMP_TABS__</script>
<script>__MAINTENANCE__</script>
</body></html>'''

INITIAL={
 "stock":[{"id":"u1","item":"Parsnips","cat":"Veg","unit":"kg","par":0,"qty":0,"qtyKnown":False,"supplier":""},
          {"id":"u2","item":"Milk","cat":"Dairy","unit":"L","par":0,"qty":0,"qtyKnown":False,"supplier":""},
          {"id":"c1","item":"Potatoes","cat":"Veg","unit":"kg","par":5,"qty":2,"qtyKnown":True,"supplier":"Supplier A"}],
 "tempReadings":[
     {"id":"t2","appId":"fridge2","value":None,"ts":"2026-10-19T16:00:00Z",
      "equipmentStatus":"awaiting_repair","notes":"Engineer not yet arrived","by":"chef"},
     {"id":"t3","appId":"fridge3","value":4.0,"ts":"2026-10-19T08:00:00Z",
      "equipmentStatus":"reading","notes":"","by":"chef"}],
 "appliances":[{"id":"fridge2","name":"Fridge 2"},{"id":"fridge3","name":"Fridge 3"}],
 "maintenance":[]
}

def snippets(source):
    def between(a,b):
        start=source.index(a);end=source.index(b,start)
        return source[start:end]
    stock_row=source.index("function stockRow(s){")
    stock_start=source.rfind("VIEWS.stock=function(v){",0,stock_row)
    stock_end=source.find("function stockMovesView(){",stock_row)
    assert stock_start>=0 and stock_end>stock_row,(stock_start,stock_row,stock_end)
    return {
      "__STOCK_VIEW__":source[stock_start:stock_end],
      "__TEMP_HISTORY__":between("function tempHistory(v){","function tempTrends(v){"),
      "__TEMP_TABS__":between("VIEWS.temps=function(v){","function tempRound(v){"),
      "__MAINTENANCE__":between("VIEWS.maintenance=function(v){","/* ---------- FRYER OIL")
    }

def run(browser,url,mobile):
    ctx=browser.new_context(viewport={"width":390,"height":850} if mobile else {"width":1150,"height":840},
                            is_mobile=mobile,has_touch=mobile)
    page=ctx.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url)
    page.evaluate("window.currentView='stock';VIEWS.stock(document.getElementById('host'))")
    host=page.locator("#host")
    assert "Stock catalogue readiness" in host.inner_text()
    assert "Counted 1/3" in host.inner_text()
    assert "Supplier assigned 1/3" in host.inner_text()
    assert "Not counted" in host.inner_text()
    assert host.get_by_text("Out",exact=True).count()==0, "Uncounted entries must not be stockouts"
    # The previously undefined step variable prevented Stock from rendering at all.
    assert len(errors)==0, errors
    page.evaluate("document.querySelectorAll('button.btn.ghost.icon.sm')[1].click()")
    item=page.evaluate("STATE.stock[0]")
    assert item["qtyKnown"] is True
    assert item["qty"]==0.1
    assert page.evaluate("saves")==1
    page.evaluate("document.getElementById('host').replaceChildren();VIEWS.stock(document.getElementById('host'))")
    assert "Counted 2/3" in host.inner_text()

    # Different screen sizes must use the appropriate temperature presentation.
    page.evaluate("document.getElementById('host').replaceChildren();tempHistory(document.getElementById('host'))")
    if mobile:
        assert host.locator(".cdc-mobile-temp-history").count()==1
        assert "Fridge 2" in host.inner_text()
        assert "Awaiting repair" in host.inner_text()
        assert "Engineer not yet arrived" in host.inner_text()
        assert host.locator("#desktop-temp-sheet").count()==0
    else:
        assert host.locator("#desktop-temp-sheet").count()==1
    before=page.evaluate("JSON.stringify(STATE.tempReadings)")
    page.evaluate("window.currentView='temps';document.getElementById('host').replaceChildren();tempTab='round';VIEWS.temps(document.getElementById('host'))")
    assert host.get_by_role("button",name="Repairs").count()==1
    host.get_by_role("button",name="Repairs").click()
    assert "Report an issue" in host.inner_text()
    assert page.evaluate("STATE.maintenance.length")==0,"Opening Repairs must not auto-create tickets"
    assert page.evaluate("JSON.stringify(STATE.tempReadings)")==before

    # Reuse the existing maintenance workflow rather than creating status readings.
    item=host.get_by_placeholder("Equipment / area")
    item.fill("Fridge 2")
    host.get_by_placeholder("What's wrong").fill("Out of order")
    host.get_by_placeholder("Action (if any)").fill("Engineer awaited")
    host.get_by_role("button",name="Log issue").click()
    latest=page.evaluate("STATE.maintenance[0]")
    assert latest["item"]=="Fridge 2" and latest["status"]=="open"
    assert latest["action"]=="Engineer awaited"
    assert page.evaluate("JSON.stringify(STATE.tempReadings)")==before
    page.evaluate("window.currentView='maintenance';document.getElementById('host').replaceChildren();VIEWS.maintenance(document.getElementById('host'))")
    assert host.get_by_role("button",name="Close",exact=True).count()==1

    # Staff can report faults, but only managers close tickets.
    page.evaluate("ME.role='staff';document.getElementById('host').replaceChildren();VIEWS.maintenance(document.getElementById('host'))")
    assert host.get_by_role("button",name="Close",exact=True).count()==0
    assert host.get_by_role("button",name="Log issue").count()==1
    assert not errors,errors
    ctx.close()
    print("PASS: "+("mobile" if mobile else "desktop")+" Stock counted flag, Repairs workflow, temperature card/table, no invented records")

def main():
    source=Path("app/main_app.js").read_text(encoding="utf-8")
    snippets_map=snippets(source)
    text=FIXTURE.replace("__STATE__",json.dumps(INITIAL))
    for k,v in snippets_map.items():text=text.replace(k,v)
    with TemporaryDirectory() as tmp:
        (Path(tmp)/"index.html").write_text(text,encoding="utf-8")
        srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),partial(http.server.SimpleHTTPRequestHandler,directory=tmp))
        Thread(target=srv.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(args=["--no-sandbox"])
                url=f"http://127.0.0.1:{srv.server_port}/index.html"
                run(browser,url,False)
                run(browser,url,True)
                browser.close()
        finally:
            srv.shutdown();srv.server_close()

if __name__=="__main__":
    main()
