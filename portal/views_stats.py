"""统计页：7 天排名 / 当前在用 / 小时级曲线 / 累计总量"""
import json
from datetime import timedelta

from django.conf import settings
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from . import state
from .models import CctmUser, ModelUsage


def _ranking(since):
    rows = (ModelUsage.objects.filter(ts__gte=since)
            .values("user__name", "user__avatar_color")
            .annotate(total=Sum("total_tokens"))
            .order_by("-total"))
    out = []
    medals = ["🥇", "🥈", "🥉"]
    for i, r in enumerate(rows):
        out.append({
            "name": r["user__name"],
            "color": r["user__avatar_color"],
            "total": int(r["total"] or 0),
            "medal": medals[i] if i < 3 else "",
        })
    return out


def stats(request):
    profile = getattr(request.user, "cctm", None) if request.user.is_authenticated else None
    if profile is None and not request.user.is_staff:
        from django.shortcuts import redirect
        return redirect("/")

    now = timezone.now()
    since = now - timedelta(days=7)
    cap = settings.CCTM["MODEL_CONCURRENCY_CAP"]

    totals = ModelUsage.objects.aggregate(
        s=Sum("total_tokens"), p=Sum("prompt_tokens"), c=Sum("completion_tokens"),
        h=Sum("cached_tokens"))
    total_all_time = totals["s"] or 0
    total_in = totals["p"] or 0
    total_out = totals["c"] or 0
    total_cached = totals["h"] or 0
    hit_pct = round(100.0 * total_cached / total_in, 1) if total_in else 0.0
    ranking = _ranking(since)

    active = [p for p in CctmUser.objects.all() if state.is_busy(p.name)]
    active_list = [{"name": p.name, "color": p.avatar_color} for p in active]

    # 小时级序列（最近 7 天，168 个点）
    hour_start = (now - timedelta(hours=167)).replace(minute=0, second=0, microsecond=0)
    buckets = {}
    rows = (ModelUsage.objects.filter(ts__gte=hour_start)
            .values("ts").annotate(s=Sum("total_tokens")))
    # 按小时聚合
    hourly = {}
    for r in ModelUsage.objects.filter(ts__gte=hour_start).only("ts", "total_tokens"):
        h = r.ts.replace(minute=0, second=0, microsecond=0)
        hourly[h] = hourly.get(h, 0) + r.total_tokens
    series = []
    cur = hour_start
    while cur <= now:
        series.append({"t": cur.strftime("%m-%d %H:%M"), "n": hourly.get(cur, 0)})
        cur += timedelta(hours=1)

    data = {
        "total_all_time": int(total_all_time),
        "total_in": int(total_in),
        "total_out": int(total_out),
        "hit_pct": hit_pct,
        "ranking": ranking,
        "active_count": len(active_list),
        "active_users": active_list,
        "cap": cap,
        "series": series,
    }
    if request.GET.get("format") == "json":
        return JsonResponse(data)
    return render(request, "portal/stats.html",
                  {"data": data,
                   "me": profile.name if profile else request.user.username})
