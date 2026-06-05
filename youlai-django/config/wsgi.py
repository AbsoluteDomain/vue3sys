"""Django WSGI 应用入口。

"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from django.core.wsgi import get_wsgi_application


def _assert_supported_python():
    version = sys.version_info[:2]
    if version < (3, 10) or version >= (3, 15):
        raise RuntimeError(
            f"当前 Python 版本为 {sys.version.split()[0]}，本项目仅支持 Python 3.10-3.14。"
        )


_assert_supported_python()

env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

application = get_wsgi_application()
