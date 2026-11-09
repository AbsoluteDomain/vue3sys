"""系统管理-审批配置应用。

"""
from django.apps import AppConfig


class ApprovalAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.system.approval"
    verbose_name = "审批配置"
