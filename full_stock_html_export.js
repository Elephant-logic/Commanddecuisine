/* Complete, offline-editable Stock list: read-only export. No stock deductions. */
(function(){
  'use strict';
  if(window.__cdcFullStockExportReady)return;
  window.__cdcFullStockExportReady=true;
  function val(x){return x==null?'':String(x).trim()}
  function norm(x){return val(x).toLowerCase().replace(/\s+/g,' ')}
  function array(x){return Array.isArray(x)?x:[]}
  function fullList(){
    if(typeof STATE==='undefined')throw new Error('Kitchen data has not loaded.');
    var all=[],byId=new Map(),byName=new Map(),unlinked=new Map(),seq=0;
    array(STATE.stock).forEach(function(s){
      if(!s)return;
      var name=val(s.item||s.name);
      if(!name)return;
      var row={id:'stock_'+(++seq),name:name,category:val(s.cat||s.category)||'Other',
        unit:val(s.unit)||'each',supplier:val(s.supplier),quantity:'',ordered:false,
        notes:'',origin:'Stock catalogue',usedIn:[],needsReview:false};
      all.push(row);
      if(s.id!=null)byId.set(String(s.id),row);
      var n=norm(name);
      if(!byName.has(n))byName.set(n,[]);
      byName.get(n).push(row);
    });
    array(STATE.recipes).forEach(function(recipe){
      if(!recipe)return;
      var dish=val(recipe.name)||'Unnamed recipe';
      array(recipe.ingredients).forEach(function(ingredient){
        if(!ingredient)return;
        var name=val(ingredient.name||ingredient.item);
        if(!name)return;
        var unit=val(ingredient.unit)||'each';
        var matches=byName.get(norm(name))||[];
        var explicit=ingredient.stockId==null?null:byId.get(String(ingredient.stockId));
        // The name is only used to avoid duplicate listing; no links/data are written.
        var existing=explicit||(matches.length===1?matches[0]:null);
        if(existing){if(!existing.usedIn.includes(dish))existing.usedIn.push(dish);return}
        var key=norm(name)+'|'+norm(unit);
        var row=unlinked.get(key);
        if(!row){
          row={id:'recipe_'+(++seq),name:name,category:'Recipe ingredient',unit:unit,
            supplier:'',quantity:'',ordered:false,notes:'',origin:'Recipe ingredient',
            usedIn:[],needsReview:matches.length>1};
          unlinked.set(key,row);all.push(row);
        }
        if(!row.usedIn.includes(dish))row.usedIn.push(dish);
      });
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