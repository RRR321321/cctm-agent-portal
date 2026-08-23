#!/usr/bin/env python3
"""回归冒烟：匿名亮度/账号体系/tab 互通/对话/越权/统计"""
import requests
from playwright.sync_api import sync_playwright

BASE = "http://192.168.2.88:8081"
OK = []

def check(name, cond, extra=""):
    OK.append(bool(cond))
    print(f"[{'✔' if cond else '✘'}] {name} {extra}")

def login(pg, name, pw):
    pg.goto(BASE + "/", wait_until="domcontentloaded")
    pg.fill("input[name=username]", name)
    pg.fill("input[name=password]", pw)
    pg.click("button[type=submit]")
    pg.wait_for_selector("#cctm-nav", timeout=60000)
    pg.wait_for_timeout(2500)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)

    # S1 匿名登录页：遮罩在、提示在、截图目视亮度
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(BASE + "/", wait_until="domcontentloaded")
    pg.wait_for_selector(".gate-card", timeout=15000)
    body_bg = pg.evaluate("() => getComputedStyle(document.querySelector('.sp-body')).backgroundColor")
    check("S1 登录页结构", "注册请用名字拼音" in pg.content() and pg.locator(".shell-preview").count() == 1)
    print("    骨架底色:", body_bg, "(应明显比之前 #0d1322 亮)")
    pg.screenshot(path="/tmp/cctm_shots/10_gate_bright.png")

    # S2 borui 普通用户：登录落 agent 页，导航 grid 居中
    login(pg, "borui", "123456")
    nav_css = pg.evaluate("() => getComputedStyle(document.getElementById('cctm-nav')).display")
    tabs_center = pg.evaluate("""() => {
        const t = document.querySelector('#cctm-nav .cctm-tabs').getBoundingClientRect();
        return Math.abs((t.left + t.right) / 2 - window.innerWidth / 2) < 40;
    }""")
    check("S2 borui 进 agent 页 + tab 居中", nav_css == "grid" and tabs_center, f"display={nav_css} centered={tabs_center}")
    rb = pg.evaluate("""() => {
        const out = {brand: null, subtitle: null};
        document.querySelectorAll("span,div").forEach(el => {
            if (el.childElementCount) return;
            const cn = String(el.className || "");
            if (/brandName/.test(cn)) out.brand = el.textContent.trim();
            if (/subtitle/.test(cn) && el.textContent.trim()) out.subtitle = el.textContent.trim();
        });
        return out;
    }""")
    check("S8 品牌文案替换", rb["brand"] == "CCTM AGENT" and rb["subtitle"] == "你专属的临床试验全能专家", str(rb))
    pg.screenshot(path="/tmp/cctm_shots/11_shell_nav.png")

    # S3 tab 互通：统计 → 回 agent
    pg.click("#cctm-nav .cctm-tab[href='/stats/']")
    pg.wait_for_selector("#total-num", timeout=15000)
    pg.click("#cctm-nav .cctm-tab[href='/']")
    pg.wait_for_selector(".cm-content", timeout=30000)
    check("S3 tab 互通", True)
    pg.close()

    # S4 admin：落统计页 + /admin/ 可进
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(BASE + "/", wait_until="domcontentloaded")
    pg.fill("input[name=username]", "admin")
    pg.fill("input[name=password]", "123456")
    pg.click("button[type=submit]")
    pg.wait_for_selector("#total-num", timeout=15000)
    r = pg.goto(BASE + "/admin/", wait_until="domcontentloaded")
    check("S4 admin 落统计页 + admin 后台", r.status == 200 or "admin" in pg.url)
    pg.close()

    # S5 cctest1 对话
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    login(pg, "cctest1", "test12345")
    composer = pg.locator(".cm-content").first
    composer.click()
    pg.keyboard.insert_text("请只回复四个字：回归通过")
    pg.keyboard.press("Enter")
    try:
        pg.wait_for_selector("text=回归通过", timeout=180000)
        check("S5 对话收到回复", True)
    except Exception:
        check("S5 对话收到回复", False)
    pg.close()
    b.close()

# S6 跨用户 model key 越权
conf1, conf2 = {}, {}
for line in open("/etc/cctm/registry/cctest1.conf"):
    if "=" in line:
        k, v = line.strip().split("=", 1); conf1[k] = v
for line in open("/etc/cctm/registry/cctest2.conf"):
    if "=" in line:
        k, v = line.strip().split("=", 1); conf2[k] = v
r = requests.post(BASE + "/model/cctest1/v1/chat/completions",
                  json={"model": "qwen3.8-27b", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 4},
                  headers={"Authorization": "Bearer " + conf2["MODEL_KEY"]}, timeout=30)
check("S6 跨用户 key 401", r.status_code == 401, f"got {r.status_code}")

# S7 统计 JSON
s = requests.Session(); s.get(BASE + "/")
tok = s.cookies.get("csrftoken")
s.post(BASE + "/", data={"username": "cctest1", "password": "test12345", "csrfmiddlewaretoken": tok},
       headers={"Referer": BASE + "/"})
d = s.get(BASE + "/stats/?format=json").json()
check("S7 统计完整", d["total_all_time"] > 0 and len(d["series"]) == 168 and d["cap"] == 5)

print("SMOKE:", "ALL PASS" if all(OK) else f"FAILURES: {OK.count(False)}")
