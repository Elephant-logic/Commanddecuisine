from pathlib import Path

p = Path('app/index.html')
text = p.read_text(encoding='utf-8')
marker = 'id="cdc-probe-calibration-upcoming-visual"'
if marker in text:
    print('Probe calibration upcoming visual already installed')
    raise SystemExit(0)

visual = r'''
<style id="cdc-probe-calibration-upcoming-style">
  .cdc-probe-calibration-upcoming{border-left-color:#e4ad37!important;}
  .cdc-probe-calibration-upcoming::before,.cdc-probe-calibration-upcoming::after{border-color:#e4ad37!important;background:#e4ad37!important;}
  .cdc-probe-calibration-upcoming svg,.cdc-probe-calibration-upcoming svg *{color:#e4ad37!important;stroke:#e4ad37!important;}
  .cdc-probe-calibration-upcoming [class*="icon"],.cdc-probe-calibration-upcoming [class*="status"]{color:#e4ad37!important;}
</style>
<script id="cdc-probe-calibration-upcoming-visual">
(()=>{
  'use strict';
  const AMBER='#e4ad37';
  function text(el){return String(el&&el.innerText||el&&el.textContent||'').trim();}
  function findCard(label){
    let el=label;
    let best=null;
    for(let i=0;i<9&&el;i++,el=el.parentElement){
      const body=text(el);
      if(/Probe calibration/i.test(body)&&/Due this week/i.test(body)){
        best=el;
        if(/\bView\b|\bOpen\b/i.test(body) && el.querySelector('button')) break;
      }
    }
    return best;
  }
  function forceAmber(card){
    if(!card)return;
    card.classList.add('cdc-probe-calibration-upcoming');
    card.style.setProperty('border-left-color',AMBER,'important');
    card.style.setProperty('--ok',AMBER);
    card.style.setProperty('--green',AMBER);
    const nodes=[card,...card.querySelectorAll('*')];
    for(const n of nodes){
      const s=getComputedStyle(n);
      const bc=s.borderLeftColor;
      const c=s.color;
      const bg=s.backgroundColor;
      if(/rgb\(72,\s*184,\s*117\)|rgb\(74,\s*177,\s*113\)|#48b875|#4ab171/i.test(bc)) n.style.setProperty('border-left-color',AMBER,'important');
      if(/rgb\(72,\s*184,\s*117\)|rgb\(74,\s*177,\s*113\)/i.test(c)) n.style.setProperty('color',AMBER,'important');
      if(n.tagName==='SVG'||n.tagName==='PATH'||n.tagName==='CIRCLE'||n.tagName==='LINE'||n.tagName==='POLYLINE'){
        n.style.setProperty('stroke',AMBER,'important');
        if(n.getAttribute('fill') && n.getAttribute('fill')!=='none') n.style.setProperty('fill',AMBER,'important');
      }
      if(/rgb\(72,\s*184,\s*117\)|rgb\(74,\s*177,\s*113\)/i.test(bg) && !/button/i.test(n.tagName)) n.style.setProperty('background-color',AMBER,'important');
    }
  }
  function fix(){
    const all=[...document.querySelectorAll('body *')];
    const labels=all.filter(el=>/^Probe calibration$/i.test(text(el)));
    for(const label of labels){
      const card=findCard(label);
      if(card) forceAmber(card);
    }
  }
  const obs=new MutationObserver(fix);
  obs.observe(document.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['class','style']});
  setInterval(fix,350);
  fix();
})();
</script>
'''

if '</body>' not in text:
    raise SystemExit('Could not find </body> in app/index.html')
text = text.replace('</body>', visual + '\n</body>', 1)
p.write_text(text, encoding='utf-8')
print('Probe calibration due-this-week card forced amber/upcoming rather than completed green')
