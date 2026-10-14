/* Command de Cuisine - stable mobile allergen matrix + ingredient workspace v6 */
(function(){
  'use strict';
  if(window.__cdcAllergenWorkspaceV6) return;
  window.__cdcAllergenWorkspaceV6=true;

  var OVERLAY='cdc-allergen-v6-overlay';
  var ALLERGENS=['Celery','Gluten','Crustaceans','Eggs','Fish','Lupin','Milk','Molluscs','Mustard','Nuts','Peanuts','Sesame','Soya','Sulphites'];

  function str(v){return String(v==null?'':v);}
  function norm(v){return str(v).toLowerCase().trim().replace(/\s+/g,' ');}
  function esc(v){return str(v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function recipes(){try{return Array.isArray(STATE.recipes)?STATE.recipes:[];}catch(e){return [];}}
  function stock(){try{return Array.isArray(STATE.stock)?STATE.stock:[];}catch(e){return [];}}
  function recipeById(id){return recipes().find(function(r){return r&&String(r.id)===String(id);})||null;}
  function stockName(x){return str(x&&(x.item||x.name||x.product||x.label)).trim();}
  function stockById(id){return stock().find(function(x){return x&&String(x.id)===String(id);})||null;}
  function ingredientStock(ing){
    if(!ing)return null;
    if(ing.stockId){var byId=stockById(ing.stockId);if(byId)return byId;}
    var n=norm(ing.name);if(!n)return null;
    var matches=stock().filter(function(x){return norm(stockName(x))===n;});
    return matches.length===1?matches[0]:null;
  }

  function canonicalAllergen(v){
    var n=norm(v);
    var aliases={
      'celery':'Celery','gluten':'Gluten','wheat':'Gluten','barley':'Gluten','rye':'Gluten','oats':'Gluten',
      'crustacean':'Crustaceans','crustaceans':'Crustaceans','prawn':'Crustaceans','prawns':'Crustaceans','shrimp':'Crustaceans','crab':'Crustaceans','lobster':'Crustaceans','scampi':'Crustaceans','langoustine':'Crustaceans',
      'egg':'Eggs','eggs':'Eggs','fish':'Fish','lupin':'Lupin','milk':'Milk','dairy':'Milk',
      'mollusc':'Molluscs','molluscs':'Molluscs','mussel':'Molluscs','mussels':'Molluscs','oyster':'Molluscs','oysters':'Molluscs','squid':'Molluscs','octopus':'Molluscs',
      'mustard':'Mustard','nut':'Nuts','nuts':'Nuts','tree nuts':'Nuts','almond':'Nuts','almonds':'Nuts','hazelnut':'Nuts','hazelnuts':'Nuts','walnut':'Nuts','walnuts':'Nuts','cashew':'Nuts','cashews':'Nuts','pistachio':'Nuts','pistachios':'Nuts','pecan':'Nuts','pecans':'Nuts',
      'peanut':'Peanuts','peanuts':'Peanuts','sesame':'Sesame','soya':'Soya','soy':'Soya',
      'sulphite':'Sulphites','sulphites':'Sulphites','sulfite':'Sulphites','sulfites':'Sulphites','sulphur dioxide':'Sulphites','sulfur dioxide':'Sulphites'
    };
    if(aliases[n])return aliases[n];
    return ALLERGENS.find(function(a){return norm(a)===n;})||'';
  }

  function uniqueAllergens(list){
    var set=new Set();
    (list||[]).forEach(function(v){var c=canonicalAllergen(v);if(c)set.add(c);});
    return ALLERGENS.filter(function(a){return set.has(a);});
  }

  function parseAllergens(value){
    if(value==null||value==='')return [];
    var raw=[];
    if(Array.isArray(value)) raw=value.map(String);
    else if(typeof value==='object') raw=Object.keys(value).filter(function(k){return value[k]===true||value[k]===1||value[k]==='yes';});
    else raw=[String(value)];
    var text=' '+raw.join(' ').toLowerCase().replace(/[^a-z0-9]+/g,' ').replace(/\s+/g,' ').trim()+' ';
    var out=[];
    var needles={
      Celery:['celery'],
      Gluten:['gluten','wheat','barley','rye','oats'],
      Crustaceans:['crustacean','crustaceans','prawn','prawns','shrimp','crab','lobster','scampi','langoustine'],
      Eggs:['egg','eggs'],
      Fish:['fish','cod','haddock','salmon','tuna','anchovy','anchovies'],
      Lupin:['lupin'],
      Milk:['milk','dairy'],
      Molluscs:['mollusc','molluscs','mussel','mussels','oyster','oysters','squid','octopus'],
      Mustard:['mustard'],
      Nuts:['tree nuts','almond','almonds','hazelnut','hazelnuts','walnut','walnuts','cashew','cashews','pistachio','pistachios','pecan','pecans'],
      Peanuts:['peanut','peanuts'],
      Sesame:['sesame'],
      Soya:['soya','soy'],
      Sulphites:['sulphite','sulphites','sulfite','sulfites','sulphur dioxide','sulfur dioxide']
    };
    ALLERGENS.forEach(function(a){
      if((needles[a]||[]).some(function(n){return text.indexOf(' '+n+' ')>=0;}))out.push(a);
    });
    return uniqueAllergens(out);
  }

  function autoSuggestions(ing){
    var n=' '+norm(ing&&ing.name).replace(/[^a-z0-9]+/g,' ')+' ';
    var out=[];
    function add(a){out.push(a);}
    if(/\b(milk|butter|cream|cheese|cheddar|parmesan|mozzarella|stilton|yoghurt|yogurt|buttermilk)\b/.test(n))add('Milk');
    if(/\b(egg|eggs|egg yolk|egg yolks)\b/.test(n))add('Eggs');
    if(/\b(flour|wheat|bread|bun|buns|brioche|naan|pasta|linguini|linguine|lasagne|lasagna|sourdough|ciabatta|breadcrumbs|batter mix)\b/.test(n))add('Gluten');
    if(/\b(mustard|dijon)\b/.test(n))add('Mustard');
    if(/\b(cod|haddock|salmon|tuna|anchovy|anchovies|white fish|fish fillet|fish fillets|fish sauce)\b/.test(n))add('Fish');
    if(/\b(scampi|prawn|prawns|shrimp|crab|lobster|langoustine)\b/.test(n))add('Crustaceans');
    if(/\b(mussel|mussels|oyster|oysters|squid|octopus)\b/.test(n))add('Molluscs');
    if(/\b(peanut|peanuts)\b/.test(n))add('Peanuts');
    if(/\b(almond|almonds|hazelnut|hazelnuts|walnut|walnuts|cashew|cashews|pistachio|pistachios|pecan|pecans)\b/.test(n))add('Nuts');
    if(/\b(sesame|tahini)\b/.test(n))add('Sesame');
    if(/\b(soya|soy|tofu)\b/.test(n))add('Soya');
    if(/\b(celery)\b/.test(n))add('Celery');
    if(/\b(lupin)\b/.test(n))add('Lupin');
    if(/\b(wine|vinegar|balsamic|worcestershire)\b/.test(n))add('Sulphites');
    return uniqueAllergens(out);
  }

  function ingredientAllergens(ing){return uniqueAllergens(parseAllergens(ing&&ing.allergens));}
  function ingredientSuggestions(ing){
    return uniqueAllergens(parseAllergens(ing&&ing.allergenSuggestions).concat(autoSuggestions(ing)));
  }
  function ingredientConfirmed(ing){
    if(!ing)return false;
    var src=norm(ing.allergenSource);
    return ing.allergenVerified===true||src==='manager-edit'||src==='user-confirmed';
  }

  function recipeAllergenState(recipe){
    var confirmed=[],draft=[];
    var items=recipe&&Array.isArray(recipe.ingredients)?recipe.ingredients:[];
    items.forEach(function(ing){
      var selected=ingredientAllergens(ing);
      if(ingredientConfirmed(ing))confirmed=confirmed.concat(selected);
      else draft=draft.concat(selected);
      draft=draft.concat(ingredientSuggestions(ing));
    });
    draft=draft.concat(parseAllergens(recipe&&recipe.allergenDrafts));
    draft=draft.concat(parseAllergens(recipe&&recipe.allergens));
    draft=draft.concat(parseAllergens(recipe&&recipe.extraAllergens));
    confirmed=uniqueAllergens(confirmed);
    draft=uniqueAllergens(draft).filter(function(a){return confirmed.indexOf(a)<0;});
    return {confirmed:confirmed,draft:draft,all:uniqueAllergens(confirmed.concat(draft))};
  }

  function canonicalUnit(u){
    u=norm(u).replace(/litres?/,'l').replace(/liters?/,'l').replace(/millilitres?/,'ml').replace(/milliliters?/,'ml').replace(/kilograms?/,'kg').replace(/grams?/,'g').replace(/ounces?/,'oz');
    if(['each','ea','count','unit','units','piece','pieces'].indexOf(u)>=0)return 'each';
    return u;
  }
  function convertQty(q,from,to){
    q=Number(q);from=canonicalUnit(from);to=canonicalUnit(to);
    if(!Number.isFinite(q)||!from||!to)return null;
    if(from===to)return q;
    var mass={g:1,kg:1000,oz:28.349523125};
    if(mass[from]&&mass[to])return q*mass[from]/mass[to];
    var vol={ml:1,l:1000};
    if(vol[from]&&vol[to])return q*vol[from]/vol[to];
    return null;
  }
  function stockQty(row){
    var keys=['actualQty','quantity','qty','onHand','currentQty','stock','amount'];
    for(var i=0;i<keys.length;i++){var n=Number(row&&row[keys[i]]);if(Number.isFinite(n))return n;}
    return null;
  }
  function stockUnit(row){return str(row&&(row.unit||row.stockUnit||row.baseUnit||row.qtyUnit)).trim();}
  function purchasingLine(ing){
    var q=Number(ing&&ing.qty),u=str(ing&&ing.unit).trim(),st=ingredientStock(ing);
    if(!st){
      return Number.isFinite(q)&&q>0&&u ? 'Need '+q+' '+u+' for one batch · not linked to Stock (optional).' : 'Not linked to Stock — optional.';
    }
    var have=stockQty(st),su=stockUnit(st);
    if(have==null)return 'Linked to '+stockName(st)+' · stock quantity not set.';
    var need=convertQty(q,u,su);
    if(need==null)return 'Linked to '+stockName(st)+' · '+have+' '+su+' on hand · check unit conversion.';
    var short=Math.max(0,need-have);
    return short>0?'Linked to '+stockName(st)+' · order about '+(Math.round(short*100)/100)+' '+su+' for one batch.':'Linked to '+stockName(st)+' · enough on hand for one batch.';
  }

  function notify(msg,bad){
    try{if(typeof toast==='function'){toast(msg,bad?'bad':'ok');return;}}catch(e){}
    if(bad)console.warn('[Command de Cuisine] '+msg);else console.info('[Command de Cuisine] '+msg);
  }
  function closeOverlay(){var x=document.getElementById(OVERLAY);if(x)x.remove();}
  async function saveState(reason){
    if(typeof save==='function'){
      var r=save(reason);
      if(r&&typeof r.then==='function')await r;
      return;
    }
    if(typeof persist==='function')await persist(reason);
  }
  function currentUser(){try{return (ME&&(ME.name||ME.username))||'manager';}catch(e){return 'manager';}}
  function snapshot(recipe,reason){
    try{
      var copy=JSON.parse(JSON.stringify(recipe));delete copy.versions;
      recipe.versions=Array.isArray(recipe.versions)?recipe.versions:[];
      recipe.versions.push({id:'rv_'+Date.now()+'_'+Math.random().toString(36).slice(2,7),data:copy,reason:reason,savedAt:new Date().toISOString(),savedBy:currentUser()});
      if(recipe.versions.length>20)recipe.versions=recipe.versions.slice(-20);
    }catch(e){}
  }

  function recomputeRecipe(recipe){
    var oldDrafts=parseAllergens(recipe.allergenDrafts).concat(parseAllergens(recipe.allergens));
    var selected=[];
    (recipe.ingredients||[]).forEach(function(ing){selected=selected.concat(ingredientAllergens(ing));});
    selected=uniqueAllergens(selected.concat(parseAllergens(recipe.extraAllergens)));
    var remainingDrafts=uniqueAllergens(oldDrafts).filter(function(a){return selected.indexOf(a)<0;});
    recipe.allergens=selected.join(', ');
    recipe.allergenDrafts=remainingDrafts;
    recipe.allergenReviewRequired=(recipe.ingredients||[]).some(function(ing){return !ingredientConfirmed(ing);})||remainingDrafts.length>0;
    recipe.needsReview=recipe.allergenReviewRequired;
    recipe.ingredientAllergensManaged=true;
  }

  function addCss(){
    if(document.getElementById('cdc-allergen-v6-css'))return;
    var st=document.createElement('style');st.id='cdc-allergen-v6-css';
    st.textContent=
      '.cdc-a6{display:flex;flex-direction:column;gap:12px}.cdc-a6-head{display:flex;gap:10px;justify-content:space-between;align-items:flex-start;flex-wrap:wrap}.cdc-a6-head h2{margin:0}.cdc-a6-copy{font-size:13px;line-height:1.45;color:var(--muted,#9ca6b3);max-width:760px}.cdc-a6-actions{display:flex;gap:8px;flex-wrap:wrap}.cdc-a6-search{width:min(380px,100%);box-sizing:border-box;padding:10px;border-radius:10px;border:1px solid var(--line,#35404b);background:var(--panel2,#20262e);color:var(--text,#fff);font:inherit}.cdc-a6-scroll{overflow:auto;-webkit-overflow-scrolling:touch;max-height:calc(100vh - 235px);border:1px solid var(--line,#35404b);border-radius:12px;overscroll-behavior:contain}.cdc-a6-table{border-collapse:separate;border-spacing:0;min-width:1090px;width:100%;background:var(--card,#1c2229)}.cdc-a6-table th,.cdc-a6-table td{border-right:1px solid var(--line,#35404b);border-bottom:1px solid var(--line,#35404b);padding:8px 6px;text-align:center;font-size:12px}.cdc-a6-table thead th{position:sticky;top:0;z-index:6;background:var(--panel,#1b2027);font-size:10px;line-height:1.15}.cdc-a6-table th:first-child,.cdc-a6-table td:first-child{position:sticky;left:0;z-index:5;background:var(--panel,#1b2027);min-width:205px;text-align:left}.cdc-a6-table thead th:first-child{z-index:8}.cdc-a6-dish{appearance:none;border:0;background:none;color:var(--brass,#e6ab31);padding:0;text-align:left;font:inherit;font-weight:800;text-decoration:underline;text-underline-offset:3px;cursor:pointer;width:100%}.cdc-a6-mark{font-size:16px;font-weight:900}.cdc-a6-mark.ok{color:var(--ok,#48b875)}.cdc-a6-mark.draft{color:var(--warn,#d99b2b)}.cdc-a6-review{display:block;margin-top:3px;font-size:9px;text-transform:uppercase;letter-spacing:.05em;color:var(--warn,#d99b2b)}.cdc-a6-empty{padding:20px;color:var(--muted,#9ca6b3)}'+
      '.cdc-a6-overlay{position:fixed;inset:0;z-index:10150;background:rgba(0,0,0,.76);display:flex;align-items:flex-end;justify-content:center;padding:10px}.cdc-a6-modal{width:min(860px,100%);max-height:94vh;overflow:auto;background:var(--card,#1c2229);border:1px solid var(--line,#35404b);border-radius:18px 18px 12px 12px;padding:14px;box-shadow:0 20px 60px rgba(0,0,0,.55)}.cdc-a6-modalhead{display:flex;gap:10px;align-items:flex-start;margin-bottom:12px}.cdc-a6-modalhead>div{flex:1}.cdc-a6-modalhead h3{margin:2px 0 0}.cdc-a6-kicker{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted,#9ca6b3)}.cdc-a6-box{border:1px solid var(--line,#35404b);background:var(--panel2,#20262e);border-radius:11px;padding:11px;margin:9px 0}.cdc-a6-box strong{display:block;margin-bottom:4px}.cdc-a6-list{display:grid;gap:8px}.cdc-a6-ing{width:100%;text-align:left;border:1px solid var(--line,#35404b);background:var(--panel2,#20262e);color:var(--text,#fff);border-radius:11px;padding:10px;font:inherit;cursor:pointer}.cdc-a6-ingtop{display:flex;gap:10px;justify-content:space-between}.cdc-a6-name{font-weight:800}.cdc-a6-meta{font-size:12px;color:var(--muted,#9ca6b3);line-height:1.4;margin-top:4px}.cdc-a6-green{color:var(--ok,#48b875)}.cdc-a6-amber{color:var(--warn,#d99b2b)}.cdc-a6-fields{display:grid;grid-template-columns:2fr 1fr 1fr;gap:8px}.cdc-a6-field{display:flex;flex-direction:column;gap:5px}.cdc-a6-field span{font-size:12px;color:var(--muted,#9ca6b3)}.cdc-a6-field input,.cdc-a6-field select,.cdc-a6-field textarea{width:100%;box-sizing:border-box;padding:10px;border-radius:10px;border:1px solid var(--line,#35404b);background:var(--panel2,#20262e);color:var(--text,#fff);font:inherit}.cdc-a6-full{grid-column:1/-1}.cdc-a6-picks{display:flex;flex-wrap:wrap;gap:6px}.cdc-a6-chip{border:1px solid var(--line,#35404b);border-radius:999px;padding:8px 10px;background:var(--panel2,#20262e);color:var(--muted,#9ca6b3);font:inherit;font-size:12px}.cdc-a6-chip.on{border-color:var(--brass,#e6ab31);background:rgba(230,171,49,.16);color:var(--text,#fff);font-weight:800}.cdc-a6-buttons{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;margin-top:12px}.cdc-a6-status{min-height:18px;font-size:12px;color:var(--muted,#9ca6b3);margin-top:8px}.cdc-a6-status.bad{color:var(--danger,#e06666)}.cdc-a6-note{font-size:12px;line-height:1.45;color:var(--muted,#9ca6b3)}'+
      '@media(max-width:650px){.cdc-a6-scroll{max-height:calc(100vh - 245px)}.cdc-a6-table{min-width:1030px}.cdc-a6-table th:first-child,.cdc-a6-table td:first-child{min-width:170px}.cdc-a6-modal{padding:11px}.cdc-a6-fields{grid-template-columns:1fr 1fr}.cdc-a6-fields .cdc-a6-namefield,.cdc-a6-full{grid-column:1/-1}}';
    document.head.appendChild(st);
  }

  function button(label,cls,fn){var b=document.createElement('button');b.type='button';b.className=cls||'btn ghost';b.textContent=label;if(fn)b.onclick=fn;return b;}
  function field(label,el,cls){var w=document.createElement('label');w.className='cdc-a6-field'+(cls?' '+cls:'');var s=document.createElement('span');s.textContent=label;w.append(s,el);return w;}
  function input(type,value){var x=document.createElement('input');x.type=type||'text';x.value=value==null?'':String(value);return x;}
  function stockSelect(value){
    var sel=document.createElement('select');
    var opt=document.createElement('option');opt.value='';opt.textContent='Not linked to Stock';sel.appendChild(opt);
    stock().slice().sort(function(a,b){return stockName(a).localeCompare(stockName(b));}).forEach(function(st){
      var o=document.createElement('option');o.value=str(st.id);o.textContent=stockName(st)||str(st.id);sel.appendChild(o);
    });
    sel.value=value?String(value):'';
    return sel;
  }
  function picker(initial){
    var box=document.createElement('div');box.className='cdc-a6-picks';
    var chosen=new Set(uniqueAllergens(initial||[]));
    function draw(){
      box.innerHTML='';
      ALLERGENS.forEach(function(a){
        var b=button(a,'cdc-a6-chip'+(chosen.has(a)?' on':''));
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
    recipe=recipeById(recipe&&recipe.id)||recipe;
    if(!recipe)return;
    closeOverlay();addCss();
    var overlay=document.createElement('div');overlay.id=OVERLAY;overlay.className='cdc-a6-overlay';
    var modal=document.createElement('div');modal.className='cdc-a6-modal';overlay.appendChild(modal);
    var head=document.createElement('div');head.className='cdc-a6-modalhead';
    head.innerHTML='<div><div class="cdc-a6-kicker">Recipe & ingredient allergens</div><h3>'+esc(recipe.name||'Recipe')+'</h3></div>';
    head.appendChild(button('Close','btn ghost',closeOverlay));modal.appendChild(head);

    var state=recipeAllergenState(recipe);
    var summary=document.createElement('div');summary.className='cdc-a6-box';
    summary.innerHTML='<strong>Allergen summary</strong>'+
      '<div class="cdc-a6-green"><b>Confirmed:</b> '+esc(state.confirmed.length?state.confirmed.join(', '):'None confirmed yet')+'</div>'+
      '<div class="cdc-a6-amber"><b>Draft / check:</b> '+esc(state.draft.length?state.draft.join(', '):'None')+'</div>'+
      '<div class="cdc-a6-note">Amber items are automatic/draft information only. Confirm against the actual ingredient label or supplier specification.</div>';
    modal.appendChild(summary);

    var items=Array.isArray(recipe.ingredients)?recipe.ingredients:[];
    var note=document.createElement('div');note.className='cdc-a6-note';
    note.textContent=items.length+' ingredients · tap an ingredient to change quantity, optional Stock link or allergens. The matrix itself cannot change anything.';
    modal.appendChild(note);

    var list=document.createElement('div');list.className='cdc-a6-list';
    if(!items.length){
      var empty=document.createElement('div');empty.className='cdc-a6-empty';empty.textContent='No ingredients saved yet.';list.appendChild(empty);
    }else{
      items.forEach(function(ing,index){
        var b=document.createElement('button');b.type='button';b.className='cdc-a6-ing';
        var chosen=ingredientAllergens(ing),suggest=ingredientSuggestions(ing),confirmed=ingredientConfirmed(ing);
        b.innerHTML='<div class="cdc-a6-ingtop"><span class="cdc-a6-name">'+esc(ing.name||'Ingredient')+'</span><span>'+esc([ing.qty,ing.unit].filter(function(v){return v!=null&&str(v)!=='';}).join(' '))+'</span></div>'+
          (ing.preparation?'<div class="cdc-a6-meta">'+esc(ing.preparation)+'</div>':'')+
          '<div class="'+(confirmed?'cdc-a6-green':'cdc-a6-amber')+'"><b>'+(confirmed?'Confirmed allergens:':'Selected draft allergens:')+'</b> '+esc(chosen.length?chosen.join(', '):'None')+'</div>'+
          (suggest.length?'<div class="cdc-a6-amber"><b>Auto suggestions:</b> '+esc(suggest.join(', '))+'</div>':'')+
          '<div class="cdc-a6-meta">'+esc(purchasingLine(ing))+'</div>';
        b.onclick=function(){openIngredient(recipe,index);};
        list.appendChild(b);
      });
    }
    modal.appendChild(list);

    var actions=document.createElement('div');actions.className='cdc-a6-buttons';
    actions.appendChild(button('+ Add ingredient','btn ghost',function(){openIngredient(recipe,-1);}));
    actions.appendChild(button('Close','btn primary',closeOverlay));
    modal.appendChild(actions);
    document.body.appendChild(overlay);
    overlay.onclick=function(e){if(e.target===overlay)closeOverlay();};
  }

  function openIngredient(recipe,index){
    recipe=recipeById(recipe&&recipe.id)||recipe;
    if(!recipe)return;
    var existing=index>=0&&Array.isArray(recipe.ingredients)?recipe.ingredients[index]:null;
    closeOverlay();addCss();

    var overlay=document.createElement('div');overlay.id=OVERLAY;overlay.className='cdc-a6-overlay';
    var modal=document.createElement('div');modal.className='cdc-a6-modal';overlay.appendChild(modal);
    var head=document.createElement('div');head.className='cdc-a6-modalhead';
    head.innerHTML='<div><div class="cdc-a6-kicker">'+(existing?'Edit ingredient':'Add ingredient')+'</div><h3>'+esc(recipe.name||'Recipe')+'</h3></div>';
    head.appendChild(button('Back','btn ghost',function(){openDish(recipe);}));modal.appendChild(head);

    var grid=document.createElement('div');grid.className='cdc-a6-fields';
    var name=input('text',existing&&existing.name||'');
    var qty=input('number',existing&&existing.qty!=null?existing.qty:'');qty.step='any';qty.min='0';qty.inputMode='decimal';
    var unit=input('text',existing&&existing.unit||'');
    var prep=input('text',existing&&(existing.preparation||existing.note)||'');
    var link=stockSelect(existing&&existing.stockId||'');
    grid.append(field('Ingredient',name,'cdc-a6-namefield'),field('Qty',qty),field('Unit',unit),field('Preparation / note',prep,'cdc-a6-full'),field('Stock link (optional)',link,'cdc-a6-full'));
    modal.appendChild(grid);

    var current=existing?ingredientAllergens(existing):[];
    var picks=picker(current);
    var allergensBox=document.createElement('div');allergensBox.className='cdc-a6-box';
    allergensBox.innerHTML='<strong>Ingredient allergens</strong><div class="cdc-a6-note">Tap allergens from the actual product you use. Nothing changes until Save ingredient.</div>';
    allergensBox.appendChild(picks);modal.appendChild(allergensBox);

    var suggestions=existing?ingredientSuggestions(existing):autoSuggestions({name:name.value});
    var suggestionBox=document.createElement('div');suggestionBox.className='cdc-a6-box';
    suggestionBox.innerHTML='<strong>Automatic draft suggestions</strong><div class="cdc-a6-amber">'+esc(suggestions.length?suggestions.join(', '):'No automatic allergen suggestion')+'</div><div class="cdc-a6-note">Suggestions are not confirmed. Check the label/spec first.</div>';
    if(suggestions.length)suggestionBox.appendChild(button('Use suggestions','btn ghost',function(){picks.setValue(suggestions);}));
    modal.appendChild(suggestionBox);

    var order=document.createElement('div');order.className='cdc-a6-box';
    order.innerHTML='<strong>Stock / ordering</strong><div class="cdc-a6-note">'+esc(purchasingLine(existing||{name:name.value,qty:qty.value,unit:unit.value,stockId:link.value}))+'</div>';
    modal.appendChild(order);

    var status=document.createElement('div');status.className='cdc-a6-status';modal.appendChild(status);
    var actions=document.createElement('div');actions.className='cdc-a6-buttons';

    if(existing){
      actions.appendChild(button('Remove ingredient','btn danger',async function(){
        if(!window.confirm('Remove '+(existing.name||'this ingredient')+' from this recipe?'))return;
        try{
          var r=recipeById(recipe.id)||recipe;snapshot(r,'remove recipe ingredient');
          r.ingredients.splice(index,1);recomputeRecipe(r);
          if(typeof audit==='function')try{audit('recipe_ingredient_removed',r.name+' · '+(existing.name||''));}catch(e){}
          await saveState('remove recipe ingredient');
          if(typeof rerender==='function')rerender();
          notify('Ingredient removed');openDish(r);
        }catch(err){status.className='cdc-a6-status bad';status.textContent='Not removed: '+(err&&err.message?err.message:String(err));}
      }));
    }

    var saveBtn=button('Save ingredient','btn primary',async function(){
      saveBtn.disabled=true;status.className='cdc-a6-status';status.textContent='Saving…';
      try{
        var nm=name.value.trim(),q=Number(qty.value),u=unit.value.trim();
        if(!nm)throw new Error('Ingredient name is required.');
        if(!Number.isFinite(q)||q<0)throw new Error('Quantity must be a valid number.');
        if(!u)throw new Error('Unit is required.');
        var r=recipeById(recipe.id)||recipe;snapshot(r,'edit recipe ingredient');
        r.ingredients=Array.isArray(r.ingredients)?r.ingredients:[];
        var next=Object.assign({},existing||{});
        next.name=nm;next.qty=q;next.unit=u;
        if(prep.value.trim())next.preparation=prep.value.trim();else delete next.preparation;
        if(link.value)next.stockId=link.value;else delete next.stockId;
        next.allergens=picks.value();
        next.allergenSource='manager-edit';
        next.allergenVerified=true;
        next.allergenReviewedAt=new Date().toISOString();
        if(suggestions.length)next.allergenSuggestions=uniqueAllergens((next.allergenSuggestions||[]).concat(suggestions));
        if(index>=0)r.ingredients[index]=next;else r.ingredients.push(next);
        recomputeRecipe(r);
        if(typeof audit==='function')try{audit('recipe_ingredient_updated',r.name+' · '+nm);}catch(e){}
        await saveState('update recipe ingredient');
        if(typeof rerender==='function')rerender();
        notify('Ingredient saved · recipe and matrix updated');
        openDish(r);
      }catch(err){
        status.className='cdc-a6-status bad';status.textContent='Not saved: '+(err&&err.message?err.message:String(err));saveBtn.disabled=false;
      }
    });
    actions.appendChild(saveBtn);modal.appendChild(actions);
    document.body.appendChild(overlay);
    overlay.onclick=function(e){if(e.target===overlay)openDish(recipe);};
  }

  function renderAllergens(v){
    try{
      addCss();
      if(!v||!v.appendChild)throw new Error('Allergen view container missing');
      v.innerHTML='';
      var wrap=document.createElement('div');wrap.className='cdc-a6';

      var head=document.createElement('div');head.className='cdc-a6-head';
      var copy=document.createElement('div');
      copy.innerHTML='<h2>Allergen matrix</h2><div class="cdc-a6-copy">View-only matrix. Tap a dish name to open its recipe ingredients. Allergens can only be changed inside an ingredient and only after pressing Save.<br><b style="color:var(--ok,#48b875)">● green</b> = confirmed · <b style="color:var(--warn,#d99b2b)">◐ amber</b> = automatic/draft, check the product label/spec.</div>';
      var actions=document.createElement('div');actions.className='cdc-a6-actions';
      if(typeof window.printAllergenMatrix==='function')actions.appendChild(button('Print matrix','btn ghost',window.printAllergenMatrix));
      if(typeof window.printDishAllergens==='function')actions.appendChild(button('Print dish sheets','btn ghost',window.printDishAllergens));
      head.append(copy,actions);wrap.appendChild(head);

      var search=input('search','');search.className='cdc-a6-search';search.placeholder='Search dishes…';wrap.appendChild(search);
      var scroll=document.createElement('div');scroll.className='cdc-a6-scroll';
      var table=document.createElement('table');table.className='cdc-a6-table';
      table.innerHTML='<thead><tr><th>Dish</th>'+ALLERGENS.map(function(a){return '<th>'+esc(a)+'</th>';}).join('')+'</tr></thead><tbody></tbody>';
      var body=table.querySelector('tbody');

      function draw(){
        body.innerHTML='';
        var q=norm(search.value);
        var rows=recipes().slice().sort(function(a,b){return str(a&&a.name).localeCompare(str(b&&b.name));}).filter(function(r){return !q||norm(r&&r.name).indexOf(q)>=0;});
        if(!rows.length){
          var none=document.createElement('tr');none.innerHTML='<td colspan="'+(ALLERGENS.length+1)+'" class="cdc-a6-empty">No dishes found.</td>';body.appendChild(none);return;
        }
        rows.forEach(function(r){
          try{
            var state=recipeAllergenState(r),confirmed=new Set(state.confirmed),draft=new Set(state.draft);
            var tr=document.createElement('tr'),td=document.createElement('td');
            var dish=button(r.name||'Untitled dish','cdc-a6-dish',function(){openDish(r);});td.appendChild(dish);
            if(r.allergenReviewRequired||r.needsReview||draft.size){var badge=document.createElement('span');badge.className='cdc-a6-review';badge.textContent='Review';td.appendChild(badge);}
            tr.appendChild(td);
            ALLERGENS.forEach(function(a){
              var cell=document.createElement('td');cell.className='cdc-a6-mark';
              if(confirmed.has(a)){cell.textContent='●';cell.classList.add('ok');cell.setAttribute('aria-label',a+' confirmed');}
              else if(draft.has(a)){cell.textContent='◐';cell.classList.add('draft');cell.setAttribute('aria-label',a+' draft');}
              tr.appendChild(cell);
            });
            body.appendChild(tr);
          }catch(rowErr){
            console.error('[Command de Cuisine] allergen row failed',r&&r.id,rowErr);
          }
        });
      }

      search.addEventListener('input',draw);draw();
      scroll.appendChild(table);wrap.appendChild(scroll);v.appendChild(wrap);
    }catch(err){
      console.error('[Command de Cuisine] allergen matrix failed',err);
      if(v&&v.innerHTML!==undefined){
        v.innerHTML='<div class="card" style="padding:16px"><h2>Allergen matrix</h2><p class="muted">The allergen screen hit a display error. No recipe or allergen data was changed.</p><button type="button" class="btn primary" id="cdc-a6-retry">Retry</button></div>';
        var retry=v.querySelector&&v.querySelector('#cdc-a6-retry');if(retry)retry.onclick=function(){renderAllergens(v);};
      }
    }
  }

  renderAllergens.__cdcSafeAllergenView=true;

  function lockRoute(){
    try{
      if(typeof VIEWS==='undefined'||!VIEWS)return false;
      ['allergens','allergen'].forEach(function(key){
        try{
          var d=Object.getOwnPropertyDescriptor(VIEWS,key);
          if(!d||d.configurable){
            Object.defineProperty(VIEWS,key,{
              configurable:true,enumerable:true,
              get:function(){return renderAllergens;},
              set:function(fn){if(fn===renderAllergens)return;}
            });
          }else{
            VIEWS[key]=renderAllergens;
          }
        }catch(e){try{VIEWS[key]=renderAllergens;}catch(_e){}}
      });
      return true;
    }catch(e){return false;}
  }

  function install(){
    addCss();
    lockRoute();
    window.CDCRecipeWorkspace={
      open:function(id){var r=recipeById(id);if(r)openDish(r);},
      editIngredient:function(id,index){var r=recipeById(id);if(r)openIngredient(r,index);},
      render:renderAllergens
    };
    console.info('[Command de Cuisine] stable allergen workspace v6 active');
  }

  document.addEventListener('click',function(e){
    try{
      var el=e.target&&e.target.closest?e.target.closest('button,a,[data-route],[data-view]'):null;
      if(!el)return;
      var key=norm((el.dataset&&(el.dataset.route||el.dataset.view))||el.textContent);
      if(key.indexOf('allergen')>=0)lockRoute();
    }catch(_e){}
  },true);

  var attempts=0,timer=setInterval(function(){attempts++;if(lockRoute()||attempts>80)clearInterval(timer);},100);
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})();