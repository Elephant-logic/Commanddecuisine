"""Browser smoke test: app menu action -> downloaded offline HTML -> editable order-only file."""
from __future__ import annotations
import functools
import http.server
import json
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent

STATE = {
    "stock": [
        {"id": "a", "item": "Tomato puree", "cat": "Ambient", "unit": "g", "qtyKnown": False},
        {"id": "b", "item": "Tomato purée", "cat": "Ambient", "unit": "g", "qtyKnown": False},
        {"id": "c", "item": "Potatoes", "cat": "Veg", "unit": "kg", "qtyKnown": False},
        {"id": "d", "item": "Salt", "cat": "Ambient", "unit": "g", "qtyKnown": False},
    ],
    "recipes": [
        {"id": "r1", "name": "Test Lasagne", "needsReview": True,
         "ingredients": [
            {"name": "Tomato purée", "stockId": "b", "qty": 100, "unit": "g"},
            {"name": "Ricotta", "qty": 300, "unit": "g"},
        ]},
    ],
    "menus": [{"id": "menu1", "name": "Test Uploaded Menu", "dishIds": ["r1"]}],
}

def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "full_stock_html_export.js").write_bytes(
            (ROOT / "full_stock_html_export.js").read_bytes())
        (root / "full_stock_order_template.html").write_bytes(
            (ROOT / "full_stock_order_template.html").read_bytes())
        fixture = """<!doctype html><html><head><meta charset="utf-8"></head>
<body><main id="view"></main><script>
var STATE=__STATE__;
var VIEWS={
  menus:function(v){v.textContent="Saved menus view";},
  stock:function(v){v.textContent="Stock view";}
};
function toast(){}
</script><script src="/full_stock_html_export.js"></script>
<script>VIEWS.menus(document.getElementById("view"));</script></body></html>
""".replace("__STATE__", json.dumps(STATE))
        (root / "index.html").write_text(fixture, encoding="utf-8")
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
                context = browser.new_context(accept_downloads=True)
                app = context.new_page()
                app.goto(f"http://127.0.0.1:{server.server_port}/index.html", wait_until="load")
                btn = app.get_by_role("button", name="Download full ordering sheet")
                assert btn.count() == 1, "Menu view must expose exactly one exporter button"
                app.evaluate("""() => window.dispatchEvent(new CustomEvent('cdc:menu-saved',
                  {detail:{name:'Test Uploaded Menu',menuId:'menu1'}}))""")
                assert "Test Uploaded Menu saved" in app.locator(".cdc-stock-explainer").inner_text()
                with app.expect_download() as action:
                    btn.click()
                download = action.value
                path = root / "full_sheet.html"
                download.save_as(path)
                text = path.read_text(encoding="utf-8")
                assert "Tomato purée" in text
                assert "Ricotta" in text
                assert "Test Uploaded Menu" in text

                sheet = context.new_page()
                sheet.goto(path.as_uri(), wait_until="load")
                assert sheet.locator("#total").inner_text() == "4", "Duplicate aliases must be consolidated"
                assert sheet.locator("#reviewNotice").is_visible(), "AI recipe review notice must be shown"
                assert sheet.locator("#selectedEmpty").is_visible(), "Start with empty order"
                sheet.get_by_role("checkbox", name="Add to order: Tomato purée").check()
                sheet.get_by_role("checkbox", name="Add to order: Ricotta").check()
                assert sheet.locator("#selCount").inner_text() == "2 selected"
                row = sheet.locator("#selectedBody tr").filter(has_text="Ricotta")
                row.get_by_role("textbox", name="quantity for Ricotta").fill("3")
                row.get_by_role("textbox", name="supplier for Ricotta").fill("Kitchen Supplies")
                assert sheet.locator("#printSelectedBody tr").count() == 2

                with sheet.expect_download() as action:
                    sheet.get_by_role("button", name="Download order-only HTML").click()
                order_download = action.value
                order_path = root / "order_only.html"
                order_download.save_as(order_path)
                order = context.new_page()
                order.goto(order_path.as_uri(), wait_until="load")
                assert order.locator("#selectedBody tr").count() == 2
                assert order.locator("#selCount").inner_text() == "2 selected"
                assert order.locator("#body").locator("xpath=ancestor::section[1]").is_hidden(), "Order-only file must hide catalogue"
                assert order.locator("#selectedBody tr").filter(has_text="Ricotta").get_by_role(
                    "textbox", name="quantity for Ricotta").input_value() == "3"

                order.locator('#add input[name="name"]').fill("Lemons")
                order.get_by_role("button", name="+ Add item").click()
                assert order.locator("#selCount").inner_text() == "3 selected"
                order.locator("#selectedBody tr").filter(has_text="Ricotta").get_by_role(
                    "button", name="Remove from order").click()
                assert order.locator("#selCount").inner_text() == "2 selected"
                order.emulate_media(media="print")
                assert order.locator("#printSelectedSheet").is_visible()
                assert order.locator("#printSelectedBody tr").count() == 2
                assert order.locator(".wrap").is_hidden(), "Print must exclude full interactive catalogue"
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
    print("PASS: Imported menu launcher, offline HTML, selections, order-only save, add/remove and print")

if __name__ == "__main__":
    main()
