#!/usr/bin/env python3
"""验证 Extra High / Max 置灰且点击无效"""
from playwright.sync_api import sync_playwright

BASE = "http://192.168.2.88:8081"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(BASE + "/", wait_until="domcontentloaded")
    pg.fill("input[name=username]", "cctest1")
    pg.fill("input[name=password]", "test12345")
    pg.click("button[type=submit]")
    pg.wait_for_selector("#cctm-nav", timeout=60000)
    pg.wait_for_timeout(2500)
    pg.click('button[aria-label="Settings"]', timeout=5000)
    pg.wait_for_timeout(1000)
    pg.click("text=Model", timeout=5000)
    pg.wait_for_timeout(800)
    pg.click('[role=combobox][aria-label="Reasoning Effort"]', timeout=5000)
    pg.wait_for_timeout(1000)
    opts = pg.evaluate("""() => {
        const out = [];
        document.querySelectorAll("[role=option]").forEach(el => {
            out.push({t: (el.textContent||"").trim(),
                      disabled: el.hasAttribute("disabled"),
                      cls: el.classList.contains("cctm-disabled-opt")});
        });
        return out;
    }""")
    print("effort options:", opts)
    try:
        pg.get_by_role("option", name="Max", exact=True).click(timeout=2000)
        print("click Max: not blocked (BAD)")
    except Exception as e:
        print("click Max blocked:", type(e).__name__)
    pg.wait_for_timeout(500)
    val = pg.evaluate('() => { const el = document.querySelector(\'[role=combobox][aria-label="Reasoning Effort"]\'); return el ? el.textContent : null; }')
    print("combobox value after Max attempt:", repr(val))
    pg.screenshot(path="/tmp/cctm_shots/08_effort_open.png")
    b.close()
print("EFFORT2_DONE")
