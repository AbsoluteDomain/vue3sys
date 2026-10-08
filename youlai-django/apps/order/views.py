"""订单管理-视图函数。

提供订单列表查询接口，支持分页、关键字搜索和日期范围筛选。
同时提供外部订单系统接口代理，避免前端跨域问题。
"""

from datetime import datetime

import json

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
    from core.pagination import parse_page_params
    return parse_page_params(request, default_size=20)


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


# ==================== 同步外部数据到本地数据库 ====================


def _parse_decimal(value):
    """安全解析 Decimal 字段，失败返回 None。"""
    if value is None or value == "":
        return None
    try:
        from decimal import Decimal
        return Decimal(str(value))
    except Exception:
        return None


def _parse_datetime_field(value):
    """安全解析日期时间字段，失败返回 None。"""
    if not value or not isinstance(value, str):
        return None
    # 兼容 "YYYY-MM-DD HH:MM:SS" 和 "YYYY-MM-DDTHH:MM:SS"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip()[:len(fmt)], fmt)
        except ValueError:
            continue
    return None


def _compute_content_hash(item):
    """对业务字段取 MD5 哈希，用于识别完全相同的重复数据。"""
    import hashlib
    fields = [
        "order_no", "contract_no", "customer_name", "customer_no",
        "material_no", "product_name", "product_model", "product_category",
        "quantity", "unit_price", "amount", "tax_unit_price", "tax_amount",
        "order_date", "delivery_date", "create_at",
    ]
    parts = []
    for f in fields:
        v = item.get(f)
        if v is not None:
            parts.append(f"{f}={v}")
    return hashlib.md5("|".join(parts).encode("utf-8")).hexdigest()


@csrf_exempt
@require_http_methods(["POST"])
def order_sync_local(request):
    """将外部订单数据同步到本地 order_list 表。

    去重策略（双层）：
    1. 有 order_no 的记录：按 order_no 去重（已在库中或同批次已插入则跳过）
    2. 无 order_no 的记录：按 content_hash（业务字段MD5）去重

    每条记录写入 synced_at（同步时间戳）和 content_hash，便于追溯。

    请求体 JSON: {"orders": [{order_no, contract_no, ...}, ...]}
    返回: {"code": "00000", "data": {"inserted": N, "skipped": M, "skipped_orders": [...]}}
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"code": "400", "msg": "请求体不是有效的 JSON"})

    orders = body.get("orders")
    if not isinstance(orders, list) or not orders:
        return JsonResponse({"code": "400", "msg": "orders 字段不能为空"})

    from django.utils import timezone
    sync_time = timezone.now()

    # === 第一层：按 order_no 批量查询已存在的 ===
    incoming_order_nos = []
    for item in orders:
        no = (item.get("order_no") or "").strip()
        if no:
            incoming_order_nos.append(no)

    existing_nos = set()
    if incoming_order_nos:
        existing_nos = set(
            OrderList.objects.filter(order_no__in=incoming_order_nos)
            .values_list("order_no", flat=True)
        )

    # === 第二层：无 order_no 的记录，按 content_hash 去重 ===
    # 先计算所有记录的 hash
    for item in orders:
        item["_hash"] = _compute_content_hash(item)

    no_order_items = [item for item in orders if not (item.get("order_no") or "").strip()]
    incoming_hashes = [item["_hash"] for item in no_order_items]

    existing_hashes = set()
    if incoming_hashes:
        existing_hashes = set(
            OrderList.objects.filter(content_hash__in=incoming_hashes)
            .values_list("content_hash", flat=True)
        )

    inserted = 0
    skipped_orders = []
    skipped_dup = 0  # 无 order_no 的重复记录数

    for item in orders:
        order_no = (item.get("order_no") or "").strip()
        content_hash = item["_hash"]

        # 有 order_no：按 order_no 去重
        if order_no and order_no in existing_nos:
            skipped_orders.append(order_no)
            continue

        # 无 order_no：按 content_hash 去重
        if not order_no and content_hash in existing_hashes:
            skipped_dup += 1
            continue

        OrderList.objects.create(
            order_no=order_no or None,
            contract_no=item.get("contract_no") or None,
            customer_name=item.get("customer_name") or None,
            customer_no=item.get("customer_no"),
            material_no=item.get("material_no") or None,
            product_name=item.get("product_name") or None,
            product_model=item.get("product_model") or None,
            product_category=item.get("product_category") or None,
            quantity=_parse_decimal(item.get("quantity")),
            unit_price=_parse_decimal(item.get("unit_price")),
            amount=item.get("amount") or None,
            tax_unit_price=_parse_decimal(item.get("tax_unit_price")),
            tax_amount=item.get("tax_amount") or None,
            order_date=_parse_datetime_field(item.get("order_date")),
            delivery_date=_parse_datetime_field(item.get("delivery_date")),
            create_at=_parse_datetime_field(item.get("create_at")),
            synced_at=sync_time,
            content_hash=content_hash,
        )
        if order_no:
            existing_nos.add(order_no)
        else:
            existing_hashes.add(content_hash)
        inserted += 1

    return JsonResponse({
        "code": "00000",
        "msg": "成功",
        "data": {
            "inserted": inserted,
            "skipped": len(skipped_orders) + skipped_dup,
            "skipped_orders": skipped_orders,
            "skipped_dup": skipped_dup,
            "sync_time": sync_time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    })
