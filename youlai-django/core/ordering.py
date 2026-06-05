"""ordering 模块。

排序工具。
"""

from typing import Dict


class SafeOrdering:
    """安全排序工具。

    通过"字段白名单"方式安全地应用排序，避免前端传入任意字段导致的 SQL 注入/异常。
    """

    @staticmethod
    def apply(queryset, field: str, direction: str, allowed_fields: Dict[str, str]):
        """按白名单对 queryset 应用 `order_by`。

        Args:
            queryset: Django QuerySet
            field: 前端传入的排序字段 key（例如 `createTime`）
            direction: 排序方向 "ASC" 或 "DESC"
            allowed_fields: key 到真实模型字段名的映射

        Returns:
            排序后的 QuerySet
        """
        field_key = (field or "id").strip()
        model_field = allowed_fields.get(field_key)
        if model_field is None:
            model_field = allowed_fields.get("id", "id")
        dir_upper = (direction or "DESC").upper()
        ordering = model_field if dir_upper == "ASC" else f"-{model_field}"
        return queryset.order_by(ordering)
