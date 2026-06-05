"""系统管理-apps.py应用配置。

"""

from django.apps import AppConfig


class SystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.system'
    label = 'system'

    def ready(self):
        from . import signals  # noqa: F401
