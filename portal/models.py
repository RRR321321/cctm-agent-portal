from django.contrib.auth.models import User
from django.db import models


class CctmUser(models.Model):
    """一个同事 = 一个 Django 账号 + 一个 qws-<name> OS 实例"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cctm")
    name = models.CharField(max_length=32, unique=True)      # = 实例名（小写拼音）
    port = models.IntegerField()
    token = models.CharField(max_length=64)                  # daemon bearer（代理时注入）
    model_key = models.CharField(max_length=64)              # 模型代理鉴权键
    avatar_color = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ModelUsage(models.Model):
    """模型代理逐请求记录的 token 用量（统计页数据源）"""
    user = models.ForeignKey(CctmUser, on_delete=models.CASCADE, related_name="usages")
    ts = models.DateTimeField(auto_now_add=True, db_index=True)
    model = models.CharField(max_length=64, default="")
    path = models.CharField(max_length=128, default="")
    prompt_tokens = models.IntegerField(default=0)
    completion_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    cached_tokens = models.IntegerField(default=0)  # 前缀缓存命中 token（usage.prompt_tokens_details.cached_tokens）
    latency_ms = models.IntegerField(default=0)
    ok = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["user", "ts"])]
