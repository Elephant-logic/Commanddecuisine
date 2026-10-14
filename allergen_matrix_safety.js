/* Command de Cuisine - safe mobile allergen matrix + ingredient editor */
(function(){
  'use strict';
  if(window.__cdcRecipeIngredientWorkspaceV5) return;
  window.__cdcRecipeIngredientWorkspaceV5=true;

  var OVERLAY='cdc-allergen-workspace-overlay';
  var ALLERGENS=['Celery','Gluten','Crustaceans','Eggs','Fish','Lupin','Milk','Molluscs','Mustard','Nuts','Peanuts','Sesame','Soya','Sulphites'];
  var ALIASES={
    celery:['celery'],gluten:['gluten','wheat','barley','rye','oats'],
    crustaceans:['crustacean','crustaceans','prawn','prawns','shrimp','crab','lobster','scampi','shellfish'],
    eggs:['egg','eggs'],fish:['fish'],lupin:['lupin'],milk:['milk','dairy'],
    molluscs:['mollusc','molluscs','mussel','mussels','oyster','oysters','squid','octopus'],
    mustard:['mustard'],nuts:['nuts','tree nuts','almond','almonds','hazelnut','hazelnuts','walnut','walnuts','cashew','cashews','pistachio','pistachios','pecan','pecans'],
    peanuts:['peanut','peanuts'],sesame:['sesame'],soya:['soya','soy'],
    sulphites:['sulphite','sulphites','sulfite','sulfites','sulphur dioxide','sulfur dioxide']
  };

  function s(v){return String(v==null?'':v);}
  function norm(v){return s(v).toLowerCase().trim().replace(/\s+/g,' ');}
  function esc(v){return s(v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function recipes(){try{return Array.isArray(STATE.recipes)?STATE.recipes:[];}catch(e){return [];}}
  function stock(){try{return Array.isArray(STATE.stock)?STATE.stock:[];}catch(e){return [];}}
  function recipeById(id){return recipes().find(function(r){return String(r&&r.id)===String(id);})||null;}
  function stockName(x){return s(x&&(x.item||x.name||x.product||x.label)).trim();}
  function stockById(id){return stock().find(function(x){return String(x&&x.id)===String(id);})||null;}
  function ingredientStock(ing){
    if(!ing)return null;
    if(ing.stockId){var byId=stockById(ing.stockId);if(byId)return byId;}
    var n=norm(ing.name);if(!n)return null;
    var matches=stock().filter(function(x){return norm(stockName(x))===n;});
    return matches.length===1?matches[0]:null;
  }

  function parseAllergens(value){
    if(value==null||value==='')return [];
    var raw=[];
    if(Array.isArray(value))raw=value.map(String);
    else if(typeof value==='object')raw=Object.keys(value).filter(function(k){return value[k]===true||value[k]===1||value[k]==='yes';});
    else raw=[String(value)];
    var words=' '+raw.join(' ').toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\s+/g,' ').trim()+' ';
    var out=[];
    ALLERGENS.forEach(function(label){
      var aliases=ALIASES[norm(label)]||[norm(label)];
      var present=aliases.some(function(a){
        var needle=' '+String(a).toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()+' ';
        return needle.trim()&&words.indexOf(needle)>=0;
      });
      if(present)out.push(label);
    });
    return out;
  }
  function uniqueAllergens(values){
    var set=new Set();
    (values||[]).forEach(function(v){
      ALLERGENS.forEach(function(a){if(norm(a)===norm(v))set.add(a);});
    });
    return ALLERGENS.filter(function(a){return set.has(a);});
  }
  function ingredientAllergens(ing){return uniqueAllergens(parseAllergens(ing&&ing.allergens));}
  function recipeAllergens(recipe){
    var all=[];
    (recipe&&Array.isArray(recipe.ingredients)?recipe.ingredients:[]).forEach(function(ing){all=all.concat(ingredientAllergens(ing));});
    all=all.concat(parseAllergens(recipe&&recipe.extraAllergens));
    if(!all.length)all=all.concat(parseAllergens(recipe&&recipe.allergens));
    return uniqueAllergens(all);
  }
  function ingredientSuggestions(ing){return uniqueAllergens(parseAllergens(ing&&ing.allergenSuggestions));}

  function canonicalUnit(u){
    u=norm(u).replace(/litres?/,'l').replace(/liters?/,'l').replace(/millilitres?/,'ml').replace(/milliliters?/,'ml').replace(/kilograms?/,'kg').replace(/grams?/,'g').replace(/ounces?/,'oz');
    if(['each','ea','count','unit','units','piece','pieces'].indexOf(u)>=0)return 'each';
    return u;
  }
  function convertQty(q,from,to){
    q=Number(q);from=canonicalUnit(from);to=canonicalUnit(to);
    if(!Number.isFinite(q)||!from||!to)return null;
    if(from===to)return q;
    var g={g:1,kg:1000,oz:28.349523125};
    if(g[from]&&g[to])return q*g[from]/g[to];
    var ml={ml:1,l:1000};
    if(ml[from]&&ml[to])return q*ml[from]/ml[to];
    return null;
  }
  function stockQty(row){
    var keys=['actualQty','quantity','qty','onHand','currentQty','stock','amount'];
    for(var i=0;i<keys.length;i++){var n=Number(row&&row[keys[i]]);if(Number.isFinite(n))return n;}
    return null;
  }
  function stockUnit(row){return s(row&&(row.unit||row.stockUnit||row.baseUnit||row.qtyUnit)).trim();}
  function purchasingLine(ing){
    var st=ingredientStock(ing),q=Number(ing&&ing.qty),u=s(ing&&ing.unit).trim();
    if(!st)return 'Not linked to Stock — that is optional.';
    var have=stockQty(st),su=stockUnit(st);
    if(have==null)return 'Linked to '+stockName(st)+' · stock quantity not set.';
    var need=convertQty(q,u,su);
    if(need==null)return 'Linked to '+stockName(st)+' · '+have+' '+su+' on hand · unit conversion needs review.';
    var short=Math.max(0,need-have);
    return short>0?'Linked to '+stockName(st)+' · order about '+(Math.round(short*100)/100)+' '+su+' for one batch.':'Linked to '+stockName(st)+' · enough on hand for one batch.';
  }

  function closeOverlay(){var x=document.getElementById(OVERLAY);if(x)x.remove();}
  function notify(msg,bad){
    try{if(typeof toast==='function'){toast(msg,bad?'bad':'ok');return;}}catch(e){}
    console[bad?'warn':'info']('[Command de Cuisine] '+msg);
  }
  async function saveState(reason){
    if(typeof save==='function'){var r=save(reason);if(r&&typeof r.then==='function')await r;return;}
    if(typeof persist==='function')await persist(reason);
  }
  function currentUser(){
    try{return (ME&&(ME.name||ME.username))||'manager';}catch(e){return 'manager';}
  }
  function snapshotVersion(recipe,reason){
    try{
      var copy=JSON.parse(JSON.stringify(recipe));delete copy.versions;
      recipe.versions=Array.isArray(recipe.versions)?recipe.versions:[];
      recipe.versions.push({id:'rv_'+Date.now()+'_'+Math.random().toString(36).slice(2,7),data:copy,reason:reason,savedAt:new Date().toISOString(),savedBy:currentUser()});
      if(recipe.versions.length>20)recipe.versions=recipe.versions.slice(-20);
    }catch(e){}
  }
  function recomputeRecipeAllergens(recipe){
    var all=[];
    (recipe.ingredients||[]).forEach(function(ing){all=all.concat(ingredientAllergens(ing));});
    all=all.concat(parseAllergens(recipe.extraAllergens));
    all=uniqueAllergens(all);
    recipe.allergens=all.join(', ');
    recipe.allergenReviewRequired=true;
    recipe.needsReview=true;
    recipe.ingredientAllergensManaged=true;
    return all;
  }

  function css(){
    if(document.getElementById('cdc-allergen-v5-css'))return;
    var st=document.createElement('style');st.id='cdc-allergen-v5-css';
    st.textContent=
      '.cdc-a5-wrap{display:flex;flex-direction:column;gap:12px}.cdc-a5-head{display:flex;gap:10px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}.cdc-a5-head h2{margin:0}.cdc-a5-copy{color:var(--muted,#9ca6b3);font-size:13px;line-height:1.45;max-width:760px}.cdc-a5-actions{display:flex;gap:8px;flex-wrap:wrap}.cdc-a5-search{width:min(360px,100%);box-sizing:border-box;background:var(--panel2,#20262e);color:var(--text,#f4f5f7);border:1px solid var(--line,#35404b);border-radius:10px;padding:10px}.cdc-a5-scroll{overflow:auto;-webkit-overflow-scrolling:touch;max-height:calc(100vh - 235px);border:1px solid var(--line,#35404b);border-radius:12px}.cdc-a5-table{border-collapse:separate;border-spacing:0;min-width:1120px;width:100%;background:var(--card,#1c2229)}.cdc-a5-table th,.cdc-a5-table td{border-right:1px solid var(--line,#35404b);border-bottom:1px solid var(--line,#35404b);padding:8px 6px;text-align:center;font-size:12px}.cdc-a5-table thead th{position:sticky;top:0;z-index:5;background:var(--panel,#1b2027);font-size:10px;line-height:1.2}.cdc-a5-table th:first-child,.cdc-a5-table td:first-child{position:sticky;left:0;z-index:4;background:var(--panel,#1b2027);min-width:220px;text-align:left}.cdc-a5-table thead th:first-child{z-index:7}.cdc-a5-dish{appearance:none;border:0;background:none;color:var(--brass,#e6ab31);padding:0;text-align:left;font:inherit;font-weight:800;text-decoration:underline;text-underline-offset:3px;cursor:pointer;width:100%}.cdc-a5-mark{font-size:17px;font-weight:900}.cdc-a5-review{display:block;margin-top:4px;font-size:9px;text-transform:uppercase;letter-spacing:.05em;color:var(--warn,#d99b2b)}.cdc-a5-empty{padding:22px;color:var(--muted,#9ca6b3)}'+
      '.cdc-a5-overlay{position:fixed;inset:0;z-index:10100;background:rgba(0,0,0,.74);display:flex;align-items:flex-end;justify-content:center;padding:10px}.cdc-a5-modal{width:min(860px,100%);max-height:94vh;overflow:auto;background:var(--card,#1c2229);border:1px solid var(--line,#35404b);border-radius:18px 18px 12px 12px;padding:15px;box-shadow:0 20px 60px rgba(0,0,0,.55)}.cdc-a5-modalhead{display:flex;align-items:flex-start;gap:10px;margin-bottom:12px}.cdc-a5-modalhead>div{flex:1}.cdc-a5-modalhead h3{margin:2px 0 0}.cdc-a5-kicker{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted,#9ca6b3)}.cdc-a5-box{border:1px solid var(--line,#35404b);background:var(--panel2,#20262e);border-radius:11px;padding:11px;margin:9px 0}.cdc-a5-box strong{display:block;margin-bottom:4px}.cdc-a5-list{display:grid;gap:8px}.cdc-a5-ing{width:100%;text-align:left;border:1px solid var(--line,#35404b);background:var(--panel2,#20262e);color:var(--text,#f4f5f7);border-radius:11px;padding:10px;font:inherit;cursor:pointer}.cdc-a5-ing-top{display:flex;gap:10px;justify-content:space-between}.cdc-a5-ing-name{font-weight:800}.cdc-a5-meta{font-size:12px;color:var(--muted,#9ca6b3);line-height:1.4;margin-top:4px}.cdc-a5-allergens{font-size:12px;margin-top:5px}.cdc-a5-suggest{font-size:11px;color:var(--warn,#d99b2b);margin-top:4px}.cdc-a5-actions2{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;margin-top:12px}.cdc-a5-field{display:flex;flex-direction:column;gap:5px;margin-bottom:10px}.cdc-a5-field span{font-size:12px;color:var(--muted,#9ca6b3)}.cdc-a5-field input,.cdc-a5-field select,.cdc-a5-field textarea{width:100%;box-sizing:border-box;background:var(--panel2,#20262e);color:var(--text,#f4f5f7);border:1px solid var(--line,#35404b);border-radius:10px;padding:10px;font:inherit}.cdc-a5-field textarea{min-height:140px}.cdc-a5-grid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:8px}.cdc-a5-grid .full{grid-column:1/-1}.cdc-a5-picks{display:flex;flex-wrap:wrap;gap:6px}.cdc-a5-chip{border:1px solid var(--line,#35404b);border-radius:999px;padding:8px 10px;background:var(--panel2,#20262e);color:var(--muted,#9ca6b3);font:inherit;font-size:12px}.cdc-a5-chip.on{border-color:var(--brass,#e6ab31);background:rgba(230,171,49,.16);color:var(--text,#fff);font-weight:800}.cdc-a5-warning{border:1px solid var(--warn,#d99b2b);border-radius:10px;padding:9px;font-size:12px;line-height:1.4;margin:10px 0}.cdc-a5-status{min-height:18px;font-size:12px;color:var(--muted,#9ca6b3);margin-top:8px}.cdc-a5-status.bad{color:var(--danger,#e06666)}.cdc-a5-status.good{color:var(--ok,#48b875)}'+
      '@media(max-width:650px){.cdc-a5-scroll{max-height:calc(100vh - 250px)}.cdc-a5-table{min-width:1040px}.cdc-a5-table th:first-child,.cdc-a5-table td:first-child{min-width:175px}.cdc-a5-modal{padding:12px}.cdc-a5-grid{grid-template-columns:1fr 1fr}.cdc-a5-grid .cdc-a5-name,.cdc-a5-grid .full{grid-column:1/-1}}';
    document.head.appendChild(st);
  }

  function field(label,el,cls){
    var w=document.createElement('label');w.className='cdc-a5-field'+(cls?' '+cls:'');
    var t=document.createElement('span');t.textContent=label;w.append(t,el);return w;
  }
  function inp(type,val){var x=document.createElement('input');x.type=type||'text';x.value=val==null?'':String(val);return x;}
  function textarea(val){var x=document.createElement('textarea');x.value=val==null?'':String(val);return x;}
  function stockSelect(value){
    var sel=document.createElement('select');
    var no=document.createElement('option');no.value='';no.textContent='Not linked to Stock';sel.appendChild(no);
    stock().slice().sort(function(a,b){return stockName(a).localeCompare(stockName(b));}).forEach(function(st){
      var o=document.createElement('option');o.value=s(st.id);o.textContent=stockName(st)||s(st.id);sel.appendChild(o);
    });
    sel.value=value?String(value):'';return sel;
  }
  function picker(initial){
    var box=document.createElement('div');box.className='cdc-a5-picks';
    var chosen=new Set(uniqueAllergens(initial||[]));
    function draw(){
      box.innerHTML='';
      ALLERGENS.forEach(function(a){
        var b=document.createElement('button');b.type='button';b.className='cdc-a5-chip'+(chosen.has(a)?' on':'');b.textContent=a;
        b.setAttribute('aria-pressed',chosen.has(a)?'true':'false');
        b.onclick=function(){if(chosen.has(a))chosen.delete(a);else chosen.add(a);draw();};
        box.appendChild(b);
      });
    }
    box.value=function(){return ALLERGENS.filter(function(a){return chosen.has(a);});};
    box.setValue=function(v){chosen=new Set(uniqueAllergens(v));draw();};
    draw();return box;
  }

  function openDish(recipe){
    if(!recipe)return;
    closeOverlay();
    var overlay=document.createElement('div');overlay.id=OVERLAY;overlay.className='cdc-a5-overlay';
    var modal=document.createElement('div');modal.className='cdc-a5-modal';overlay.appendChild(modal);
    var head=document.createElement('div');head.className='cdc-a5-modalhead';
    head.innerHTML='<div><div class="cdc-a5-kicker">Recipe & allergen workspace</div><h3>'+esc(recipe.name||'Recipe')+'</h3></div>';
    var close=document.createElement('button');close.type='button';close.className='btn ghost';close.textContent='Close';close.onclick=closeOverlay;head.appendChild(close);modal.appendChild(head);

    var current=recipeAllergens(recipe);
    var summary=document.createElement('div');summary.className='cdc-a5-box';
    summary.innerHTML='<strong>Recipe allergen summary</strong><div>'+esc(current.length?current.join(', '):'None currently selected')+'</div>'+
      (recipe.allergenReviewRequired?'<span class="cdc-a5-review">Needs allergen review</span>':'');
    modal.appendChild(summary);

    var note=document.createElement('div');note.className='cdc-a5-meta';
    note.textContent='Tap an ingredient to edit its quantity, optional Stock link and allergens. Nothing changes until you press Save ingredient.';
    modal.appendChild(note);

    var list=document.createElement('div');list.className='cdc-a5-list';
    var items=Array.isArray(recipe.ingredients)?recipe.ingredients:[];
    if(!items.length){
      var empty=document.createElement('div');empty.className='cdc-a5-empty';empty.textContent='No ingredients saved yet.';
      list.appendChild(empty);
    }else{
      items.forEach(function(ing,index){
        var b=document.createElement('button');b.type='button';b.className='cdc-a5-ing';
        var als=ingredientAllergens(ing),suggest=ingredientSuggestions(ing),st=ingredientStock(ing);
        b.innerHTML='<div class="cdc-a5-ing-top"><span class="cdc-a5-ing-name">'+esc(ing.name||'Ingredient')+'</span><span>'+esc([ing.qty,ing.unit].filter(function(v){return v!=null&&s(v)!=='';}).join(' '))+'</span></div>'+
          (ing.preparation?'<div class="cdc-a5-meta">'+esc(ing.preparation)+'</div>':'')+
          '<div class="cdc-a5-allergens"><b>Allergens:</b> '+esc(als.length?als.join(', '):'None selected')+'</div>'+
          (suggest.length?'<div class="cdc-a5-suggest">Draft suggestion: '+esc(suggest.join(', '))+' — check the actual product label/spec.</div>':'')+
          '<div class="cdc-a5-meta">'+esc(st?'Stock link: '+stockName(st):'Not linked to Stock')+' · '+esc(purchasingLine(ing))+'</div>';
        b.onclick=function(){openIngredient(recipeById(recipe.id)||recipe,index);};
        list.appendChild(b);
      });
    }
    modal.appendChild(list);

    var actions=document.createElement('div');actions.className='cdc-a5-actions2';
    var add=document.createElement('button');add.type='button';add.className='btn ghost';add.textContent='+ Add ingredient';add.onclick=function(){openIngredient(recipeById(recipe.id)||recipe,-1);};
    var details=document.createElement('button');details.type='button';details.className='btn ghost';details.textContent='Edit yield / method';details.onclick=function(){openRecipeDetails(recipeById(recipe.id)||recipe);};
    var reviewed=document.createElement('button');reviewed.type='button';reviewed.className='btn primary';reviewed.textContent='Mark allergen review complete';
    reviewed.onclick=async function(){
      var r=recipeById(recipe.id)||recipe;
      snapshotVersion(r,'allergen review complete');
      r.allergenReviewRequired=false;
      if(typeof audit==='function')try{audit('recipe_allergens_reviewed',r.name);}catch(e){}
      try{await saveState('recipe allergen review complete');notify('Allergen review marked complete');if(typeof rerender==='function')rerender();openDish(r);}
      catch(err){notify('Could not save allergen review',true);}
    };
    actions.append(add,details,reviewed);
    modal.appendChild(actions);
    document.body.appendChild(overlay);
    overlay.onclick=function(e){if(e.target===overlay)closeOverlay();};
  }

  function openIngredient(recipe,index){
    if(!recipe)return;
    var existing=index>=0&&Array.isArray(recipe.ingredients)?recipe.ingredients[index]:null;
    closeOverlay();
    var overlay=document.createElement('div');overlay.id=OVERLAY;overlay.className='cdc-a5-overlay';
    var modal=document.createElement('div');modal.className='cdc-a5-modal';overlay.appendChild(modal);
    var head=document.createElement('div');head.className='cdc-a5-modalhead';
    head.innerHTML='<div><div class="cdc-a5-kicker">'+(existing?'Edit ingredient':'Add ingredient')+'</div><h3>'+esc(recipe.name||'Recipe')+'</h3></div>';
    var back=document.createElement('button');back.type='button';back.className='btn ghost';back.textContent='Back';back.onclick=function(){openDish(recipeById(recipe.id)||recipe);};head.appendChild(back);modal.appendChild(head);

    var grid=document.createElement('div');grid.className='cdc-a5-grid';
    var name=inp('text',existing&&existing.name||'');var qty=inp('number',existing&&existing.qty!=null?existing.qty:'');qty.step='any';qty.min='0.0001';qty.inputMode='decimal';
    var unit=inp('text',existing&&existing.unit||'');var prep=inp('text',existing&&(existing.preparation||existing.note)||'');
    var link=stockSelect(existing&&existing.stockId||'');
    grid.append(field('Ingredient',name,'cdc-a5-name'),field('Qty',qty),field('Unit',unit),field('Preparation / note',prep,'full'),field('Stock link (optional)',link,'full'));
    modal.appendChild(grid);

    var warn=document.createElement('div');warn.className='cdc-a5-warning';
    warn.textContent='Choose allergens from the actual ingredient/packaging you use. The matrix itself cannot be tapped to change allergens.';
    modal.appendChild(warn);

    var pickerBox=picker(existing?ingredientAllergens(existing):[]);
    var label=document.createElement('div');label.className='cdc-a5-box';label.innerHTML='<strong>Ingredient allergens</strong><div class="cdc-a5-meta">Tap to select or remove. Changes apply only when you save this ingredient.</div>';
    label.appendChild(pickerBox);modal.appendChild(label);

    var suggestions=existing?ingredientSuggestions(existing):[];
    if(suggestions.length){
      var sg=document.createElement('div');sg.className='cdc-a5-box';
      sg.innerHTML='<strong>Draft suggestions</strong><div>'+esc(suggestions.join(', '))+'</div><div class="cdc-a5-meta">These are not treated as selected until you apply/check them.</div>';
      var apply=document.createElement('button');apply.type='button';apply.className='btn ghost';apply.textContent='Apply suggestions';apply.style.marginTop='8px';apply.onclick=function(){pickerBox.setValue(suggestions);};sg.appendChild(apply);modal.appendChild(sg);
    }

    var status=document.createElement('div');status.className='cdc-a5-status';modal.appendChild(status);
    var actions=document.createElement('div');actions.className='cdc-a5-actions2';
    if(existing){
      var del=document.createElement('button');del.type='button';del.className='btn danger';del.textContent='Remove ingredient';
      del.onclick=async function(){
        if(!window.confirm('Remove '+(existing.name||'this ingredient')+' from this recipe?'))return;
        var r=recipeById(recipe.id)||recipe;snapshotVersion(r,'remove recipe ingredient');
        r.ingredients.splice(index,1);recomputeRecipeAllergens(r);
        try{if(typeof audit==='function')audit('recipe_ingredient_removed',r.name+' · '+(existing.name||''));await saveState('remove recipe ingredient');if(typeof rerender==='function')rerender();openDish(r);}
        catch(err){status.className='cdc-a5-status bad';status.textContent='Could not remove ingredient: '+(err&&err.message||err);}
      };
      actions.appendChild(del);
    }
    var saveBtn=document.createElement('button');saveBtn.type='button';saveBtn.className='btn primary';saveBtn.textContent='Save ingredient';
    saveBtn.onclick=async function(){
      status.className='cdc-a5-status';status.textContent='Saving…';saveBtn.disabled=true;
      try{
        var nm=name.value.trim(),q=Number(qty.value),u=unit.value.trim();
        if(!nm)throw new Error('Ingredient name is required.');
        if(!Number.isFinite(q)||q<=0)throw new Error('Quantity must be greater than zero.');
        if(!u)throw new Error('Unit is required.');
        var r=recipeById(recipe.id)||recipe;snapshotVersion(r,'edit recipe ingredient');
        r.ingredients=Array.isArray(r.ingredients)?r.ingredients:[];
        var next={name:nm,qty:q,unit:u,allergens:pickerBox.value(),allergenSource:'manager-edit',allergenReviewedAt:new Date().toISOString()};
        if(prep.value.trim())next.preparation=prep.value.trim();
        if(link.value)next.stockId=link.value;
        if(existing&&existing.allergenSuggestions)next.allergenSuggestions=existing.allergenSuggestions;
        if(index>=0)r.ingredients[index]=next;else r.ingredients.push(next);
        recomputeRecipeAllergens(r);
        if(typeof audit==='function')try{audit('recipe_ingredient_updated',r.name+' · '+nm);}catch(e){}
        await saveState('update recipe ingredient');
        if(typeof rerender==='function')rerender();
        notify('Ingredient saved · matrix updated');
        openDish(r);
      }catch(err){
        status.className='cdc-a5-status bad';status.textContent='Not saved: '+(err&&err.message?err.message:String(err));saveBtn.disabled=false;
      }
    };
    actions.appendChild(saveBtn);modal.appendChild(actions);
    document.body.appendChild(overlay);
    overlay.onclick=function(e){if(e.target===overlay)openDish(recipeById(recipe.id)||recipe);};
  }

  function openRecipeDetails(recipe){
    closeOverlay();
    var overlay=document.createElement('div');overlay.id=OVERLAY;overlay.className='cdc-a5-overlay';
    var modal=document.createElement('div');modal.className='cdc-a5-modal';overlay.appendChild(modal);
    var head=document.createElement('div');head.className='cdc-a5-modalhead';
    head.innerHTML='<div><div class="cdc-a5-kicker">Recipe details</div><h3>'+esc(recipe.name||'Recipe')+'</h3></div>';
    var back=document.createElement('button');back.type='button';back.className='btn ghost';back.textContent='Back';back.onclick=function(){openDish(recipeById(recipe.id)||recipe);};head.appendChild(back);modal.appendChild(head);
    var yieldEl=inp('text',recipe.yield||recipe.portions||'');
    var method=textarea(Array.isArray(recipe.method)?recipe.method.join('\n'):recipe.method||'');
    modal.append(field('Yield / portions',yieldEl),field('Method',method));
    var status=document.createElement('div');status.className='cdc-a5-status';modal.appendChild(status);
    var actions=document.createElement('div');actions.className='cdc-a5-actions2';
    var saveBtn=document.createElement('button');saveBtn.type='button';saveBtn.className='btn primary';saveBtn.textContent='Save recipe details';
    saveBtn.onclick=async function(){
      saveBtn.disabled=true;status.textContent='Saving…';
      try{
        var r=recipeById(recipe.id)||recipe;snapshotVersion(r,'edit recipe details');
        r.yield=yieldEl.value.trim()||r.yield||'1';
        r.method=method.value.split(/\n+/).map(function(x){return x.trim();}).filter(Boolean);
        r.needsReview=true;
        if(typeof audit==='function')try{audit('recipe_updated',r.name+' · yield / method');}catch(e){}
        await saveState('update recipe details');if(typeof rerender==='function')rerender();notify('Recipe updated');openDish(r);
      }catch(err){status.className='cdc-a5-status bad';status.textContent='Not saved: '+(err&&err.message||err);saveBtn.disabled=false;}
    };
    actions.appendChild(saveBtn);modal.appendChild(actions);document.body.appendChild(overlay);
  }

  function renderAllergens(v){
    css();
    v.innerHTML='';
    var wrap=document.createElement('div');wrap.className='cdc-a5-wrap';
    var head=document.createElement('div');head.className='cdc-a5-head';
    var copy=document.createElement('div');copy.innerHTML='<h2>Allergen matrix</h2><div class="cdc-a5-copy">Read-only summary. Tap a dish name to see its recipe and ingredients. Allergens can only be changed inside an ingredient editor and require an explicit save.</div>';
    var actions=document.createElement('div');actions.className='cdc-a5-actions';
    if(typeof window.printAllergenMatrix==='function'){var p=document.createElement('button');p.type='button';p.className='btn ghost';p.textContent='Print matrix';p.onclick=window.printAllergenMatrix;actions.appendChild(p);}
    if(typeof window.printDishAllergens==='function'){var d=document.createElement('button');d.type='button';d.className='btn ghost';d.textContent='Print dish sheets';d.onclick=window.printDishAllergens;actions.appendChild(d);}
    head.append(copy,actions);wrap.appendChild(head);

    var search=inp('search','');search.className='cdc-a5-search';search.placeholder='Search dishes…';wrap.appendChild(search);
    var scroll=document.createElement('div');scroll.className='cdc-a5-scroll';
    var table=document.createElement('table');table.className='cdc-a5-table';
    table.innerHTML='<thead><tr><th>Dish</th>'+ALLERGENS.map(function(a){return '<th>'+esc(a)+'</th>';}).join('')+'</tr></thead><tbody></tbody>';
    var body=table.querySelector('tbody');

    function draw(){
      body.innerHTML='';
      var q=norm(search.value);
      var rows=recipes().slice().sort(function(a,b){return s(a.name).localeCompare(s(b.name));}).filter(function(r){return !q||norm(r.name).indexOf(q)>=0;});
      if(!rows.length){var tr=document.createElement('tr');tr.innerHTML='<td colspan="'+(ALLERGENS.length+1)+'" class="cdc-a5-empty">No dishes found.</td>';body.appendChild(tr);return;}
      rows.forEach(function(r){
        var present=new Set(recipeAllergens(r));
        var tr=document.createElement('tr');
        var td=document.createElement('td');
        var b=document.createElement('button');b.type='button';b.className='cdc-a5-dish';b.textContent=r.name||'Untitled dish';b.onclick=function(){openDish(recipeById(r.id)||r);};td.appendChild(b);
        if(r.allergenReviewRequired||r.needsReview){var badge=document.createElement('span');badge.className='cdc-a5-review';badge.textContent='Review';td.appendChild(badge);}
        tr.appendChild(td);
        ALLERGENS.forEach(function(a){var c=document.createElement('td');c.className='cdc-a5-mark';c.textContent=present.has(a)?'●':'';tr.appendChild(c);});
        body.appendChild(tr);
      });
    }
    search.addEventListener('input',draw);draw();
    scroll.appendChild(table);wrap.appendChild(scroll);v.appendChild(wrap);
  }

  function install(){
    try{
      if(typeof VIEWS==='undefined'||!VIEWS)return false;
      VIEWS.allergens=renderAllergens;
      VIEWS.allergens.__cdcSafeIngredientView=true;
      css();
      window.CDCRecipeWorkspace={open:function(id){var r=recipeById(id);if(r)openDish(r);},editIngredient:function(id,index){var r=recipeById(id);if(r)openIngredient(r,index);}};
      console.info('[Command de Cuisine] safe ingredient allergen workspace active; matrix is read-only');
      return true;
    }catch(err){console.error('[Command de Cuisine] allergen workspace install failed',err);return false;}
  }

  var tries=0,t=setInterval(function(){tries++;if(install()||tries>80)clearInterval(t);},100);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})();