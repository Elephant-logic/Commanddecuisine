"""Reproduce and prevent the Timers buttons/input focus bug in a real browser.

Uses the actual assembled Kitchen Tools v2 script, without authentication,
user accounts, database connections, or saved kitchen state.
"""
from __future__ import annotations
import functools
import http.server
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

SOURCE=Path("app/kitchen_tools_v2.js")


def timer_data(page):
    return page.evaluate("() => window.CDCTimers.list()")


def test_context(browser, base_url, mobile):
    context=browser.new_context(
        viewport={"width":390,"height":844} if mobile else {"width":1150,"height":840},
        is_mobile=mobile,
        has_touch=mobile,
        device_scale_factor=2 if mobile else 1,
    )
    page=context.new_page()
    errors=[]
    page.on("pageerror",lambda e: errors.append(str(e)))
    page.goto(base_url,wait_until="load")
    page.locator("#cdc-ktv2-dock").wait_for()
    page.locator("#cdc-ktv2-dock").click()
    assert page.locator("#cdc-ktv2-panel").is_visible()

    # This failed on the original code: every 500 ms tick replaced inputs.
    page.locator("#cdc-ktv2-name").fill("Fish on the grill")
    page.locator("#cdc-ktv2-min").fill("2")
    page.locator("#cdc-ktv2-sec").fill("15")
    page.locator("#cdc-ktv2-sec").focus()
    page.wait_for_timeout(1250)
    assert page.evaluate("document.activeElement.id")=="cdc-ktv2-sec",(
        "Timer is redrawing form during input: button taps will be lost")
    assert page.locator("#cdc-ktv2-name").input_value()=="Fish on the grill"
    assert page.locator("#cdc-ktv2-min").input_value()=="2"
    assert page.locator("#cdc-ktv2-sec").input_value()=="15"

    page.get_by_role("button",name="Start timer").click()
    timers=timer_data(page)
    assert len(timers)==1 and timers[0]["name"]=="Fish on the grill", timers
    assert timers[0]["durationMs"]==135000 and timers[0]["status"]=="running", timers

    card=page.locator('.cdc-ktv2-timer[data-id="'+timers[0]["id"]+'"]')
    # Long press/click verifies stable button survives >500ms between down and up.
    pause=card.locator('[data-act="pause"]')
    pause.scroll_into_view_if_needed()
    box=pause.bounding_box()
    assert box, "Pause button is missing"
    page.mouse.move(box["x"]+box["width"]/2,box["y"]+box["height"]/2)
    page.mouse.down()
    page.wait_for_timeout(750)
    page.mouse.up()
    assert timer_data(page)[0]["status"]=="paused","Pause tap was swallowed by a panel redraw"

    card.locator('[data-act="plus1"]').click()
    paused=timer_data(page)[0]
    assert paused["status"]=="paused" and paused["remainingMs"]>190000,paused
    card.locator('[data-act="pause"]').click()
    assert timer_data(page)[0]["status"]=="running","Resume failed"

    card.locator('[data-act="plus5"]').click()
    timer=timer_data(page)[0]
    assert timer["endAt"]-timer["durationMs"]>0 and timer["endAt"]>0
    card.locator('[data-act="restart"]').click()
    restarted=timer_data(page)[0]
    assert restarted["status"]=="running" and 130000<=restarted["endAt"]-page.evaluate("Date.now()")<=140000,restarted

    card.locator('[data-act="remove"]').click()
    assert timer_data(page)==[],"Cancel failed"

    # The buttons which already worked must still work.
    page.locator('[data-preset="3"]').click()
    active=timer_data(page)
    assert len(active)==1 and active[0]["durationMs"]==180000,active
    page.locator(".cdc-ktv2-close").click()
    assert page.locator("#cdc-ktv2-panel").count()==0
    page.locator("#cdc-ktv2-dock").click()
    assert len(timer_data(page))==1,"Existing timer disappeared on reopen"

    # Other controls in Kitchen Tools must retain focus and work too.
    page.locator("#cdc-ktv2-conv-value").fill("2")
    page.locator("#cdc-ktv2-conv-from").select_option("kg")
    page.locator("#cdc-ktv2-conv-to").select_option("g")
    assert "2000" in page.locator("#cdc-ktv2-conv-result").inner_text()
    page.locator("#cdc-ktv2-scale-from").fill("10")
    page.locator("#cdc-ktv2-scale-to").fill("20")
    page.locator("#cdc-ktv2-scale-qty").fill("3")
    assert "6" in page.locator("#cdc-ktv2-scale-result").inner_text()
    page.wait_for_timeout(650)
    assert page.locator("#cdc-ktv2-scale-qty").input_value()=="3"
    assert not errors, "Unexpected browser script errors: "+repr(errors)
    context.close()
    print("PASS: "+("mobile touch" if mobile else "desktop")+" custom timer, long-press pause, resume, add time, restart, cancel, presets, converter and scaler")


def main():
    assert SOURCE.is_file(),"Must test actual built app/kitchen_tools_v2.js"
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        (root/"kitchen_tools_v2.js").write_bytes(SOURCE.read_bytes())
        (root/"index.html").write_text("""<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Timer isolation test</title></head><body><main id="view"></main>
<script src="/kitchen_tools_v2.js"></script></body></html>""",encoding="utf-8")
        handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(root))
        httpd=http.server.ThreadingHTTPServer(("127.0.0.1",0),handler)
        threading.Thread(target=httpd.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(headless=True,args=["--no-sandbox"])
                url="http://127.0.0.1:"+str(httpd.server_port)+"/index.html"
                test_context(browser,url,mobile=False)
                test_context(browser,url,mobile=True)
                browser.close()
        finally:
            httpd.shutdown()
            httpd.server_close()

if __name__=="__main__":
    main()
