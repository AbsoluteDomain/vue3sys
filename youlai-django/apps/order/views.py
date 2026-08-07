"""订单管理-视图函数。

提供订单列表查询接口，支持分页、关键字搜索和日期范围筛选。
同时提供外部订单系统接口代理，避免前端跨域问题。
"""

from datetime import datetime

import requests as http_requests
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.datetime import format_local_datetime, local_day_range_datetimes

from .models import OrderList

# 外部订单系统接口基地址（可通过环境变量覆盖）
EXTERNAL_ORDER_API_BASE = "http://172.20.45.143:35203"
# 外部接口请求超时时间（秒）
EXTERNAL_ORDER_TIMEOUT = 60


def _parse_date_param(value):
    """解析日期参数，支持 'YYYY-MM-DD' 格式。"""
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _parse_page_params(request):
    """解析分页参数。"""
    try:
        page_num = int(request.GET.get("pageNum", 1))
    except (TypeError, ValueError):
        page_num = 1
    try:
        page_size = int(request.GET.get("pageSize", 20))
    except (TypeError, ValueError):
        page_size = 20
    if page_num < 1:
        page_num = 1
    if page_size < 1:
        page_size = 20
    return page_num, page_size


def _serialize_order(order):
    """序列化订单数据为字典。"""
    return {
        "id": order.id,
        "order_no": order.order_no or "",
        "contract_no": order.contract_no or "",
        "customer_name": order.customer_name or "",
        "customer_no": order.customer_no,
        "material_no": order.material_no or "",
        "product_name": order.product_name or "",
        "product_model": order.product_model or "",
        "product_category": order.product_category or "",
        "quantity": float(order.quantity) if order.quantity is not None else None,
        "unit_price": float(order.unit_price) if order.unit_price is not None else None,
        "amount": order.amount or "",
        "tax_unit_price": float(order.tax_unit_price) if order.tax_unit_price is not None else None,
        "tax_amount": order.tax_amount or "",
        "order_date": format_local_datetime(order.order_date) or "",
        "delivery_date": format_local_datetime(order.delivery_date) or "",
        "create_at": format_local_datetime(order.create_at) or "",
    }


@csrf_exempt
@require_http_methods(["GET"])
def order_list(request):
    """订单列表查询，支持分页、关键字搜索和日期范围筛选。"""
    page_num, page_size = _parse_page_params(request)

    # 关键字搜索（在订单号、合同编号、客户名称、商品名称、天链型号、物料编号中模糊匹配）
    keyword = (request.GET.get("keyword", "") or "").strip()
    # 精确字段筛选
    order_no = (request.GET.get("order_no", "") or "").strip()
    contract_no = (request.GET.get("contract_no", "") or "").strip()
    customer_name = (request.GET.get("customer_name", "") or "").strip()
    product_name = (request.GET.get("product_name", "") or "").strip()
    product_model = (request.GET.get("product_model", "") or "").strip()
    material_no = (request.GET.get("material_no", "") or "").strip()

    # 日期范围筛选
    order_start_date = _parse_date_param(
        request.GET.get("order_start_date") or request.GET.get("orderStartDate")
    )
    order_end_date = _parse_date_param(
        request.GET.get("order_end_date") or request.GET.get("orderEndDate")
    )
    delivery_start_date = _parse_date_param(
        request.GET.get("delivery_start_date") or request.GET.get("deliveryStartDate")
    )
    delivery_end_date = _parse_date_param(
        request.GET.get("delivery_end_date") or request.GET.get("deliveryEndDate")
    )

    qs = OrderList.objects.all()

    if keyword:
        qs = qs.filter(
            Q(order_no__icontains=keyword)
            | Q(contract_no__icontains=keyword)
            | Q(customer_name__icontains=keyword)
            | Q(product_name__icontains=keyword)
            | Q(product_model__icontains=keyword)
            | Q(material_no__icontains=keyword)
        )
    if order_no:
        qs = qs.filter(order_no__icontains=order_no)
    if contract_no:
        qs = qs.filter(contract_no__icontains=contract_no)
    if customer_name:
        qs = qs.filter(customer_name__icontains=customer_name)
    if product_name:
        qs = qs.filter(product_name__icontains=product_name)
    if product_model:
        qs = qs.filter(product_model__icontains=product_model)
    if material_no:
        qs = qs.filter(material_no__icontains=material_no)

    if order_start_date or order_end_date:
        if order_start_date and order_end_date and order_start_date > order_end_date:
            return JsonResponse({"code": "400", "msg": "订单开始日期不能晚于结束日期"})
        if order_start_date:
            start_dt, _ = local_day_range_datetimes(order_start_date, order_start_date)
            qs = qs.filter(order_date__gte=start_dt)
        if order_end_date:
            _, end_dt = local_day_range_datetimes(order_end_date, order_end_date)
            qs = qs.filter(order_date__lte=end_dt)

    if delivery_start_date or delivery_end_date:
        if delivery_start_date and delivery_end_date and delivery_start_date > delivery_end_date:
            return JsonResponse({"code": "400", "msg": "交付开始日期不能晚于结束日期"})
        if delivery_start_date:
            start_dt, _ = local_day_range_datetimes(delivery_start_date, delivery_start_date)
            qs = qs.filter(delivery_date__gte=start_dt)
        if delivery_end_date:
            _, end_dt = local_day_range_datetimes(delivery_end_date, delivery_end_date)
            qs = qs.filter(delivery_date__lte=end_dt)

    # 默认按创建日期降序
    sort_prop = (request.GET.get("sortProp", "") or "").strip()
    sort_order = (request.GET.get("sortOrder", "") or "").strip()

    sort_field_map = {
        "id": "id",
        "order_no": "order_no",
        "contract_no": "contract_no",
        "customer_name": "customer_name",
        "product_name": "product_name",
        "product_model": "product_model",
        "quantity": "quantity",
        "unit_price": "unit_price",
        "order_date": "order_date",
        "delivery_date": "delivery_date",
        "create_at": "create_at",
    }
    db_sort_field = sort_field_map.get(sort_prop, "create_at")
    db_sort_prefix = "-" if sort_order == "descending" else ""
    # create_at 可能为空，添加 id 作为次级排序保证稳定
    qs = qs.order_by(f"{db_sort_prefix}{db_sort_field}", "-id")

    total = qs.count()
    start = (page_num - 1) * page_size
    page_items = list(qs[start : start + page_size])

    return JsonResponse(
        {
            "code": "00000",
            "msg": "成功",
            "data": {
                "list": [_serialize_order(item) for item in page_items],
                "total": total,
                "pageNum": page_num,
                "pageSize": page_size,
            },
        }
    )


# ==================== 外部订单系统接口代理 ====================


def _proxy_get(path, params=None):
    """代理 GET 请求到外部订单接口。

    Args:
        path: 接口路径，如 /api/health
        params: 可选查询参数

    Returns:
        dict: 外部接口返回的 JSON 数据，出错时返回 {"error": "..."}
    """
    url = f"{EXTERNAL_ORDER_API_BASE}{path}"
    try:
        resp = http_requests.get(url, params=params, timeout=EXTERNAL_ORDER_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except http_requests.exceptions.Timeout:
        return {"error": f"请求外部接口超时（{EXTERNAL_ORDER_TIMEOUT}秒）"}
    except http_requests.exceptions.ConnectionError:
        return {"error": f"无法连接到外部接口：{EXTERNAL_ORDER_API_BASE}"}
    except http_requests.exceptions.HTTPError as e:
        return {"error": f"外部接口返回错误：{e.response.status_code}"}
    except Exception as e:
        return {"error": f"请求外部接口失败：{str(e)}"}


def _normalize_order_list(result):
    """将外部接口返回的数据统一为列表格式。"""
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        # 尝试常见的列表字段名
        for key in ("data", "list", "orders", "results", "items"):
            val = result.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                return [val]
        # 如果是单个订单对象
        if any(k in result for k in ("order_no", "orderNo", "contract_no", "product_name")):
            return [result]
    return []


@csrf_exempt
@require_http_methods(["GET"])
def order_health_check(request):
    """健康检查 - 代理转发到外部接口 GET /api/health"""
    result = _proxy_get("/api/health")
    if "error" in result:
        return JsonResponse({"code": "500", "msg": result["error"], "data": None})
    return JsonResponse({"code": "00000", "msg": "成功", "data": result})


@csrf_exempt
@require_http_methods(["GET"])
def order_sync_all(request):
    """全量查询 - 代理转发到外部接口 GET /api/orders

    支持可选日期参数 start_date, end_date
    """
    params = {}
    start_date = (request.GET.get("start_date", "") or "").strip()
    end_date = (request.GET.get("end_date", "") or "").strip()
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    result = _proxy_get("/api/orders", params=params if params else None)
    if "error" in result:
        return JsonResponse({"code": "500", "msg": result["error"], "data": None})

    data_list = _normalize_order_list(result)
    return JsonResponse({
        "code": "00000",
        "msg": "成功",
        "data": {"list": data_list, "total": len(data_list)},
    })


@csrf_exempt
@require_http_methods(["GET"])
def order_sync_today(request):
    """查询当天 - 代理转发到外部接口 GET /api/orders/today"""
    result = _proxy_get("/api/orders/today")
    if "error" in result:
        return JsonResponse({"code": "500", "msg": result["error"], "data": None})

    data_list = _normalize_order_list(result)
    return JsonResponse({
        "code": "00000",
        "msg": "成功",
        "data": {"list": data_list, "total": len(data_list)},
    })


@csrf_exempt
@require_http_methods(["GET"])
def order_sync_since(request, since_date):
    """增量查询 - 代理转发到外部接口 GET /api/orders/since/{date}

    日期拼接到 URL 路径中。
    """
    result = _proxy_get(f"/api/orders/since/{since_date}")
    if "error" in result:
        return JsonResponse({"code": "500", "msg": result["error"], "data": None})

    data_list = _normalize_order_list(result)
    return JsonResponse({
        "code": "00000",
        "msg": "成功",
        "data": {"list": data_list, "total": len(data_list)},
    })


@csrf_exempt
@require_http_methods(["GET"])
def order_by_no(request, order_no):
    """按订单号查询 - 代理转发到外部接口 GET /api/orders/{order_no}

    订单号拼接到 URL 路径最后。
    """
    result = _proxy_get(f"/api/orders/{order_no}")
    if "error" in result:
        return JsonResponse({"code": "500", "msg": result["error"], "data": None})

    data_list = _normalize_order_list(result)
    return JsonResponse({
        "code": "00000",
        "msg": "成功",
        "data": {"list": data_list, "total": len(data_list)},
    })
