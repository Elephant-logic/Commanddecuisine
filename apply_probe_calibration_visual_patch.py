from pathlib import Path

p = Path('app/index.html')
text = p.read_text(encoding='utf-8')
marker = 'id="cdc-probe-calibration-upcoming-visual"'
if marker in text:
    print('Probe calibration upcoming visual already installed')
    raise SystemExit(0)

visual = r'''
<style id="cdc-probe-calibration-upcoming-style">
  .cdc-probe-calibration-upcoming{border-left-color:var(--warn,#e4ad37)!important;}
  .cdc-probe-calibration-upcoming svg{color:var(--warn,#e4ad37)!important;stroke:var(--warn,#e4ad37)!important;}
  .cdc-probe-calibration-upcoming [class*="icon"]{color:var(--warn,#e4ad37)!important;}
</style>
<script id="cdc-probe-calibration-upcoming-visual">
(()=>{
  'use strict';
  function leafText(el){return el&&el.children.length===0?String(el.textContent||'').trim():'';}
  function fix(){
    const labels=[...document.querySelectorAll('body *')].filter(el=>leafText(el)==='Probe calibration');
    for(const label of labels){
      let card=label;
      for(let i=0;i<7&&card;i++,card=card.parentElement){
        const body=String(card.innerText||'');
        if(/Probe calibration/i.test(body)&&/Due this week/i.test(body)&&(/View|Open/i.test(body))){
          card.classList.add('cdc-probe-calibration-upcoming');
          card.style.borderLeftColor='var(--warn,#e4ad37)';
          break;
        }
      }
    }
  }
  const obs=new MutationObserver(fix);
  obs.observe(document.documentElement,{childList:true,subtree:true});
  setInterval(fix,750);
  fix();
})();
</script>
'''

if '</body>' not in text:
    raise SystemExit('Could not find </body> in app/index.html')
text = text.replace('</body>', visual + '\n</body>', 1)
p.write_text(text, encoding='utf-8')
print('Probe calibration due-this-week card shown amber/upcoming rather than completed green')
