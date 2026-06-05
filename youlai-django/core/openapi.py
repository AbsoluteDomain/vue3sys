"""openapi 模块。

提供 OpenAPI/Swagger 文档响应结构的辅助函数。
"""

from drf_spectacular.utils import inline_serializer
from rest_framework import serializers


def resp(name: str, data_serializer):
    """OpenAPI 标准响应结构：{code,msg,data}。

    Args:
        name: 序列化器名称
        data_serializer: 数据字段的序列化器

    Returns:
        inline_serializer 生成的响应序列化器
    """
    return inline_serializer(
        name=name,
        fields={
            "code": serializers.CharField(),
            "msg": serializers.CharField(),
            "data": data_serializer,
        },
    )


def page_resp(name: str, item_serializer):
    """OpenAPI 分页响应结构：{code,msg,data:{list,total}}。

    Args:
        name: 序列化器名称
        item_serializer: 列表项的序列化器

    Returns:
        inline_serializer 生成的分页响应序列化器
    """
    return inline_serializer(
        name=name,
        fields={
            "code": serializers.CharField(),
            "msg": serializers.CharField(),
            "data": inline_serializer(
                name=f"{name}Data",
                fields={
                    "list": item_serializer,
                    "total": serializers.IntegerField(),
                },
            ),
        },
    )


__all__ = [
    "resp",
    "page_resp",
]
