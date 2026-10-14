/* Command de Cuisine - safer mobile allergen matrix */
(function(){
  'use strict';
  if(window.__cdcAllergenMatrixGuard) return;
  window.__cdcAllergenMatrixGuard=true;

  var STYLE_ID='cdc-allergen-matrix-guard-css';

  function addCss(){
    if(document.getElementById(STYLE_ID)) return;
    var s=document.createElement('style');
    s.id=STYLE_ID;
    s.textContent=
      '.cdc-allergen-safe-note{display:flex;gap:10px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;margin:0 0 12px;padding:12px 14px;border:1px solid var(--line,#39434e);border-radius:12px;background:var(--panel2,#20262e);font-size:13px;line-height:1.45}'+
      '.cdc-allergen-safe-note b{display:block;margin-bottom:2px;color:var(--ink,#f4f5f7)}'+
      '.cdc-allergen-safe-note span{color:var(--muted,#9ca6b3)}'+
      '.cdc-allergen-scroll{overflow:auto!important;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;position:relative;max-width:100%}'+
      '.cdc-allergen-guarded{border-collapse:separate!important;border-spacing:0!important}'+
      '.cdc-allergen-guarded thead th,.cdc-allergen-guarded tr:first-child>th{position:sticky!important;top:0!important;z-index:12!important;background:var(--panel,#1c2229)!important;box-shadow:0 1px 0 var(--line,#39434e)}'+
      '.cdc-allergen-guarded th:first-child,.cdc-allergen-guarded td:first-child{position:sticky!important;left:0!important;z-index:11!important;background:var(--panel,#1c2229)!important;min-width:150px!important;max-width:190px!important;box-shadow:1px 0 0 var(--line,#39434e)}'+
      '.cdc-allergen-guarded thead th:first-child,.cdc-allergen-guarded tr:first-child>th:first-child{z-index:14!important}'+
      '.cdc-allergen-guarded td,.cdc-allergen-guarded th{touch-action:pan-x pan-y!important}'+
      '.cdc-allergen-guarded input,.cdc-allergen-guarded button,.cdc-allergen-guarded select,[data-cdc-allergen-locked="1"]{cursor:default!important}'+
      '.cdc-allergen-guarded input[type="checkbox"]{pointer-events:none!important;opacity:1!important;filter:none!important}'+
      '.cdc-allergen-guarded [aria-pressed],.cdc-allergen-guarded [role="button"]{pointer-events:none!important}'+
      '@media(max-width:700px){.cdc-allergen-scroll{max-height:calc(100vh - 210px)}.cdc-allergen-guarded{min-width:920px!important}.cdc-allergen-guarded th:first-child,.cdc-allergen-guarded td:first-child{min-width:145px!important;max-width:160px!important}.cdc-allergen-safe-note{position:sticky;left:0;z-index:20}}';
    document.head.appendChild(s);
  }

  function text(el){ return String(el&&el.textContent||'').trim(); }

  function looksLikeMatrix(table){
    if(!table) return false;
    var all=(text(table.parentElement)+' '+text(table)).toLowerCase();
    if(all.indexOf('allergen')>=0) return true;
    var ths=table.querySelectorAll('th');
    return ths.length>=8;
  }

  function lockTable(table){
    if(!table || table.dataset.cdcAllergenLocked==='1') return;
    table.dataset.cdcAllergenLocked='1';
    table.classList.add('cdc-allergen-guarded');

    var parent=table.parentElement;
    if(parent) parent.classList.add('cdc-allergen-scroll');

    Array.prototype.forEach.call(
      table.querySelectorAll('input,button,select,textarea,[contenteditable="true"],[role="button"],[aria-pressed]'),
      function(el){
        el.setAttribute('aria-disabled','true');
        el.setAttribute('tabindex','-1');
        el.dataset.cdcAllergenLocked='1';
        if(el.tagName==='INPUT' || el.tagName==='SELECT' || el.tagName==='TEXTAREA' || el.tagName==='BUTTON'){
          try{ el.disabled=true; }catch(_e){}
        }
        if(el.hasAttribute('contenteditable')) el.setAttribute('contenteditable','false');
      }
    );

    var stop=function(ev){
      var target=ev.target;
      if(!target || !table.contains(target)) return;
      var interactive=target.closest && target.closest('input,button,select,textarea,[role="button"],[aria-pressed],[contenteditable],td,th');
      if(!interactive) return;
      // Keep ordinary horizontal/vertical scrolling intact. Only block actions
      // capable of changing matrix state.
      if(ev.type==='click' || ev.type==='change' || ev.type==='input' || ev.type==='keydown'){
        if(ev.type==='keydown' && ev.key!=='Enter' && ev.key!==' ') return;
        ev.preventDefault();
        ev.stopImmediatePropagation();
      }
    };
    table.addEventListener('click',stop,true);
    table.addEventListener('change',stop,true);
    table.addEventListener('input',stop,true);
    table.addEventListener('keydown',stop,true);
  }

  function addNote(view){
    if(!view || view.querySelector('.cdc-allergen-safe-note')) return;
    var note=document.createElement('div');
    note.className='cdc-allergen-safe-note';
    note.innerHTML='<div><b>View-only allergen matrix</b><span>To change an allergen, edit the recipe itself. This prevents accidental taps changing safety information.</span></div>';
    var firstCard=view.querySelector('.card,.panel,.section') || view;
    firstCard.insertBefore(note,firstCard.firstChild);
  }

  function protect(view){
    addCss();
    if(!view) return;
    var tables=Array.prototype.slice.call(view.querySelectorAll('table')).filter(looksLikeMatrix);
    tables.forEach(lockTable);
    if(tables.length) addNote(view);
  }

  function wrapView(){
    try{
      if(typeof VIEWS==='undefined' || !VIEWS || typeof VIEWS.allergens!=='function') return false;
      if(VIEWS.allergens.__cdcAllergenSafeWrapped) return true;
      var original=VIEWS.allergens;
      var wrapped=function(v){
        var out=original.apply(this,arguments);
        try{ protect(v); }catch(e){ console.warn('allergen matrix guard',e); }
        setTimeout(function(){ try{ protect(v); }catch(_e){} },50);
        return out;
      };
      wrapped.__cdcAllergenSafeWrapped=true;
      VIEWS.allergens=wrapped;
      return true;
    }catch(e){ return false; }
  }

  function scanCurrent(){
    try{
      var root=document.querySelector('main,#app,.app') || document.body;
      if(!root) return;
      var tables=Array.prototype.slice.call(root.querySelectorAll('table')).filter(looksLikeMatrix);
      if(tables.length){
        tables.forEach(lockTable);
        var view=tables[0].closest('.view,.page,.content,.card') || root;
        addNote(view);
      }
    }catch(e){}
  }

  function start(){
    addCss();
    var tries=0;
    var timer=setInterval(function(){
      tries++;
      if(wrapView() || tries>60) clearInterval(timer);
    },100);
    new MutationObserver(function(){ scanCurrent(); }).observe(document.documentElement,{childList:true,subtree:true});
    scanCurrent();
    console.info('[Command de Cuisine] Allergen matrix locked read-only with sticky mobile headers');
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();