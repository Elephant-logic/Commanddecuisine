from pathlib import Path

# Fix the actual source of the red raw <svg> text in Temperature history.
fixes = Path('app/kitchen_fixes_20260810.js')
js = fixes.read_text(encoding='utf-8')
old_icon = "el('div',{class:'dk-ic'},icon('alert'))"
new_icon = "el('div',{class:'dk-ic',html:icon('alert')})"
icon_fixes = js.count(old_icon)
if icon_fixes:
    js = js.replace(old_icon, new_icon)
    fixes.write_text(js, encoding='utf-8')

# Also make equipment add/remove changes persist even where the original Settings
# controls only mutate STATE and rerender. This prevents deleted test units from
# continuing to appear as missing temperature rounds after a reload.
main = Path('app/main_app.js')
text = main.read_text(encoding='utf-8')
marker = '/* CDC temperature review UI repair 20260917 */'
if marker not in text:
    text += r'''

/* CDC temperature review UI repair 20260917 */
setTimeout(()=>{
  try{
    if(typeof rerender!=="function" || typeof STATE==="undefined") return;

    const knownApplianceIds=new Set((STATE.appliances||[]).map(a=>String(a&&a.id||"")));
    const applianceSignature=()=>JSON.stringify((STATE.appliances||[]).map(a=>String(a&&a.id||"")).sort());
    let lastApplianceSignature=applianceSignature();

    function persistApplianceChange(){
      let metadataChanged=false;
      (STATE.appliances||[]).forEach(a=>{
        const id=String(a&&a.id||"");
        if(id && !knownApplianceIds.has(id)){
          knownApplianceIds.add(id);
          if(!a.createdAt){
            a.createdAt=(typeof nowISO==="function"?nowISO():new Date().toISOString());
            metadataChanged=true;
          }
        }
      });
      const next=applianceSignature();
      if(next===lastApplianceSignature && !metadataChanged)return;
      lastApplianceSignature=next;
      try{ if(typeof save==="function") save("equipment change"); }catch(e){ console.error("equipment persistence failed",e); }
    }

    // Defensive cleanup for any cached older markup. The source icon is fixed
    // above, but this removes literal SVG text if an old cached renderer produced it.
    function scrubEscapedSvg(){
      try{
        if(typeof ROUTE!=="undefined" && ROUTE!=="temps")return;
        const root=document.querySelector("#view");
        if(!root)return;
        const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
        const dirty=[];
        let node;
        while((node=walker.nextNode())){
          const s=String(node.nodeValue||"");
          if(s.includes("<svg") && s.includes("</svg>"))dirty.push(node);
        }
        dirty.forEach(n=>{
          n.nodeValue=String(n.nodeValue||"").replace(/<svg[\s\S]*?<\/svg>/gi,"").replace(/^\s+/,"");
        });
      }catch(e){ console.error("temperature review svg cleanup failed",e); }
    }

    const baseRerender=rerender;
    rerender=function(...args){
      const result=baseRerender.apply(this,args);
      persistApplianceChange();
      scrubEscapedSvg();
      return result;
    };

    document.addEventListener("click",()=>{
      setTimeout(()=>{ persistApplianceChange(); scrubEscapedSvg(); },0);
    },true);

    scrubEscapedSvg();
  }catch(e){ console.error("temperature review UI repair failed",e); }
},0);
'''
    main.write_text(text,encoding='utf-8')

print(f'Temperature review alert icon fixed ({icon_fixes} source occurrence(s)); appliance add/remove changes now persist automatically')
