#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Django's command-line utility for administrative tasks.

"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def _assert_supported_python():
    version = sys.version_info[:2]
    if version < (3, 10) or version >= (3, 15):
        raise RuntimeError(
            f"当前 Python 版本为 {sys.version.split()[0]}，本项目仅支持 Python 3.10-3.14。\n"
            "原因：Python 3.15 及以上在 Windows 上部分依赖可能缺少预编译 wheel，"
            "安装时会提示不支持或要求从源码编译。"
        )


def main():
    """Run administrative tasks."""
    # Load local .env for development (if present)
    env_path = Path(__file__).resolve().parent / '.env'
    settings_module = os.getenv('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
    if settings_module == 'config.settings.dev' and env_path.exists():
        load_dotenv(env_path)

    try:
        _assert_supported_python()
    except RuntimeError as exc:
        sys.stderr.write(str(exc) + "\n")
        sys.exit(1)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "无法导入 Django。请确认已安装 Django，并且在 PYTHONPATH 环境变量中可用；"
            "如果使用虚拟环境，请确认已激活。"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
