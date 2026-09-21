/* Command de Cuisine - clean mobile temperature minus control */
(function () {
  'use strict';
  if (window.__cdcTempMinusClean) return;
  window.__cdcTempMinusClean = true;

  function txt(v) { return String(v == null ? '' : v).trim(); }

  function isSignButton(btn) {
    if (!btn || btn.tagName !== 'BUTTON') return false;
    var t = txt(btn.textContent).replace(/\s+/g, '');
    return t === '+' || t === '−' || t === '-' || t === '±';
  }

  function looksLikeTemperatureInput(input) {
    if (!input || input.tagName !== 'INPUT') return false;
    var ph = txt(input.getAttribute('placeholder')).toLowerCase();
    var name = txt(input.getAttribute('name')).toLowerCase();
    var aria = txt(input.getAttribute('aria-label')).toLowerCase();
    if (ph.indexOf('°c') >= 0 || ph.indexOf('ºc') >= 0) return true;
    if (name.indexOf('temp') >= 0 || aria.indexOf('temp') >= 0) return true;
    var node = input.parentElement;
    for (var i = 0; node && i < 4; i++, node = node.parentElement) {
      var context = txt(node.textContent).toLowerCase();
      if ((context.indexOf('temperature') >= 0 || context.indexOf('fridge') >= 0 || context.indexOf('freezer') >= 0) &&
          (input.getAttribute('step') === '0.1' || input.dataset.cdcTempSign === '1')) return true;
    }
    return input.dataset.cdcTempSign === '1';
  }

  function fire(input) {
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function unwrapOldControl(input) {
    var wrap = input.parentElement;
    if (!wrap || !wrap.classList || !wrap.classList.contains('cdc-temp-signed-input')) return;
    var parent = wrap.parentNode;
    if (!parent) return;
    parent.insertBefore(input, wrap);
    wrap.remove();
  }

  function controlRow(input) {
    var node = input.parentElement;
    for (var i = 0; node && i < 4; i++, node = node.parentElement) {
      var buttons = Array.prototype.slice.call(node.querySelectorAll('button')).filter(isSignButton);
      if (buttons.length) return node;
      if (node.querySelector && node.querySelector('select') && i > 0) return node;
    }
    return input.parentElement;
  }

  function cleanOldButtons(row) {
    if (!row || !row.querySelectorAll) return;
    Array.prototype.slice.call(row.querySelectorAll('button')).forEach(function (btn) {
      if (isSignButton(btn) && !btn.classList.contains('cdc-temp-minus-only')) btn.remove();
    });
  }

  function makeNegative(input) {
    var raw = txt(input.value).replace(',', '.');
    if (!raw) {
      input.value = '-';
    } else if (raw !== '-') {
      var n = Number(raw);
      if (Number.isFinite(n)) input.value = String(-Math.abs(n));
      else if (raw.charAt(0) !== '-') input.value = '-' + raw.replace(/^\+/, '');
    }
    fire(input);
    input.focus();
    try { input.setSelectionRange(input.value.length, input.value.length); } catch (e) {}
  }

  function enhance(input) {
    if (!looksLikeTemperatureInput(input)) return;

    unwrapOldControl(input);
    input.dataset.cdcTempSign = 'clean';
    input.type = 'text';
    input.setAttribute('inputmode', 'decimal');
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('enterkeyhint', 'done');
    input.setAttribute('aria-label', input.getAttribute('aria-label') || 'Temperature in degrees Celsius');
    input.style.minWidth = '0';

    var row = controlRow(input);
    cleanOldButtons(row);

    if (input.parentElement && input.parentElement.querySelector(':scope > .cdc-temp-minus-only')) return;

    var minus = document.createElement('button');
    minus.type = 'button';
    minus.className = 'btn ghost cdc-temp-minus-only';
    minus.textContent = '−';
    minus.title = 'Make temperature negative';
    minus.setAttribute('aria-label', 'Make temperature negative');
    minus.style.cssText = 'min-width:46px;padding-left:12px;padding-right:12px;font-size:22px;font-weight:800;';

    input.insertAdjacentElement('afterend', minus);
    minus.addEventListener('click', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      makeNegative(input);
    });

    input.addEventListener('blur', function () {
      var raw = txt(input.value).replace(',', '.');
      if (!raw || raw === '-') return;
      var n = Number(raw);
      if (Number.isFinite(n)) {
        input.value = String(n);
        fire(input);
      }
    });
  }

  function scan() {
    var inputs = document.querySelectorAll('input');
    for (var i = 0; i < inputs.length; i++) enhance(inputs[i]);
  }

  var queued = false;
  function queueScan() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () {
      queued = false;
      scan();
    });
  }

  function start() {
    scan();
    new MutationObserver(queueScan).observe(document.documentElement, { childList: true, subtree: true });
    window.CDCTemperatureSignControl = { refresh: queueScan };
    console.info('[Command de Cuisine] Clean single-minus temperature entry active');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();