(()=>{
  'use strict';

  const STYLE_ID='cdc-recipe-import-style';
  const OVERLAY_ID='cdc-recipe-import-overlay';

  function addStyle(){
    if(document.getElementById(STYLE_ID)) return;
    const s=document.createElement('style');
    s.id=STYLE_ID;
    s.textContent=`
      .cdc-recipe-import-card{margin-bottom:16px;padding:14px;border:1px solid var(--line,#35404b);border-radius:14px;background:var(--card,#1c2229)}
      .cdc-recipe-import-row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
      .cdc-recipe-import-copy{flex:1;min-width:190px}
      .cdc-recipe-import-copy b{display:block;margin-bottom:3px}
      .cdc-ri-overlay{position:fixed;inset:0;z-index:10020;background:rgba(0,0,0,.72);display:flex;align-items:flex-end;justify-content:center;padding:12px}
      .cdc-ri-modal{width:min(720px,100%);max-height:92vh;overflow:auto;background:var(--card,#1c2229);border:1px solid var(--line,#35404b);border-radius:18px 18px 12px 12px;padding:16px;box-shadow:0 18px 60px rgba(0,0,0,.55)}
      .cdc-ri-head{display:flex;align-items:center;gap:10px;margin-bottom:12px}.cdc-ri-head h3{margin:0;flex:1}
      .cdc-ri-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.cdc-ri-grid .full{grid-column:1/-1}
      .cdc-ri-field{display:flex;flex-direction:column;gap:5px}.cdc-ri-field span{font-size:12px;color:var(--muted,#9ca6b3)}
      .cdc-ri-field input,.cdc-ri-field select,.cdc-ri-field textarea{width:100%;box-sizing:border-box;background:var(--panel2,#20262e);color:var(--text,#f4f5f7);border:1px solid var(--line,#35404b);border-radius:10px;padding:10px;font:inherit}
      .cdc-ri-field textarea{min-height:100px;resize:vertical}.cdc-ri-actions{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;margin-top:12px}
      .cdc-ri-status{font-size:12px;color:var(--muted,#9ca6b3);margin-top:8px;min-height:18px}.cdc-ri-status.bad{color:var(--danger,#e06666)}.cdc-ri-status.good{color:var(--ok,#48b875)}
      .cdc-ri-sourcehint{font-size:12px;color:var(--muted,#9ca6b3);margin-top:4px}
      @media(max-width:620px){.cdc-ri-grid{grid-template-columns:1fr}.cdc-ri-grid .full{grid-column:auto}.cdc-ri-modal{padding:14px}}
    `;
    document.head.appendChild(s);
  }

  function btn(label, cls='btn primary'){
    const b=document.createElement('button'); b.type='button'; b.className=cls; b.textContent=label; return b;
  }

  function escText(v){ return v==null?'':String(v); }
  function outputText(r){
    try{
      const joined=(r.output||[]).flatMap(o=>o.content||[]).map(c=>c.text||c.output_text||'').join(' ').trim();
      return joined||r.output_text||'';
    }catch(_){ return r&&r.output_text||''; }
  }
  function parseJsonLoose(t){
    let x=String(t||'').trim().replace(/^```(?:json)?\s*/i,'').replace(/```\s*$/,'').trim();
    try{return JSON.parse(x);}catch(_){ }
    const a=x.indexOf('{'), b=x.lastIndexOf('}');
    if(a>=0&&b>a) return JSON.parse(x.slice(a,b+1));
    throw new Error('Could not read recipe details from the AI response.');
  }
  function fileDataUrl(file){
    return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(file);});
  }
  function ingredientLines(items){
    return (Array.isArray(items)?items:[]).map(i=>`${escText(i.name)} | ${escText(i.qty)} | ${escText(i.unit)}`).join('\n');
  }
  function parseIngredientLines(text){
    return String(text||'').split(/\n+/).map(s=>s.trim()).filter(Boolean).map(line=>{
      const p=line.split('|').map(x=>x.trim());
      if(p.length>=3){
        const q=Number(p[1]); return {name:p[0],qty:Number.isFinite(q)?q:p[1],unit:p[2]};
      }
      return {name:line,qty:1,unit:''};
    });
  }
  function linkIngredient(i){
    const out={name:i.name||'Ingredient',qty:i.qty==null?0:i.qty,unit:i.unit||''};
    try{ if(typeof stockByName==='function'){const s=stockByName(out.name);if(s)out.stockId=s.id;} }catch(_){ }
    return out;
  }

  function openImporter(){
    addStyle();
    document.getElementById(OVERLAY_ID)?.remove();
    const overlay=document.createElement('div'); overlay.id=OVERLAY_ID; overlay.className='cdc-ri-overlay';
    const modal=document.createElement('div'); modal.className='cdc-ri-modal'; overlay.appendChild(modal);

    const head=document.createElement('div'); head.className='cdc-ri-head';
    const h=document.createElement('h3'); h.textContent='Import / update recipe';
    const close=btn('Close','btn ghost'); close.onclick=()=>overlay.remove(); head.append(h,close); modal.appendChild(head);

    const grid=document.createElement('div'); grid.className='cdc-ri-grid'; modal.appendChild(grid);
    const field=(label,el,full=false)=>{const w=document.createElement('label');w.className='cdc-ri-field'+(full?' full':'');const s=document.createElement('span');s.textContent=label;w.append(s,el);grid.appendChild(w);return el;};

    const target=document.createElement('select');
    target.innerHTML='<option value="">Create a new recipe</option>';
    try{(STATE.recipes||[]).slice().sort((a,b)=>String(a.name||'').localeCompare(String(b.name||''))).forEach(r=>{const o=document.createElement('option');o.value=r.id;o.textContent='Update: '+(r.name||'Unnamed recipe');target.appendChild(o);});}catch(_){ }
    field('Save as',target,true);

    const photo=document.createElement('input'); photo.type='file'; photo.accept='image/*'; photo.setAttribute('capture','environment'); field('Recipe photo / camera',photo,true);
    const sourceNotes=document.createElement('textarea'); sourceNotes.placeholder='Paste or type handwritten/typed recipe notes here. You can use notes, a photo, or both.'; field('Recipe notes',sourceNotes,true);

    const read=btn('Read recipe from photo / notes');
    const readWrap=document.createElement('div');readWrap.className='full';readWrap.appendChild(read);grid.appendChild(readWrap);
    const status=document.createElement('div');status.className='cdc-ri-status full';grid.appendChild(status);

    const name=document.createElement('input'); field('Recipe name',name);
    const category=document.createElement('input'); category.placeholder='Starter, Main, Dessert…'; field('Category',category);
    const yieldEl=document.createElement('input'); yieldEl.placeholder='e.g. 10 portions'; field('Yield',yieldEl);
    const allergens=document.createElement('input'); allergens.placeholder='e.g. gluten, milk, egg'; field('Allergens',allergens);
    const ingredients=document.createElement('textarea'); ingredients.placeholder='One ingredient per line: Flour | 500 | g'; field('Ingredients — Name | Qty | Unit',ingredients,true);
    const method=document.createElement('textarea'); method.placeholder='Method / preparation steps'; field('Method',method,true);

    function loadExisting(){
      if(!target.value) return;
      try{
        const r=(STATE.recipes||[]).find(x=>String(x.id)===String(target.value)); if(!r)return;
        name.value=r.name||''; category.value=r.cat||r.category||''; yieldEl.value=r.yield||''; allergens.value=r.allergens||'';
        ingredients.value=ingredientLines(r.ingredients||[]); method.value=Array.isArray(r.method)?r.method.join('\n'):r.method||'';
      }catch(_){ }
    }
    target.onchange=loadExisting;

    read.onclick=async()=>{
      const f=photo.files&&photo.files[0];
      const notes=sourceNotes.value.trim();
      if(!f&&!notes){status.className='cdc-ri-status bad full';status.textContent='Add a recipe photo or some notes first.';return;}
      read.disabled=true; status.className='cdc-ri-status full'; status.textContent='Reading recipe…';
      try{
        let image=null; if(f) image=await fileDataUrl(f);
        let existing='';
        if(target.value){try{const r=(STATE.recipes||[]).find(x=>String(x.id)===String(target.value));if(r)existing=`\nExisting recipe being updated: ${JSON.stringify({name:r.name,category:r.cat,yield:r.yield,allergens:r.allergens,ingredients:r.ingredients,method:r.method})}`;}catch(_){}}
        const prompt=`Extract the professional kitchen recipe from the supplied photo and/or notes. Return JSON only with this exact shape: {"name":"","category":"","yield":"","allergens":"","ingredients":[{"name":"","qty":0,"unit":"g"}],"method":""}. Preserve stated quantities and units exactly where possible. Use practical units such as g, kg, oz, ml, L, each, pack, tin, bottle, tray, bunch. Method should be clear kitchen instructions. If a field is not present, return an empty string or empty array rather than inventing it.${existing}${notes?`\nSource notes:\n${notes}`:''}`;
        const content=[{type:'input_text',text:prompt}]; if(image)content.push({type:'input_image',image_url:image});
        if(typeof api!=='function') throw new Error('The app AI service is not available.');
        const res=await api('/api/openai/responses',{method:'POST',body:JSON.stringify({model:'gpt-4o-mini',input:[{role:'user',content}]})});
        const data=parseJsonLoose(outputText(res));
        if(data.name)name.value=data.name;
        if(data.category)category.value=data.category;
        if(data.yield)yieldEl.value=data.yield;
        if(data.allergens)allergens.value=Array.isArray(data.allergens)?data.allergens.join(', '):data.allergens;
        if(Array.isArray(data.ingredients)&&data.ingredients.length)ingredients.value=ingredientLines(data.ingredients);
        if(data.method)method.value=Array.isArray(data.method)?data.method.join('\n'):data.method;
        status.className='cdc-ri-status good full'; status.textContent='Recipe read. Check the details below, then save.';
      }catch(err){status.className='cdc-ri-status bad full';status.textContent='Could not read recipe: '+(err&&err.message?err.message:String(err));}
      finally{read.disabled=false;}
    };

    const actions=document.createElement('div'); actions.className='cdc-ri-actions'; modal.appendChild(actions);
    const cancel=btn('Cancel','btn ghost');cancel.onclick=()=>overlay.remove();
    const saveBtn=btn('Save recipe');
    saveBtn.onclick=()=>{
      const nm=name.value.trim(); if(!nm){status.className='cdc-ri-status bad full';status.textContent='Recipe name is required.';return;}
      try{
        let r=target.value?(STATE.recipes||[]).find(x=>String(x.id)===String(target.value)):null;
        const isNew=!r;
        if(!r) r={id:(typeof uid==='function'?uid('r'):'r_'+Date.now()),name:nm,cat:'Mains',allergens:'',method:'',cost:0,price:0,yield:'1',ingredients:[]};
        r.name=nm;
        r.cat=category.value.trim()||r.cat||'Other';
        r.yield=yieldEl.value.trim()||r.yield||'1';
        r.allergens=allergens.value.trim();
        r.method=method.value.trim();
        r.ingredients=parseIngredientLines(ingredients.value).map(linkIngredient);
        if(isNew) STATE.recipes.push(r);
        if(typeof audit==='function')audit(isNew?'import_recipe':'update_recipe_from_source',r.name);
        if(typeof save==='function')save(isNew?'import recipe':'update recipe from photo/notes');
        status.className='cdc-ri-status good full';status.textContent=isNew?'Recipe added.':'Recipe updated.';
        try{if(typeof toast==='function')toast(isNew?'Recipe added':'Recipe updated','ok');}catch(_){ }
        overlay.remove();
        try{if(typeof rerender==='function')rerender();}catch(_){ }
      }catch(err){status.className='cdc-ri-status bad full';status.textContent='Could not save recipe: '+(err&&err.message?err.message:String(err));}
    };
    actions.append(cancel,saveBtn);
    overlay.onclick=e=>{if(e.target===overlay)overlay.remove();};
    document.body.appendChild(overlay);
  }

  function addLauncher(v){
    if(!v||v.querySelector('.cdc-recipe-import-card')) return;
    const card=document.createElement('div');card.className='cdc-recipe-import-card';
    const row=document.createElement('div');row.className='cdc-recipe-import-row';
    const copy=document.createElement('div');copy.className='cdc-recipe-import-copy';copy.innerHTML='<b>Recipe upload</b><div class="muted">Create or update a recipe from a photo, camera image or pasted notes.</div>';
    const b=btn('Import / update recipe');b.onclick=openImporter;
    row.append(copy,b);card.appendChild(row);
    v.prepend(card);
  }

  function install(){
    try{
      if(typeof VIEWS==='undefined'||!VIEWS||typeof VIEWS.recipes!=='function') return false;
      if(VIEWS.recipes.__cdcRecipeImportWrapped) return true;
      const original=VIEWS.recipes;
      const wrapped=function(v){const r=original.apply(this,arguments);try{addLauncher(v);}catch(e){console.warn('recipe import launcher',e);}return r;};
      wrapped.__cdcRecipeImportWrapped=true; VIEWS.recipes=wrapped; addStyle(); return true;
    }catch(e){return false;}
  }
  let tries=0;const timer=setInterval(()=>{tries++;if(install()||tries>40)clearInterval(timer);},100);
})();
