/* Command de Cuisine - local AM/PM temperature round rollover */
(function(){
  'use strict';
  if(window.__cdcTempRoundRollover) return;
  window.__cdcTempRoundRollover=true;

  function localKey(){
    var d=new Date();
    var day=[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');
    return day+'|'+(d.getHours()<12?'am':'pm');
  }

  var last=localKey();

  function rerenderForClock(force){
    var nowKey=localKey();
    if(!force && nowKey===last) return;
    last=nowKey;
    try{
      if(typeof rerender==='function') rerender();
    }catch(e){
      console.warn('[Command de Cuisine] temperature round clock refresh failed',e);
    }
    try{
      if(window.CDCTemperatureDashboard&&typeof window.CDCTemperatureDashboard.refresh==='function'){
        window.CDCTemperatureDashboard.refresh();
      }
    }catch(e){}
  }

  function start(){
    // Re-render once after load so a page restored from mobile browser cache
    // cannot keep yesterday's date or the pre-noon AM round.
    setTimeout(function(){rerenderForClock(true);},250);
    setInterval(function(){rerenderForClock(false);},30000);
    window.addEventListener('focus',function(){rerenderForClock(true);});
    window.addEventListener('pageshow',function(){rerenderForClock(true);});
    document.addEventListener('visibilitychange',function(){
      if(!document.hidden) rerenderForClock(true);
    });
    window.CDCTemperatureRoundClock={refresh:function(){rerenderForClock(true);},key:localKey};
    console.info('[Command de Cuisine] Temperature round uses local noon AM/PM rollover');
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();