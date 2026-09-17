/* ============================================================================
   integration_bridge.js  —  Command de Cuisine
   ----------------------------------------------------------------------------
   Makes the modules actually feed each other. Two real cross-module breaks are
   repaired here, both additive and reversible:

   1. MENU SCHEMA BRIDGE
      Different importers store a menu's dishes under different keys:
        • base UI + detailed_menu_recipes.js   → menu.dishIds
        • menu_photo_complete_import_patch.js  → menu.recipeIds
      Downstream code primarily reads dishIds. This mirrors the two keys with
      dishIds canonical, so every importer feeds the same menu/prep/stock flow.

   2. RECIPE → STOCK LINK HARDENING
      Ingredients get a persistent stockId only when their normalised name maps
      to exactly ONE stock item. Duplicate stock names are deliberately treated
      as ambiguous and are never auto-linked. Existing explicit stockIds are
      never overwritten.

   window.linkHealth() reports valid, unlinked and ambiguous ingredient links.
   ========================================================================== */
(function () {
  'use strict';
  if (window.__cdcIntegrationBridge) return;
  window.__cdcIntegrationBridge = true;

  function ready() { return typeof STATE !== 'undefined' && typeof save === 'function' && typeof rerender === 'function'; }
  var norm = function (s) { return String(s == null ? '' : s).toLowerCase().trim().replace(/\s+/g, ' '); };

  function normalizeMenus() {
    var changed = false;
    (STATE.menus || []).forEach(function (m) {
      if (!m || typeof m !== 'object') return;
      var canon;
      if (Array.isArray(m.dishIds)) canon = m.dishIds.slice();
      else if (Array.isArray(m.recipeIds)) canon = m.recipeIds.slice();
      else canon = [];
      var seen = {}, clean = [];
      canon.forEach(function (id) {
        var k = String(id);
        if (id != null && !seen[k]) { seen[k] = 1; clean.push(id); }
      });
      var a = JSON.stringify(m.dishIds || null), b = JSON.stringify(m.recipeIds || null), c = JSON.stringify(clean);
      if (a !== c || b !== c) {
        m.dishIds = clean.slice();
        m.recipeIds = clean.slice();
        changed = true;
      }
    });
    return changed;
  }

  function stockNameIndex() {
    var idx = {};
    (STATE.stock || []).forEach(function (s) {
      var n = norm(s && (s.item || s.name));
      if (!n || !s || s.id == null) return;
      if (!idx[n]) idx[n] = [];
      idx[n].push(s.id);
    });
    return idx;
  }

  function hardenIngredientLinks() {
    if (!Array.isArray(STATE.stock)) return false;
    var byName = stockNameIndex();
    var changed = false;
    (STATE.recipes || []).forEach(function (r) {
      (r.ingredients || []).forEach(function (ing) {
        if (!ing || (ing.stockId != null && ing.stockId !== '')) return;
        var ids = byName[norm(ing.name)] || [];
        if (ids.length === 1) {
          ing.stockId = ids[0];
          changed = true;
        }
      });
    });
    return changed;
  }

  function linkHealth() {
    var total = 0, linked = 0, ambiguous = 0, details = [];
    var idx = stockNameIndex();
    var stockIds = {};
    (STATE.stock || []).forEach(function (s) { if (s && s.id != null) stockIds[String(s.id)] = true; });
    (STATE.recipes || []).forEach(function (r) {
      (r.ingredients || []).forEach(function (ing) {
        total++;
        var hasExplicit = !!(ing && ing.stockId != null && ing.stockId !== '');
        if (hasExplicit) {
          if (stockIds[String(ing.stockId)]) linked++;
          else if (details.length < 40) details.push({ recipe: r && r.name, ingredient: ing && ing.name, reason: 'explicit stock link no longer exists' });
          return;
        }
        var ids = idx[norm(ing && ing.name)] || [];
        if (ids.length === 1) linked++;
        else {
          var why = ids.length > 1 ? 'ambiguous duplicate stock name' : 'no exact stock match';
          if (ids.length > 1) ambiguous++;
          if (details.length < 40) details.push({ recipe: r && r.name, ingredient: ing && ing.name, reason: why });
        }
      });
    });
    return { total: total, linked: linked, unlinked: total - linked, ambiguous: ambiguous, details: details };
  }

  function pass() {
    var a = false, b = false;
    try { a = normalizeMenus(); } catch (e) {}
    try { b = hardenIngredientLinks(); } catch (e) {}
    return a || b;
  }

  function install() {
    if (!ready()) return setTimeout(install, 200);
    pass();
    if (!window.__cdcSaveBridged) {
      window.__cdcSaveBridged = true;
      var origSave = save;
      window.save = function (reason) { try { pass(); } catch (e) {} return origSave(reason); };
      try { save = window.save; } catch (e) {}
    }
    if (!window.__cdcRerenderBridged) {
      window.__cdcRerenderBridged = true;
      var origRerender = rerender;
      window.rerender = function () { try { normalizeMenus(); } catch (e) {} return origRerender.apply(this, arguments); };
      try { rerender = window.rerender; } catch (e) {}
    }
    window.linkHealth = linkHealth;
    var h = linkHealth();
    console.info('[Command de Cuisine] integration bridge active — menus unified, ' +
      h.linked + '/' + h.total + ' recipe ingredients linked/resolvable' +
      (h.ambiguous ? ' (' + h.ambiguous + ' ambiguous duplicate-name link' + (h.ambiguous === 1 ? '' : 's') + ')' : ''));
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true });
  else install();
})();
