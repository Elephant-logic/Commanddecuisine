from pathlib import Path

p = Path('app/index.html')
text = p.read_text(encoding='utf-8')
marker = 'id="cdc-recipe-editor-import-button"'
if marker in text:
    print('Recipe editor import button already installed')
    raise SystemExit(0)

js = r'''
<script id="cdc-recipe-editor-import-button">
(()=>{
  'use strict';
  const BTN_CLASS='cdc-recipe-editor-import';

  function txt(el){return String(el&&el.textContent||'').trim();}
  function findLauncher(){
    return [...document.querySelectorAll('button')].find(b=>txt(b)==='Import / update recipe');
  }
  function findEditor(){
    const candidates=[...document.querySelectorAll('h1,h2,h3,h4,div')].filter(el=>{
      const t=txt(el).toUpperCase();
      return (t==='NEW RECIPE'||t==='EDIT RECIPE'||t==='UPDATE RECIPE') && el.children.length===0;
    });
    for(const title of candidates){
      let box=title;
      for(let i=0;i<8 && box;i++,box=box.parentElement){
        const body=String(box.innerText||'').toUpperCase();
        if(body.includes('DISH NAME') && (body.includes('SAVE RECIPE')||body.includes('SAVE CHANGES')||body.includes('UPDATE RECIPE'))){
          return {title,box,isEdit:txt(title).toUpperCase()!=='NEW RECIPE'};
        }
      }
    }
    return null;
  }
  function firstDishNameInput(box){
    const inputs=[...box.querySelectorAll('input[type="text"],input:not([type])')];
    return inputs[0]||null;
  }
  function chooseExistingByName(name){
    if(!name) return;
    setTimeout(()=>{
      const overlay=document.getElementById('cdc-recipe-import-overlay');
      if(!overlay) return;
      const sel=overlay.querySelector('select');
      if(!sel) return;
      const want=String(name).trim().toLowerCase();
      const opt=[...sel.options].find(o=>String(o.textContent||'').replace(/^Update:\s*/i,'').trim().toLowerCase()===want);
      if(opt){sel.value=opt.value;sel.dispatchEvent(new Event('change',{bubbles:true}));}
    },80);
  }
  function install(){
    const ed=findEditor();
    if(!ed || ed.box.querySelector('.'+BTN_CLASS)) return;
    const wrap=document.createElement('div');
    wrap.className=BTN_CLASS;
    wrap.style.cssText='margin:14px 0 18px;padding:12px;border:1px solid var(--line,#35404b);border-radius:12px;background:var(--panel2,#20262e)';
    const b=document.createElement('button');
    b.type='button';
    b.className='btn primary';
    b.style.cssText='width:100%;min-height:48px;font-weight:800';
    b.textContent=ed.isEdit?'📷 Update from photo / notes':'📷 Import from photo / notes';
    const hint=document.createElement('div');
    hint.className='muted';
    hint.style.cssText='font-size:12px;margin-top:8px;text-align:center';
    hint.textContent=ed.isEdit?'Read a photo or pasted notes and update this recipe.':'Read a photo or pasted notes and create the recipe automatically.';
    b.onclick=()=>{
      const launcher=findLauncher();
      if(!launcher){
        alert('Recipe import is still loading. Close this recipe form, reopen Recipes, and try again.');
        return;
      }
      const currentName=firstDishNameInput(ed.box)?.value||'';
      launcher.click();
      if(ed.isEdit || currentName) chooseExistingByName(currentName);
    };
    wrap.append(b,hint);
    ed.title.insertAdjacentElement('afterend',wrap);
  }

  const obs=new MutationObserver(install);
  obs.observe(document.documentElement,{childList:true,subtree:true});
  setInterval(install,500);
  install();
})();
</script>
'''

if '</body>' not in text:
    raise SystemExit('Could not find </body> in app/index.html')
text = text.replace('</body>', js + '\n</body>', 1)
p.write_text(text, encoding='utf-8')
print('Recipe editor photo/notes button installed in New/Edit Recipe forms')
