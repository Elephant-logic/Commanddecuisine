/* Command de Cuisine - mobile temperature sign control */
(function () {
  'use strict';
  if (window.__cdcTempSignControl) return;
  window.__cdcTempSignControl = true;

  function looksLikeTemperatureInput(input) {
    if (!input || input.tagName !== 'INPUT') return false;
    var ph = String(input.getAttribute('placeholder') || '').toLowerCase();
    var name = String(input.getAttribute('name') || '').toLowerCase();
    var aria = String(input.getAttribute('aria-label') || '').toLowerCase();
    if (ph.indexOf('°c') >= 0 || ph.indexOf('ºc') >= 0) return true;
    if (name.indexOf('temp') >= 0 || aria.indexOf('temp') >= 0) return true;
    var p = input.parentElement;
    var context = p && p.parentElement ? String(p.parentElement.textContent || '').toLowerCase() : '';
    return input.getAttribute('step') === '0.1' && (context.indexOf('temperature') >= 0 || context.indexOf('fridge') >= 0 || context.indexOf('freezer') >= 0);
  }

  function dispatch(input) {
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function enhance(input) {
    if (!looksLikeTemperatureInput(input) || input.dataset.cdcTempSign === '1') return;
    input.dataset.cdcTempSign = '1';

    input.type = 'text';
    input.setAttribute('inputmode', 'decimal');
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('enterkeyhint', 'done');
    input.setAttribute('aria-label', input.getAttribute('aria-label') || 'Temperature in degrees Celsius');

    var parent = input.parentNode;
    if (!parent) return;

    var wrap = document.createElement('div');
    wrap.className = 'cdc-temp-signed-input';
    wrap.style.cssText = 'display:flex;align-items:stretch;gap:6px;min-width:0;width:100%;';
    parent.insertBefore(wrap, input);
    wrap.appendChild(input);
    input.style.flex = '1 1 auto';
    input.style.minWidth = '0';

    var sign = document.createElement('button');
    sign.type = 'button';
    sign.className = 'btn ghost';
    sign.textContent = '±';
    sign.title = 'Change temperature sign';
    sign.setAttribute('aria-label', 'Change temperature sign');
    sign.style.cssText = 'min-width:46px;padding-left:10px;padding-right:10px;font-size:20px;font-weight:800;';
    wrap.appendChild(sign);

    sign.addEventListener('click', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      var raw = String(input.value || '').trim().replace(',', '.');

      if (!raw) {
        input.value = '-';
      } else if (raw === '-') {
        input.value = '';
      } else {
        var n = Number(raw);
        if (Number.isFinite(n)) {
          input.value = n < 0 ? String(Math.abs(n)) : '-' + String(Math.abs(n));
        } else {
          input.value = raw.charAt(0) === '-' ? raw.slice(1) : '-' + raw.replace(/^\+/, '');
        }
      }
      dispatch(input);
      input.focus();
      try { input.setSelectionRange(input.value.length, input.value.length); } catch (e) {}
    });

    input.addEventListener('blur', function () {
      var raw = String(input.value || '').trim().replace(',', '.');
      if (!raw || raw === '-') return;
      var n = Number(raw);
      if (Number.isFinite(n)) {
        input.value = String(n);
        dispatch(input);
      }
    });
  }

  function scan(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var inputs = scope.querySelectorAll ? scope.querySelectorAll('input') : [];
    for (var i = 0; i < inputs.length; i++) enhance(inputs[i]);
    if (scope.tagName === 'INPUT') enhance(scope);
  }

  var queued = false;
  function queueScan() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () {
      queued = false;
      scan(document);
    });
  }

  function start() {
    scan(document);
    var obs = new MutationObserver(queueScan);
    obs.observe(document.documentElement, { childList: true, subtree: true });
    window.CDCTemperatureSignControl = { refresh: queueScan };
    console.info('[Command de Cuisine] Mobile temperature ± control active');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();