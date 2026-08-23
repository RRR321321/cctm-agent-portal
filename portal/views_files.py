"""文件管理：浏览/下载/上传/删除。

权限矩阵（2026-08-23 定）：
- 个人工作区（本人）：浏览/下载/上传/删除
- 公共区（所有人含 admin）：浏览/上传/删除，不可下载
- admin（无 profile）：文件页仅公共区

存储模型：工作区目录 2770（组=该用户私有组，borui 在组内），
agent 侧 qws@.service UMask=0002 保证组可读写；上传文件 chmod 664；
公共区 chown borui 由门户代写代删。
"""
import os
import shutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import CctmUser

MAX_UPLOAD_BYTES = 500 * 1024 * 1024


def _profile(request):
    return getattr(request.user, "cctm", None)


def _roots(request):
    profile = _profile(request)
    root = Path(settings.CCTM["FILES_ROOT"])
    roots = {}
    if profile is not None:
        roots["mine"] = root / profile.name
    shared = root / "shared"
    if shared.is_dir():
        roots["shared"] = shared
    return roots


def _resolve(request, area, rel):
    """把 area+rel 解析成绝对路径；越界/非法/无权返回 None。

    用词法规范化（不展开软链）：工作区内 .qwen/skills 是指向共享目录的软链，
    若 resolve() 会"逃出"工作区被误拒；.. 穿越由 normpath 词法拦截。
    """
    root = _roots(request).get(area)
    if root is None:
        return None
    root = root.resolve()
    rel = (rel or "").strip().replace("\\", "/").lstrip("/")
    if "\x00" in rel:
        return None
    clean = os.path.normpath(rel) if rel else "."
    if clean == ".." or clean.startswith("../") or os.path.isabs(clean):
        return None
    return root / clean


@login_required
def page(request):
    profile = _profile(request)
    if profile is None and not request.user.is_staff:
        return redirect("/")
    me = profile.name if profile else request.user.username
    return render(request, "portal/files.html",
                  {"me": me, "has_mine": profile is not None})


@login_required
def list_dir(request):
    path = _resolve(request, request.GET.get("area", "mine"),
                    request.GET.get("path", ""))
    if path is None:
        return JsonResponse({"error": "bad path"}, status=403)
    if not path.is_dir():
        return JsonResponse({"error": "bad path"}, status=400)
    entries = []
    for name in sorted(os.listdir(path), key=str.lower):
        child = path / name
        try:
            st = child.stat()
        except OSError:
            continue
        entries.append({
            "name": name,
            "is_dir": child.is_dir(),
            "size": st.st_size,
            "mtime": int(st.st_mtime),
        })
    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return JsonResponse({"area": request.GET.get("area", "mine"),
                         "path": request.GET.get("path", ""),
                         "entries": entries})


@login_required
def download(request):
    if request.GET.get("area", "mine") == "shared":
        return JsonResponse({"error": "shared is not downloadable"}, status=403)
    path = _resolve(request, "mine", request.GET.get("path", ""))
    if path is None or not path.is_file():
        return JsonResponse({"error": "bad path"}, status=400)
    return FileResponse(open(path, "rb"), as_attachment=True, filename=path.name)


@require_POST
@login_required
def upload(request):
    area = request.POST.get("area", "mine")
    base = _resolve(request, area, request.POST.get("path", ""))
    if base is None or not base.is_dir():
        return JsonResponse({"error": "bad path"}, status=403)

    relpath = (request.POST.get("relpath") or "").strip().replace("\\", "/")
    relpath = relpath.lstrip("/")
    if "\x00" in relpath or relpath.startswith(".."):
        return JsonResponse({"error": "bad relpath"}, status=400)
    f = request.FILES.get("file")
    if f is None:
        return JsonResponse({"error": "no file"}, status=400)
    if f.size > MAX_UPLOAD_BYTES:
        return JsonResponse({"error": "file too large (max 500MB)"}, status=413)

    clean = os.path.normpath(relpath)
    if clean == ".." or clean.startswith("../") or os.path.isabs(clean):
        return JsonResponse({"error": "bad relpath"}, status=400)
    target = base / clean
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "wb") as out:
        for chunk in f.chunks():
            out.write(chunk)
    os.chmod(target, 0o664)  # 让 agent（同组）可读写上传的文件
    return JsonResponse({"ok": True, "name": relpath})


@require_POST
@login_required
def delete(request):
    area = request.POST.get("area", "mine")
    rel = (request.POST.get("path") or "").strip()
    if not rel:
        return JsonResponse({"error": "cannot delete root"}, status=400)
    path = _resolve(request, area, rel)
    if path is None:
        return JsonResponse({"error": "bad path"}, status=403)
    try:
        if os.path.islink(path):
            # 软链只删链本身，绝不顺着 rmtree（防误删共享目录）
            os.unlink(path)
        elif path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()
        else:
            return JsonResponse({"error": "not found"}, status=404)
    except OSError as e:
        return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"ok": True})
