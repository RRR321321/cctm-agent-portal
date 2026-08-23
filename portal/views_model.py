"""模型代理：/model/<用户>/v1/* -> DGX 隧道，逐请求记录 token 用量"""
import json
import logging
import time
from hmac import compare_digest
from pathlib import Path

import requests as upstream
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from . import state
from .models import CctmUser, ModelUsage

log = logging.getLogger("cctm.model")

_dgx_key_cache = None


def _dgx_key():
    global _dgx_key_cache
    if _dgx_key_cache is None:
        try:
            _dgx_key_cache = Path(settings.CCTM["DGX_KEY_FILE"]).read_text().strip()
        except OSError:
            _dgx_key_cache = ""
    return _dgx_key_cache


def _cached(usage):
    if not usage:
        return 0
    det = usage.get("prompt_tokens_details") or {}
    return int(det.get("cached_tokens", 0) or 0)


def _record(profile, model, path, usage, latency_ms, ok):
    try:
        ModelUsage.objects.create(
            user=profile, model=model or "", path=path[:128],
            prompt_tokens=int(usage.get("prompt_tokens", 0)) if usage else 0,
            completion_tokens=int(usage.get("completion_tokens", 0)) if usage else 0,
            total_tokens=int(usage.get("total_tokens", 0)) if usage else 0,
            cached_tokens=_cached(usage),
            latency_ms=int(latency_ms), ok=ok)
    except Exception as e:
        log.warning("usage record failed: %s", e)


@csrf_exempt
def model_proxy(request, name, subpath):
    profile = CctmUser.objects.filter(name=name).first()
    if profile is None:
        return JsonResponse({"error": {"message": "unknown user"}}, status=404)

    auth = request.headers.get("Authorization", "")
    if not compare_digest(auth, f"Bearer {profile.model_key}"):
        return JsonResponse({"error": {"message": "invalid api key"}}, status=401)

    target = f"{settings.CCTM['TUNNEL_UPSTREAM']}/v1/{subpath}"
    if request.META.get("QUERY_STRING"):
        target += "?" + request.META["QUERY_STRING"]

    headers = {"Authorization": f"Bearer {_dgx_key()}"}
    ctype = request.headers.get("Content-Type")
    if ctype:
        headers["Content-Type"] = ctype

    body = request.body
    model_name = ""
    is_stream = False
    if request.method == "POST" and body:
        try:
            payload = json.loads(body)
            if isinstance(payload, dict):
                model_name = str(payload.get("model", ""))
                is_stream = bool(payload.get("stream"))
                if is_stream:
                    payload.setdefault("stream_options", {})["include_usage"] = True
                    body = json.dumps(payload).encode()
        except (ValueError, TypeError):
            pass

    if request.method != "POST":
        # /models 等查询类直通，不记账
        try:
            up = upstream.request(request.method, target, headers=headers,
                                  timeout=(10, 60))
        except upstream.RequestException as e:
            return _bad_gateway(e)
        return HttpResponse(up.content, status=up.status_code,
                            content_type=up.headers.get("Content-Type", "application/json"))

    state.model_begin(name)
    t0 = time.time()
    try:
        try:
            up = upstream.post(target, headers=headers, data=body,
                               stream=is_stream, timeout=(10, 1800))
        except upstream.RequestException as e:
            _record(profile, model_name, subpath, None, (time.time() - t0) * 1000, False)
            return _bad_gateway(e)

        if not is_stream:
            data = up.content
            usage = None
            try:
                obj = json.loads(data)
                if isinstance(obj, dict):
                    usage = obj.get("usage")
            except (ValueError, TypeError):
                pass
            _record(profile, model_name, subpath, usage, (time.time() - t0) * 1000,
                    up.status_code < 400)
            return HttpResponse(data, status=up.status_code,
                                content_type=up.headers.get("Content-Type", "application/json"))
        return _stream_response(up, profile, model_name, subpath, t0, up.status_code)
    finally:
        state.model_end(name)


def _stream_response(up, profile, model_name, subpath, t0, status):
    usage_holder = {"usage": None}
    ok = status < 400

    def gen():
        buf = ""
        try:
            for chunk in up.iter_content(chunk_size=None):
                if not chunk:
                    continue
                buf += chunk.decode("utf-8", "replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line.startswith("data:") and line[5:].strip() != "[DONE]":
                        try:
                            obj = json.loads(line[5:])
                            if isinstance(obj, dict) and obj.get("usage"):
                                usage_holder["usage"] = obj["usage"]
                        except (ValueError, TypeError):
                            pass
                yield chunk
        finally:
            _record(profile, model_name, subpath, usage_holder["usage"],
                    (time.time() - t0) * 1000, ok)

    resp = StreamingHttpResponse(gen(), status=up.status_code,
                                 content_type=up.headers.get("Content-Type", "text/event-stream"))
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp


def _bad_gateway(e):
    log.error("model upstream error: %s", e)
    return JsonResponse(
        {"error": {"message": "模型服务暂不可用（到 DGX 的链路异常），请稍后重试或联系管理员",
                   "type": "upstream_error"}},
        status=502)
