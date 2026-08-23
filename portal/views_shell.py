"""Shell 反向代理：/shell/* -> 用户实例 127.0.0.1:<port>/*，HTML 注入导航条等"""
import logging

import requests as upstream
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from . import instances, state

log = logging.getLogger("cctm.shell")

_HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
                "te", "trailers", "transfer-encoding", "upgrade", "host",
                "accept-encoding", "content-length", "content-encoding"}


def _inject_snippet(html, profile):
    staff = "1" if profile.user.is_staff else "0"
    snippet = (
        f'<script>window.CCTM_USER="{profile.name}";'
        f'window.CCTM_COLOR="{profile.avatar_color}";'
        f'window.CCTM_STAFF="{staff}";</script>'
        '<link rel="stylesheet" href="/static/portal/inject.css">'
        '<script src="/static/portal/inject.js" defer></script>'
    )
    lower = html.lower()
    idx = lower.find("</head>")
    if idx >= 0:
        return html[:idx] + snippet + html[idx:]
    return snippet + html


def _forward_headers(request):
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in _HOP_HEADERS and k.lower() != "authorization"}
    headers["Accept-Encoding"] = "identity"  # 要求明文，便于注入
    return headers


def _touch(profile):
    state.touch(profile.name)
    last = profile.last_active_at
    if last is None or (timezone.now() - last).total_seconds() > 60:
        profile.last_active_at = timezone.now()
        profile.save(update_fields=["last_active_at"])


@csrf_exempt
def shell_proxy(request, subpath=""):
    profile = getattr(request.user, "cctm", None) if request.user.is_authenticated else None
    if profile is None:
        return redirect_to_gate()
    if not instances.ensure_running(profile):
        return render(request, "portal/shell_error.html",
                      {"name": profile.name}, status=503)

    # Django 路由会把 %2F 解码成 /（path_info 已解码），直接拼 subpath 会破坏
    # SPA 的编码路径参数（/workspace/%2Fsrv%2F...）。用 gunicorn 的 RAW_URI 原始请求行。
    raw = request.META.get("RAW_URI", "")
    raw_path = raw.split("?", 1)[0] if raw else ""
    if raw_path:
        url = f"http://127.0.0.1:{profile.port}{raw_path}"
    else:
        url = f"http://127.0.0.1:{profile.port}/{subpath}"
    if request.META.get("QUERY_STRING"):
        url += "?" + request.META["QUERY_STRING"]
    headers = _forward_headers(request)
    headers["Authorization"] = f"Bearer {profile.token}"
    body = request.body if request.method in ("POST", "PUT", "PATCH", "DELETE") else None

    try:
        up = upstream.request(request.method, url, headers=headers, data=body,
                              stream=True, timeout=(10, 1800), allow_redirects=False)
    except upstream.RequestException as e:
        log.error("upstream error for %s/%s: %s", profile.name, subpath, e)
        return render(request, "portal/shell_error.html",
                      {"name": profile.name}, status=502)

    _touch(profile)
    ctype = up.headers.get("Content-Type", "")

    if "text/html" in ctype:
        html = _inject_snippet(up.content.decode("utf-8", "replace"), profile)
        resp = HttpResponse(html, status=up.status_code, content_type=ctype or "text/html")
    elif "text/event-stream" in ctype or up.headers.get("Transfer-Encoding") == "chunked":
        resp = StreamingHttpResponse(up.iter_content(chunk_size=4096),
                                     status=up.status_code, content_type=ctype)
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"
    else:
        resp = HttpResponse(up.content, status=up.status_code,
                            content_type=ctype or "application/octet-stream")

    for k, v in up.headers.items():
        if k.lower() in _HOP_HEADERS:
            continue
        resp[k] = v
    if "text/html" in ctype:
        resp["Content-Length"] = str(len(resp.content))
    return resp


def redirect_to_gate():
    from django.shortcuts import redirect
    return redirect("/")


def root(request):
    """根路径分发：已登录且有实例 → webshell；staff → 统计页；否则登录遮罩页"""
    from django.shortcuts import redirect
    from .views_auth import gate
    if request.user.is_authenticated:
        if getattr(request.user, "cctm", None) is not None:
            return shell_proxy(request, subpath="")
        if request.user.is_staff:
            return redirect("/stats/")
    return gate(request)
