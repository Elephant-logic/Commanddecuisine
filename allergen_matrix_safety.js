/* Command de Cuisine - safe read-only allergen matrix with recipe drill-down */
(function(){
  'use strict';
  if(window.__cdcSafeAllergenMatrix) return;
  window.__cdcSafeAllergenMatrix=true;

  function text(el){ return String(el&&el.textContent||'').trim(); }
  function norm(v){ return String(v==null?'':v).toLowerCase().trim().replace(/\s+/g,' '); }
  function esc(v){ return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];}); }

  function allergenViewRoot(){
    var tables=[].slice.call(document.querySelectorAll('table'));
    for(var i=0;i<tables.length;i++){
      var t=tables[i];
      var s=String(t.textContent||'').toLowerCase();
      if(s.indexOf('gluten')>=0 && (s.indexOf('milk')>=0 || s.indexOf('dairy')>=0) && s.indexOf('egg')>=0){
        return {table:t,root:t.closest('.card,.panel,.section')||t.parentElement};
      }
    }
    var heads=[].slice.call(document.querySelectorAll('h1,h2,h3,h4,.section-title'));
    for(var j=0;j<heads.length;j++){
      if(/allergen\s+matrix/i.test(text(heads[j]))){
        var r=heads[j].closest('.card,.panel,.section')||heads[j].parentElement;
        var tb=r&&r.querySelector('table');
        if(tb) return {table:tb,root:r};
      }
    }
    return null;
  }

  function recipes(){
    try{return Array.isArray(STATE.recipes)?STATE.recipes:[];}catch(e){return [];}
  }
  function stocks(){
    try{return Array.isArray(STATE.stock)?STATE.stock:[];}catch(e){return [];}
  }
  function suppliers(){
    try{return Array.isArray(STATE.suppliers)?STATE.suppliers:[];}catch(e){return [];}
  }
  function recipeByName(name){
    var n=norm(name);
    if(!n) return null;
    var exact=recipes().filter(function(r){return norm(r&&r.name)===n;});
    return exact.length===1?exact[0]:null;
  }
  function recipeById(id){
    return recipes().find(function(r){return String(r&&r.id)===String(id);})||null;
  }

  function blockMatrixEdit(ev){
    var table=ev.currentTarget;
    if(!table || !table.contains(ev.target)) return;
    if(ev.target.closest && ev.target.closest('.cdc-allergen-dish-open')) return;
    ev.preventDefault();
    ev.stopPropagation();
    if(typeof ev.stopImmediatePropagation==='function') ev.stopImmediatePropagation();
  }

  function lockInteractiveControls(table){
    var nodes=table.querySelectorAll('input,button,select,textarea,[role="checkbox"],[role="switch"],label');
    for(var i=0;i<nodes.length;i++){
      var el=nodes[i];
      if(el.classList.contains('cdc-allergen-dish-open')) continue;
      el.setAttribute('aria-disabled','true');
      el.setAttribute('tabindex','-1');
      el.classList.add('cdc-allergen-locked-control');
    }
    if(!table.dataset.cdcAllergenLocked){
      table.dataset.cdcAllergenLocked='1';
      table.addEventListener('click',blockMatrixEdit,true);
      table.addEventListener('change',blockMatrixEdit,true);
      table.addEventListener('dblclick',blockMatrixEdit,true);
      table.addEventListener('contextmenu',blockMatrixEdit,true);
      table.addEventListener('keydown',function(ev){
        if((ev.key==='Enter'||ev.key===' ') && !(ev.target.closest&&ev.target.closest('.cdc-allergen-dish-open'))){ blockMatrixEdit(ev); }
      },true);
    }
  }

  function formatAllergens(value){
    if(value==null||value==='') return '';
    if(Array.isArray(value)) return value.map(String).filter(Boolean).join(', ');
    if(typeof value==='object'){
      return Object.keys(value).filter(function(k){return value[k]===true||value[k]==='yes'||value[k]===1;}).join(', ');
    }
    return String(value).trim();
  }

  function stockForIngredient(ing){
    if(!ing) return null;
    var all=stocks();
    if(ing.stockId!=null&&ing.stockId!==''){
      var explicit=all.find(function(s){return String(s&&s.id)===String(ing.stockId);});
      if(explicit) return explicit;
    }
    var n=norm(ing.name);
    var matches=all.filter(function(s){return norm(s&&(s.item||s.name))===n;});
    return matches.length===1?matches[0]:null;
  }

  function supplierForStock(stock){
    if(!stock) return null;
    var all=suppliers();
    if(stock.supplierId!=null){
      var byId=all.find(function(s){return String(s&&s.id)===String(stock.supplierId);});
      if(byId) return byId;
    }
    var name=stock.supplierName||stock.supplier||'';
    if(name){
      var byName=all.find(function(s){return norm(s&&(s.name||s.company))===norm(name);});
      if(byName) return byName;
    }
    return null;
  }

  function allergenSourceText(stock,ing){
    var candidates=[];
    if(ing) candidates.push(ing.allergens,ing.allergenDeclaration,ing.declaredAllergens);
    if(stock) candidates.push(stock.allergens,stock.supplierAllergens,stock.declaredAllergens,stock.allergenDeclaration,stock.allergenInfo);
    for(var i=0;i<candidates.length;i++){
      var t=formatAllergens(candidates[i]);
      if(t) return t;
    }
    return '';
  }

  function linkState(recipe,ing){
    var stock=stockForIngredient(ing);
    var supplier=supplierForStock(stock);
    var src=allergenSourceText(stock,ing);
    var stockName=stock&&(stock.item||stock.name)||'';
    var supplierName=supplier&&(supplier.name||supplier.company)||stock&&(stock.supplierName||stock.supplier)||'';
    return {stock:stock,stockName:stockName,supplierName:supplierName,allergens:src};
  }

  function closeInspector(){
    var old=document.getElementById('cdc-allergen-recipe-overlay');
    if(old) old.remove();
  }

  function showToast(msg,bad){
    try{if(typeof toast==='function') return toast(msg,bad?'bad':'ok');}catch(e){}
    console[bad?'warn':'info']('[Command de Cuisine] '+msg);
  }

  function findNavTarget(){
    var selectors=[
      '[data-route="recipes"]','[data-view="recipes"]','[data-nav="recipes"]',
      '[href="#recipes"]','[href="/recipes"]'
    ];
    for(var i=0;i<selectors.length;i++){
      var el=document.querySelector(selectors[i]);
      if(el) return el;
    }
    var nodes=[].slice.call(document.querySelectorAll('button,a,[role="button"]'));
    return nodes.find(function(el){return /^recipes$/i.test(text(el));})||null;
  }

  function invokeRoute(name){
    var helpers=['go','navigate','setRoute','routeTo','showView','openView'];
    for(var i=0;i<helpers.length;i++){
      try{
        var fn=window[helpers[i]];
        if(typeof fn==='function'){ fn(name); return true; }
      }catch(e){}
    }
    var nav=findNavTarget();
    if(nav){ try{nav.click();return true;}catch(e){} }
    try{
      var worked=Function('try{ROUTE="recipes";if(typeof rerender==="function")rerender();return true}catch(e){return false}')();
      if(worked) return true;
    }catch(e){}
    return false;
  }

  function clickRecipeEdit(recipe){
    var name=String(recipe&&recipe.name||'').trim();
    if(!name) return false;
    var candidates=[].slice.call(document.querySelectorAll('h1,h2,h3,h4,h5,strong,b,button,a,div,span'));
    var exact=candidates.filter(function(el){
      var t=text(el);
      return t===name && t.length<140;
    });
    for(var i=0;i<exact.length;i++){
      var node=exact[i];
      var box=node.closest('.card,.panel,.row,.item,.list-item,article,li')||node.parentElement;
      if(!box) continue;
      var controls=[].slice.call(box.querySelectorAll('button,a,[role="button"]'));
      var edit=controls.find(function(b){return /^(edit|edit recipe|modify)$/i.test(text(b));});
      if(edit){ edit.click(); return true; }
      var view=controls.find(function(b){return /^(view|open|recipe)$/i.test(text(b));});
      if(view){
        view.click();
        setTimeout(function(){
          var overlays=[].slice.call(document.querySelectorAll('[role="dialog"],.modal,.sheet,.overlay,.drawer'));
          for(var j=0;j<overlays.length;j++){
            if(norm(overlays[j].textContent).indexOf(norm(name))<0) continue;
            var eb=[].slice.call(overlays[j].querySelectorAll('button,a,[role="button"]')).find(function(b){return /edit/i.test(text(b));});
            if(eb){eb.click();break;}
          }
        },120);
        return true;
      }
      if(node.matches('button,a,[role="button"]')){ node.click(); return true; }
    }
    return false;
  }

  function openBuiltInEditor(recipe){
    closeInspector();

    var direct=[
      ['CDCRecipeEditor','open'],
      ['CDCRecipeEditor','edit'],
      ['recipeEditor','open']
    ];
    for(var i=0;i<direct.length;i++){
      try{
        var obj=window[direct[i][0]];
        var fn=obj&&obj[direct[i][1]];
        if(typeof fn==='function'){ fn.call(obj,recipe.id||recipe,recipe); return; }
      }catch(e){}
    }
    var fns=['editRecipe','openRecipeEditor','showRecipeEditor','openRecipe'];
    for(var j=0;j<fns.length;j++){
      try{
        if(typeof window[fns[j]]==='function'){ window[fns[j]](recipe,recipe.id); return; }
      }catch(e){}
    }

    invokeRoute('recipes');
    var tries=0;
    var timer=setInterval(function(){
      tries++;
      if(clickRecipeEdit(recipe)){
        clearInterval(timer);
        return;
      }
      if(tries>=12){
        clearInterval(timer);
        showToast('Opened Recipes. Find "'+recipe.name+'" and tap Edit.',false);
      }
    },160);
  }

  function ingredientRows(recipe){
    var list=Array.isArray(recipe&&recipe.ingredients)?recipe.ingredients:[];
    if(!list.length) return '<div class="cdc-allergen-empty">No ingredients are saved on this recipe yet.</div>';
    return list.map(function(ing){
      var link=linkState(recipe,ing||{});
      var qty=[ing&&ing.qty,ing&&ing.unit].filter(function(v){return v!=null&&String(v)!=='';}).join(' ');
      var status=link.stock
        ? '<span class="cdc-link-good">Linked to '+esc(link.stockName||'stock item')+'</span>'
        : '<span class="cdc-link-warn">Not linked to a stock item</span>';
      var supplier=link.supplierName?'<div class="cdc-allergen-meta">Supplier: '+esc(link.supplierName)+'</div>':'';
      var declared=link.allergens
        ? '<div class="cdc-allergen-meta"><strong>Linked allergen source:</strong> '+esc(link.allergens)+'</div>'
        : '<div class="cdc-allergen-meta muted">No linked supplier/stock allergen declaration available.</div>';
      return '<div class="cdc-allergen-ing">'+
        '<div class="cdc-allergen-ing-top"><strong>'+esc(ing&&ing.name||'Ingredient')+'</strong><span>'+esc(qty)+'</span></div>'+
        '<div>'+status+'</div>'+supplier+declared+
      '</div>';
    }).join('');
  }

  function openInspector(recipe){
    if(!recipe) return;
    closeInspector();
    var overlay=document.createElement('div');
    overlay.id='cdc-allergen-recipe-overlay';
    overlay.className='cdc-allergen-recipe-overlay';
    overlay.innerHTML=
      '<div class="cdc-allergen-recipe-modal" role="dialog" aria-modal="true" aria-label="Recipe allergen details">'+
        '<div class="cdc-allergen-recipe-head"><div><div class="cdc-allergen-kicker">Recipe & allergen sources</div><h3>'+esc(recipe.name||'Recipe')+'</h3></div><button type="button" class="btn ghost cdc-allergen-close">Close</button></div>'+
        '<div class="cdc-allergen-current"><strong>Recipe allergens</strong><div>'+esc(formatAllergens(recipe.allergens)||'None currently listed')+'</div></div>'+
        (recipe.allergenSyncStatus?'<div class="cdc-allergen-sync">Allergen sync: '+esc(recipe.allergenSyncStatus)+'</div>':'')+
        (recipe.stockLinkIssues&&recipe.stockLinkIssues.length?'<div class="cdc-allergen-warning">Some ingredients need their stock link checking before supplier allergen data can fully drive this recipe.</div>':'')+
        '<div class="cdc-allergen-section-title">Ingredients & links</div>'+
        '<div class="cdc-allergen-ingredients">'+ingredientRows(recipe)+'</div>'+
        '<div class="cdc-allergen-explain">Edit the recipe rather than the matrix. Saving the recipe updates the matrix from the recipe and its linked ingredient data.</div>'+
        '<div class="cdc-allergen-actions"><button type="button" class="btn ghost cdc-allergen-close2">Cancel</button><button type="button" class="btn primary cdc-allergen-edit-recipe">Edit recipe</button></div>'+
      '</div>';
    document.body.appendChild(overlay);
    overlay.querySelector('.cdc-allergen-close').onclick=closeInspector;
    overlay.querySelector('.cdc-allergen-close2').onclick=closeInspector;
    overlay.querySelector('.cdc-allergen-edit-recipe').onclick=function(){ openBuiltInEditor(recipeById(recipe.id)||recipe); };
    overlay.addEventListener('click',function(ev){if(ev.target===overlay) closeInspector();});
  }

  function decorateDishLinks(table){
    var rows=table.querySelectorAll('tbody tr');
    for(var i=0;i<rows.length;i++){
      var cell=rows[i].querySelector('td:first-child,th:first-child');
      if(!cell) continue;
      var existing=cell.querySelector('.cdc-allergen-dish-open');
      if(existing){
        var existingRecipe=recipeById(existing.dataset.recipeId);
        if(existingRecipe) existing.textContent=existingRecipe.name;
        continue;
      }
      var raw=cell.dataset.cdcDishName||text(cell);
      var recipe=recipeByName(raw);
      if(!recipe) continue;
      cell.dataset.cdcDishName=recipe.name;
      cell.innerHTML='';
      var b=document.createElement('button');
      b.type='button';
      b.className='cdc-allergen-dish-open';
      b.dataset.recipeId=recipe.id;
      b.textContent=recipe.name;
      b.setAttribute('aria-label','Open recipe '+recipe.name);
      b.addEventListener('click',function(ev){
        ev.preventDefault();ev.stopPropagation();
        var r=recipeById(this.dataset.recipeId);
        if(r) openInspector(r);
      });
      cell.appendChild(b);
    }
  }

  function addInfo(root,table){
    var note=root.querySelector('.cdc-allergen-safe-note');
    if(!note){
      note=document.createElement('div');
      note.className='cdc-allergen-safe-note';
      table.parentNode.insertBefore(note,table);
    }
    note.innerHTML='<div><strong>Matrix is view only</strong><span>Tap a dish name to see its recipe, linked ingredients and allergen sources. Edit the recipe there; the matrix updates automatically.</span></div>';
  }

  function wrapTable(table){
    if(table.parentElement && table.parentElement.classList.contains('cdc-allergen-scroll')) return table.parentElement;
    var wrap=document.createElement('div');
    wrap.className='cdc-allergen-scroll';
    table.parentNode.insertBefore(wrap,table);
    wrap.appendChild(table);
    return wrap;
  }

  function protect(){
    var found=allergenViewRoot();
    if(!found) return false;
    var table=found.table, root=found.root||table.parentElement;
    table.classList.add('cdc-allergen-safe-table');
    addInfo(root,table);
    wrapTable(table);
    decorateDishLinks(table);
    lockInteractiveControls(table);
    return true;
  }

  function css(){
    if(document.getElementById('cdc-allergen-safe-css')) return;
    var style=document.createElement('style');
    style.id='cdc-allergen-safe-css';
    style.textContent=
      '.cdc-allergen-safe-note{margin:0 0 12px;padding:12px 14px;border:1px solid var(--line,#3b4652);border-radius:12px;background:var(--panel2,#20262e);display:flex;gap:10px;align-items:flex-start}.cdc-allergen-safe-note strong{display:block;color:var(--text,#f4f5f7);font-size:13px;margin-bottom:2px}.cdc-allergen-safe-note span{display:block;color:var(--muted,#9ca6b3);font-size:12px;line-height:1.4}.cdc-allergen-scroll{overflow:auto;max-height:min(68vh,720px);overscroll-behavior:contain;-webkit-overflow-scrolling:touch;border:1px solid var(--line,#35404b);border-radius:12px}.cdc-allergen-safe-table{min-width:1050px;border-collapse:separate!important;border-spacing:0!important}.cdc-allergen-safe-table thead th{position:sticky!important;top:0!important;z-index:5!important;background:var(--panel,#1b2027)!important;box-shadow:0 1px 0 var(--line,#35404b);white-space:nowrap}.cdc-allergen-safe-table th:first-child,.cdc-allergen-safe-table td:first-child{position:sticky!important;left:0!important;z-index:4!important;background:var(--panel,#1b2027)!important;min-width:155px!important;max-width:190px!important;box-shadow:1px 0 0 var(--line,#35404b);text-align:left!important}.cdc-allergen-safe-table thead th:first-child{z-index:7!important}.cdc-allergen-safe-table th:not(:first-child),.cdc-allergen-safe-table td:not(:first-child){min-width:72px;text-align:center}.cdc-allergen-locked-control{pointer-events:none!important;cursor:default!important}.cdc-allergen-dish-open{appearance:none;border:0;background:transparent;color:var(--brass,#e6ab31);font:inherit;font-weight:800;text-align:left;padding:10px 8px;margin:-8px;width:calc(100% + 16px);cursor:pointer;text-decoration:underline;text-decoration-thickness:1px;text-underline-offset:3px}.cdc-allergen-safe-table tbody td{touch-action:pan-x pan-y}.cdc-allergen-recipe-overlay{position:fixed;inset:0;z-index:10040;background:rgba(0,0,0,.72);display:flex;align-items:flex-end;justify-content:center;padding:12px}.cdc-allergen-recipe-modal{width:min(720px,100%);max-height:92vh;overflow:auto;background:var(--card,#1c2229);border:1px solid var(--line,#35404b);border-radius:18px 18px 12px 12px;padding:16px;box-shadow:0 18px 60px rgba(0,0,0,.55)}.cdc-allergen-recipe-head{display:flex;align-items:flex-start;gap:12px;margin-bottom:14px}.cdc-allergen-recipe-head>div:first-child{flex:1}.cdc-allergen-recipe-head h3{margin:2px 0 0;font-size:24px}.cdc-allergen-kicker,.cdc-allergen-section-title{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted,#9ca6b3);font-weight:800}.cdc-allergen-current{padding:12px;border-radius:12px;background:var(--panel2,#20262e);border:1px solid var(--line,#35404b);margin-bottom:10px}.cdc-allergen-current strong{display:block;margin-bottom:4px}.cdc-allergen-sync,.cdc-allergen-warning,.cdc-allergen-explain{font-size:12px;line-height:1.45;color:var(--muted,#9ca6b3);margin:8px 0}.cdc-allergen-warning{padding:10px;border:1px solid var(--warn,#d99b2b);border-radius:10px;color:var(--text,#f4f5f7)}.cdc-allergen-section-title{margin:16px 0 8px}.cdc-allergen-ingredients{display:grid;gap:8px}.cdc-allergen-ing{padding:11px 12px;border:1px solid var(--line,#35404b);border-radius:11px;background:var(--panel2,#20262e)}.cdc-allergen-ing-top{display:flex;justify-content:space-between;gap:12px;margin-bottom:6px}.cdc-allergen-ing-top span{color:var(--muted,#9ca6b3)}.cdc-link-good{color:var(--ok,#48b875);font-size:12px;font-weight:700}.cdc-link-warn{color:var(--warn,#d99b2b);font-size:12px;font-weight:700}.cdc-allergen-meta{font-size:12px;color:var(--muted,#9ca6b3);margin-top:4px}.cdc-allergen-meta strong{color:var(--text,#f4f5f7)}.cdc-allergen-empty{padding:16px;text-align:center;color:var(--muted,#9ca6b3);border:1px dashed var(--line,#35404b);border-radius:10px}.cdc-allergen-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:16px}.cdc-allergen-safe-table tbody tr:active td{background:inherit!important}@media(max-width:620px){.cdc-allergen-scroll{max-height:62vh;margin-left:-4px;margin-right:-4px}.cdc-allergen-safe-table{min-width:980px}.cdc-allergen-safe-table th:first-child,.cdc-allergen-safe-table td:first-child{min-width:135px!important;max-width:155px!important}.cdc-allergen-safe-table th:not(:first-child),.cdc-allergen-safe-table td:not(:first-child){min-width:66px;font-size:12px}.cdc-allergen-safe-note{margin-bottom:10px}.cdc-allergen-recipe-modal{max-height:94vh;padding:14px}.cdc-allergen-actions{position:sticky;bottom:-14px;background:var(--card,#1c2229);padding:12px 0 4px}}';
    document.head.appendChild(style);
  }

  function wrapView(){ return false; }

  function start(){
    css();

    // Do not wrap VIEWS.allergens. The Allergen tab owns its own render lifecycle,
    // and wrapping it can destabilise the view on mobile. Protect the rendered
    // matrix afterwards instead, and never let a protection error escape.
    var timer=0;
    function safeProtect(){
      clearTimeout(timer);
      timer=setTimeout(function(){
        try{ protect(); }
        catch(err){ console.warn('[Command de Cuisine] allergen matrix protection skipped',err); }
      },80);
    }

    safeProtect();
    var obs=new MutationObserver(function(){ safeProtect(); });
    obs.observe(document.documentElement,{childList:true,subtree:true});
    setTimeout(safeProtect,300);
    console.info('[Command de Cuisine] Allergen matrix protected post-render; tab renderer left untouched');
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();