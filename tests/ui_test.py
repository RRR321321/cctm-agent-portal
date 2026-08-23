#!/usr/bin/env python3
"""UI 测试：登录遮罩 / 注册空格校验 / shell 注入 / 思考档位 / 统计页"""
import os
from playwright.sync_api import sync_playwright

BASE = "http://192.168.2.88:8081"
OUT = "/tmp/cctm_shots"
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})

    # [1] 未登录首页 = 遮罩登录页（下层有发暗的 webshell 预览）
    pg.goto(BASE + "/", wait_until="domcontentloaded")
    pg.wait_for_selector(".gate-card", timeout=15000)
    ok1 = ("注册请用名字拼音，不能有空格" in pg.content()
           and pg.locator(".shell-preview").count() == 1
           and pg.locator(".gate-overlay").count() == 1)
    pg.screenshot(path=f"{OUT}/01_gate.png")
    print(f"[1] 登录遮罩页: {ok1}")

    # [2] 注册：输入含空格用户名 → 红色警告 + 禁止提交
    pg.goto(BASE + "/register/", wait_until="domcontentloaded")
    pg.wait_for_selector("#reg-username", timeout=15000)
    pg.fill("#reg-username", "bad name")
    pg.wait_for_timeout(300)
    warn = pg.locator("#name-warn")
    ok2 = warn.is_visible() and "空格" in warn.inner_text() and pg.locator("#reg-submit").is_disabled()
    pg.screenshot(path=f"{OUT}/02_register_space.png")
    print(f"[2] 空格红字警告: {ok2} ({warn.inner_text() if warn.is_visible() else '-'})")

    # [3] 登录进 shell：导航条注入 + 标题
    pg.goto(BASE + "/", wait_until="domcontentloaded")
    pg.fill("input[name=username]", "cctest1")
    pg.fill("input[name=password]", "test12345")
    pg.click("button[type=submit]")
    pg.wait_for_selector("#cctm-nav", timeout=60000)
    pg.wait_for_timeout(4000)
    tabs = pg.locator("#cctm-nav .cctm-tab").all_inner_texts()
    body_len = pg.evaluate("() => document.body.innerText.length")
    ok3 = pg.title() == "CCTM AGENT" and "CCTM AGENT" in tabs and "agent 统计" in tabs
    pg.screenshot(path=f"{OUT}/03_shell.png")
    print(f"[3] shell 注入: {ok3}, title={pg.title()}, tabs={tabs}, bodyText={body_len}")

    # [4] 思考档位：找设置/思考入口并检查 xhigh/max 置灰
    probe = pg.evaluate("""() => {
        const res = {triggers: [], options: []};
        document.querySelectorAll('button, [role=button], [aria-label], [title]').forEach(el => {
            const s = ((el.textContent||'') + '|' + (el.getAttribute('aria-label')||'') + '|' + (el.getAttribute('title')||'')).toLowerCase();
            if (/思考|thinking|reason|effort|设置|settings/.test(s) && el.childElementCount <= 3) {
                res.triggers.push({tag: el.tagName, text: (el.textContent||'').trim().slice(0,30), aria: el.getAttribute('aria-label')||'', title: el.getAttribute('title')||''});
            }
        });
        document.querySelectorAll('button,[role=option],[role=menuitem],[role=menuitemradio],li,option,span,div').forEach(el => {
            const t = (el.textContent||'').trim();
            if (/^(low|medium|high|xhigh|max|x-high)$/i.test(t) && el.childElementCount === 0) {
                res.options.push({tag: el.tagName, text: t,
                    disabled: el.hasAttribute('disabled') || el.classList.contains('cctm-disabled-opt')});
            }
        });
        return res;
    }""")
    print(f"[4] 思考档位探测: triggers={probe['triggers'][:5]} options={probe['options']}")
    # 尝试点开含"思考/effort"的触发器再看一次
    clicked = False
    for t in probe["triggers"]:
        try:
            if t["text"]:
                pg.locator(f"{t['tag'].lower()}", has_text=t["text"]).first.click(timeout=2000)
                clicked = True
                break
        except Exception:
            continue
    if clicked:
        pg.wait_for_timeout(800)
        probe2 = pg.evaluate("""() => {
            const out = [];
            document.querySelectorAll('button,[role=option],[role=menuitem],[role=menuitemradio],li,option,span,div').forEach(el => {
                const t = (el.textContent||'').trim();
                if (/^(low|medium|high|xhigh|max|x-high)$/i.test(t) && el.childElementCount === 0) {
                    out.push({text: t, disabled: el.hasAttribute('disabled') || el.classList.contains('cctm-disabled-opt')});
                }
            });
            return out;
        }""")
        pg.screenshot(path=f"{OUT}/04_effort.png")
        print(f"[4b] 展开后档位: {probe2}")
    else:
        pg.screenshot(path=f"{OUT}/04_effort.png")
        print("[4b] 未找到思考档位触发器（可能在设置弹窗里）")

    # [5] 统计页
    pg.goto(BASE + "/stats/", wait_until="domcontentloaded")
    pg.wait_for_selector("#total-num", timeout=15000)
    pg.wait_for_timeout(2000)
    total = pg.locator("#total-num").inner_text()
    rank_items = pg.locator("#rank-list .rank-item").count()
    medal = pg.locator("#rank-list .rank-medal").first.inner_text() if rank_items else ""
    active = pg.locator("#active-num").inner_text() + pg.locator("#active-cap").inner_text()
    chart_ok = pg.evaluate("() => !!window.Chart && !!document.getElementById('trend-chart')")
    pg.screenshot(path=f"{OUT}/05_stats.png")
    print(f"[5] 统计页: total={total}, rank={rank_items}(medal={medal}), active={active}, chart={chart_ok}")

    b.close()
print("UI_DONE")
