"""serializers 模块。

序列化器扩展。
"""

from django.db import models
from rest_framework import serializers


class BigIntAsStringField(serializers.Field):
    """BigInt 字段序列化为字符串，避免前端精度丢失。"""

    def to_representation(self, value):
        if value is None:
            return None
        return str(value)

    def to_internal_value(self, data):
        if data is None:
            return None
        try:
            return int(data)
        except (TypeError, ValueError):
            raise serializers.ValidationError("字段必须为整数或数字字符串")


class StandardModelSerializer(serializers.ModelSerializer):
    """标准模型序列化器。

    自动将 BigInt 类型字段序列化为字符串。
    """

    serializer_field_mapping = serializers.ModelSerializer.serializer_field_mapping.copy()
    serializer_field_mapping.update(
        {
            models.BigIntegerField: BigIntAsStringField,
            models.BigAutoField: BigIntAsStringField,
        }
    )
