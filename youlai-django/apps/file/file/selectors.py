"""平台-文件查询。

"""

from __future__ import annotations

import re

from django.conf import settings


def extract_file_path(path_or_url: str) -> str | None:
    if not path_or_url:
        return None

    if path_or_url.startswith(('http://', 'https://')):
        bucket_name = settings.MINIO_BUCKET_NAME
        pattern = f"(?:https?://[^/]+/{bucket_name}/)(.+)"
        match = re.search(pattern, path_or_url)
        if match:
            return match.group(1)
        return None

    return path_or_url
