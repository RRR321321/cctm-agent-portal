from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _read_secret(path, default=""):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return default


SECRET_KEY = _read_secret(BASE_DIR / ".secret_key", "cctm-insecure-dev-key")
DEBUG = False
# IT 有公网转发，域名不固定，放开 Host 校验（DEBUG=False，CSRF 仍生效）
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "portal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "portal_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "portal_project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "err.log",
        },
    },
    "loggers": {
        "django.request": {"handlers": ["file"], "level": "ERROR"},
        "cctm": {"handlers": ["file"], "level": "INFO"},
    },
}

LOGIN_URL = "/"
SESSION_COOKIE_AGE = 12 * 3600
SESSION_SAVE_EVERY_REQUEST = True

# ---- CCTM 平台参数 ----
CCTM = {
    # cctm-provision 写入的实例注册表（root:cctm 640，borui 经 cctm 组可读）
    "REGISTRY_DIR": "/etc/cctm/registry",
    # DGX SSH 隧道入口（127.0.0.1:8080 -> 192.168.2.219 gate）
    "TUNNEL_UPSTREAM": "http://127.0.0.1:8080",
    # DGX gate/llama-server 的 API key（600 文件）
    "DGX_KEY_FILE": str(BASE_DIR / ".dgx_key"),
    # 同时运行的实例上限（15GB 内存保护），满了先回收最闲的
    "MAX_RUNNING_INSTANCES": 10,
    # 空闲回收秒数
    "IDLE_REAP_SECONDS": 20 * 60,
    # 模型端并发上限（DGX gate MAX_CONCURRENT，展示用）
    "MODEL_CONCURRENCY_CAP": 5,
    "PORTAL_ORIGIN": "http://192.168.2.88:8081",
    # 用户文件根目录（/files/ 文件管理页的数据源；shared 为公共只读区）
    "FILES_ROOT": "/srv/cctm_agent_files",
    "AVATAR_PALETTE": [
        "#2563eb", "#16a34a", "#dc2626", "#d97706", "#7c3aed",
        "#0891b2", "#db2777", "#65a30d", "#ea580c", "#0d9488",
        "#9333ea", "#4f46e5",
    ],
}
