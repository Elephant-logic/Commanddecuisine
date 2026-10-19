"""Check generated deployment assets without accessing the live service or database."""
from pathlib import Path

app=Path('app')
index=(app/'index.html').read_text(encoding='utf-8')
server=(app/'server.py').read_text(encoding='utf-8')
importer=(app/'reliable_menu_import.js').read_text(encoding='utf-8')
exporter=(app/'full_stock_html_export.js').read_text(encoding='utf-8')
template=(app/'full_stock_order_template.html').read_text(encoding='utf-8')
assert index.count('<script src="/full_stock_html_export.js?v=20261019-full-list1"></script>')==1, 'Missing or duplicate exporter script'
assert server.count("'/full_stock_html_export.js'")==1, 'Exporter route missing or duplicated'
assert server.count("'/full_stock_order_template.html'")==1, 'Order template route missing or duplicated'
assert "window.dispatchEvent(new CustomEvent('cdc:menu-saved'" in importer, 'Missing menu-save signal'
assert "'cdc:menu-saved'" in exporter, 'Exporter not listening to menu-save signal'
assert 'function fullList()' in exporter, 'Missing full catalogue aggregator'
assert 'function saveSelectedHtml()' in template, 'Missing separate editable order export'
assert 'id="selectedOrderPanel"' in template, 'Missing selected-order section'
assert 'id="printSelectedSheet"' in template, 'Missing order-only print sheet'
assert 'function saveSelectedCsv()' in template, 'Missing order-only CSV'
assert 'reviewCount' in template, 'Missing recipe verification warning'
assert 'orderOnly:isOrderOnly' in template, 'Edited order-only mode must persist'
print('PASS: Final ZIP-and-patches build serves and loads all ordering assets exactly once')
