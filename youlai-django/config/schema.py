"""schema 模块。

Author: Ray.Hao
Version: 0.0.1
"""

SPECTACULAR_SETTINGS = {
    "TITLE": "youlai-django",
    "DESCRIPTION": "youlai 全家桶（Python/Django）权限管理后台接口文档",
    "VERSION": "1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api",
    "SWAGGER_UI_SETTINGS": {
        "tagsSorter": "alpha",
    },
    "TAGS": [
        {"name": "01.认证接口"},
        {"name": "02.用户接口"},
        {"name": "03.角色接口"},
        {"name": "04.菜单接口"},
        {"name": "05.部门接口"},
        {"name": "06.字典接口"},
        {"name": "07.系统配置"},
        {"name": "08.通知公告"},
        {"name": "09.日志接口"},
        {"name": "10.文件接口"},
        {"name": "11.代码生成"},
        {"name": "12.统计分析"},
    ],
}
