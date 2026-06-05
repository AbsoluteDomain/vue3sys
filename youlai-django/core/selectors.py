"""selectors 模块。

选择器基类。
"""

from django.db.models import QuerySet


class BaseSelector:
    """选择器基类。

    用于封装复杂的查询逻辑。
    """

    @staticmethod
    def apply_filters(qs: QuerySet, filters):
        """应用过滤条件。

        Args:
            qs: QuerySet
            filters: 过滤条件

        Returns:
            过滤后的 QuerySet
        """
        return qs
