from django.contrib import admin

from .models import CctmUser, ModelUsage


@admin.register(CctmUser)
class CctmUserAdmin(admin.ModelAdmin):
    list_display = ("name", "port", "created_at", "last_active_at")
    exclude = ("token", "model_key")


@admin.register(ModelUsage)
class ModelUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "ts", "model", "total_tokens", "ok")
    list_filter = ("user", "ok")
    date_hierarchy = "ts"
