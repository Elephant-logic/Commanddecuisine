/* Command de Cuisine - authoritative temperature dashboard */
(function(){
  'use strict';
  if(window.__cdcAuthoritativeTempDashboard) return;
  window.__cdcAuthoritativeTempDashboard=true;

  var cache={readings:[], fetchedAt:0, loading:false};
  var OFFLINE=new Set(['out_of_order','not_in_use','defrosting','awaiting_repair']);
  var STATUS_LABEL={
    out_of_order:'Out of order',
    not_in_use:'Not in use',
    defrosting:'Defrosting',
    awaiting_repair:'Awaiting repair'
  };

  function esc(s){
    return String(s==null?'':s).replace(/[&<>"']/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }
  function localDay(ts){
    var d=new Date(ts||'');
    if(Number.isNaN(d.getTime())) return String(ts||'').slice(0,10);
    return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
  }
  function dayKey(d){
    return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
  }
  function shortDay(d){ return d.toLocaleDateString(undefined,{weekday:'short',day:'numeric'}); }
  function statusOf(r){
    var s=String((r&&r.equipmentStatus)||'reading').trim().toLowerCase();
    return s||'reading';
  }
  function hasValue(r){ return statusOf(r)==='reading' && Number.isFinite(Number(r&&r.value)); }
  function applianceById(id){
    try{
      if(typeof appById==='function') return appById(id);
      return (STATE.appliances||[]).find(function(a){return String(a.id)===String(id);})||null;
    }catch(e){return null;}
  }
  function isDanger(r){
    var a=applianceById(r.appId);
    if(!a) return false;
    try{
      if(typeof tempStatus==='function') return tempStatus(a,Number(r.value))==='danger';
    }catch(e){}
    var v=Number(r.value);
    var name=String(a.name||'').toLowerCase();
    if(/freezer/.test(name)) return v>-15;
    if(/fridge|cold|chill/.test(name)) return v>8;
    return false;
  }
  function fmt(v){
    var n=Number(v);
    return Number.isFinite(n)?(Math.round(n*10)/10).toFixed(1).replace(/\.0$/,''):'—';
  }

  async function fetchReadings(force){
    if(cache.loading) return cache.readings;
    if(!force && cache.readings.length && Date.now()-cache.fetchedAt<30000) return cache.readings;
    if(typeof navigator!=='undefined' && navigator.onLine===false) return cache.readings;
    cache.loading=true;
    try{
      var res=await fetch('/api/temperature-readings',{credentials:'same-origin',cache:'no-store',headers:{'Accept':'application/json'}});
      var data=await res.json().catch(function(){return {};});
      if(!res.ok || !data || data.ok!==true || !Array.isArray(data.readings)) throw new Error((data&&data.error)||'Temperature data unavailable');
      cache.readings=data.readings.slice().sort(function(a,b){return new Date(a.ts)-new Date(b.ts);});
      cache.fetchedAt=Date.now();
      try{ if(window.STATE && Array.isArray(STATE.tempReadings)) STATE.tempReadings=cache.readings.slice(); }catch(e){}
      return cache.readings;
    }catch(err){
      console.error('[Command de Cuisine] authoritative temperature dashboard fetch failed',err);
      return cache.readings;
    }finally{
      cache.loading=false;
    }
  }

  function findGraphCard(){
    var nodes=document.querySelectorAll('h1,h2,h3,h4,h5,h6,.section-title,.card-title,div');
    var heading=null;
    for(var i=0;i<nodes.length;i++){
      var t=String(nodes[i].textContent||'').trim().replace(/\s+/g,' ').toUpperCase();
      if(t.indexOf('COLD-CHAIN COMPLIANCE')===0 && t.length<80){ heading=nodes[i]; break; }
    }
    if(!heading) return null;
    var card=heading.closest('.card,.panel,.section,.box');
    if(card) return card;
    var p=heading.parentElement;
    while(p && p!==document.body){
      var text=String(p.textContent||'').toUpperCase();
      if(text.indexOf('14-DAY TREND')>=0 || text.indexOf('FRIDGE 2')>=0) return p;
      p=p.parentElement;
    }
    return heading.parentElement;
  }

  function barsSvg(readings){
    var today=new Date(), data=[];
    for(var offset=6;offset>=0;offset--){
      var d=new Date(today.getFullYear(),today.getMonth(),today.getDate()-offset);
      var key=dayKey(d);
      var rows=readings.filter(function(r){return hasValue(r)&&localDay(r.ts)===key;});
      var ok=rows.filter(function(r){return !isDanger(r);}).length;
      data.push({label:shortDay(d),has:rows.length>0,value:rows.length?Math.round(ok/rows.length*100):0,count:rows.length});
    }
    var w=620,h=170,pl=12,pr=12,pt=20,pb=38;
    var bw=(w-pl-pr)/7;
    var body=data.map(function(d,i){
      var x=pl+i*bw, cx=x+bw/2;
      if(!d.has){
        return '<line x1="'+(cx-18)+'" x2="'+(cx+18)+'" y1="'+(h-pb-4)+'" y2="'+(h-pb-4)+'" stroke="var(--line2)" stroke-width="3" />'+
          '<text x="'+cx+'" y="'+(h-pb-12)+'" text-anchor="middle" fill="var(--muted)" font-size="12">—</text>'+
          '<text x="'+cx+'" y="'+(h-10)+'" text-anchor="middle" fill="var(--faint)" font-size="12">'+esc(d.label)+'</text>';
      }
      var bh=Math.max(3,(d.value/100)*(h-pt-pb)), y=h-pb-bh;
      var color=d.value>=95?'var(--ok)':d.value>=80?'var(--warn)':'var(--danger)';
      return '<rect x="'+(x+bw*.18).toFixed(1)+'" y="'+y.toFixed(1)+'" width="'+(bw*.64).toFixed(1)+'" height="'+bh.toFixed(1)+'" rx="5" fill="'+color+'" />'+
        '<text x="'+cx.toFixed(1)+'" y="'+Math.max(13,y-6).toFixed(1)+'" text-anchor="middle" fill="var(--muted)" font-size="12">'+d.value+'%</text>'+
        '<text x="'+cx.toFixed(1)+'" y="'+(h-10)+'" text-anchor="middle" fill="var(--faint)" font-size="12">'+esc(d.label)+'</text>';
    }).join('');
    return '<svg viewBox="0 0 '+w+' '+h+'" width="100%" role="img" aria-label="Cold-chain readings in range for the last seven calendar days">'+body+'</svg>';
  }

  function coldApps(readings){
    var ids=new Set(readings.map(function(r){return String(r.appId||'');}));
    var apps=[];
    try{ apps=(STATE.appliances||[]).filter(function(a){return a&&ids.has(String(a.id));}); }catch(e){}
    if(!apps.length){
      var seen=new Set();
      readings.forEach(function(r){
        var a=applianceById(r.appId);
        if(a&&!seen.has(String(a.id))){seen.add(String(a.id));apps.push(a);}
      });
    }
    return apps.sort(function(a,b){return String(a.name||'').localeCompare(String(b.name||''));});
  }

  function latestEvent(readings,appId){
    var rows=readings.filter(function(r){return String(r.appId)===String(appId);});
    return rows.length?rows[rows.length-1]:null;
  }
  function defaultApp(apps,readings){
    var saved='';
    try{saved=localStorage.getItem('cdc_temp_trend_app')||'';}catch(e){}
    if(saved && apps.some(function(a){return String(a.id)===saved;})) return saved;
    for(var i=0;i<apps.length;i++){
      var last=latestEvent(readings,apps[i].id);
      if(last && hasValue(last)) return String(apps[i].id);
    }
    for(var j=0;j<apps.length;j++){
      var any=readings.some(function(r){return String(r.appId)===String(apps[j].id)&&hasValue(r);});
      if(any) return String(apps[j].id);
    }
    return apps[0]?String(apps[0].id):'';
  }

  function trendSvg(readings,appId){
    var now=new Date(), start=new Date(now.getFullYear(),now.getMonth(),now.getDate()-13);
    var startMs=start.getTime(), end=new Date(now.getFullYear(),now.getMonth(),now.getDate()+1).getTime()-1;
    var rows=readings.filter(function(r){
      var t=new Date(r.ts).getTime();
      return String(r.appId)===String(appId)&&Number.isFinite(t)&&t>=startMs&&t<=end;
    }).sort(function(a,b){return new Date(a.ts)-new Date(b.ts);});
    var numeric=rows.filter(hasValue);
    var statuses=rows.filter(function(r){return OFFLINE.has(statusOf(r));});
    var latest=rows.length?rows[rows.length-1]:null;
    var w=620,h=220,pl=46,pr=14,pt=18,pb=46;
    if(!numeric.length){
      var latestLabel=latest&&OFFLINE.has(statusOf(latest))?STATUS_LABEL[statusOf(latest)]:'No numeric readings';
      return '<div class="cdc-auth-temp-empty"><strong>'+esc(latestLabel)+'</strong><span>No temperature line is drawn without actual numeric readings.</span></div>'+
        statusStrip(statuses,startMs,end,w);
    }
    var values=numeric.map(function(r){return Number(r.value);});
    var min=Math.min.apply(null,values), max=Math.max.apply(null,values);
    var spread=Math.max(2,max-min), pad=Math.max(1,spread*.2); min-=pad;max+=pad;
    function x(ts){return pl+((new Date(ts).getTime()-startMs)/(end-startMs))*(w-pl-pr);}
    function y(v){return pt+(max-v)/(max-min)*(h-pt-pb);}
    var statusTimes=statuses.map(function(r){return new Date(r.ts).getTime();}).filter(Number.isFinite);
    var segments=[],seg=[];
    numeric.forEach(function(r){
      if(seg.length){
        var prev=seg[seg.length-1],a=new Date(prev.ts).getTime(),b=new Date(r.ts).getTime();
        var interruption=statusTimes.some(function(t){return t>a&&t<b;});
        if(interruption || b-a>36*3600*1000){segments.push(seg);seg=[];}
      }
      seg.push(r);
    });
    if(seg.length)segments.push(seg);
    var lines=segments.map(function(s){
      return '<polyline fill="none" stroke="var(--brass)" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" points="'+
        s.map(function(r){return x(r.ts).toFixed(1)+','+y(Number(r.value)).toFixed(1);}).join(' ')+'"/>';
    }).join('');
    var dots=numeric.map(function(r){
      return '<circle cx="'+x(r.ts).toFixed(1)+'" cy="'+y(Number(r.value)).toFixed(1)+'" r="3.6" fill="var(--brass)"><title>'+esc(localDay(r.ts)+' '+(r.period||'')+' · '+fmt(r.value)+'°C')+'</title></circle>';
    }).join('');
    var yLabels=[max,(max+min)/2,min].map(function(v){
      return '<text x="'+(pl-7)+'" y="'+(y(v)+4).toFixed(1)+'" text-anchor="end" fill="var(--faint)" font-size="11">'+fmt(v)+'°</text>';
    }).join('');
    var xLabels='';
    for(var i=0;i<14;i+=3){
      var d=new Date(start.getFullYear(),start.getMonth(),start.getDate()+i),xx=pl+(i/13)*(w-pl-pr);
      xLabels+='<text x="'+xx.toFixed(1)+'" y="'+(h-10)+'" text-anchor="middle" fill="var(--faint)" font-size="11">'+esc(shortDay(d))+'</text>';
    }
    var statusMarks=statuses.map(function(r){
      var xx=x(r.ts),label=statusOf(r)==='out_of_order'?'OOO':statusOf(r)==='awaiting_repair'?'REPAIR':statusOf(r)==='not_in_use'?'N/U':'DEF';
      return '<rect x="'+(xx-8).toFixed(1)+'" y="'+(h-pb+9)+'" width="16" height="16" rx="4" fill="var(--danger)" opacity=".75"><title>'+esc(STATUS_LABEL[statusOf(r)]||statusOf(r))+'</title></rect>'+
        '<text x="'+xx.toFixed(1)+'" y="'+(h-pb+22)+'" text-anchor="middle" fill="var(--ink)" font-size="7">'+esc(label)+'</text>';
    }).join('');
    var latestText=latest&&OFFLINE.has(statusOf(latest))?'<div class="cdc-auth-temp-status bad">'+esc(STATUS_LABEL[statusOf(latest)])+'</div>':'';
    return latestText+'<svg viewBox="0 0 '+w+' '+h+'" width="100%" role="img" aria-label="Actual temperature readings over the last fourteen days">'+
      '<line x1="'+pl+'" x2="'+(w-pr)+'" y1="'+(h-pb)+'" y2="'+(h-pb)+'" stroke="var(--line2)"/>'+yLabels+lines+dots+statusMarks+xLabels+'</svg>';
  }
  function statusStrip(statuses,startMs,endMs,w){
    if(!statuses.length) return '';
    var grouped={};
    statuses.forEach(function(r){grouped[localDay(r.ts)]=STATUS_LABEL[statusOf(r)]||statusOf(r);});
    return '<div class="cdc-auth-temp-status-list">'+Object.keys(grouped).sort().map(function(k){return '<span><b>'+esc(k.slice(5))+'</b> '+esc(grouped[k])+'</span>';}).join('')+'</div>';
  }

  function renderCard(readings){
    var card=findGraphCard();
    if(!card) return false;
    var apps=coldApps(readings);
    if(!apps.length) return false;
    var selected=card.dataset.cdcTrendApp;
    if(!selected || !apps.some(function(a){return String(a.id)===selected;})) selected=defaultApp(apps,readings);
    card.dataset.cdcTrendApp=selected;

    card.innerHTML=
      '<div class="cdc-auth-temp-block">'+
        '<h3 class="cdc-auth-temp-title">Cold-chain compliance — last 7 days</h3>'+
        '<div class="cdc-auth-temp-sub">Actual saved numeric readings in range. Equipment recorded Out of order / Not in use is not treated as a temperature reading.</div>'+
        barsSvg(readings)+
        '<div class="cdc-auth-temp-trend-head"><h3 class="cdc-auth-temp-title">Temperature trends — last 14 days</h3>'+
          '<select class="input cdc-auth-temp-select" aria-label="Choose appliance">'+apps.map(function(a){return '<option value="'+esc(a.id)+'"'+(String(a.id)===selected?' selected':'')+'>'+esc(a.name||a.id)+'</option>';}).join('')+'</select>'+
        '</div>'+
        '<div class="cdc-auth-temp-sub">Real saved readings only. Status periods break the line instead of inventing values.</div>'+
        '<div class="cdc-auth-temp-trend">'+trendSvg(readings,selected)+'</div>'+
      '</div>';
    var sel=card.querySelector('.cdc-auth-temp-select');
    if(sel) sel.addEventListener('change',function(){
      card.dataset.cdcTrendApp=this.value;
      try{localStorage.setItem('cdc_temp_trend_app',this.value);}catch(e){}
      var t=card.querySelector('.cdc-auth-temp-trend');
      if(t)t.innerHTML=trendSvg(cache.readings,this.value);
    });
    return true;
  }

  function installCss(){
    if(document.getElementById('cdc-authoritative-temp-css')) return;
    var s=document.createElement('style');s.id='cdc-authoritative-temp-css';
    s.textContent=
      '.cdc-auth-temp-block{padding:4px 2px}.cdc-auth-temp-title{margin:10px 0 6px;font-family:var(--display);letter-spacing:.04em;text-transform:uppercase}.cdc-auth-temp-sub{color:var(--muted);font-size:13px;line-height:1.4;margin-bottom:8px}.cdc-auth-temp-trend-head{display:flex;gap:12px;align-items:center;justify-content:space-between;margin-top:18px}.cdc-auth-temp-select{max-width:220px;min-width:150px}.cdc-auth-temp-empty{min-height:145px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;color:var(--muted);text-align:center}.cdc-auth-temp-empty strong{color:var(--ink);font-size:18px}.cdc-auth-temp-status{display:inline-flex;padding:5px 9px;border-radius:999px;margin:2px 0 4px;font-size:12px;font-weight:800}.cdc-auth-temp-status.bad{background:rgba(214,74,74,.13);color:var(--danger)}.cdc-auth-temp-status-list{display:flex;flex-wrap:wrap;gap:7px;margin-top:8px}.cdc-auth-temp-status-list span{border:1px solid var(--line);border-radius:8px;padding:6px 8px;color:var(--muted);font-size:11px}@media(max-width:620px){.cdc-auth-temp-trend-head{align-items:flex-start;flex-direction:column}.cdc-auth-temp-select{width:100%;max-width:none}}';
    document.head.appendChild(s);
  }

  var queued=false;
  async function refresh(force){
    if(queued&&!force)return;
    queued=true;
    try{
      installCss();
      var readings=await fetchReadings(!!force);
      renderCard(readings);
    }finally{queued=false;}
  }
  function schedule(){
    clearTimeout(schedule._t);
    schedule._t=setTimeout(function(){refresh(false);},120);
  }

  function start(){
    installCss();
    refresh(true);
    new MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true});
    window.addEventListener('focus',function(){refresh(true);});
    window.addEventListener('online',function(){refresh(true);});
    document.addEventListener('visibilitychange',function(){if(!document.hidden)refresh(true);});
    window.CDCTemperatureDashboard={refresh:function(){return refresh(true);},readings:function(){return cache.readings.slice();}};
    console.info('[Command de Cuisine] Authoritative server-backed temperature dashboard active');
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true}); else start();
})();