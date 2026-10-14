/* Command de Cuisine - stable read-only allergen matrix + recipe ingredient workspace */
(function(){
  'use strict';
  if(window.__cdcRecipeIngredientWorkspaceV3) return;
  window.__cdcRecipeIngredientWorkspaceV3=true;

  var OVERLAY='cdc-recipe-workspace-overlay';
  var lastProtectedTable=null;
  var ALLERGEN_STATUS='Needs review after ingredient change';

  function s(v){return String(v==null?'':v);}
  function norm(v){return s(v).toLowerCase().trim().replace(/\s+/g,' ');}
  function esc(v){return s(v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function text(el){return s(el&&el.textContent).trim();}
  function recipes(){try{return Array.isArray(STATE.recipes)?STATE.recipes:[];}catch(e){return [];}}
  function stock(){try{return Array.isArray(STATE.stock)?STATE.stock:[];}catch(e){return [];}}
  function recipeById(id){return recipes().find(function(r){return String(r&&r.id)===String(id);})||null;}
  function recipeByName(name){
    var n=norm(name); if(!n)return null;
    var rows=recipes().filter(function(r){return norm(r&&r.name)===n;});
    return rows.length===1?rows[0]:null;
  }
  function stockName(row){return s(row&&(row.item||row.name||row.product||row.label)).trim();}
  function stockUnit(row){return s(row&&(row.unit||row.stockUnit||row.baseUnit||row.qtyUnit)).trim();}
  function stockQty(row){
    var keys=['actualQty','quantity','qty','onHand','currentQty','stock','amount'];
    for(var i=0;i<keys.length;i++){
      var n=Number(row&&row[keys[i]]);
      if(Number.isFinite(n))return n;
    }
    return null;
  }
  function stockById(id){return stock().find(function(x){return String(x&&x.id)===String(id);})||null;}
  function stockForIngredient(ing){
    if(!ing)return null;
    if(ing.stockId!=null&&ing.stockId!==''){
      var x=stockById(ing.stockId); if(x)return x;
    }
    var n=norm(ing.name);
    if(!n)return null;
    var matches=stock().filter(function(x){return norm(stockName(x))===n;});
    return matches.length===1?matches[0]:null;
  }

  function canonicalUnit(u){
    u=norm(u).replace(/litres?/,'l').replace(/liters?/,'l').replace(/millilitres?/,'ml').replace(/milliliters?/,'ml').replace(/kilograms?/,'kg').replace(/grams?/,'g').replace(/ounces?/,'oz');
    if(['each','ea','count','unit','units','piece','pieces'].indexOf(u)>=0)return 'each';
    return u;
  }
  function convertQty(q,from,to){
    q=Number(q); from=canonicalUnit(from); to=canonicalUnit(to);
    if(!Number.isFinite(q)||!from||!to)return null;
    if(from===to)return q;
    var grams={g:1,kg:1000,oz:28.349523125};
    if(grams[from]&&grams[to])return q*grams[from]/grams[to];
    var ml={ml:1,l:1000};
    if(ml[from]&&ml[to])return q*ml[from]/ml[to];
    if(from==='each'&&to==='each')return q;
    return null;
  }

  function purchasingLine(ing){
    var q=Number(ing&&ing.qty), u=s(ing&&ing.unit).trim();
    var st=stockForIngredient(ing);
    if(!st){
      return {kind:'unlinked',text:(Number.isFinite(q)&&q>0?q+' '+u+' required for one batch · ':'')+'not linked to Stock'};
    }
    var have=stockQty(st), su=stockUnit(st);
    if(have==null)return {kind:'linked',text:'Linked to '+stockName(st)+' · stock quantity not set'};
    var needInStockUnit=convertQty(q,u,su);
    if(needInStockUnit==null)return {kind:'linked',text:'Linked to '+stockName(st)+' · '+have+' '+su+' on hand · unit conversion needs review'};
    var short=Math.max(0,needInStockUnit-have);
    return short>0
      ?{kind:'short',text:'Linked to '+stockName(st)+' · order about '+round(short)+' '+su+' for one batch'}
      :{kind:'ok',text:'Linked to '+stockName(st)+' · enough on hand for one batch'};
  }
  function round(n){return String(Math.round(Number(n)*100)/100);}

  function formatAllergens(value){
    if(value==null||value==='')return '';
    if(Array.isArray(value))return value.map(String).filter(Boolean).join(', ');
    if(typeof value==='object')return Object.keys(value).filter(function(k){return value[k]===true||value[k]==='yes'||value[k]===1;}).join(', ');
    return String(value).trim();
  }

  function closeWorkspace(){
    var old=document.getElementById(OVERLAY);
    if(old)old.remove();
  }
  function notify(msg,bad){
    try{if(typeof toast==='function')return toast(msg,bad?'bad':'ok');}catch(e){}
    console[bad?'warn':'info']('[Command de Cuisine] '+msg);
  }

  function ingredientSummary(recipe){
    var items=Array.isArray(recipe&&recipe.ingredients)?recipe.ingredients:[];
    if(!items.length){
      return '<div class="cdc-rw-empty"><strong>No ingredients saved yet</strong><span>This recipe needs an ingredient list before stock requirements and supplier links can work.</span></div>';
    }
    return items.map(function(ing){
      var p=purchasingLine(ing||{});
      var st=stockForIngredient(ing);
      var qty=[ing&&ing.qty,ing&&ing.unit].filter(function(v){return v!=null&&s(v)!=='';}).join(' ');
      var prep=s(ing&&ing.preparation||ing&&ing.note).trim();
      return '<div class="cdc-rw-ing">'+
        '<div class="cdc-rw-ing-head"><strong>'+esc(ing&&ing.name||'Ingredient')+'</strong><span>'+esc(qty)+'</span></div>'+
        (prep?'<div class="cdc-rw-meta">'+esc(prep)+'</div>':'')+
        '<div class="cdc-rw-purchase '+esc(p.kind)+'">'+esc(p.text)+'</div>'+
        (st?'<div class="cdc-rw-meta">Stock link: '+esc(stockName(st))+'</div>':'')+
      '</div>';
    }).join('');
  }

  function showInspector(recipe){
    if(!recipe)return;
    closeWorkspace();
    var overlay=document.createElement('div');
    overlay.id=OVERLAY; overlay.className='cdc-rw-overlay';
    overlay.innerHTML=
      '<div class="cdc-rw-modal" role="dialog" aria-modal="true">'+
        '<div class="cdc-rw-head"><div><div class="cdc-rw-kicker">Recipe workspace</div><h3>'+esc(recipe.name||'Recipe')+'</h3></div><button type="button" class="btn ghost cdc-rw-close">Close</button></div>'+
        '<div class="cdc-rw-box"><strong>Recipe allergens</strong><div>'+esc(formatAllergens(recipe.allergens)||'None currently listed')+'</div>'+
          '<div class="cdc-rw-meta">The matrix is a summary of the recipe. Edit the recipe here, not the matrix.</div></div>'+
        '<div class="cdc-rw-section">Ingredients & purchasing</div>'+
        '<div class="cdc-rw-list">'+ingredientSummary(recipe)+'</div>'+
        '<div class="cdc-rw-actions"><button type="button" class="btn primary cdc-rw-edit">Edit recipe & ingredients</button></div>'+
      '</div>';
    document.body.appendChild(overlay);
    overlay.querySelector('.cdc-rw-close').onclick=closeWorkspace;
    overlay.querySelector('.cdc-rw-edit').onclick=function(){openEditor(recipeById(recipe.id)||recipe);};
    overlay.addEventListener('click',function(e){if(e.target===overlay)closeWorkspace();});
  }

  function field(label,input){
    var w=document.createElement('label');w.className='cdc-rw-field';
    var t=document.createElement('span');t.textContent=label;w.append(t,input);return w;
  }
  function input(type,value){
    var x=document.createElement('input');x.type=type||'text';x.value=value==null?'':String(value);return x;
  }
  function textarea(value){
    var x=document.createElement('textarea');x.value=value==null?'':String(value);return x;
  }
  function stockSelect(value){
    var sel=document.createElement('select');
    var none=document.createElement('option');none.value='';none.textContent='Not linked to Stock';sel.appendChild(none);
    stock().slice().sort(function(a,b){return stockName(a).localeCompare(stockName(b));}).forEach(function(st){
      var o=document.createElement('option');o.value=s(st.id);o.textContent=stockName(st)||s(st.id);sel.appendChild(o);
    });
    sel.value=value==null?'':String(value);
    return sel;
  }

  function buildIngredientRow(ing,container){
    ing=ing||{};
    var row=document.createElement('div');row.className='cdc-rw-edit-ing';
    var name=input('text',ing.name||'');name.placeholder='Ingredient';
    var qty=input('number',ing.qty==null?'':ing.qty);qty.step='any';qty.min='0.0001';qty.inputMode='decimal';
    var unit=input('text',ing.unit||'');unit.placeholder='g / kg / ml / L / each';
    var link=stockSelect(ing.stockId||'');
    var prep=input('text',ing.preparation||ing.note||'');prep.placeholder='Preparation / note';
    var remove=document.createElement('button');remove.type='button';remove.className='btn danger';remove.textContent='Remove';
    var purchase=document.createElement('div');purchase.className='cdc-rw-row-note';
    function refresh(){
      purchase.textContent=purchasingLine({name:name.value,qty:qty.value,unit:unit.value,stockId:link.value}).text;
    }
    [name,qty,unit,link].forEach(function(el){el.addEventListener('input',refresh);el.addEventListener('change',refresh);});
    remove.onclick=function(){row.remove();};
    row.append(field('Ingredient',name),field('Qty',qty),field('Unit',unit),field('Stock link (optional)',link),field('Preparation / note',prep),remove,purchase);
    row._read=function(){
      var nm=name.value.trim(); if(!nm)return null;
      var q=Number(qty.value);
      if(!Number.isFinite(q)||q<=0)throw new Error('Give '+nm+' a quantity greater than zero.');
      var u=unit.value.trim();
      if(!u)throw new Error('Give '+nm+' a unit.');
      var out={name:nm,qty:q,unit:u};
      if(prep.value.trim())out.preparation=prep.value.trim();
      if(link.value)out.stockId=link.value;
      return out;
    };
    container.appendChild(row);refresh();
    return row;
  }

  function outputText(r){
    try{
      var joined=(r.output||[]).flatMap(function(o){return o.content||[];}).map(function(c){return c.text||c.output_text||'';}).join(' ').trim();
      return joined||r.output_text||'';
    }catch(e){return r&&r.output_text||'';}
  }
  function parseJsonLoose(t){
    var x=s(t).trim().replace(/^\`\`\`(?:json)?\s*/i,'').replace(/\`\`\`\s*$/,'').trim();
    try{return JSON.parse(x);}catch(e){}
    var a=x.indexOf('{'),b=x.lastIndexOf('}');
    if(a>=0&&b>a)return JSON.parse(x.slice(a,b+1));
    throw new Error('Could not read the ingredient draft.');
  }

  function openEditor(recipe){
    if(!recipe)return;
    closeWorkspace();
    var overlay=document.createElement('div');overlay.id=OVERLAY;overlay.className='cdc-rw-overlay';
    var modal=document.createElement('div');modal.className='cdc-rw-modal cdc-rw-editor';
    overlay.appendChild(modal);
    var head=document.createElement('div');head.className='cdc-rw-head';
    head.innerHTML='<div><div class="cdc-rw-kicker">Edit recipe</div><h3>'+esc(recipe.name||'Recipe')+'</h3></div>';
    var close=document.createElement('button');close.type='button';close.className='btn ghost';close.textContent='Close';close.onclick=closeWorkspace;head.appendChild(close);modal.appendChild(head);

    var status=document.createElement('div');status.className='cdc-rw-status';
    var yieldEl=input('text',recipe.yield||recipe.portions||'');
    var allergens=input('text',formatAllergens(recipe.allergens));
    var method=textarea(Array.isArray(recipe.method)?recipe.method.join('\n'):recipe.method||'');
    modal.append(field('Yield / portions',yieldEl),field('Recipe allergens',allergens));
    var warn=document.createElement('div');warn.className='cdc-rw-warning';warn.textContent='Allergens are safety-critical. Changing ingredients does not automatically guess allergens. Review label/spec data before marking a recipe verified.';modal.appendChild(warn);

    var section=document.createElement('div');section.className='cdc-rw-section';section.textContent='Ingredients';modal.appendChild(section);
    var rows=document.createElement('div');rows.className='cdc-rw-edit-list';modal.appendChild(rows);
    var existing=Array.isArray(recipe.ingredients)?recipe.ingredients:[];
    existing.forEach(function(ing){buildIngredientRow(ing,rows);});
    if(!existing.length)buildIngredientRow({},rows);

    var add=document.createElement('button');add.type='button';add.className='btn ghost';add.textContent='+ Add ingredient';add.onclick=function(){buildIngredientRow({},rows);};modal.appendChild(add);
    modal.append(field('Method',method));

    var tools=document.createElement('div');tools.className='cdc-rw-tools';
    var draft=document.createElement('button');draft.type='button';draft.className='btn ghost';draft.textContent='Build ingredient draft';
    tools.appendChild(draft);modal.appendChild(tools);
    modal.appendChild(status);

    var actions=document.createElement('div');actions.className='cdc-rw-actions';
    var saveBtn=document.createElement('button');saveBtn.type='button';saveBtn.className='btn primary';saveBtn.textContent='Save recipe';
    actions.appendChild(saveBtn);modal.appendChild(actions);

    draft.onclick=async function(){
      draft.disabled=true;status.className='cdc-rw-status';status.textContent='Building ingredient draft…';
      try{
        if(typeof api!=='function')throw new Error('AI service is unavailable.');
        var prompt='Create an editable ingredient and method DRAFT for this kitchen recipe. Return JSON only: {"ingredients":[{"name":"","qty":0,"unit":"g","preparation":""}],"method":[""]}. Use practical commercial-kitchen quantities for the stated yield. Do NOT return allergens and do NOT claim anything is verified. Recipe: '+JSON.stringify({name:recipe.name,description:recipe.description||'',yield:yieldEl.value||recipe.yield||'',method:method.value||recipe.method||''});
        var res=await api('/api/openai/responses',{method:'POST',body:JSON.stringify({model:'gpt-4o-mini',input:[{role:'user',content:[{type:'input_text',text:prompt}]}]})});
        var data=parseJsonLoose(outputText(res));
        if(!Array.isArray(data.ingredients)||!data.ingredients.length)throw new Error('No ingredients came back.');
        rows.innerHTML='';
        data.ingredients.forEach(function(ing){buildIngredientRow(ing,rows);});
        if(Array.isArray(data.method)&&data.method.length)method.value=data.method.join('\n');
        status.className='cdc-rw-status good';status.textContent='Draft built. Review quantities, stock links and allergens before saving.';
      }catch(err){
        status.className='cdc-rw-status bad';status.textContent='Could not build draft: '+(err&&err.message?err.message:String(err));
      }finally{draft.disabled=false;}
    };

    saveBtn.onclick=async function(){
      saveBtn.disabled=true;status.className='cdc-rw-status';status.textContent='Saving…';
      var snapshot=JSON.parse(JSON.stringify(recipe));
      try{
        var items=[];
        [].slice.call(rows.querySelectorAll('.cdc-rw-edit-ing')).forEach(function(row){
          var x=row._read();if(x)items.push(x);
        });
        if(!items.length)throw new Error('Add at least one ingredient.');
        recipe.ingredients=items;
        recipe.yield=yieldEl.value.trim()||recipe.yield||'1';
        recipe.allergens=allergens.value.trim();
        recipe.method=method.value.split(/\n+/).map(function(x){return x.trim();}).filter(Boolean);
        recipe.allergenVerified=false;
        recipe.allergenSyncStatus=ALLERGEN_STATUS;
        recipe.needsReview=true;
        if(typeof audit==='function')audit('recipe_updated',recipe.name+' · ingredients / stock links');
        var result=null;
        if(typeof save==='function')result=save('update recipe ingredients');
        if(result&&typeof result.then==='function')await result;
        if(typeof persist==='function')await persist('update recipe ingredients');
        if(typeof rerender==='function')rerender();
        status.className='cdc-rw-status good';status.textContent='Recipe saved.';
        setTimeout(function(){showInspector(recipeById(recipe.id)||recipe);},160);
      }catch(err){
        Object.keys(recipe).forEach(function(k){delete recipe[k];});
        Object.assign(recipe,snapshot);
        status.className='cdc-rw-status bad';status.textContent='Not saved: '+(err&&err.message?err.message:String(err));
        saveBtn.disabled=false;
      }
    };

    document.body.appendChild(overlay);
    overlay.addEventListener('click',function(e){if(e.target===overlay)closeWorkspace();});
  }

  function blockMatrixEdit(ev){
    var target=ev.target&&ev.target.closest?ev.target:null;
    if(target&&target.closest('.cdc-allergen-dish-open'))return;
    ev.preventDefault();ev.stopPropagation();
    if(typeof ev.stopImmediatePropagation==='function')ev.stopImmediatePropagation();
  }
  function findMatrix(){
    var tables=[].slice.call(document.querySelectorAll('table'));
    for(var i=0;i<tables.length;i++){
      var t=tables[i],txt=norm(t.textContent);
      if(txt.indexOf('gluten')>=0&&txt.indexOf('egg')>=0&&(txt.indexOf('milk')>=0||txt.indexOf('dairy')>=0))return t;
    }
    return null;
  }
  function protectTable(table){
    if(!table||!table.isConnected)return false;
    if(table.dataset.cdcSafeAllergen==='1')return true;
    table.dataset.cdcSafeAllergen='1';table.classList.add('cdc-allergen-safe-table');
    var wrap=table.parentElement;
    if(!wrap||!wrap.classList.contains('cdc-allergen-scroll')){
      wrap=document.createElement('div');wrap.className='cdc-allergen-scroll';
      table.parentNode.insertBefore(wrap,table);wrap.appendChild(table);
    }
    var note=document.createElement('div');note.className='cdc-allergen-safe-note';
    note.innerHTML='<strong>View-only allergen matrix</strong><span>Tap a dish name to open its recipe and ingredients. Edit there; the matrix updates from the recipe.</span>';
    wrap.parentNode.insertBefore(note,wrap);

    [].slice.call(table.querySelectorAll('tbody tr')).forEach(function(row){
      var cell=row.querySelector('td:first-child,th:first-child');if(!cell)return;
      var recipe=recipeByName(text(cell));if(!recipe)return;
      cell.innerHTML='';
      var b=document.createElement('button');b.type='button';b.className='cdc-allergen-dish-open';b.textContent=recipe.name;b.dataset.recipeId=recipe.id;
      b.onclick=function(e){e.preventDefault();e.stopPropagation();var r=recipeById(this.dataset.recipeId);if(r)showInspector(r);};
      cell.appendChild(b);
    });
    [].slice.call(table.querySelectorAll('input,select,textarea,button,[role="checkbox"],[role="switch"],label')).forEach(function(el){
      if(el.classList.contains('cdc-allergen-dish-open'))return;
      el.setAttribute('aria-disabled','true');el.setAttribute('tabindex','-1');el.classList.add('cdc-allergen-locked-control');
    });
    ['click','change','dblclick','contextmenu'].forEach(function(name){table.addEventListener(name,blockMatrixEdit,true);});
    return true;
  }

  function css(){
    if(document.getElementById('cdc-rw-style'))return;
    var st=document.createElement('style');st.id='cdc-rw-style';st.textContent=
      '.cdc-allergen-safe-note{display:flex;flex-direction:column;gap:3px;margin:0 0 10px;padding:11px 12px;border:1px solid var(--line,#35404b);border-radius:11px;background:var(--panel2,#20262e)}.cdc-allergen-safe-note span{font-size:12px;color:var(--muted,#9ca6b3)}'+
      '.cdc-allergen-scroll{overflow:auto;max-height:66vh;-webkit-overflow-scrolling:touch;border:1px solid var(--line,#35404b);border-radius:12px}.cdc-allergen-safe-table{min-width:1000px;border-collapse:separate!important;border-spacing:0!important}.cdc-allergen-safe-table thead th{position:sticky!important;top:0!important;z-index:6!important;background:var(--panel,#1b2027)!important}.cdc-allergen-safe-table th:first-child,.cdc-allergen-safe-table td:first-child{position:sticky!important;left:0!important;z-index:5!important;background:var(--panel,#1b2027)!important;min-width:145px!important}.cdc-allergen-safe-table thead th:first-child{z-index:8!important}.cdc-allergen-safe-table th:not(:first-child),.cdc-allergen-safe-table td:not(:first-child){min-width:68px;text-align:center}.cdc-allergen-locked-control{pointer-events:none!important}.cdc-allergen-dish-open{appearance:none;border:0;background:transparent;color:var(--brass,#e6ab31);font:inherit;font-weight:800;text-align:left;padding:9px 6px;width:100%;cursor:pointer;text-decoration:underline;text-underline-offset:3px}'+
      '.cdc-rw-overlay{position:fixed;inset:0;z-index:10060;background:rgba(0,0,0,.74);display:flex;align-items:flex-end;justify-content:center;padding:10px}.cdc-rw-modal{width:min(760px,100%);max-height:94vh;overflow:auto;background:var(--card,#1c2229);border:1px solid var(--line,#35404b);border-radius:18px 18px 12px 12px;padding:15px}.cdc-rw-head{display:flex;gap:10px;align-items:flex-start;margin-bottom:12px}.cdc-rw-head>div{flex:1}.cdc-rw-head h3{margin:2px 0 0}.cdc-rw-kicker,.cdc-rw-section{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted,#9ca6b3);font-weight:800}.cdc-rw-box,.cdc-rw-ing,.cdc-rw-edit-ing{border:1px solid var(--line,#35404b);border-radius:11px;background:var(--panel2,#20262e);padding:11px}.cdc-rw-box strong{display:block;margin-bottom:4px}.cdc-rw-section{margin:16px 0 8px}.cdc-rw-list,.cdc-rw-edit-list{display:grid;gap:8px}.cdc-rw-ing-head{display:flex;justify-content:space-between;gap:10px}.cdc-rw-meta,.cdc-rw-row-note{font-size:12px;color:var(--muted,#9ca6b3);margin-top:5px}.cdc-rw-purchase{font-size:12px;font-weight:700;margin-top:6px}.cdc-rw-purchase.short,.cdc-rw-purchase.unlinked{color:var(--warn,#d99b2b)}.cdc-rw-purchase.ok{color:var(--ok,#48b875)}.cdc-rw-empty{padding:18px;text-align:center;border:1px dashed var(--line,#35404b);border-radius:11px;display:flex;flex-direction:column;gap:6px;color:var(--muted,#9ca6b3)}.cdc-rw-empty strong{color:var(--text,#f4f5f7)}.cdc-rw-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px;position:sticky;bottom:-15px;background:var(--card,#1c2229);padding:10px 0 4px}.cdc-rw-field{display:flex;flex-direction:column;gap:5px;margin-bottom:9px}.cdc-rw-field>span{font-size:12px;color:var(--muted,#9ca6b3)}.cdc-rw-field input,.cdc-rw-field select,.cdc-rw-field textarea{width:100%;box-sizing:border-box;background:var(--panel2,#20262e);color:var(--text,#f4f5f7);border:1px solid var(--line,#35404b);border-radius:9px;padding:10px;font:inherit}.cdc-rw-field textarea{min-height:120px}.cdc-rw-edit-ing{display:grid;grid-template-columns:2fr .8fr .8fr 1.4fr 2fr auto;gap:8px;align-items:end}.cdc-rw-edit-ing .cdc-rw-field{margin:0}.cdc-rw-row-note{grid-column:1/-1}.cdc-rw-warning{padding:10px;border:1px solid var(--warn,#d99b2b);border-radius:10px;font-size:12px;line-height:1.4;margin-bottom:12px}.cdc-rw-tools{display:flex;gap:8px;margin-top:10px}.cdc-rw-status{min-height:20px;font-size:12px;color:var(--muted,#9ca6b3);margin-top:8px}.cdc-rw-status.bad{color:var(--danger,#e06666)}.cdc-rw-status.good{color:var(--ok,#48b875)}'+
      '@media(max-width:720px){.cdc-rw-edit-ing{grid-template-columns:1fr 1fr}.cdc-rw-edit-ing .cdc-rw-field:first-child,.cdc-rw-edit-ing .cdc-rw-field:nth-child(4),.cdc-rw-edit-ing .cdc-rw-field:nth-child(5),.cdc-rw-row-note{grid-column:1/-1}.cdc-rw-edit-ing>.btn{grid-column:1/-1}.cdc-rw-modal{padding:13px}.cdc-allergen-scroll{max-height:64vh}.cdc-allergen-safe-table{min-width:960px}}';
    document.head.appendChild(st);
  }

  function tryProtect(){
    var table=findMatrix();
    if(!table)return false;
    if(table!==lastProtectedTable){
      lastProtectedTable=table;
      try{protectTable(table);}catch(err){console.warn('[Command de Cuisine] allergen matrix protection failed',err);}
    }
    return true;
  }

  function start(){
    css();
    // Avoid a document-wide MutationObserver: the matrix is large on phones and
    // its own render can create a mutation storm. Poll lightly and only rework a
    // newly-rendered table.
    tryProtect();
    setInterval(function(){
      if(lastProtectedTable&&!lastProtectedTable.isConnected)lastProtectedTable=null;
      tryProtect();
    },700);
    document.addEventListener('click',function(e){
      var el=e.target&&e.target.closest?e.target.closest('button,a,[role="button"]'):null;
      if(el&&/allergen/i.test(text(el)))setTimeout(tryProtect,180);
    },true);
    window.CDCRecipeWorkspace={open:function(id){var r=recipeById(id);if(r)showInspector(r);},edit:function(id){var r=recipeById(id);if(r)openEditor(r);}};
    console.info('[Command de Cuisine] Stable allergen matrix + recipe ingredient workspace active');
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();