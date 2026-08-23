"""登录（遮罩页）/ 注册 / 改密 / 退出"""
import random
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from . import instances
from .models import CctmUser

NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,30}$")


def _parse_kv(text):
    """从 cctm-provision 的 stdout 解析 KEY=VALUE"""
    info = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if line and "=" in line and not line.startswith("OK "):
            k, v = line.split("=", 1)
            info[k.strip()] = v.strip()
    return info or None


def _profile(request):
    if request.user.is_authenticated:
        return getattr(request.user, "cctm", None)
    return None


def gate(request):
    """首页：已登录→进 shell；未登录→遮罩登录页"""
    if _profile(request):
        return redirect("/")
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("/stats/")
    error = None
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip().lower()
        password = request.POST.get("password") or ""
        user = authenticate(request, username=username, password=password)
        if user is not None and (getattr(user, "cctm", None) is not None
                                 or user.is_staff):
            login(request, user)
            return redirect("/")
        error = "用户名或密码错误"
    return render(request, "portal/gate.html", {"error": error})


def register(request):
    if _profile(request):
        return redirect("/shell/")
    error = None
    if request.method == "POST":
        raw = (request.POST.get("username") or "").strip()
        name = raw.lower()
        password = request.POST.get("password") or ""
        confirm = request.POST.get("confirm") or ""
        if " " in raw:
            error = "用户名不能有空格"
        elif not NAME_RE.match(name):
            error = "用户名只能用小写字母、数字、下划线和连字符，且以字母开头"
        elif User.objects.filter(username=name).exists():
            error = "该用户名已被注册"
        elif len(password) < 6:
            error = "密码至少 6 位"
        elif password != confirm:
            error = "两次输入的密码不一致"
        else:
            try:
                ok, msg = instances.provision(name)
            except Exception as e:
                ok, msg = False, str(e)
            if not ok:
                error = f"开通失败：{msg}（请联系管理员）"
            else:
                info = _parse_kv(msg) or instances.registry_info(name)
                if not info or "TOKEN" not in info:
                    error = "开通异常：读不到实例注册表，请联系管理员"
                else:
                    user = User.objects.create_user(username=name, password=password)
                    palette = settings.CCTM["AVATAR_PALETTE"]
                    CctmUser.objects.create(
                        user=user, name=name,
                        port=int(info["PORT"]),
                        token=info["TOKEN"], model_key=info["MODEL_KEY"],
                        avatar_color=random.choice(palette))
                    login(request, user)
                    return redirect("/")
    return render(request, "portal/register.html", {"error": error})


@login_required
def change_password(request):
    if not _profile(request):
        return redirect("/")
    error = done = None
    if request.method == "POST":
        current = request.POST.get("current") or ""
        new = request.POST.get("new") or ""
        confirm = request.POST.get("confirm") or ""
        if not request.user.check_password(current):
            error = "当前密码不正确"
        elif len(new) < 6:
            error = "新密码至少 6 位"
        elif new != confirm:
            error = "两次输入的新密码不一致"
        else:
            request.user.set_password(new)
            request.user.save()
            update_session_auth_hash(request, request.user)
            done = "密码修改成功"
    return render(request, "portal/change_password.html",
                  {"error": error, "done": done})


def do_logout(request):
    logout(request)
    return redirect("/")
