#!/usr/bin/env python3
"""全面测试 A：UI 真实对话 / 斜杠命令禁用 / skill 共享 / 会话隔离"""
import subprocess
import time
from playwright.sync_api import sync_playwright

BASE = "http://192.168.2.88:8081"

def login(pg, name, pw):
    pg.goto(BASE + "/", wait_until="domcontentloaded")
    pg.fill("input[name=username]", name)
    pg.fill("input[name=password]", pw)
    pg.click("button[type=submit]")
    pg.wait_for_selector("#cctm-nav", timeout=60000)
    pg.wait_for_timeout(2500)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)

    # ---- cctest1：真实对话 ----
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    login(pg, "cctest1", "test12345")
    composer = pg.locator(".cm-content").first
    composer.click()
    pg.keyboard.insert_text("请只回复四个字：测试成功")
    pg.keyboard.press("Enter")
    try:
        pg.wait_for_selector("text=测试成功", timeout=180000)
        print("[A1] UI 真实对话: 收到回复 ✔")
    except Exception:
        print("[A1] UI 真实对话: 超时未收到回复 ✘")
        pg.screenshot(path="/tmp/cctm_shots/09_chat.png")

    # ---- 斜杠命令：/model /auth 应不可用 ----
    composer = pg.locator(".cm-content").first
    composer.click()
    pg.keyboard.insert_text("/")
    pg.wait_for_timeout(1500)
    menu_text = pg.evaluate("() => document.body.innerText")
    has_model = "/model" in menu_text or "model" in [l.strip() for l in menu_text.splitlines()]
    # 更精确：弹出菜单里找 model/auth 条目
    slash_items = pg.evaluate("""() => {
        const out = [];
        document.querySelectorAll('[role=option],[role=menuitem],li,button').forEach(el => {
            const t = (el.textContent||'').trim();
            if (/^\\/?model$/i.test(t) || /^\\/?auth$/i.test(t)) out.push(t);
        });
        return out;
    }""")
    print(f"[A2] 斜杠菜单中 model/auth 条目: {slash_items} (空=已禁用 ✔)")
    pg.keyboard.press("Escape")
    pg.screenshot(path="/tmp/cctm_shots/09_chat.png")

    # ---- cctest1 会话列表现在有 1 个会话 ----
    pg.wait_for_timeout(2000)
    side1 = pg.evaluate("() => document.body.innerText")
    pg.close()

    # ---- cctest2：看不到 cctest1 的会话 ----
    pg2 = b.new_page(viewport={"width": 1440, "height": 900})
    login(pg2, "cctest2", "newpass123")
    side2 = pg2.evaluate("() => document.body.innerText")
    # cctest1 的会话标题是用户发的第一句话的摘要；直接检查 cctest2 侧栏不含 cctest1 的会话
    # 用 API 更准：fetch 会话列表
    sess2 = pg2.evaluate("""async () => {
        const r = await fetch('/workspaces/' + encodeURIComponent('/srv/cctm_agent_files/cctest2') + '/sessions');
        return await r.json();
    }""")
    sess1_titles = "测试成功"
    leak = sess1_titles in str(sess2)
    print(f"[A3] cctest2 会话数: {len(sess2.get('sessions', []))}, 泄漏 cctest1 会话: {leak} (False=✔)")
    pg2.close()
    b.close()

# ---- skill 共享：borui 写一个共享 skill，cctest2 应能看到 ----
subprocess.run(["bash", "-c", """
mkdir -p /home/borui/tmpskill/dmp-writer 2>/dev/null
cat > /tmp/dmp-writer-skill.md <<'MD'
---
name: dmp-writer
description: 测试用共享 skill（数据管理计划模板）
---
# DMP Writer (shared test)
MD
"""], check=True)
# 通过 ssh 放到共享目录（borui 在 cctm 组，可写）
subprocess.run(["ssh", "-o", "BatchMode=yes", "borui@192.168.2.88",
                "mkdir -p /srv/cctm_shared/skills/dmp-writer && cat /tmp/dmp-writer-skill.md > /srv/cctm_shared/skills/dmp-writer/SKILL.md 2>/dev/null || true"], check=False)
# 直接本地写（远程）
subprocess.run(["ssh", "-o", "BatchMode=yes", "borui@192.168.2.88",
                "mkdir -p /srv/cctm_shared/skills/dmp-writer && printf -- '---\\nname: dmp-writer\\ndescription: 测试用共享 skill\\n---\\n# DMP Writer shared test\\n' > /srv/cctm_shared/skills/dmp-writer/SKILL.md && ls /srv/cctm_shared/skills/"], check=True)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    login(pg, "cctest2", "newpass123")
    skills = pg.evaluate("""async () => {
        const r = await fetch('/workspace/skills');
        return await r.json();
    }""")
    names = [s.get("name") for s in (skills if isinstance(skills, list) else skills.get("skills", []))]
    print(f"[A4] cctest2 可见 skills: {names} (含 dmp-writer=✔)")
    b.close()
print("BATCH_A_DONE")
