"""进程内在途/活跃状态（gunicorn 单 worker + threads 模式）"""
import threading
import time

_lock = threading.Lock()
_inflight = {}        # name -> 在途模型请求数
_last_activity = {}   # name -> 最近活动时间戳


def model_begin(name):
    with _lock:
        _inflight[name] = _inflight.get(name, 0) + 1
        _last_activity[name] = time.time()


def model_end(name):
    with _lock:
        _inflight[name] = max(0, _inflight.get(name, 0) - 1)
        _last_activity[name] = time.time()


def touch(name):
    with _lock:
        _last_activity[name] = time.time()


def is_busy(name, window=90.0):
    """在途请求 >0 或最近 window 秒内有活动视为"在用"""
    with _lock:
        if _inflight.get(name, 0) > 0:
            return True
        ts = _last_activity.get(name, 0)
        return (time.time() - ts) < window


def snapshot():
    with _lock:
        return dict(_inflight), dict(_last_activity)
