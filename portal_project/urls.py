from django.contrib import admin
from django.urls import include, path
from django.views.static import serve as static_serve

from portal_project import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    # 内网部署直接由 Django 发静态文件（必须在门户兜底代理路由之前）
    path("static/<path:path>", static_serve, {"document_root": settings.BASE_DIR / "static"}),
    path("", include("portal.urls")),
]
