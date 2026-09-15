from pathlib import Path

p = Path('app/main_app.js')
text = p.read_text(encoding='utf-8')

# The old seven-day chart silently treated a day with zero temperature
# readings as 100% compliant. That made an empty day look perfect. Replace it
# with a strictly evidence-based cold-chain series: real readings => real
# percentage; no readings => N/A.
start = text.find('function weekCompliance(){')
end = text.find('function dueDockets(){', start)
if start < 0 or end < 0:
    raise SystemExit('weekCompliance function markers not found')

new_week = r'''function weekCompliance(){
  const out=[];
  const base=new Date();
  for(let d=6;d>=0;d--){
    const day=new Date(base.getFullYear(),base.getMonth(),base.getDate()-d);
    const ds=[day.getFullYear(),String(day.getMonth()+1).padStart(2,"0"),String(day.getDate()).padStart(2,"0")].join("-");
    const reads=STATE.tempReadings.filter(r=>r&&tempRecordHasValue(r)&&String(r.ts||"").slice(0,10)===ds);
    if(!reads.length){
      out.push({label:dayName(day),value:0,hasData:false,color:"var(--faint)"});
      continue;
    }
    let ok=0;
    reads.forEach(r=>{const a=appById(r.appId);if(a&&tempStatus(a,r.value)!=="danger")ok++;});
    const pct=Math.round(ok/reads.length*100);
    out.push({label:dayName(day),value:pct,hasData:true,color:pct>=95?"var(--ok)":pct>=80?"var(--warn)":"var(--danger)"});
  }
  return out;
}
'''
text = text[:start] + new_week + text[end:]

# Teach the shared bar renderer to show missing evidence as an em dash rather
# than a zero-height value that can be mistaken for measured data.
bstart = text.find('function bars(data,opts={}){')
bend = text.find('/* ============================================================', bstart)
if bstart < 0 or bend < 0:
    raise SystemExit('bars function markers not found')

new_bars = r'''function bars(data,opts={}){
  // data:[{label,value,color,hasData?}]
  const w=opts.w||560,h=opts.h||160,pad={l:8,r:8,t:10,b:24};
  const valid=data.filter(d=>d&&d.hasData!==false&&Number.isFinite(+d.value));
  const max=Math.max(1,...valid.map(d=>+d.value));
  const bw=(w-pad.l-pad.r)/Math.max(1,data.length);
  return `<svg viewBox="0 0 ${w} ${h}" width="100%" style="display:block">${
    data.map((d,i)=>{
      const has=!!d&&d.hasData!==false&&Number.isFinite(+d.value);
      const val=has?+d.value:0;
      const bh=has?(val/max)*(h-pad.t-pad.b):0;
      const x=pad.l+i*bw;
      const y=h-pad.b-bh;
      const mark=has
        ?`<rect x="${(x+bw*0.16).toFixed(1)}" y="${y.toFixed(1)}" width="${(bw*0.68).toFixed(1)}" height="${Math.max(2,bh).toFixed(1)}" rx="4" fill="${d.color||"var(--brass)"}"/>`
        :`<line x1="${(x+bw*0.28).toFixed(1)}" x2="${(x+bw*0.72).toFixed(1)}" y1="${(h-pad.b-2).toFixed(1)}" y2="${(h-pad.b-2).toFixed(1)}" stroke="var(--line2)" stroke-width="2"/>`;
      return `${mark}
      <text x="${(x+bw/2).toFixed(1)}" y="${h-8}" text-anchor="middle" fill="var(--faint)" font-size="10.5" font-family="var(--display)">${esc(d.label)}</text>
      <text x="${(x+bw/2).toFixed(1)}" y="${has?(y-5).toFixed(1):(h-pad.b-8).toFixed(1)}" text-anchor="middle" fill="var(--muted)" font-size="10.5" font-family="var(--mono)">${has?Math.round(val):"—"}</text>`;
    }).join("")}</svg>`;
}

'''
text = text[:bstart] + new_bars + text[bend:]

# Be explicit about what the seven-day graph measures. It is cold-chain
# readings, not a made-up all-purpose compliance score.
text = text.replace('Compliance — last 7 days', 'Cold-chain compliance — last 7 days')

# A genuine 0% day is still data. Only hasData=false means no evidence.
old_guard = 'weekData.some(x=>x&&x.hasData!==false&&x.value>0)||STATE.tempReadings.some(r=>{const t=new Date(r.ts).getTime();return Number.isFinite(t)&&t>=Date.now()-7*864e5;})'
if old_guard in text:
    text = text.replace(old_guard, 'weekData.some(x=>x&&x.hasData!==false)', 1)

p.write_text(text, encoding='utf-8')
print('Graphs now use recorded evidence: missing cold-chain days show N/A, never invented 100%; seven-day graph labelled accurately')
