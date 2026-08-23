#!/usr/bin/env python3
"""B3b：确定性 LRU 顶替（1&2 空闲 95s 后访问 3）"""
import subprocess
import time
import requests

BASE = "http://192.168.2.88:8081"

def login(name, pw):
    s = requests.Session()
    s.get(BASE + "/")
    tok = s.cookies.get("csrftoken")
    s.post(BASE + "/", data={"username": name, "password": pw,
                             "csrfmiddlewaretoken": tok},
           headers={"Referer": BASE + "/"})
    return s

def running():
    return {n: subprocess.run(["sudo", "-n", "systemctl", "is-active", "qws@" + n],
                              capture_output=True, text=True).stdout.strip()
            for n in ["cctest1", "cctest2", "cctest3"]}

s1 = login("cctest1", "test12345")
s1.get(BASE + "/", timeout=120)
s2 = login("cctest2", "newpass123")
s2.get(BASE + "/", timeout=120)
print("t0:", running())
print("等 95s 让 1&2 脱离在用窗口...")
time.sleep(95)
s3 = login("cctest3", "test12345")
s3.get(BASE + "/", timeout=120)
time.sleep(3)
r = running()
active = [k for k, v in r.items() if v == "active"]
print("访问3后:", r)
print("LRU 结果:", "✔ cctest1 被顶替" if r["cctest1"] != "active" and len(active) == 2 else "✘ 未顶替")
print("B3B_DONE")
