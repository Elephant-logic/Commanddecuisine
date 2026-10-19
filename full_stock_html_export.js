/* Complete, offline-editable Stock list: read-only export. No stock deductions. */
(function(){
  'use strict';
  if(window.__cdcFullStockExportReady)return;
  window.__cdcFullStockExportReady=true;
  function val(x){return x==null?'':String(x).trim()}
  function valNorm(x){
    return val(x).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase()
      .replace(/[^a-z0-9]+/g,' ').trim();
  }
  const ALIASES={
    'chili powder':'chilli powder',
    'mozzarella cheese':'mozzarella',
    'parmesan cheese':'parmesan',
    'tomato paste':'tomato puree',
    'fresh parsley':'parsley',
    'cilantro':'fresh coriander',
    'nacho chips':'tortilla chips',
    'plain yoghurt':'natural yoghurt',
    'salt to taste':'salt',
    'ginger':'fresh ginger',
    'tomato slices':'tomatoes'
  };
  const PREFERRED={
    'chilli powder':'Chilli powder',
    'fresh coriander':'Fresh coriander',
    'fresh ginger':'Fresh ginger',
    'natural yoghurt':'Natural yoghurt',
    'tomato puree':'Tomato purée',
    'tomatoes':'Tomatoes',
    'tortilla chips':'Tortilla chips',
    'parsley':'Parsley'
  };
  function norm(x){const n=valNorm(x);return ALIASES[n]||n}
  function array(x){return Array.isArray(x)?x:[]}
  function appendNote(row,msg){
    if(!msg || row.notes.includes(msg))return;
    row.notes+=(row.notes?'; ':'')+msg;
  }
  function fullList(){
    if(typeof STATE==='undefined')throw new Error('Kitchen data has not loaded.');
    var all=[],byId=new Map(),byName=new Map(),seq=0;
    array(STATE.stock).forEach(function(s){
      if(!s)return;
      var name=val(s.item||s.name), key=norm(name);
      if(!key)return;
      // This is a recipe instruction, not a separate purchasable item.
      // Salt and black pepper have their own independent catalogue lines.
      if(key==='salt and black pepper to taste')return;
      var row=byName.get(key);
      if(!row){
        row={id:'stock_'+(++seq),name:PREFERRED[key]||name,
          category:val(s.cat||s.category)||'Other',
          unit:val(s.unit)||'each',supplier:val(s.supplier),quantity:'',ordered:false,
          notes:'',origin:'Stock catalogue',usedIn:[],needsReview:false};
        all.push(row);byName.set(key,row);
      }else{
        if(val(s.unit) && val(s.unit)!==row.unit){
          row.needsReview=true;appendNote(row,'Confirm unit; another catalogue entry uses '+val(s.unit));
        }
        if(val(s.supplier) && val(s.supplier)!==row.supplier){
          row.needsReview=true;appendNote(row,'Other supplier: '+val(s.supplier));
        }
        if(name.toLowerCase()!==row.name.toLowerCase())
          appendNote(row,'Also listed as: '+name);
      }
      if(s.id!=null)byId.set(String(s.id),row);
    });
    var salt=byName.get('salt'),pepper=byName.get('black pepper');
    if(salt)appendNote(salt,'Also used in “Salt and black pepper, to taste”');
    if(pepper)appendNote(pepper,'Also used in “Salt and black pepper, to taste”');
    array(STATE.recipes).forEach(function(recipe){
      if(!recipe)return;
      var dish=val(recipe.name)||'Unnamed recipe';
      array(recipe.ingredients).forEach(function(ingredient){
        if(!ingredient)return;
        var name=val(ingredient.name||ingredient.item),key=norm(name);
        if(!key)return;
        if(key==='salt and black pepper to taste'){
          [salt,pepper].forEach(function(row){
            if(row&&!row.usedIn.includes(dish))row.usedIn.push(dish);
          });
          return;
        }
        var unit=val(ingredient.unit)||'each';
        var explicit=ingredient.stockId==null?null:byId.get(String(ingredient.stockId));
        var existing=explicit||byName.get(key);
        if(existing){
          if(!existing.usedIn.includes(dish))existing.usedIn.push(dish);
          return;
        }
        var row={id:'recipe_'+(++seq),name:PREFERRED[key]||name,
          category:'Recipe ingredient',unit:unit,
          supplier:'',quantity:'',ordered:false,notes:'',
          origin:'Recipe ingredient',usedIn:[dish],needsReview:false};
        all.push(row);byName.set(key,row);
      });
    });
    // Review alternatives instead of quietly choosing a product on behalf of the kitchen.
    all.forEach(function(row){
      if(/\sor\s/i.test(row.name)){
        row.needsReview=true;appendNote(row,'Choose which of the recipe alternatives to order');
      }
      var k=norm(row.name);
      if(k==='tomato puree'){
        row.needsReview=true;appendNote(row,'Confirm tomato paste and purée are interchangeable for the supplier');
      }
      if(k==='tortilla chips'){
        row.needsReview=true;appendNote(row,'Confirm nacho chips and tortilla chips are the same product');
      }
    });
    return all.sort(function(a,b){return a.category.localeCompare(b.category)||a.name.localeCompare(b.name)});
  }
  async function exportHtml(){
    try{
      var items=fullList();
      if(!items.length){alert('No Stock catalogue or saved recipe ingredients found. Save your imported menu/recipes first.');return}
      var response=await fetch('/full_stock_order_template.html?v=20261019-full1',{credentials:'same-origin'});
      if(!response.ok)throw new Error('Stock order template is unavailable');
      var template=await response.text();
      var regex=/(<script type="application\/json" id="order-data">)[\s\S]*?(<\/script>)/;
      if(!regex.test(template))throw new Error('Stock order template is invalid');
      var data=JSON.stringify({title:'Complete Kitchen Stock List',created:new Date().toISOString(),items:items})
        .replace(/</g,'\\u003c');
      var html=template.replace(regex,function(match,open,close){return open+data+close});
      var blob=new Blob([html],{type:'text/html;charset=utf-8'});
      var url=URL.createObjectURL(blob),a=document.createElement('a');
      a.href=url;a.download='Command-de-Cuisine-Full-Stock-'+new Date().toISOString().slice(0,10)+'.html';
      document.body.appendChild(a);a.click();a.remove();
      setTimeout(function(){URL.revokeObjectURL(url)},2000);
      if(typeof toast==='function')toast('Downloaded complete, editable Stock list','ok');
    }catch(err){console.error('Complete Stock export failed',err);alert('Could not export the full Stock list: '+(err&&err.message||err))}
  }
  function launcher(view){
    if(!view||typeof view.querySelector!=='function'||view.querySelector('.cdc-full-stock-export'))return;
    var box=document.createElement('div');box.className='cdc-full-stock-export';
    box.style.cssText='display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:13px;margin:0 0 14px;border:1px solid var(--line,#ddd);border-radius:12px;background:var(--card,#fff)';
    var copy=document.createElement('div');copy.style.cssText='flex:1;min-width:195px';
    var h=document.createElement('strong');h.textContent='Download the FULL Stock list';
    var p=document.createElement('div');p.textContent='Every catalogue item plus every saved recipe ingredient, even when already in Stock. Edit, add and remove items offline.';
    p.style.cssText='font-size:12px;opacity:.75;margin-top:4px';copy.append(h,p);
    var b=document.createElement('button');b.type='button';b.className='btn primary';
    b.textContent='Download full editable HTML';b.addEventListener('click',exportHtml);
    box.append(copy,b);view.prepend(box);
  }
  function install(){
    if(typeof VIEWS==='undefined'||!VIEWS)return;
    ['stock','menus','menu'].forEach(function(name){
      try{
        var fn=VIEWS[name];
        if(typeof fn!=='function'||fn.__cdcFullStockWrapped)return;
        var wrapper=function(){var output=fn.apply(this,arguments);launcher(arguments[0]);return output};
        wrapper.__cdcFullStockWrapped=true;
        VIEWS[name]=wrapper;
      }catch(err){console.warn('Stock export launcher:',err)}
    });
  }
  window.CDCDownloadFullStockHTML=exportHtml;
  install();setInterval(install,1200);
})();