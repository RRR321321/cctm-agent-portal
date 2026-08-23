"""qws@ 实例的生命周期管理：拉起 / 停止 / 空闲回收 / 并发上限顶替"""
import logging
import subprocess
import threading
import time

import requests
from django.conf import settings

from . import state

log = logging.getLogger("cctm.instances")

_UNIT_PREFIX = "qws@"
_start_lock = threading.Lock()
_reaper_started = False


def _sudo(*args, timeout=60):
    return subprocess.run(["sudo", "-n", *args], capture_output=True,
                          text=True, timeout=timeout)


def unit_name(name):
    return f"{_UNIT_PREFIX}{name}"


def is_running(name):
    r = _sudo("systemctl", "is-active", unit_name(name), timeout=10)
    return r.returncode == 0 and r.stdout.strip() == "active"


def _health_ok(port, token):
    try:
        r = requests.get(f"http://127.0.0.1:{port}/health",
                         headers={"Authorization": f"Bearer {token}"}, timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False


def wait_ready(profile, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if _health_ok(profile.port, profile.token):
            return True
        time.sleep(0.5)
    return False


def _running_profiles():
    from .models import CctmUser
    return [p for p in CctmUser.objects.all() if is_running(p.name)]


def _stop(profile):
    log.info("stopping instance %s (idle reclaim)", profile.name)
    _sudo("systemctl", "stop", unit_name(profile.name), timeout=90)


def ensure_running(profile):
    """保证实例在跑；返回是否就绪。含并发上限的 LRU 顶替。"""
    with _start_lock:
        if is_running(profile.name):
            if wait_ready(profile, timeout=10):
                return True
        # 顶替：运行数到达上限时先停最闲的（跳过在用的）
        cap = settings.CCTM["MAX_RUNNING_INSTANCES"]
        running = _running_profiles()
        while len(running) >= cap:
            idle_candidates = sorted(
                (p for p in running if p.name != profile.name
                 and not state.is_busy(p.name)),
                key=lambda p: p.last_active_at or p.created_at)
            if not idle_candidates:
                break  # 全忙，宁可超配也不拒绝
            _stop(idle_candidates[0])
            running = _running_profiles()
        log.info("starting instance %s", profile.name)
        r = _sudo("systemctl", "start", unit_name(profile.name), timeout=120)
        if r.returncode != 0:
            log.error("start failed for %s: %s", profile.name, r.stderr.strip())
            return False
        return wait_ready(profile)


def stop_instance(name):
    _sudo("systemctl", "stop", unit_name(name), timeout=90)


def provision(name):
    """调用 cctm-provision（sudoers NOPASSWD）。返回 (ok, message)"""
    r = _sudo("/usr/local/sbin/cctm-provision", name, timeout=120)
    out = (r.stdout or "").strip()
    if r.returncode == 0 and out.startswith("OK"):
        return True, out
    return False, out or (r.stderr or "").strip() or f"rc={r.returncode}"


def registry_info(name):
    """读 /etc/cctm/registry/<name>.conf（KEY=VALUE）"""
    import os
    path = os.path.join(settings.CCTM["REGISTRY_DIR"], f"{name}.conf")
    info = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    info[k.strip()] = v.strip()
    except OSError:
        return None
    return info or None


def _reap_loop():
    idle_s = settings.CCTM["IDLE_REAP_SECONDS"]
    while True:
        time.sleep(60)
        try:
            from .models import CctmUser
            now = time.time()
            for p in CctmUser.objects.all():
                if not is_running(p.name):
                    continue
                if state.is_busy(p.name):
                    continue
                last = p.last_active_at.timestamp() if p.last_active_at else 0
                if last and now - last > idle_s:
                    _stop(p)
        except Exception as e:  # 回收线程不能死
            log.warning("reaper error: %s", e)


def start_reaper():
    global _reaper_started
    if _reaper_started:
        return
    _reaper_started = True
    t = threading.Thread(target=_reap_loop, daemon=True, name="cctm-reaper")
    t.start()
