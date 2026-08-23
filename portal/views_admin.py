"""用户管理（仅 staff）：用户列表 + 删除用户（账号+工作区+全部文件+配置）。"""
import logging
import subprocess

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import state
from .models import CctmUser, ModelUsage

log = logging.getLogger("cctm.admin")


def _staff(view):
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            return redirect("/")
        return view(request, *args, **kwargs)
    return wrapped


@login_required
@_staff
def users_page(request):
    rows = []
    for p in CctmUser.objects.all():
        total = (ModelUsage.objects.filter(user=p)
                 .aggregate(s=Sum("total_tokens"))["s"] or 0)
        rows.append({
            "name": p.name,
            "color": p.avatar_color,
            "created": p.created_at.strftime("%Y-%m-%d %H:%M"),
            "last_active": p.last_active_at.strftime("%m-%d %H:%M") if p.last_active_at else "—",
            "total": int(total),
            "busy": state.is_busy(p.name),
        })
    return render(request, "portal/users.html", {"me": request.user.username,
                                                 "rows": rows})


@require_POST
@login_required
@_staff
def delete_user(request):
    name = (request.POST.get("name") or "").strip()
    profile = CctmUser.objects.filter(name=name).first()
    if profile is None:
        return JsonResponse({"error": "用户不存在"}, status=404)
    if profile.user.is_staff or profile.user == request.user:
        return JsonResponse({"error": "不能删除管理员账号"}, status=403)

    r = subprocess.run(["sudo", "-n", "/usr/local/sbin/cctm-deprovision", name],
                       capture_output=True, text=True, timeout=120)
    if r.returncode not in (0, 3):
        log.error("deprovision %s failed: %s %s", name, r.stdout, r.stderr)
        return JsonResponse({"error": "系统侧删除失败：" + (r.stdout + r.stderr).strip()[:200]},
                            status=500)
    profile.user.delete()  # 级联 CctmUser + ModelUsage
    return JsonResponse({"ok": True, "name": name})
