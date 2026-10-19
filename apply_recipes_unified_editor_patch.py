"""Expose the existing verified recipe/ingredient workspace directly in Recipes.

Patch only the assembled Recipes card view, retaining its legacy details/pricing
editor as a separate action. No data writes, auth modifications, or state changes.
"""
from pathlib import Path
import re

path=Path('app/main_app.js')
index=Path('app/index.html')
if not path.is_file() or not index.is_file():
    raise SystemExit('The assembled app is missing. Run this patch after production build.')

text=path.read_text(encoding='utf-8')
start=text.find('VIEWS.recipes=function(v){')
end=text.find('\nfunction editRecipe(r){',start)
if start<0 or end<=start:
    raise SystemExit('Cannot locate unique Recipes view and legacy details editor')
view=text[start:end]
old_click='    c.addEventListener("click",()=>editRecipe(r));'
new_click="""    c.addEventListener("click",()=>{
      const workspace=window.CDCRecipeWorkspace;
      if(workspace&&typeof workspace.open==="function")workspace.open(r.id);
      else editRecipe(r);
    });"""
if view.count(old_click)!=1:
    raise SystemExit('Original recipe card click handler changed; manual review required')
view=view.replace(old_click,new_click,1)

old_append='    grid.append(c);'
new_append="""    // The same safe ingredient editor used from Allergens, not a second copy.
    const recipeActions=el("div",{class:"cdc-recipe-actions",style:"display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;padding-top:12px;border-top:1px solid var(--line,#35404b)"});
    function action(label,handler){
      const b=el("button",{class:"btn sm",type:"button",style:"min-height:42px;flex:1 1 155px;white-space:normal",html:label});
      b.addEventListener("click",e=>{e.preventDefault();e.stopPropagation();handler();});
      recipeActions.appendChild(b);
    }
    action("Edit ingredients & allergens",()=>{
      const workspace=window.CDCRecipeWorkspace;
      if(workspace&&typeof workspace.open==="function")workspace.open(r.id);
      else toast("Ingredient editor not available. Refresh Recipes and try again.","warn");
    });
    action("📷 Update from photo / notes",()=>{
      const importer=window.CDCRecipeImporter;
      if(importer&&typeof importer.open==="function")importer.open(r.id);
      else toast("Recipe photo / notes importer is not ready. Refresh Recipes and try again.","warn");
    });
    action("Edit dish details",()=>editRecipe(r));
    c.appendChild(recipeActions);
    grid.append(c);"""
if view.count(old_append)!=1:
    raise SystemExit('Original Recipes card render location changed; manual review required')
view=view.replace(old_append,new_append,1)
text=text[:start]+view+text[end:]
if 'window.CDCRecipeWorkspace' not in text or 'window.CDCRecipeImporter' not in text:
    raise SystemExit('Recipe editing entry points missing')
path.write_text(text,encoding='utf-8')

# Both entry points must already exist in the assembled build.
assembled=index.read_text(encoding='utf-8')
if 'window.CDCRecipeImporter' not in assembled or 'allergen_matrix_safety.js' not in assembled:
    raise SystemExit('Existing importer or allergen workspace is missing; cannot safely link Recipes.')
# The app shell caches scripts by URL. Force a new version for existing devices.
pattern=r'main_app\.js(?:\?v=[A-Za-z0-9._-]+)?'
if len(re.findall(pattern,assembled))!=1:
    raise SystemExit('Expected exactly one main application script reference')
fresh=re.sub(pattern,'main_app.js?v=20261019-recipes-unified1',assembled)
index.write_text(fresh,encoding='utf-8')
print('Recipes cards now open the Allergens ingredient editor and offer photo/notes and dish details actions')
