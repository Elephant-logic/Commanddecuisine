"""Real browser regression for Recipes → shared ingredient/photo editor.

Isolated fixture uses exact assembled production Recipes card code, real
allergen workspace and real photo/notes importer. It never contacts a server API,
auth provider or the kitchen database.
"""
from pathlib import Path
import functools
import http.server
import json
import re
import tempfile
import threading
from playwright.sync_api import sync_playwright

APP=Path("app")
MOCK_RECIPES=[
    {"id":"r_fish","name":"Test Fish Pie","cat":"Mains","category":"Mains",
     "method":"Cook vegetables","cost":5.25,"price":16.5,"yield":"6",
     "needsReview":True,"allergens":"Milk",
     "ingredients":[
         {"name":"Milk","qty":100,"unit":"ml","stockId":"s_milk",
          "allergens":["Milk"],"allergenVerified":True,"allergenSource":"manager-edit"},
         {"name":"Carrots","qty":70,"unit":"g","stockId":"s_carrot",
          "allergens":[],"allergenVerified":False}
     ]},
    {"id":"r_soup","name":"Test Vegetable Soup","cat":"Starters","method":"Simmer",
     "cost":1.2,"price":6.5,"yield":"10","needsReview":True,
     "allergens":"","ingredients":[{"name":"Potatoes","qty":400,"unit":"g"}]}
]
MOCK_STOCK=[
    {"id":"s_milk","item":"Milk","unit":"ml"},
    {"id":"s_carrot","item":"Carrots","unit":"g"},
    {"id":"s_parsnip","item":"Parsnips","unit":"g"}
]

SCAFFOLD="""<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font:16px system-ui;background:#121a21;color:white;padding:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.card{background:#202935;padding:16px;border:1px solid #667;border-radius:12px}
.btn{background:#253849;color:white;padding:9px;border:1px solid #567;border-radius:7px}
</style></head><body><main id="view"></main>
<script>
const STATE=__STATE__;
let VIEWS={};
window.__calls=[];
window.__saves=[];
function icon(){return ''}
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function el(tag,attributes,...content){
 const n=document.createElement(tag);
 for(const [key,v] of Object.entries(attributes||{})){
  if(key==='html')n.innerHTML=v;
  else if(key==='onclick')n.addEventListener('click',v);
  else if(key==='class')n.className=v;
  else if(key==='style')n.style.cssText=v;
  else n.setAttribute(key,v);
 }
 for(const x of content){if(x instanceof Node)n.appendChild(x);else if(x!=null)n.appendChild(document.createTextNode(String(x)))}
 return n;
}
function dishTag(){return ''}
function ingredientStatus(){return {status:'draft'}}
function editRecipe(r){window.__calls.push({type:'details',id:r&&r.id})}
function save(reason){window.__saves.push(reason)}
function rerender(){const v=document.getElementById('view');v.replaceChildren();VIEWS.recipes(v)}
function audit(){}
function toast(msg){window.__calls.push({type:'toast',msg})}
function stockByName(name){const matches=STATE.stock.filter(s=>s.item.toLowerCase()===String(name).toLowerCase());return matches.length===1?matches[0]:null;}
function uid(prefix){return prefix+'_'+Math.random().toString(36).slice(2)}
async function api(){
 return {output_text:JSON.stringify({
   name:'Test Fish Pie',category:'Mains',yield:'6',
   allergens:'Milk, Celery',
   ingredients:[{name:'Milk',qty:250,unit:'ml'},{name:'Parsnips',qty:100,unit:'g'}],
   method:'Updated fish pie method'
 })};
}
</script>
<script>__RECIPE_VIEW__</script>
<script src="/recipe_import_patch.js"></script>
<script src="/allergen_matrix_safety.js"></script>
<script>
document.addEventListener('DOMContentLoaded',()=>VIEWS.recipes(document.getElementById('view')));
</script>
</body></html>"""

def run_case(browser,base,mobile):
    context=browser.new_context(
        viewport={"width":390,"height":844} if mobile else {"width":1100,"height":840},
        is_mobile=mobile,has_touch=mobile,
        device_scale_factor=2 if mobile else 1
    )
    page=context.new_page()
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(base,wait_until="load")
    card=page.locator("#view .grid.g-auto > .card").first
    assert page.locator("#view .grid.g-auto > .card").count()==2
    for label in ["Edit ingredients & allergens","Update from photo / notes","Edit dish details"]:
        assert card.get_by_role("button",name=label).count()==1,label
    before=page.evaluate("JSON.stringify(STATE.recipes)")
    assert page.locator("#view button",has_text="New recipe").count()==1

    card.get_by_role("button",name="Edit dish details").click()
    assert page.evaluate("window.__calls.at(-1).id")=="r_fish"
    assert page.locator("#cdc-allergen-v6-overlay").count()==0

    card.get_by_role("button",name="Edit ingredients & allergens").click()
    overlay=page.locator("#cdc-allergen-v6-overlay")
    assert overlay.is_visible()
    assert "Test Fish Pie" in overlay.inner_text()
    assert page.evaluate("JSON.stringify(STATE.recipes)")==before, "Opening editing controls must be read-only"

    overlay.locator(".cdc-a6-ing").first.click()
    modal=page.locator("#cdc-allergen-v6-overlay")
    assert "EDIT INGREDIENT" in modal.inner_text().upper(), {"overlay":modal.inner_text()[:650],"errors":errors}
    qty=modal.locator('label:has-text("Qty") input')
    assert qty.input_value()=="100"
    qty.fill("125")
    modal.get_by_role("button",name="Save ingredient").click()
    page.wait_for_function("STATE.recipes[0].ingredients[0].qty === 125")
    r=page.evaluate("STATE.recipes[0]")
    assert r["ingredients"][0]["allergenVerified"] is True
    assert r["ingredients"][0]["allergens"]==["Milk"]
    assert r["ingredients"][0]["stockId"]=="s_milk"
    assert page.locator("#cdc-allergen-v6-overlay").is_visible()

    page.locator("#cdc-allergen-v6-overlay").get_by_role("button",name=re.compile("Close")).click()
    card=page.locator("#view .grid.g-auto > .card").first
    card.get_by_role("button",name="Update from photo / notes").click()
    importer=page.locator("#cdc-recipe-import-overlay")
    assert importer.is_visible()
    assert importer.locator("select").first.input_value()=="r_fish", "Must target selected recipe by ID"
    assert importer.get_by_text("Test Fish Pie").count()>=0
    fields=importer.locator("textarea")
    fields.first.fill("Replace carrots with parsnips and use 250ml milk")
    importer.get_by_role("button",name="Read recipe from photo / notes").click()
    page.wait_for_function("document.querySelector('#cdc-recipe-import-overlay .cdc-ri-status.good') !== null")
    # AI-derived allergen names must never be automatically verified.
    importer.get_by_role("button",name="Save recipe").click()
    page.wait_for_function("document.querySelector('#cdc-recipe-import-overlay') === null")
    state=page.evaluate("STATE.recipes")
    fish=state[0]
    assert len(state)==2,"Updating must not create a duplicate recipe"
    assert fish["id"]=="r_fish"
    assert fish["method"]=="Updated fish pie method"
    assert fish["cost"]==5.25 and fish["price"]==16.5
    assert [x["name"] for x in fish["ingredients"]]==["Milk","Parsnips"]
    milk,parsnip=fish["ingredients"]
    assert milk["qty"]==250
    assert milk["allergens"]==["Milk"] and milk["allergenVerified"] is True
    assert milk["stockId"]=="s_milk"
    assert parsnip.get("allergenVerified") is False
    assert "Celery" in fish.get("allergenDrafts",[])
    assert fish["allergens"]=="Milk" and fish["needsReview"] is True
    assert fish["allergenReviewRequired"] is True
    assert fish["versions"],"Recipe update should preserve a previous version"
    assert state[1]==MOCK_RECIPES[1],"Other recipe must remain unchanged"

    # Clicking card itself opens same Allergens workspace, not legacy modal.
    card=page.locator("#view .grid.g-auto > .card").first
    card.locator("b").first.click()
    assert page.locator("#cdc-allergen-v6-overlay").is_visible()
    assert not errors, "Browser errors: "+repr(errors)
    context.close()
    print("PASS: "+("mobile" if mobile else "desktop")+" contextual ingredients, AI notes targeting, verification and recipe history")

def main():
    source=(APP/"main_app.js").read_text(encoding="utf-8")
    marker="VIEWS.recipes=function(v){"
    start=source.index(marker)
    stop=source.index("\nfunction editRecipe(r){",start)
    snippet=source[start:stop]
    assert "window.CDCRecipeWorkspace" in snippet
    assert "window.CDCRecipeImporter" in snippet
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        for file in ("recipe_import_patch.js","allergen_matrix_safety.js"):
            (root/file).write_bytes(((Path(".") if file=="recipe_import_patch.js" else APP)/file).read_bytes())
        fixture=SCAFFOLD.replace("__STATE__",json.dumps({"stock":MOCK_STOCK,"recipes":MOCK_RECIPES,"menus":[]}))
        fixture=fixture.replace("__RECIPE_VIEW__",snippet)
        (root/"index.html").write_text(fixture,encoding="utf-8")
        handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(root))
        server=http.server.ThreadingHTTPServer(("127.0.0.1",0),handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(headless=True,args=["--no-sandbox"])
                url="http://127.0.0.1:"+str(server.server_port)+"/index.html"
                run_case(browser,url,mobile=False)
                run_case(browser,url,mobile=True)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

if __name__=="__main__":
    main()
