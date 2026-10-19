"""Desktop/mobile browser check of legacy Recipes editing: Cancel is safe."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from functools import partial
import http.server
import json
from playwright.sync_api import sync_playwright

HTML='''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body><div id="host"></div>
<script>
const STATE=__STATE__, ME={username:'chef',role:'manager'};
let saved=0;
function uid(){return 'new_'+Math.random().toString(36).slice(2)}
function icon(){return ''}
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function $(selector){return document.querySelector(selector)}
function stockById(id){return STATE.stock.find(s=>s.id===id)||null;}
function save(){saved++}function rerender(){}function toast(){}
function el(tag,attrs,...children){
 const n=document.createElement(tag);
 for(const [k,v] of Object.entries(attrs||{})){
  if(k==='html')n.innerHTML=v;
  else if(k==='class')n.className=v;
  else if(k==='style')n.style.cssText=v;
  else if(k==='onclick')n.addEventListener('click',v);
  else n.setAttribute(k,v);
 }
 children.forEach(c=>{if(c instanceof Node)n.appendChild(c);else if(c!=null&&c!=='')n.appendChild(document.createTextNode(String(c)))});
 return n;
}
function modal(params){
 const overlay=document.createElement('div');
 overlay.className='modal';
 overlay.setAttribute('role','dialog');
 const heading=el('h2',{},params.title);
 overlay.appendChild(heading);
 overlay.appendChild(params.body);
 const actions=el('div',{class:'footer'});
 (params.footer||[]).forEach(n=>{if(n instanceof Node)actions.appendChild(n)});
 const result={close(){overlay.remove();}};
 const cancel=el('button',{type:'button','data-close':'1'},'Cancel edit');
 cancel.onclick=()=>result.close();
 actions.appendChild(cancel);
 overlay.appendChild(actions);
 document.getElementById('host').appendChild(overlay);
 return result;
}
</script>
<script>__EDITOR__</script></body></html>'''

INITIAL={
 "recipes":[{"id":"r1","name":"Fish pie","cat":"Mains","allergens":"Milk",
            "allergenVerified":True,"allergenReviewRequired":False,
            "allergenDrafts":[],"method":"Bake","cost":5.25,"price":14.50,
            "ingredients":[{"stockId":"s1","name":"Milk","qty":150,"unit":"ml","allergens":["Milk"],"allergenVerified":True},
                           {"stockId":"s2","name":"Carrots","qty":80,"unit":"g"}]}],
 "stock":[{"id":"s1","item":"Milk"},{"id":"s2","item":"Carrots"},{"id":"s3","item":"Parsnips"}]
}

def check(browser,url,mobile):
    context=browser.new_context(viewport={"width":390,"height":844} if mobile else {"width":1150,"height":820},
                                has_touch=mobile,is_mobile=mobile)
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda x: errors.append(str(x)))
    page.goto(url)
    before=page.evaluate("JSON.stringify(STATE.recipes[0])")
    page.evaluate("editRecipe(STATE.recipes[0])")
    overlay=page.get_by_role("dialog")
    assert overlay.is_visible()
    assert overlay.get_by_text("Allergen notes (draft",exact=False).count()==1
    overlay.locator(".chip button.x").first.click()
    assert page.evaluate("STATE.recipes[0].ingredients.length")==2, "Ingredient removed before Save!"
    overlay.locator("input#rn").fill("Renamed without saving")
    overlay.get_by_role("button",name="Cancel edit").click()
    assert page.evaluate("JSON.stringify(STATE.recipes[0])")==before
    assert page.evaluate("saved")==0

    # Modifying and saving the local draft commits exactly once.
    page.evaluate("editRecipe(STATE.recipes[0])")
    overlay=page.get_by_role("dialog")
    overlay.locator(".chip button.x").nth(1).click()
    overlay.locator("input#rn").fill("Fish pie updated")
    overlay.locator("input#ra").fill("Eggs, Celery")
    overlay.get_by_role("button",name="Save recipe").click()
    row=page.evaluate("STATE.recipes[0]")
    assert row["name"]=="Fish pie updated"
    assert len(row["ingredients"])==1
    assert row["ingredients"][0]["allergenVerified"] is True
    assert row["allergens"]=="Milk","Must not overwrite existing verified ingredient allergens"
    assert row["allergenDrafts"]==["Eggs","Celery"]
    assert row["allergenReviewRequired"] is True and row["needsReview"] is True
    assert page.evaluate("saved")==1

    # New recipes with free-text allergen notes must never be approved.
    page.evaluate("editRecipe()")
    overlay=page.get_by_role("dialog")
    overlay.locator("input#rn").fill("New sample dish")
    overlay.locator("input#ra").fill("Fish")
    overlay.get_by_role("button",name="Save recipe").click()
    second=page.evaluate("STATE.recipes[1]")
    assert second["name"]=="New sample dish"
    assert second["allergens"]==""
    assert second["allergenDrafts"]==["Fish"]
    assert second["needsReview"] is True
    assert page.evaluate("saved")==2
    assert not errors,errors
    context.close()
    print("PASS: "+("mobile" if mobile else "desktop")+" - recipe Cancel rolls back, Save commits, allergen notes remain drafts")

def main():
    source=Path("app/main_app.js").read_text(encoding="utf-8")
    start=source.index("function editRecipe(r){")
    end=source.index("\n/* ---------- REPORTS ---------- */",start)
    editor=source[start:end]
    with TemporaryDirectory() as tmp:
        folder=Path(tmp)
        (folder/"index.html").write_text(HTML.replace("__STATE__",json.dumps(INITIAL))
                                    .replace("__EDITOR__",editor),encoding="utf-8")
        srv=http.server.ThreadingHTTPServer(("127.0.0.1",0),partial(http.server.SimpleHTTPRequestHandler,directory=tmp))
        Thread(target=srv.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(args=["--no-sandbox"])
                url=f"http://127.0.0.1:{srv.server_port}/index.html"
                check(browser,url,False)
                check(browser,url,True)
                browser.close()
        finally:
            srv.shutdown();srv.server_close()

if __name__=="__main__":
    main()
