"""平台-代码生成常量。

"""

from __future__ import annotations

from dataclasses import dataclass


CODE_OK = "00000"
MSG_OK = "成功"

CODEGEN_DOWNLOAD_FILE_NAME = "youlai-admin-code.zip"
CODEGEN_BACKEND_APP_NAME = "youlai-django"
CODEGEN_DJANGO_BACKEND_APP_NAME = "youlai-django"
CODEGEN_FRONTEND_APP_NAME = "vue3-element-admin"
DEFAULT_AUTHOR = "youlaitech"
DEFAULT_MODULE_NAME = "system"
DEFAULT_PACKAGE_NAME = ""
DEFAULT_REMOVE_TABLE_PREFIX = "sys_"


@dataclass(frozen=True)
class TemplateConfig:
    template_path: str
    subpackage_name: str
    extension: str


TEMPLATE_CONFIGS: dict[str, TemplateConfig] = {
    "API": TemplateConfig("frontend/api.ts.vm", "api", ".ts"),
    "API_TYPES": TemplateConfig("frontend/api-types.ts.vm", "types", ".ts"),
    "VIEW": TemplateConfig("frontend/index.vue.vm", "views", ".vue"),
    "DjangoModels": TemplateConfig("backend/models.py.vm", "", ".py"),
    "DjangoSerializers": TemplateConfig("backend/serializers.py.vm", "", ".py"),
    "DjangoViews": TemplateConfig("backend/views.py.vm", "", ".py"),
    "DjangoUrls": TemplateConfig("backend/urls.py.vm", "", ".py"),
}


DJANGO_TEMPLATE_CONFIGS: dict[str, TemplateConfig] = TEMPLATE_CONFIGS
