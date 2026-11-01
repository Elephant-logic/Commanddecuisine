"""Verify original (unchanged) Temperature gaps feature and server route.

Uses demo readings only in isolated browser fixtures; never writes live records.
"""
import ast
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from functools import partial
import http.server
from playwright.sync_api import sync_playwright

def verify_server():
    source=Path("app/server.py").read_text(encoding="utf-8")
    tree=ast.parse(source)
    assignments=[n for n in tree.body if isinstance(n,ast.Assign)
                 and any(isinstance(t,ast.Name) and t.id=="RUNTIME_FILES" for t in n.targets)]
    assert len(assignments)==1
    routes=ast.literal_eval(assignments[0].value)
    assert routes.count("/temperature_gap_fill.js")==1, "Original script not available via server's static routes"
    assert 'temperature_gap_fill.js?v=20261101-staticroute1' in source
    script=Path("app/temperature_gap_fill.js").read_text(encoding="utf-8")
    assert "Temperature gaps" in script and "Fill missing" in script
    assert "window.openTemperatureGapFill=fillGap" in script
    print("PASS: original gap-fill file routed and cache-busted, with original UI unchanged")

BASE='''<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font:15px system-ui;padding:10px;background:#101927;color:#eef2f8}
.card,.docket{border:1px solid #576578;border-radius:7px;padding:10px;margin-bottom:9px}
.btn,button{background:#3c556d;color:white;border:1px solid #7894ac;border-radius:5px;padding:7px}
</style></head><body><div id="view"></div>
<script>
const NativeDate=Date;
class FrozenDate extends NativeDate{
 constructor(...args){super(...(args.length?args:["2026-11-01T19:55:00Z"]))}
 static now(){return new NativeDate("2026-11-01T19:55:00Z").getTime()}
}
Date=FrozenDate;
const STATE=__STATE__;
const VIEWS={history:function(v){v.append(document.createTextNode("History"));}};
const launches=[];
function el(tag,attrs,...parts){
 const element=document.createElement(tag);
 for(const [key,val] of Object.entries(attrs||{})){
  if(key==="html")element.innerHTML=val;
  else if(key==="class")element.className=val;
  else if(key==="style")element.style.cssText=val;
  else if(key.startsWith("on")&&typeof val==="function")element.addEventListener(key.slice(2),val);
  else element.setAttribute(key,String(val));
 }
 parts.forEach(x=>{if(x instanceof Node)element.append(x);else if(x!=null)element.append(document.createTextNode(String(x)))});
 return element;
}
function icon(){return ""}
function isMgr(){return true}
function tempRecordHasValue(r){return !!r&&r.value!==null&&Number.isFinite(Number(r.value))}
function tempRecordLocalDay(r){return new Date(r.ts).toISOString().slice(0,10)}
function tempRecordPeriod(r){return String(r.period||"am").toLowerCase()}
function tempUnitOfflineForSlot(appId,date,period){return appId==="fridge2"}
function backfillRound(date,period){launches.push([date,period])}
function toast(){}
function modal(){return {close(){}}}
</script>
<script src="/temperature_gap_fill.js"></script>
<script>VIEWS.history(document.getElementById("view"))</script>
</body></html>'''

def fixture():
    apps=[{"id":f"fridge{i}","name":f"Fridge {i}","type":"fridge"} for i in (1,2,3)]
    apps.extend({"id":f"freezer{i}","name":f"Freezer {i}","type":"freezer"} for i in (1,2,3))
    apps.append({"id":"cold","name":"Cold Room","type":"fridge"})
    rows=[]
    for day,rounds in [("2026-10-30",["AM","PM"]),("2026-10-31",["AM"])]:
        for period in rounds:
            for a in apps:
                if a["id"]=="fridge2":
                    rows.append({"appId":"fridge2","ts":f"{day}T"+("09:00:00Z" if period=="AM" else "17:00:00Z"),
                                 "period":period,"equipmentStatus":"out_of_order","value":None})
                else:
                    rows.append({"appId":a["id"],"ts":f"{day}T"+("09:00:00Z" if period=="AM" else "17:00:00Z"),
                                 "period":period,"equipmentStatus":"reading","value":-18 if a["type"]=="freezer" else 4})
    return {"appliances":apps,"tempReadings":rows}

def test_browser():
    with TemporaryDirectory() as folder:
        root=Path(folder)
        (root/"index.html").write_text(BASE.replace("__STATE__",json.dumps(fixture())),encoding="utf-8")
        (root/"temperature_gap_fill.js").write_bytes(Path("app/temperature_gap_fill.js").read_bytes())
        server=http.server.ThreadingHTTPServer(("127.0.0.1",0),
                 partial(http.server.SimpleHTTPRequestHandler,directory=folder))
        Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(args=["--no-sandbox"])
                for is_mobile in (False,True):
                    ctx=browser.new_context(viewport={"width":390,"height":840} if is_mobile else {"width":1160,"height":840},
                                            is_mobile=is_mobile,has_touch=is_mobile)
                    page=ctx.new_page()
                    errors=[]
                    page.on("pageerror",lambda err:errors.append(str(err)))
                    page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
                    area=page.locator("#view")
                    assert area.get_by_text("Temperature gaps",exact=True).count()==1
                    assert "3 missing rounds" in area.inner_text()
                    assert area.get_by_role("button",name="Fill missing").count()==3
                    assert "2026-10-31 · PM" in area.inner_text()
                    assert "2026-11-01 · AM" in area.inner_text()
                    assert "2026-11-01 · PM" in area.inner_text()
                    assert "Fridge 2" not in area.inner_text(), "Out-of-order fridge must not generate missing numeric slots"
                    area.get_by_role("button",name="Fill missing").first.click()
                    assert page.evaluate("launches")==[["2026-10-31","pm"]]
                    assert not errors, errors
                    ctx.close()
                    print("PASS: original Temperature gaps and Fill missing work on "+("phone" if is_mobile else "desktop"))
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

if __name__=="__main__":
    verify_server()
    test_browser()
