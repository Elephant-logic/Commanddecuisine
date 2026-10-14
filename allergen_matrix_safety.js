/* Command de Cuisine - safe read-only allergen matrix */
(function(){
  'use strict';
  if(window.__cdcSafeAllergenMatrix) return;
  window.__cdcSafeAllergenMatrix=true;

  function text(el){ return String(el&&el.textContent||'').trim(); }

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

  function blockMatrixEdit(ev){
    var table=ev.currentTarget;
    if(!table || !table.contains(ev.target)) return;
    ev.preventDefault();
    ev.stopPropagation();
    if(typeof ev.stopImmediatePropagation==='function') ev.stopImmediatePropagation();
  }

  function lockInteractiveControls(table){
    var nodes=table.querySelectorAll('input,button,select,textarea,[role="checkbox"],[role="switch"],label');
    for(var i=0;i<nodes.length;i++){
      var el=nodes[i];
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
        if(ev.key==='Enter'||ev.key===' '){ blockMatrixEdit(ev); }
      },true);
    }
  }

  function addInfo(root,table){
    if(root.querySelector('.cdc-allergen-safe-note')) return;
    var note=document.createElement('div');
    note.className='cdc-allergen-safe-note';
    note.innerHTML='<div><strong>View only</strong><span>Change allergens in the recipe. The matrix updates from the recipe, so a scroll or accidental tap cannot alter allergen data.</span></div>';
    table.parentNode.insertBefore(note,table);
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
    lockInteractiveControls(table);
    return true;
  }

  function css(){
    if(document.getElementById('cdc-allergen-safe-css')) return;
    var style=document.createElement('style');
    style.id='cdc-allergen-safe-css';
    style.textContent=
      '.cdc-allergen-safe-note{margin:0 0 12px;padding:12px 14px;border:1px solid var(--line,#3b4652);border-radius:12px;background:var(--panel2,#20262e);display:flex;gap:10px;align-items:flex-start}.cdc-allergen-safe-note strong{display:block;color:var(--text,#f4f5f7);font-size:13px;margin-bottom:2px}.cdc-allergen-safe-note span{display:block;color:var(--muted,#9ca6b3);font-size:12px;line-height:1.4}.cdc-allergen-scroll{overflow:auto;max-height:min(68vh,720px);overscroll-behavior:contain;-webkit-overflow-scrolling:touch;border:1px solid var(--line,#35404b);border-radius:12px}.cdc-allergen-safe-table{min-width:1050px;border-collapse:separate!important;border-spacing:0!important}.cdc-allergen-safe-table thead th{position:sticky!important;top:0!important;z-index:5!important;background:var(--panel,#1b2027)!important;box-shadow:0 1px 0 var(--line,#35404b);white-space:nowrap}.cdc-allergen-safe-table th:first-child,.cdc-allergen-safe-table td:first-child{position:sticky!important;left:0!important;z-index:4!important;background:var(--panel,#1b2027)!important;min-width:155px!important;max-width:190px!important;box-shadow:1px 0 0 var(--line,#35404b);text-align:left!important}.cdc-allergen-safe-table thead th:first-child{z-index:7!important}.cdc-allergen-safe-table th:not(:first-child),.cdc-allergen-safe-table td:not(:first-child){min-width:72px;text-align:center}.cdc-allergen-locked-control{pointer-events:none!important;cursor:default!important}.cdc-allergen-safe-table tbody td{touch-action:pan-x pan-y}.cdc-allergen-safe-table tbody tr:active td{background:inherit!important}@media(max-width:620px){.cdc-allergen-scroll{max-height:62vh;margin-left:-4px;margin-right:-4px}.cdc-allergen-safe-table{min-width:980px}.cdc-allergen-safe-table th:first-child,.cdc-allergen-safe-table td:first-child{min-width:135px!important;max-width:155px!important}.cdc-allergen-safe-table th:not(:first-child),.cdc-allergen-safe-table td:not(:first-child){min-width:66px;font-size:12px}.cdc-allergen-safe-note{margin-bottom:10px}}';
    document.head.appendChild(style);
  }

  function wrapView(){
    try{
      if(typeof VIEWS==='undefined'||!VIEWS||typeof VIEWS.allergens!=='function') return false;
      if(VIEWS.allergens.__cdcSafeMatrixWrapped) return true;
      var original=VIEWS.allergens;
      var wrapped=function(){
        var out=original.apply(this,arguments);
        try{ setTimeout(protect,0); }catch(e){}
        return out;
      };
      wrapped.__cdcSafeMatrixWrapped=true;
      VIEWS.allergens=wrapped;
      return true;
    }catch(e){ return false; }
  }

  function start(){
    css();
    wrapView();
    protect();
    var obs=new MutationObserver(function(){ protect(); wrapView(); });
    obs.observe(document.documentElement,{childList:true,subtree:true});
    setTimeout(protect,250);
    console.info('[Command de Cuisine] Allergen matrix is read-only with sticky headers');
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();