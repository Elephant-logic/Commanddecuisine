from pathlib import Path
import re

p = Path('app/main_app.js')
text = p.read_text(encoding='utf-8')

# ---------------------------------------------------------------------------
# Evidence helpers used by the dashboard and the Temperature > Trends page.
# Never plot status-only rows as 0C and never infer a missing round as complete.
# ---------------------------------------------------------------------------
start = text.find('function readingSeries(appId)')
end = text.find('function dueDockets(){', start)
if start < 0 or end < 0:
    raise SystemExit('Temperature graph helper markers not found')

helpers = r'''const DASH_TEMP_OFFLINE_STATUSES=new Set(["out_of_order","awaiting_repair","not_in_use","defrosting"]);
function dashTempHasValue(r){
  if(typeof tempRecordHasValue==='function')return tempRecordHasValue(r);
  return !!(r&&String(r.equipmentStatus||'reading')==='reading'&&r.value!==null&&r.value!==''&&Number.isFinite(Number(r.value)));
}
function dashTempDay(r){
  if(typeof tempRecordLocalDay==='function')return tempRecordLocalDay(r);
  const s=String(r&&r.ts||'');
  return /^\d{4}-\d{2}-\d{2}/.test(s)?s.slice(0,10):'';
}
function dashTempPeriod(r){
  if(typeof tempRecordPeriod==='function')return tempRecordPeriod(r);
  const p=String(r&&r.period||'').toLowerCase();
  if(p==='am'||p==='pm')return p;
  const d=new Date(r&&r.ts||'');
  return !Number.isNaN(d.getTime())&&d.getHours()>=12?'pm':'am';
}
function dashTempStatusKey(r){return dashTempHasValue(r)?'reading':String(r&&r.equipmentStatus||'').toLowerCase();}
function dashTempStatusLabel(r){
  if(dashTempHasValue(r))return 'Reading';
  if(typeof tempRecordStatusLabel==='function')return tempRecordStatusLabel(r)||'Status';
  const labels={out_of_order:'Out of order',awaiting_repair:'Awaiting repair',not_in_use:'Not in use',defrosting:'Defrosting'};
  return labels[dashTempStatusKey(r)]||'Status';
}
function dashTempLatest(appId){
  return (STATE.tempReadings||[]).filter(r=>r&&r.appId===appId).sort((a,b)=>String(b.ts||'').localeCompare(String(a.ts||'')))[0]||null;
}
function dashTempRowsInSlot(appId,ds,period){
  return (STATE.tempReadings||[]).filter(r=>r&&r.appId===appId&&dashTempDay(r)===ds&&dashTempPeriod(r)===period);
}
function dashTempOfflineAtSlot(appId,ds,period){
  try{if(typeof tempUnitOfflineForSlot==='function')return !!tempUnitOfflineForSlot(appId,ds,period);}catch(_e){}
  const rows=(STATE.tempReadings||[]).filter(r=>{
    if(!r||r.appId!==appId)return false;
    const d=dashTempDay(r),p=dashTempPeriod(r);
    if(!d)return false;
    if(d<ds)return true;
    if(d>ds)return false;
    return period==='pm'||p==='am';
  }).sort((a,b)=>String(a.ts||'').localeCompare(String(b.ts||'')));
  const latest=rows[rows.length-1]||null;
  return !!(latest&&!dashTempHasValue(latest)&&DASH_TEMP_OFFLINE_STATUSES.has(dashTempStatusKey(latest)));
}
function dashTempDuePeriods(ds){
  // Use the browser's local calendar date, not UTC ISO date. Around midnight
  // local time, todayISO() can still be yesterday in UTC and wrongly blank
  // yesterday's completed round on the dashboard.
  const now=new Date();
  const today=[now.getFullYear(),String(now.getMonth()+1).padStart(2,'0'),String(now.getDate()).padStart(2,'0')].join('-');
  if(ds<today)return ['am','pm'];
  if(ds>today)return [];
  const h=now.getHours();
  if(h>=18)return ['am','pm'];
  if(h>=11)return ['am'];
  return [];
}
function dashTempOfflineSince(appId){
  const rows=(STATE.tempReadings||[]).filter(r=>r&&r.appId===appId).sort((a,b)=>String(a.ts||'').localeCompare(String(b.ts||'')));
  let since=null,current='';
  for(const r of rows){
    const key=dashTempStatusKey(r);
    if(DASH_TEMP_OFFLINE_STATUSES.has(key)){
      if(key!==current)since=r;
    }else since=null;
    current=key;
  }
  return since;
}
function readingSeries(appId,days=14){
  const cutoff=new Date(); cutoff.setHours(0,0,0,0); cutoff.setDate(cutoff.getDate()-(Math.max(1,days)-1));
  return (STATE.tempReadings||[]).filter(r=>{
    if(!r||r.appId!==appId||!dashTempHasValue(r))return false;
    const d=new Date(r.ts||'');
    return Number.isNaN(d.getTime())?dashTempDay(r)>=[cutoff.getFullYear(),String(cutoff.getMonth()+1).padStart(2,'0'),String(cutoff.getDate()).padStart(2,'0')].join('-'):d.getTime()>=cutoff.getTime();
  }).sort((a,b)=>String(a.ts||'').localeCompare(String(b.ts||''))).map(r=>({ts:r.ts,value:Number(r.value)}));
}
function weekCompliance(){
  const out=[]; const base=new Date();
  for(let d=6;d>=0;d--){
    const day=new Date(base.getFullYear(),base.getMonth(),base.getDate()-d);
    const ds=[day.getFullYear(),String(day.getMonth()+1).padStart(2,'0'),String(day.getDate()).padStart(2,'0')].join('-');
    const reads=(STATE.tempReadings||[]).filter(r=>r&&dashTempDay(r)===ds&&dashTempHasValue(r));
    if(!reads.length){out.push({label:dayName(day),value:0,hasData:false,color:'var(--faint)'});continue;}
    let ok=0; reads.forEach(r=>{const a=appById(r.appId);if(a&&tempStatus(a,Number(r.value))!=='danger')ok++;});
    const pct=Math.round(ok/reads.length*100);
    out.push({label:dayName(day),value:pct,hasData:true,color:pct>=95?'var(--ok)':pct>=80?'var(--warn)':'var(--danger)'});
  }
  return out;
}
function weekRoundCompletion(){
  const out=[]; const base=new Date();
  const units=(STATE.appliances||[]).filter(a=>a&&(a.type==='fridge'||a.type==='freezer'));
  for(let d=6;d>=0;d--){
    const day=new Date(base.getFullYear(),base.getMonth(),base.getDate()-d);
    const ds=[day.getFullYear(),String(day.getMonth()+1).padStart(2,'0'),String(day.getDate()).padStart(2,'0')].join('-');
    const periods=dashTempDuePeriods(ds);
    if(!periods.length){out.push({label:dayName(day)+' '+day.getDate(),value:0,hasData:false,color:'var(--faint)'});continue;}
    let expected=0,done=0;
    periods.forEach(period=>units.forEach(a=>{
      if(dashTempOfflineAtSlot(a.id,ds,period))return;
      expected++;
      if(dashTempRowsInSlot(a.id,ds,period).some(dashTempHasValue))done++;
    }));
    const pct=expected?Math.round(done/expected*100):0;
    out.push({label:dayName(day)+' '+day.getDate(),value:pct,hasData:expected>0,color:pct>=100?'var(--ok)':pct>0?'var(--warn)':'var(--danger)'});
  }
  return out;
}
'''
text = text[:start] + helpers + text[end:]

# Generic bars: fixed percentage ceiling when requested and explicit N/A marker.
bstart = text.find('function bars(data,opts={}){')
bend = text.find('/* =========================================================', bstart)
if bstart < 0 or bend < 0:
    raise SystemExit('bars function markers not found')
new_bars = r'''function bars(data,opts={}){
  // data:[{label,value,color,hasData?}]
  const w=opts.w||560,h=opts.h||160,pad={l:8,r:8,t:10,b:24};
  const valid=data.filter(d=>d&&d.hasData!==false&&Number.isFinite(+d.value));
  const max=opts.max!=null?Math.max(1,+opts.max):Math.max(1,...valid.map(d=>+d.value));
  const suffix=opts.suffix||'';
  const bw=(w-pad.l-pad.r)/Math.max(1,data.length);
  return `<svg viewBox="0 0 ${w} ${h}" width="100%" style="display:block">${
    data.map((d,i)=>{
      const has=!!d&&d.hasData!==false&&Number.isFinite(+d.value);
      const val=has?+d.value:0;
      const bh=has?(Math.max(0,Math.min(max,val))/max)*(h-pad.t-pad.b):0;
      const x=pad.l+i*bw;
      const y=h-pad.b-bh;
      const mark=has
        ?`<rect x="${(x+bw*0.16).toFixed(1)}" y="${y.toFixed(1)}" width="${(bw*0.68).toFixed(1)}" height="${Math.max(2,bh).toFixed(1)}" rx="4" fill="${d.color||'var(--brass)'}"/>`
        :`<line x1="${(x+bw*0.28).toFixed(1)}" x2="${(x+bw*0.72).toFixed(1)}" y1="${(h-pad.b-2).toFixed(1)}" y2="${(h-pad.b-2).toFixed(1)}" stroke="var(--line2)" stroke-width="2"/>`;
      return `${mark}
      <text x="${(x+bw/2).toFixed(1)}" y="${h-8}" text-anchor="middle" fill="var(--faint)" font-size="10.5" font-family="var(--display)">${esc(d.label)}</text>
      <text x="${(x+bw/2).toFixed(1)}" y="${has?(y-5).toFixed(1):(h-pad.b-8).toFixed(1)}" text-anchor="middle" fill="var(--muted)" font-size="10.5" font-family="var(--mono)">${has?Math.round(val)+suffix:'-'}</text>`;
    }).join('')}</svg>`;
}

'''
text = text[:bstart] + new_bars + text[bend:]

# Dashboard: round completion + honest all-unit status. Remove the arbitrary
# single "flagged unit" trend which could show stale pre-fault values.
pass_start = text.find('VIEWS.pass=function(v){')
block_start = text.find('  const wk=el("div",{class:"card"});', pass_start)
block_end_marker = '  row.append(wk); v.append(row);'
block_end = text.find(block_end_marker, block_start)
if pass_start < 0 or block_start < 0 or block_end < 0:
    raise SystemExit('Dashboard graph block not found')
block_end += len(block_end_marker)
new_dashboard = r'''  const wk=el("div",{class:"card"});
  wk.append(el("div",{class:"card-head"},el("h3",{},"Temperature rounds - last 7 days"),el("div",{class:"spacer"}),
    el("button",{class:"btn sm ghost",html:"History",onclick:()=>{tempTab="history";navigate("temps");}})));
  const completion=weekRoundCompletion();
  wk.insertAdjacentHTML("beforeend",bars(completion,{suffix:"%",max:100}));
  wk.insertAdjacentHTML("beforeend",`<div class="muted" style="font-size:11.5px;margin-top:2px">Shows completion of required AM/PM temperature checks. Units recorded as out of order, awaiting repair, not in use or defrosting are excluded while that status is active. A dash means no round is due yet.</div>`);

  const statusHead=el("div",{class:"card-head",style:"margin-top:14px"},el("h3",{},"Cold-chain status"),el("div",{class:"spacer"}),
    el("button",{class:"btn sm ghost",html:"View trends",onclick:()=>{tempTab="trends";navigate("temps");}}));
  wk.append(statusHead);
  const statusList=el("div",{});
  (STATE.appliances||[]).filter(a=>a&&(a.type==="fridge"||a.type==="freezer")).forEach(a=>{
    const r=dashTempLatest(a.id);
    let cls='',main='No record',detail='No temperature or equipment status recorded';
    if(r&&dashTempHasValue(r)){
      const st=tempStatus(a,Number(r.value));
      cls=st==='danger'?'over':st==='warn'?'due':'done';
      main=Number(r.value).toFixed(1)+'\u00b0C';
      detail=(st==='danger'?'Breach':st==='warn'?'Above target':'In range')+'  -  '+fmtDate(dashTempDay(r))+' '+dashTempPeriod(r).toUpperCase();
    }else if(r){
      const key=dashTempStatusKey(r),since=dashTempOfflineSince(a.id)||r;
      cls=DASH_TEMP_OFFLINE_STATUSES.has(key)?'due':'';
      main=dashTempStatusLabel(r);
      detail='Since '+fmtDate(dashTempDay(since))+'  -  last confirmed '+fmtDate(dashTempDay(r))+' '+dashTempPeriod(r).toUpperCase();
    }
    const d=el("div",{class:"docket "+cls,style:"margin-bottom:7px"});
    d.innerHTML=`<div class="dk-ic">${icon('temp')}</div><div style="flex:1"><div class="dk-t">${esc(a.name)}</div><div class="dk-s">${esc(detail)}</div></div><div style="text-align:right;font-weight:800;white-space:nowrap">${esc(main)}</div>`;
    statusList.append(d);
  });
  wk.append(statusList);
  row.append(wk); v.append(row);'''
text = text[:block_start] + new_dashboard + text[block_end:]

# Temperature > Trends: numeric lines only. Current offline/status units show
# their real status instead of plotting null/status rows as zero or stale data.
tstart = text.find('function tempTrends(v){')
tend = text.find('function tempProbes(v){', tstart)
if tstart < 0 or tend < 0:
    raise SystemExit('Temperature trends view markers not found')
new_trends = r'''function tempTrends(v){
  const grid=el("div",{class:"grid g2"});
  STATE.appliances.forEach(a=>{
    const c=el("div",{class:"card"});
    const current=dashTempLatest(a.id);
    const currentKey=dashTempStatusKey(current);
    const offline=!!(current&&!dashTempHasValue(current)&&DASH_TEMP_OFFLINE_STATUSES.has(currentKey));
    c.innerHTML=`<div class="card-head"><h3>${esc(a.name)}</h3><div class="spacer"></div><span class="tag ${offline?'warn':a.type==='freezer'?'cold':a.type==='hot'?'warn':'cold'}">${offline?esc(dashTempStatusLabel(current)):esc(a.type)}</span></div>`;
    if(offline){
      const since=dashTempOfflineSince(a.id)||current;
      c.insertAdjacentHTML("beforeend",`<div class="empty" style="padding:18px 10px"><h4>${esc(dashTempStatusLabel(current))}</h4><div>Status active since ${esc(fmtDate(dashTempDay(since)))}. No temperature line is drawn while this unit is offline.</div></div>`);
    }else{
      const series=readingSeries(a.id,14);
      const last=series[series.length-1];
      c.insertAdjacentHTML("beforeend",lineChart(series,{color:a.type==='hot'?'var(--warn)':'var(--cold)',target:a.target,critical:a.critical,type:a.type,h:130}));
      c.insertAdjacentHTML("beforeend",`<div class="muted" style="font-size:12px;margin-top:8px">Latest ${last?Number(last.value).toFixed(1)+'\u00b0C':'-'}${last?'  -  '+esc(fmtDate(dashTempDay(last)))+' '+esc(dashTempPeriod(last).toUpperCase()):''}  -  target ${a.type==='hot'?'>=':'<='} ${a.target}\u00b0C  -  limit ${a.critical}\u00b0C</div>`);
    }
    grid.append(c);
  });
  v.append(grid);
}
'''
text = text[:tstart] + new_trends + text[tend:]

# Report charts remain genuine in-range percentages, not round-completion bars.
text = text.replace('bars(weekCompliance())', 'bars(weekCompliance(),{suffix:"%",max:100})')

p.write_text(text, encoding='utf-8')

# main_app.js is loaded directly from index.html; bump its URL so kitchen phones
# cannot keep the old dashboard/trend code from cache.
index = Path('app/index.html')
if index.exists():
    html = index.read_text(encoding='utf-8')
    html, n = re.subn(r'main_app\.js\?v=[^"\']+', 'main_app.js?v=20260924-tempdashboard2', html, count=1)
    if n != 1:
        raise SystemExit('main_app.js cache-bust marker not found')
    index.write_text(html, encoding='utf-8')

final = p.read_text(encoding='utf-8')
checks = [
    'function weekRoundCompletion(){',
    'Temperature rounds - last 7 days',
    'Cold-chain status',
    'No temperature line is drawn while this unit is offline.',
    'function readingSeries(appId,days=14)',
]
for marker in checks:
    if marker not in final:
        raise SystemExit(f'Accurate temperature dashboard marker missing: {marker}')
print('Temperature dashboard now shows true round completion, all-unit status and status-aware 14-day trends')
