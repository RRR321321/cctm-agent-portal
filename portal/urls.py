from django.urls import path

from . import views_admin, views_auth, views_files, views_model, views_shell, views_stats

urlpatterns = [
    # 根路径：已登录 → webshell；未登录 → 遮罩登录页
    path("", views_shell.root, name="root"),
    path("register/", views_auth.register, name="register"),
    path("change-password/", views_auth.change_password, name="change_password"),
    path("logout/", views_auth.do_logout, name="logout"),
    path("model/<name>/v1/<path:subpath>", views_model.model_proxy, name="model_proxy"),
    path("stats/", views_stats.stats, name="stats"),
    path("files/", views_files.page, name="files"),
    path("files/api/list", views_files.list_dir, name="files_list"),
    path("files/api/download", views_files.download, name="files_download"),
    path("files/api/upload", views_files.upload, name="files_upload"),
    path("files/api/delete", views_files.delete, name="files_delete"),
    path("users/", views_admin.users_page, name="users"),
    path("users/api/delete", views_admin.delete_user, name="users_delete"),
    # 兜底：其余路径全部代理到用户实例（/assets、/session、SSE 等）
    path("<path:subpath>", views_shell.shell_proxy, name="shell_sub"),
]
