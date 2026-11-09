"""单元测试专用配置。

使用 SQLite 内存库运行测试，避免 MySQL 测试库在建库阶段因
「未迁移应用先建表、引用尚未由迁移创建的表」而失败。
"""
from .dev import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
