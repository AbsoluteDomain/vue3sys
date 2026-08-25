"""pagination 模块。

统一分页响应结构。
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

# 分页每页条数的全局上限，防止单次查询加载过多数据导致接口卡顿
MAX_PAGE_SIZE = 100


def parse_page_params(request, default_size: int = 10, max_size: int = MAX_PAGE_SIZE):
    """解析普通 Django 视图中的分页参数。

    从 request.GET 读取 pageNum / pageSize，统一做下限保护与上限封顶，
    避免前端传入过大的 pageSize 导致单次查询数据量过大、接口卡死。

    Args:
        request: Django HTTP 请求对象。
        default_size: pageSize 缺省值（解析失败或未传时使用）。
        max_size: pageSize 允许的最大值，默认 MAX_PAGE_SIZE。

    Returns:
        (page_num, page_size)
    """
    try:
        page_num = int(request.GET.get("pageNum", 1))
    except (TypeError, ValueError):
        page_num = 1
    try:
        page_size = int(request.GET.get("pageSize", default_size))
    except (TypeError, ValueError):
        page_size = default_size
    page_num = max(page_num, 1)
    page_size = max(min(page_size, max_size), 1)
    return page_num, page_size


class StandardResultsPagination(PageNumberPagination):
    """统一分页响应。

    将 DRF PageNumberPagination 的分页结果封装为项目统一响应结构：
    `{code, msg, data: {list, total}}`
    """

    page_size_query_param = "pageSize"
    page_query_param = "pageNum"
    max_page_size = MAX_PAGE_SIZE

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
