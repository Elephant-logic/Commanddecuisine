/* Command de Cuisine - stable read-only allergen matrix + ingredient allergen workspace */
(function(){
  'use strict';
  if(window.__cdcRecipeIngredientWorkspaceV4) return;
  window.__cdcRecipeIngredientWorkspaceV4=true;

  var OVERLAY='cdc-recipe-workspace-overlay';
  var ALLERGEN_STATUS='Needs review after ingredient change';
  var ALLERGENS=[
    'Celery','Gluten','Crustaceans','Eggs','Fish','Lupin','Milk',
    'Molluscs','Mustard','Nuts','Peanuts','Sesame','Soya','Sulphites'
  ];
  var ALIASES={
    celery:['celery'],
    gluten:['gluten','wheat','barley','rye','oats'],
    crustaceans:['crustacean','crustaceans','prawn','prawns','shrimp','shrimp','crab','lobster','scampi'],
    eggs:['egg','eggs'],
    fish:['fish'],
    lupin:['lupin'],
    milk:['milk','dairy'],
    molluscs:['mollusc','molluscs','mussel','mussels','oyster','oysters','squid','octopus'],
    mustard:['mustard'],
    nuts:['nuts','tree nuts','almond','almonds','hazelnut','hazelnuts','walnut','walnuts','cashew','cashews','pistachio','pistachios','pecan','pecans','brazil nut','brazil nuts'],
    peanuts:['peanut','peanuts'],
    sesame:['sesame'],
    soya:['soya','soy'],
    sulphites:['sulphite','sulphites','sulfite','sulfites','sulphur dioxide','sulfur dioxide']
  };

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
  function round(n){return String(Math.round(Number(n)*100)/100);}
  function purchasingLine(ing){
    var q=Number(ing&&ing.qty), u=s(ing&&ing.unit).trim();
    var st=stockForIngredient(ing);
    if(!st){
      return {kind:'unlinked',text:(Number.isFinite(q)&&q>0?q+' '+u+' required for one batch · ':'')+'not linked to Stock (that is optional)'};
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

  function labelForKey(key){
    key=norm(key);
    for(var i=0;i<ALLERGENS.length;i++)if(norm(ALLERGENS[i])===key)return ALLERGENS[i];
    return '';
  }
  function parseAllergens(value){
    if(value==null||value==='')return [];
    var raw=[];
    if(Array.isArray(value)) raw=value.map(String);
    else if(typeof value==='object') raw=Object.keys(value).filter(function(k){return value[k]===true||value[k]==='yes'||value[k]===1;});
    else raw=[String(value)];
    var joined=' '+raw.join(' , ').toLowerCase()+' ';
    var words=' '+joined.replace(/[^a-z0-9]+/g,' ').replace(/\s+/g,' ').trim()+' ';
    function hasAlias(a){
      var needle=' '+String(a).toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\s+/g,' ').trim()+' ';
      return needle.trim()!=='' && words.indexOf(needle)>=0;
    }
    var out=[];
    ALLERGENS.forEach(function(label){
      var key=norm(label), aliases=ALIASES[key]||[key];
      if(aliases.some(hasAlias))out.push(label);
    });
    return out;
  }
  function uniqueAllergens(values){
    var set=new Set();
    (values||[]).forEach(function(v){
      var label=labelForKey(v)||ALLERGENS.find(function(a){return norm(a)===norm(v);});
      if(label)set.add(label);
    });
    return ALLERGENS.filter(function(a){return set.has(a);});
  }
  function formatAllergens(value){return parseAllergens(value).join(', ');}
  function ingredientAllergens(ing){return uniqueAllergens(parseAllergens(ing&&ing.allergens));}
  function rollup(items,extras){
    var all=[];
    (items||[]).forEach(function(i){all=all.concat(ingredientAllergens(i));});
    all=all.concat(extras||[]);
    return uniqueAllergens(all);
  }
  function stockDeclaredAllergens(st){
    if(!st)return [];
    var fields=['supplierAllergens','declaredAllergens','allergenDeclaration','allergenSpec','allergens'];
    for(var i=0;i<fields.length;i++){
      var x=parseAllergens(st[fields[i]]);
      if(x.length)return x;
    }
    return [];
  }

  function closeWorkspace(){var old=document.getElementById(OVERLAY);if(old)old.remove();}
  function notify(msg,bad){
    try{if(typeof toast==='function')return toast(msg,bad?'bad':'ok');}catch(e){}
    console[bad?'warn':'info']('[Command de Cuisine] '+msg);
  }
  async function saveState(reason){
    if(typeof save==='function'){
      var r=save(reason);
      if(r&&typeof r.then==='function')await r;
      return;
    }
    if(typeof persist==='function')await persist(reason);
  }

  function ingredientSummary(recipe){
    var items=Array.isArray(recipe&&recipe.ingredients)?recipe.ingredients:[];
    if(!items.length){
      return '<div class="cdc-rw-empty"><strong>No ingredients saved yet</strong><span>Open Edit recipe & ingredients. You can add them yourself or build a draft, then review it.</span></div>';
    }
    return items.map(function(ing){
      var p=purchasingLine(ing||{}), st=stockForIngredient(ing), als=ingredientAllergens(ing);
      var qty=[ing&&ing.qty,ing&&ing.unit].filter(function(v){return v!=null&&s(v)!=='';}).join(' ');
      var prep=s(ing&&ing.preparation||ing&&ing.note).trim();
      return '<div class="cdc-rw-ing">'+
        '<div class="cdc-rw-ing-head"><strong>'+esc(ing&&ing.name||'Ingredient')+'</strong><span>'+esc(qty)+'</span></div>'+
        (prep?'<div class="cdc-rw-meta">'+esc(prep)+'</div>':'')+
        '<div class="cdc-rw-allergen-line"><b>Allergens:</b> '+esc(als.length?als.join(', '):'None selected')+'</div>'+
        '<div class="cdc-rw-purchase '+esc(p.kind)+'">'+esc(p.text)+'</div>'+
        (st?'<div class="cdc-rw-meta">Stock link: '+esc(stockName(st))+'</div>':'')+
      '</div>';
    }).join('');
  }

  function showInspector(recipe){
    if(!recipe)return;
    closeWorkspace();
    var overlay=document.createElement('div');overlay.id=OVERLAY;overlay.className='cdc-rw-overlay';
    overlay.innerHTML=
      '<div class="cdc-rw-modal" role="dialog" aria-modal="true">'+
        '<div class="cdc-rw-head"><div><div class="cdc-rw-kicker">Recipe workspace</div><h3>'+esc(recipe.name||'Recipe')+'</h3></div><button type="button" class="btn ghost cdc-rw-close">Close</button></div>'+
        '<div class="cdc-rw-box"><strong>Recipe allergen summary</strong><div>'+esc(formatAllergens(recipe.allergens)||'None currently listed')+'</div>'+
          '<div class="cdc-rw-meta">This summary is updated from ingredient allergen selections when you save the recipe.</div></div>'+
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
  function input(type,value){var x=document.createElement('input');x.type=type||'text';x.value=value==null?'':String(value);return x;}
  function textarea(value){var x=document.createElement('textarea');x.value=value==null?'':String(value);return x;}
  function stockSelect(value){
    var sel=document.createElement('select');
    var none=document.createElement('option');none.value='';none.textContent='Not linked to Stock';sel.appendChild(none);
    stock().slice().sort(function(a,b){return stockName(a).localeCompare(stockName(b));}).forEach(function(st){
      var o=document.createElement('option');o.value=s(st.id);o.textContent=stockName(st)||s(st.id);sel.appendChild(o);
    });
    sel.value=value==null?'':String(value);return sel;
  }
  function allergenPicker(initial,onChange){
    var box=document.createElement('div');box.className='cdc-rw-allergen-picker';
    var chosen=new Set(uniqueAllergens(initial||[]));
    function render(){
      box.innerHTML='';
      ALLERGENS.forEach(function(label){
        var b=document.createElement('button');b.type='button';
        b.className='cdc-rw-allergen-chip'+(chosen.has(label)?' on':'');
        b.textContent=label;b.setAttribute('aria-pressed',chosen.has(label)?'true':'false');
        b.onclick=function(){
          if(chosen.has(label))chosen.delete(label);else chosen.add(label);
          render();if(onChange)onChange(Array.from(chosen));
        };
        box.appendChild(b);
      });
    }
    box.value=function(){return ALLERGENS.filter(function(a){return chosen.has(a);});};
    box.setValue=function(values){chosen=new Set(uniqueAllergens(values));render();if(onChange)onChange(box.value());};
    render();return box;
  }

  function buildIngredientRow(ing,container,onRecipePreview){
    ing=ing||{};
    var row=document.createElement('div');row.className='cdc-rw-edit-ing';
    var name=input('text',ing.name||'');name.placeholder='Ingredient';
    var qty=input('number',ing.qty==null?'':ing.qty);qty.step='any';qty.min='0.0001';qty.inputMode='decimal';
    var unit=input('text',ing.unit||'');unit.placeholder='g / kg / ml / L / each';
    var link=stockSelect(ing.stockId||'');
    var prep=input('text',ing.preparation||ing.note||'');prep.placeholder='Preparation / note';
    var remove=document.createElement('button');remove.type='button';remove.className='btn danger';remove.textContent='Remove ingredient';
    var purchase=document.createElement('div');purchase.className='cdc-rw-row-note';
    var alHead=document.createElement('div');alHead.className='cdc-rw-allergen-head';
    var alLabel=document.createElement('strong');alLabel.textContent='Ingredient allergens';
    var alHelp=document.createElement('span');alHelp.textContent='Tap to select what this actual ingredient contains.';
    alHead.append(alLabel,alHelp);
    var picker=allergenPicker(ingredientAllergens(ing),function(){if(onRecipePreview)onRecipePreview();});
    var spec=document.createElement('div');spec.className='cdc-rw-row-note';
    var useSpec=document.createElement('button');useSpec.type='button';useSpec.className='btn ghost cdc-rw-use-spec';useSpec.textContent='Use Stock/spec allergens';useSpec.style.display='none';

    function refresh(){
      var probe={name:name.value,qty:qty.value,unit:unit.value,stockId:link.value};
      purchase.textContent=purchasingLine(probe).text;
      var st=stockById(link.value), declared=stockDeclaredAllergens(st);
      if(declared.length){
        spec.textContent='Linked Stock/spec allergens: '+declared.join(', ');
        useSpec.style.display='';
        useSpec.onclick=function(){picker.setValue(declared);};
      }else{
        spec.textContent=link.value?'No allergen declaration saved on this Stock item.':'Stock link is optional.';
        useSpec.style.display='none';
      }
    }
    [name,qty,unit,link].forEach(function(el){el.addEventListener('input',refresh);el.addEventListener('change',refresh);});
    remove.onclick=function(){row.remove();if(onRecipePreview)onRecipePreview();};

    row.append(
      field('Ingredient',name),field('Qty',qty),field('Unit',unit),field('Stock link (optional)',link),field('Preparation / note',prep),
      remove,alHead,picker,spec,useSpec,purchase
    );
    row._read=function(){
      var nm=name.value.trim();if(!nm)return null;
      var q=Number(qty.value);if(!Number.isFinite(q)||q<=0)throw new Error('Give '+nm+' a quantity greater than zero.');
      var u=unit.value.trim();if(!u)throw new Error('Give '+nm+' a unit.');
      var out={name:nm,qty:q,unit:u,allergens:picker.value()};
      if(prep.value.trim())out.preparation=prep.value.trim();
      if(link.value)out.stockId=link.value;
      return out;
    };
    row._allergens=function(){return picker.value();};
    container.appendChild(row);refresh();return row;
  }

  function outputText(r){
    try{
      var joined=(r.output||[]).flatMap(function(o){return o.content||[];}).map(function(c){return c.text||c.output_text||'';}).join(' ').trim();
      return joined||r.output_text||'';
    }catch(e){return r&&r.output_text||'';}
  }
  function parseJsonLoose(t){
    var x=s(t).trim().replace(/^```(?:json)?\s*/i,'').replace(/```\s*$/,'').trim();
    try{return JSON.parse(x);}catch(e){}
    var a=x.indexOf('{'),b=x.lastIndexOf('}');
    if(a>=0&&b>a)return JSON.parse(x.slice(a,b+1));
    throw new Error('Could not read the ingredient draft.');
  }

  function openEditor(recipe){
    if(!recipe)return;
    closeWorkspace();
    var overlay=document.createElement('div');overlay.id=OVERLAY;overlay.className='cdc-rw-overlay';
    var modal=document.createElement('div');modal.className='cdc-rw-modal cdc-rw-editor';overlay.appendChild(modal);
    var head=document.createElement('div');head.className='cdc-rw-head';
    head.innerHTML='<div><div class="cdc-rw-kicker">Edit recipe</div><h3>'+esc(recipe.name||'Recipe')+'</h3></div>';
    var close=document.createElement('button');close.type='button';close.className='btn ghost';close.textContent='Close';close.onclick=closeWorkspace;head.appendChild(close);modal.appendChild(head);

    var status=document.createElement('div');status.className='cdc-rw-status';
    var yieldEl=input('text',recipe.yield||recipe.portions||'');
    var method=textarea(Array.isArray(recipe.method)?recipe.method.join('\n'):recipe.method||'');
    modal.append(field('Yield / portions',yieldEl));

    var section=document.createElement('div');section.className='cdc-rw-section';section.textContent='Ingredients';modal.appendChild(section);
    var intro=document.createElement('div');intro.className='cdc-rw-meta';intro.textContent='Ingredients do not have to exist in Stock. Link them only when useful for stock levels, costing and order requirements.';modal.appendChild(intro);
    var rows=document.createElement('div');rows.className='cdc-rw-edit-list';modal.appendChild(rows);

    var existing=Array.isArray(recipe.ingredients)?recipe.ingredients:[];
    var oldRecipeAllergens=parseAllergens(recipe.allergens);
    var existingIngRollup=rollup(existing,[]);
    var extras=oldRecipeAllergens.filter(function(a){return existingIngRollup.indexOf(a)<0;});

    var preview=document.createElement('div');preview.className='cdc-rw-box cdc-rw-preview';
    var extraTitle=document.createElement('div');extraTitle.className='cdc-rw-section';extraTitle.textContent='Additional recipe allergens';
    var extraHelp=document.createElement('div');extraHelp.className='cdc-rw-meta';extraHelp.textContent='Use these only for allergens that apply to the finished dish but are not yet assigned to an ingredient.';
    var extraPicker=allergenPicker(extras,refreshPreview);

    function collectRowAllergens(){
      var all=[];
      [].slice.call(rows.querySelectorAll('.cdc-rw-edit-ing')).forEach(function(row){if(row._allergens)all=all.concat(row._allergens());});
      return uniqueAllergens(all);
    }
    function refreshPreview(){
      var summary=rollup([],collectRowAllergens().concat(extraPicker.value()));
      preview.innerHTML='<strong>Recipe allergen summary after save</strong><div>'+esc(summary.length?summary.join(', '):'None selected')+'</div>';
    }

    existing.forEach(function(ing){buildIngredientRow(ing,rows,refreshPreview);});
    if(!existing.length)buildIngredientRow({},rows,refreshPreview);

    var add=document.createElement('button');add.type='button';add.className='btn ghost';add.textContent='+ Add ingredient';
    add.onclick=function(){buildIngredientRow({},rows,refreshPreview);refreshPreview();};modal.appendChild(add);
    modal.append(extraTitle,extraHelp,extraPicker,preview);

    var warn=document.createElement('div');warn.className='cdc-rw-warning';warn.textContent='Allergens are safety-critical. Select allergens from the actual ingredient label/spec you use. The app will not guess from an ingredient name.';modal.appendChild(warn);
    modal.append(field('Method',method));

    var tools=document.createElement('div');tools.className='cdc-rw-tools';
    var draft=document.createElement('button');draft.type='button';draft.className='btn ghost';draft.textContent=existing.length?'Rebuild ingredient draft':'Build ingredient draft';
    tools.appendChild(draft);modal.appendChild(tools);
    modal.appendChild(status);

    var actions=document.createElement('div');actions.className='cdc-rw-actions';
    var saveBtn=document.createElement('button');saveBtn.type='button';saveBtn.className='btn primary';saveBtn.textContent='Save recipe & update matrix';
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
        data.ingredients.forEach(function(ing){buildIngredientRow(ing,rows,refreshPreview);});
        if(Array.isArray(data.method)&&data.method.length)method.value=data.method.join('\n');
        refreshPreview();
        status.className='cdc-rw-status good';status.textContent='Draft built. Now check quantities and select allergens from the ingredients you actually use.';
      }catch(err){
        status.className='cdc-rw-status bad';status.textContent='Could not build draft: '+(err&&err.message?err.message:String(err));
      }finally{draft.disabled=false;}
    };

    saveBtn.onclick=async function(){
      saveBtn.disabled=true;status.className='cdc-rw-status';status.textContent='Saving…';
      var snapshot=JSON.parse(JSON.stringify(recipe));
      try{
        var items=[];
        [].slice.call(rows.querySelectorAll('.cdc-rw-edit-ing')).forEach(function(row){var x=row._read();if(x)items.push(x);});
        if(!items.length)throw new Error('Add at least one ingredient.');
        var summary=rollup(items,extraPicker.value());
        recipe.ingredients=items;
        recipe.yield=yieldEl.value.trim()||recipe.yield||'1';
        recipe.allergens=summary.join(', ');
        recipe.method=method.value.split(/\n+/).map(function(x){return x.trim();}).filter(Boolean);
        recipe.allergenVerified=false;
        recipe.allergenSyncStatus=ALLERGEN_STATUS;
        recipe.needsReview=true;
        recipe.ingredientAllergensManaged=true;
        if(typeof audit==='function')audit('recipe_updated',recipe.name+' · ingredients / ingredient allergens / stock links');
        await saveState('update recipe ingredients and allergens');
        if(typeof rerender==='function')rerender();
        status.className='cdc-rw-status good';status.textContent='Recipe saved. Allergen matrix updated from its ingredients.';
        setTimeout(function(){showInspector(recipeById(recipe.id)||recipe);},160);
      }catch(err){
        Object.keys(recipe).forEach(function(k){delete recipe[k];});Object.assign(recipe,snapshot);
        status.className='cdc-rw-status bad';status.textContent='Not saved: '+(err&&err.message?err.message:String(err));saveBtn.disabled=false;
      }
    };

    document.body.appendChild(overlay);
    overlay.addEventListener('click',function(e){if(e.target===overlay)closeWorkspace();});
    refreshPreview();
  }

  function findMatrix(){
    var tables=[].slice.call(document.querySelectorAll('table'));
    for(var i=0;i<tables.length;i++){
      var t=tables[i],tx=norm(t.textContent);
      if(tx.indexOf('gluten')>=0&&tx.indexOf('egg')>=0&&(tx.indexOf('milk')>=0||tx.indexOf('dairy')>=0))return t;
    }
    return null;
  }
  function matrixEvent(ev){
    var table=ev.currentTarget;
    var cell=ev.target&&ev.target.closest?ev.target.closest('td,th'):null;
    if(!cell||!table.contains(cell))return;
    var row=cell.parentElement, first=row&&row.children&&row.children[0];
    var bodyRow=row&&row.parentElement&&String(row.parentElement.tagName).toLowerCase()==='tbody';
    if(bodyRow&&cell===first){
      var recipe=recipeByName(text(first));
      if(recipe){
        ev.preventDefault();ev.stopPropagation();if(typeof ev.stopImmediatePropagation==='function')ev.stopImmediatePropagation();
        showInspector(recipe);return;
      }
    }
    if(bodyRow){
      ev.preventDefault();ev.stopPropagation();if(typeof ev.stopImmediatePropagation==='function')ev.stopImmediatePropagation();
    }
  }
  function protectTable(table){
    if(!table||!table.isConnected)return false;
    if(table.dataset.cdcSafeAllergen==='1')return true;
    table.dataset.cdcSafeAllergen='1';table.classList.add('cdc-allergen-safe-table');
    var parent=table.parentElement;
    if(parent)parent.classList.add('cdc-allergen-scroll');

    [].slice.call(table.querySelectorAll('tbody tr')).forEach(function(row){
      var cell=row.children&&row.children[0];if(!cell)return;
      var recipe=recipeByName(text(cell));
      if(recipe){cell.classList.add('cdc-allergen-dish-cell');cell.setAttribute('role','button');cell.setAttribute('tabindex','0');cell.dataset.recipeId=recipe.id;}
    });
    ['click','change','input','dblclick','contextmenu'].forEach(function(name){table.addEventListener(name,matrixEvent,true);});
    table.addEventListener('keydown',function(e){
      var cell=e.target&&e.target.closest?e.target.closest('td,th'):null;
      if(cell&&cell.classList.contains('cdc-allergen-dish-cell')&&(e.key==='Enter'||e.key===' ')){
        e.preventDefault();var r=recipeById(cell.dataset.recipeId)||recipeByName(text(cell));if(r)showInspector(r);return;
      }
      if(cell&&cell.closest('tbody')){e.preventDefault();e.stopPropagation();}
    },true);

    if(parent&&!parent.querySelector(':scope > .cdc-allergen-safe-note')){
      var note=document.createElement('div');note.className='cdc-allergen-safe-note';
      note.innerHTML='<strong>View-only allergen matrix</strong><span>Tap a dish name to open its recipe. Change allergens on the actual ingredients; saving the recipe updates this matrix.</span>';
      parent.insertBefore(note,table);
    }
    return true;
  }

  function css(){
    if(document.getElementById('cdc-rw-style'))return;
    var st=document.createElement('style');st.id='cdc-rw-style';st.textContent=
      '.cdc-allergen-safe-note{display:flex;flex-direction:column;gap:3px;margin:0 0 10px;padding:11px 12px;border:1px solid var(--line,#35404b);border-radius:11px;background:var(--panel2,#20262e);position:sticky;left:0;z-index:9}.cdc-allergen-safe-note span{font-size:12px;color:var(--muted,#9ca6b3)}'+
      '.cdc-allergen-scroll{overflow:auto!important;-webkit-overflow-scrolling:touch}.cdc-allergen-safe-table{min-width:1000px;border-collapse:separate!important;border-spacing:0!important}.cdc-allergen-safe-table thead th{position:sticky!important;top:0!important;z-index:6!important;background:var(--panel,#1b2027)!important}.cdc-allergen-safe-table th:first-child,.cdc-allergen-safe-table td:first-child{position:sticky!important;left:0!important;z-index:5!important;background:var(--panel,#1b2027)!important;min-width:145px!important}.cdc-allergen-safe-table thead th:first-child{z-index:8!important}.cdc-allergen-safe-table th:not(:first-child),.cdc-allergen-safe-table td:not(:first-child){min-width:68px;text-align:center}.cdc-allergen-dish-cell{cursor:pointer!important;color:var(--brass,#e6ab31)!important;font-weight:800!important;text-decoration:underline;text-underline-offset:3px}'+
      '.cdc-rw-overlay{position:fixed;inset:0;z-index:10080;background:rgba(0,0,0,.74);display:flex;align-items:flex-end;justify-content:center;padding:10px}.cdc-rw-modal{width:min(900px,100%);max-height:94vh;overflow:auto;background:var(--card,#1c2229);border:1px solid var(--line,#35404b);border-radius:18px 18px 12px 12px;padding:16px;box-shadow:0 20px 60px rgba(0,0,0,.55)}.cdc-rw-head{display:flex;gap:10px;align-items:flex-start;margin-bottom:12px}.cdc-rw-head>div{flex:1}.cdc-rw-head h3{margin:2px 0 0}.cdc-rw-kicker{text-transform:uppercase;letter-spacing:.08em;font-size:11px;color:var(--muted,#9ca6b3)}.cdc-rw-box{padding:11px;border:1px solid var(--line,#35404b);border-radius:11px;background:var(--panel2,#20262e);margin-bottom:12px}.cdc-rw-box>div{margin-top:4px}.cdc-rw-section{font-weight:800;margin:14px 0 8px}.cdc-rw-meta{font-size:12px;color:var(--muted,#9ca6b3);line-height:1.4}.cdc-rw-list{display:grid;gap:9px}.cdc-rw-ing{padding:10px;border:1px solid var(--line,#35404b);border-radius:10px}.cdc-rw-ing-head{display:flex;gap:10px;justify-content:space-between}.cdc-rw-allergen-line{font-size:12px;margin-top:6px}.cdc-rw-purchase{font-size:12px;margin-top:6px}.cdc-rw-purchase.short{color:var(--warn,#d99b2b)}.cdc-rw-purchase.ok{color:var(--ok,#48b875)}.cdc-rw-empty{display:flex;flex-direction:column;gap:5px;padding:16px;border:1px dashed var(--line,#35404b);border-radius:11px}.cdc-rw-actions{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;margin-top:12px}.cdc-rw-field{display:flex;flex-direction:column;gap:5px;margin-bottom:10px}.cdc-rw-field>span{font-size:12px;color:var(--muted,#9ca6b3)}.cdc-rw-field input,.cdc-rw-field select,.cdc-rw-field textarea{width:100%;box-sizing:border-box;background:var(--panel2,#20262e);color:var(--text,#f4f5f7);border:1px solid var(--line,#35404b);border-radius:9px;padding:10px;font:inherit}.cdc-rw-field textarea{min-height:120px}.cdc-rw-edit-list{display:grid;gap:12px}.cdc-rw-edit-ing{display:grid;grid-template-columns:2fr .8fr .8fr 1.4fr 2fr auto;gap:8px;align-items:end;padding:12px;border:1px solid var(--line,#35404b);border-radius:12px}.cdc-rw-edit-ing .cdc-rw-field{margin:0}.cdc-rw-row-note,.cdc-rw-allergen-head,.cdc-rw-allergen-picker,.cdc-rw-use-spec{grid-column:1/-1}.cdc-rw-allergen-head{display:flex;flex-direction:column;gap:2px}.cdc-rw-allergen-head span{font-size:12px;color:var(--muted,#9ca6b3)}.cdc-rw-allergen-picker{display:flex;flex-wrap:wrap;gap:6px}.cdc-rw-allergen-chip{border:1px solid var(--line,#35404b);border-radius:999px;padding:7px 10px;background:var(--panel2,#20262e);color:var(--muted,#9ca6b3);font:inherit;font-size:12px}.cdc-rw-allergen-chip.on{background:rgba(230,171,49,.16);border-color:var(--brass,#e6ab31);color:var(--text,#fff);font-weight:800}.cdc-rw-warning{padding:10px;border:1px solid var(--warn,#d99b2b);border-radius:10px;font-size:12px;line-height:1.4;margin:12px 0}.cdc-rw-tools{display:flex;gap:8px;margin-top:10px}.cdc-rw-status{min-height:20px;font-size:12px;color:var(--muted,#9ca6b3);margin-top:8px}.cdc-rw-status.bad{color:var(--danger,#e06666)}.cdc-rw-status.good{color:var(--ok,#48b875)}'+
      '@media(max-width:720px){.cdc-rw-edit-ing{grid-template-columns:1fr 1fr}.cdc-rw-edit-ing .cdc-rw-field:first-child,.cdc-rw-edit-ing .cdc-rw-field:nth-child(4),.cdc-rw-edit-ing .cdc-rw-field:nth-child(5),.cdc-rw-row-note,.cdc-rw-allergen-head,.cdc-rw-allergen-picker,.cdc-rw-use-spec{grid-column:1/-1}.cdc-rw-edit-ing>.btn{grid-column:1/-1}.cdc-rw-modal{padding:13px}.cdc-allergen-safe-table{min-width:960px}}';
    document.head.appendChild(st);
  }

  var protectTimer=null;
  function tryProtect(){
    var table=findMatrix();
    if(table)try{protectTable(table);}catch(err){console.warn('[Command de Cuisine] allergen matrix protection failed',err);}
  }
  function scheduleProtect(){
    clearTimeout(protectTimer);protectTimer=setTimeout(tryProtect,120);
  }
  function start(){
    css();scheduleProtect();
    document.addEventListener('click',function(e){
      var el=e.target&&e.target.closest?e.target.closest('button,a,[role="button"]'):null;
      if(el&&/allergen/i.test(text(el)))setTimeout(tryProtect,180);
    },true);
    window.addEventListener('hashchange',scheduleProtect);
    window.addEventListener('popstate',scheduleProtect);
    window.CDCRecipeWorkspace={open:function(id){var r=recipeById(id);if(r)showInspector(r);},edit:function(id){var r=recipeById(id);if(r)openEditor(r);}};
    console.info('[Command de Cuisine] Stable read-only allergen matrix + ingredient allergen workspace active');
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();