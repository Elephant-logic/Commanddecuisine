from pathlib import Path

main = Path('app/main_app.js')
text = main.read_text(encoding='utf-8')
marker = '/* CDC temperature review UI repair 20260917 */'
if marker not in text:
    text += r'''

/* CDC temperature review UI repair 20260917 */
setTimeout(()=>{
  try{
    if(typeof rerender!=="function" || typeof STATE==="undefined") return;

    const applianceSignature=()=>JSON.stringify((STATE.appliances||[]).map(a=>String(a&&a.id||"")).sort());
    let lastApplianceSignature=applianceSignature();

    function persistApplianceChange(){
      const next=applianceSignature();
      if(next===lastApplianceSignature)return;
      lastApplianceSignature=next;
      try{ if(typeof save==="function") save("equipment change"); }catch(e){ console.error("equipment persistence failed",e); }
    }

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
print('Temperature review raw SVG cleanup installed; appliance add/remove changes now persist automatically')
