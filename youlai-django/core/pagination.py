"""pagination 模块。

统一分页响应结构。
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    """统一分页响应。

    将 DRF PageNumberPagination 的分页结果封装为项目统一响应结构：
    `{code, msg, data: {list, total}}`
    """

    page_size_query_param = "pageSize"
    page_query_param = "pageNum"
    max_page_size = 200

    def get_paginated_response(self, data):
        """返回统一分页响应结构。"""
        return Response(
            {
                "code": "00000",
                "msg": "成功",
                "data": {
                    "list": data,
                    "total": self.page.paginator.count,
                },
            }
        )
