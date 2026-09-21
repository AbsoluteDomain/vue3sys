import json
import logging
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.product.boms.models import AssemblyRecipe, BomList
from apps.product.utils.warehouse_logger import create_warehouse_log, log_inventory_operation

logger = logging.getLogger(__name__)
from apps.product.products.models import Product, WarehouseLog
from core.datetime import format_local_datetime, local_date_key, local_day_range_datetimes
from core.datetime import make_local_aware, parse_local_datetime_text

from apps.system.dicts.models import DictionaryItem
from apps.system.operation_logs.utils import format_finish_product_rollback_description

try:
    from apps.system.operation_logs.services import log_operation_from_request

    OPERATION_LOGS_AVAILABLE = True
except ImportError:
    OPERATION_LOGS_AVAILABLE = False

from .models import FinishProduct, FinishedProductLog

VALID_STATUS = {
    FinishProduct.STATUS_UNTESTED,
    FinishProduct.STATUS_TESTING,
    FinishProduct.STATUS_PASS,
    FinishProduct.STATUS_FAIL,
}

TRACKABLE_FIELDS = FinishedProductLog.TRACKABLE_FIELDS


def _log_if_available(request, **kwargs):
    if OPERATION_LOGS_AVAILABLE:
        log_operation_from_request(request, **kwargs)


def _compute_changed_fields(before_data, after_data):
    """对比前后快照，返回实际变化的列展示字段键列表"""
    before = before_data or {}
    after = after_data or {}
    changed = []
    for key in TRACKABLE_FIELDS:
        if before.get(key) != after.get(key):
            changed.append(key)
    return changed


def _log_finish_product_operation(request, item, operation_type,
                                   before_data=None, after_data=None, description=""):
    """写入成品操作记录到 finished_product_log 表"""
    try:
        from apps.system.operation_logs.request_user import get_client_ip, get_request_operator
        operator = get_request_operator(request)
        if not operator:
            return
        user_id, user_name = operator
        changed = _compute_changed_fields(before_data, after_data)
        # create 操作 before_data 为空，changed 设为 after_data 中存在的全部字段
        if operation_type == FinishedProductLog.OPERATION_CREATE and after_data and not before_data:
            changed = [k for k in TRACKABLE_FIELDS if k in (after_data or {})]

        fp_id = None
        sn_code = ""
        if item:
            fp_id = item.id
            sn_code = item.sn_code or ""
        elif before_data:
            fp_id = before_data.get("id")
            sn_code = before_data.get("sn_code") or ""

        FinishedProductLog.objects.create(
            finish_product_id=fp_id,
            sn_code=sn_code,
            operation_type=operation_type,
            operator_id=user_id,
            operator_name=user_name,
            before_data=before_data,
            after_data=after_data,
            changed_fields=changed,
            description=(description or "")[:500],
            ip=get_client_ip(request),
        )
    except Exception as e:
        logger.error("记录成品操作日志失败: %s", str(e))


def _snapshot_unqualified_items(finish_product_id):
    """快照某成品的全部不良项（含字典标签），按值排序"""
    items = UnqualifiedItem.objects.filter(
        finish_product_id=finish_product_id
    ).order_by("unqualified_value")
    labels = {}
    values = [it.unqualified_value for it in items]
    if values:
        for di in DictionaryItem.objects.filter(
            dict_code="unqualified_status",
            value__in=[str(v) for v in set(values)],
            status=1,
        ):
            try:
                labels[int(di.value)] = di.label
            except (ValueError, TypeError):
                pass
    return [{"value": v, "label": labels.get(v, f"未知({v})")} for v in values]


def _log_unqualified_operation(request, fp_id, sn_code, before_items, after_items, description):
    """写入不良详情操作记录到 finished_product_log 表"""
    try:
        from apps.system.operation_logs.request_user import get_client_ip, get_request_operator
        operator = get_request_operator(request)
        if not operator:
            return
        user_id, user_name = operator
        changed = ["unqualified_items"] if before_items != after_items else []
        FinishedProductLog.objects.create(
            finish_product_id=fp_id,
            sn_code=sn_code or "",
            operation_type=FinishedProductLog.OPERATION_UNQUALIFIED,
            operator_id=user_id,
            operator_name=user_name,
            before_data={"unqualified_items": before_items},
            after_data={"unqualified_items": after_items},
            changed_fields=changed,
            description=(description or "")[:500],
            ip=get_client_ip(request),
        )
    except Exception as e:
        logger.error("记录不良详情操作日志失败: %s", str(e))


def _get_valid_dict_int_values(dict_code):
    """从字典表读取启用的字典项值，转为整数集合。

    用于替代筛选条件中硬编码的状态值，使得在字典管理中新增/启用的字典项
    能够立即被筛选命中，无需修改后端代码。
    """
    valid = set()
    for v in DictionaryItem.objects.filter(
        dict_code=dict_code, status=1
    ).values_list("value", flat=True):
        try:
            valid.add(int(v))
        except (TypeError, ValueError):
            continue
    return valid


def _recipe_part_info(row):
    """从 BOM 明细行解析绑定的产品零件信息"""
    if row.raw_material_id:
        return {
            "product_id": row.raw_material_id,
            "product_name": row.raw_material_name or "",
            "quantity": row.raw_material_quantity,
        }
    if row.component_id:
        return {
            "product_id": row.component_id,
            "product_name": row.component_name or "",
            "quantity": row.component_quantity,
        }
    return {
        "product_id": None,
        "product_name": "",
        "quantity": None,
    }


def _parse_date_param(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _empty_daily_bucket(date_str):
    return {
        "date": date_str,
        "newCount": 0,
        "passCount": 0,
        "failCount": 0,
        "pendingNewCount": 0,
        "testingCount": 0,
        "repairCount": 0,
        "repairTestingCount": 0,
        "repairPassCount": 0,
        "pendingRepairCount": 0,
        "stockInCount": 0,
        "stockOutCount": 0,
        "stockOutSaleCount": 0,
        "stockOutDevCount": 0,
    }


def _parse_optional_datetime(body, field_keys, field_label):
    """解析可清空的日期时间字段，支持 snake_case / camelCase。"""
    present_key = next((key for key in field_keys if key in body), None)
    if present_key is None:
        return None, False

    raw_value = body.get(present_key)
    if raw_value is None or str(raw_value).strip() == "":
        return None, True

    parsed = parse_local_datetime_text(raw_value)
    if parsed is None:
        raise ValueError(f"{field_label}格式无效，请使用 YYYY-MM-DD HH:MM:SS")
    return make_local_aware(parsed), True


def _filter_by_bom_type(qs, bom_type):
    """根据BOM类型筛选成品查询集。bom_type: 'joint'=关节(0), 'arm'=机械臂(1), 其他值不筛选"""
    if not bom_type:
        return qs
    if bom_type in ("joint", "0"):
        bom_ids = list(BomList.objects.filter(type=BomList.TYPE_JOINT, is_del=0).values_list("id", flat=True))
        return qs.filter(bom_id__in=bom_ids)
    elif bom_type in ("arm", "1"):
        bom_ids = list(BomList.objects.filter(type=BomList.TYPE_ROBOT_ARM, is_del=0).values_list("id", flat=True))
        return qs.filter(bom_id__in=bom_ids)
    return qs


def _increment_daily_count(daily_map, summary, day, count_key):
    bucket = daily_map.get(day)
    if not bucket:
        return
    bucket[count_key] += 1
    summary[count_key] += 1


TEST_TIME_STAT_CATEGORIES = {
    "passCount",
    "failCount",
    "pendingNewCount",
    "testingCount",
    "repairTestingCount",
    "repairPassCount",
    "pendingRepairCount",
}


def _accumulate_test_time_stats(item, daily_map, summary):
    """按测试状态修改时间与状态/返修标记累计测试相关统计。"""
    day = local_date_key(item.test_time)
    if not day:
        return
    bucket = daily_map.get(day)
    if not bucket:
        return

    if item.status == FinishProduct.STATUS_PASS:
        bucket["passCount"] += 1
        summary["passCount"] += 1
    elif item.status == FinishProduct.STATUS_FAIL:
        bucket["failCount"] += 1
        summary["failCount"] += 1

    if item.repair == FinishProduct.REPAIR_NEW:
        if item.status == FinishProduct.STATUS_UNTESTED:
            bucket["pendingNewCount"] += 1
            summary["pendingNewCount"] += 1
        elif item.status == FinishProduct.STATUS_TESTING:
            bucket["testingCount"] += 1
            summary["testingCount"] += 1
    elif item.repair == FinishProduct.REPAIR_REPAIRED:
        if item.status == FinishProduct.STATUS_PASS:
            bucket["repairPassCount"] += 1
            summary["repairPassCount"] += 1
        elif item.status == FinishProduct.STATUS_UNTESTED:
            bucket["pendingRepairCount"] += 1
            summary["pendingRepairCount"] += 1
        elif item.status == FinishProduct.STATUS_TESTING:
            bucket["repairTestingCount"] += 1
            summary["repairTestingCount"] += 1


def finish_product_daily_stats(request):
    """按日期统计成品：新品按创建时间，测试按测试状态修改时间，返修按更新时间，入库/出库按各自时间"""
    end_date = _parse_date_param(
        request.GET.get("end_date") or request.GET.get("endDate")
    )
    start_date = _parse_date_param(
        request.GET.get("start_date") or request.GET.get("startDate")
    )

    if not end_date:
        end_date = timezone.localdate()
    if not start_date:
        start_date = end_date - timedelta(days=29)
    if start_date > end_date:
        return JsonResponse({"code": "400", "msg": "开始日期不能晚于结束日期"})
    if (end_date - start_date).days > 366:
        return JsonResponse({"code": "400", "msg": "日期范围不能超过366天"})

    bom_type = (request.GET.get("bom_type") or request.GET.get("bomType") or "").strip()

    daily_map = {}
    current = start_date
    while current <= end_date:
        daily_map[current.isoformat()] = _empty_daily_bucket(current.isoformat())
        current += timedelta(days=1)

    summary = _empty_daily_bucket("")
    summary.pop("date", None)

    start_dt, end_dt = local_day_range_datetimes(start_date, end_date)

    create_qs = FinishProduct.active_queryset().filter(
        create_time__isnull=False,
        create_time__gte=start_dt,
        create_time__lte=end_dt,
    )
    create_qs = _filter_by_bom_type(create_qs, bom_type)

    for item in create_qs:
        day = local_date_key(item.create_time)
        if not day:
            continue
        bucket = daily_map.get(day)
        if not bucket:
            continue

        bucket["newCount"] += 1
        summary["newCount"] += 1

    test_qs = FinishProduct.active_queryset().filter(
        test_time__isnull=False,
        test_time__gte=start_dt,
        test_time__lte=end_dt,
    )
    test_qs = _filter_by_bom_type(test_qs, bom_type)
    for item in test_qs:
        _accumulate_test_time_stats(item, daily_map, summary)

    update_qs = FinishProduct.active_queryset().filter(
        update_time__isnull=False,
        update_time__gte=start_dt,
        update_time__lte=end_dt,
    )
    update_qs = _filter_by_bom_type(update_qs, bom_type)

    for item in update_qs:
        day = local_date_key(item.update_time)
        if not day:
            continue
        bucket = daily_map.get(day)
        if not bucket:
            continue

        if item.repair == FinishProduct.REPAIR_REPAIRED:
            bucket["repairCount"] += 1
            summary["repairCount"] += 1

    stock_in_qs = FinishProduct.active_queryset().filter(
        stock_in_time__isnull=False,
        stock_in_time__gte=start_dt,
        stock_in_time__lte=end_dt,
        inventory_stock=FinishProduct.INVENTORY_IN,
    )
    stock_in_qs = _filter_by_bom_type(stock_in_qs, bom_type)
    for item in stock_in_qs:
        day = local_date_key(item.stock_in_time)
        _increment_daily_count(daily_map, summary, day, "stockInCount")

    stock_out_qs = FinishProduct.active_queryset().filter(
        stock_out_time__isnull=False,
        stock_out_time__gte=start_dt,
        stock_out_time__lte=end_dt,
        inventory_stock__in=[FinishProduct.INVENTORY_OUT_SALE, FinishProduct.INVENTORY_OUT_DEV],
    )
    stock_out_qs = _filter_by_bom_type(stock_out_qs, bom_type)
    for item in stock_out_qs:
        day = local_date_key(item.stock_out_time)
        bucket = daily_map.get(day)
        if not bucket:
            continue
        bucket["stockOutCount"] += 1
        summary["stockOutCount"] += 1
        if item.inventory_stock == FinishProduct.INVENTORY_OUT_DEV:
            bucket["stockOutDevCount"] += 1
            summary["stockOutDevCount"] += 1
        else:
            bucket["stockOutSaleCount"] += 1
            summary["stockOutSaleCount"] += 1

    current_stock_in_count = _filter_by_bom_type(
        FinishProduct.active_queryset().filter(inventory_stock=FinishProduct.INVENTORY_IN), bom_type
    ).count()

    return JsonResponse(
        {
            "code": "00000",
            "msg": "成功",
            "data": {
                "summary": summary,
                "currentStockInCount": current_stock_in_count,
                "daily": list(daily_map.values()),
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "bomType": bom_type or "all",
            },
        }
    )


def _apply_field_date_range(qs, time_field, start_date, end_date):
    """按指定时间字段与日期范围筛选（含首尾日全天）"""
    if not start_date and not end_date:
        return qs
    if start_date and end_date and start_date > end_date:
        return qs.none()

    if not start_date:
        start_date = end_date
    if not end_date:
        end_date = start_date

    start_dt, end_dt = local_day_range_datetimes(start_date, end_date)
    return qs.filter(
        **{f"{time_field}__isnull": False},
        **{f"{time_field}__gte": start_dt},
        **{f"{time_field}__lte": end_dt},
    )


def _apply_time_range_filter(qs, request):
    """支持创建时间、更新时间独立日期范围筛选"""
    create_start = _parse_date_param(
        request.GET.get("create_start_date") or request.GET.get("createStartDate")
    )
    create_end = _parse_date_param(
        request.GET.get("create_end_date") or request.GET.get("createEndDate")
    )
    update_start = _parse_date_param(
        request.GET.get("update_start_date") or request.GET.get("updateStartDate")
    )
    update_end = _parse_date_param(
        request.GET.get("update_end_date") or request.GET.get("updateEndDate")
    )

    qs = _apply_field_date_range(qs, "create_time", create_start, create_end)
    qs = _apply_field_date_range(qs, "update_time", update_start, update_end)
    return qs


def _parse_page_params(request):
    from core.pagination import parse_page_params
    return parse_page_params(request)


def _get_dict_label(dict_code, int_value):
    """根据字典编码和整数值获取字典项的标签。"""
    try:
        item = DictionaryItem.objects.filter(
            dict_code=dict_code, status=1, value=str(int_value)
        ).first()
        if item:
            return item.label
    except Exception:
        pass
    return str(int_value)


def _serialize_finish_product(item, bom_map=None):
    bom_type = None
    bom_type_name = ""
    bom_model = ""
    bom_name = ""
    material_code = ""

    bom = None
    if bom_map and item.bom_id in bom_map:
        bom = bom_map[item.bom_id]
    elif item.bom_id:
        try:
            bom = BomList.objects.get(id=item.bom_id, is_del=0)
        except BomList.DoesNotExist:
            bom = None

    if bom:
        bom_type = bom.type
        bom_type_name = bom.get_type_display()
        bom_model = bom.bom_model
        bom_name = bom.bom_name or ""
        material_code = bom.material_code or ""

    return {
            "id": item.id,
            "sn_code": item.sn_code or "",
            "bom_id": item.bom_id,
            "bom_type": bom_type,
            "bom_type_name": bom_type_name,
            "bom_model": bom_model,
            "bom_name": bom_name,
            "material_code": material_code,
            "parent_sn_code": item.parent_sn_code or "",
            "name": item.name,
            "status": item.status,
            "status_name": item.get_status_display(),
            "description": item.description or "",
            "create_time": format_local_datetime(item.create_time) or "",
            "update_time": format_local_datetime(item.update_time) or "",
            "test_time": format_local_datetime(item.test_time) or "",
            "stock_in_time": format_local_datetime(item.stock_in_time) or "",
            "stock_out_time": format_local_datetime(item.stock_out_time) or "",
            "inventory_stock": item.inventory_stock,
            "inventory_stock_name": _get_dict_label("storage_status", item.inventory_stock),
            "repair": item.repair,
            "repair_name": item.get_repair_display(),
            "cons_status": item.cons_status,
            "cons_status_name": item.get_cons_status_display() if item.cons_status is not None else "",
        }


BOARD_DETAIL_CATEGORIES = {
    "newCount",
    "passCount",
    "failCount",
    "pendingNewCount",
    "testingCount",
    "repairCount",
    "repairTestingCount",
    "repairPassCount",
    "pendingRepairCount",
    "stockInCount",
    "stockOutCount",
    "stockOutSaleCount",
    "stockOutDevCount",
    "currentStockInCount",
}


def _apply_board_category_filter(qs, category):
    """按看板统计项筛选，规则与 finish_product_daily_stats 一致"""
    if category == "newCount":
        return qs
    if category in TEST_TIME_STAT_CATEGORIES:
        qs = qs.filter(test_time__isnull=False)
    if category == "passCount":
        return qs.filter(status=FinishProduct.STATUS_PASS)
    if category == "failCount":
        return qs.filter(status=FinishProduct.STATUS_FAIL)
    if category == "pendingNewCount":
        return qs.filter(
            repair=FinishProduct.REPAIR_NEW,
            status=FinishProduct.STATUS_UNTESTED,
        )
    if category == "testingCount":
        return qs.filter(
            repair=FinishProduct.REPAIR_NEW,
            status=FinishProduct.STATUS_TESTING,
        )
    if category == "repairCount":
        return qs.filter(repair=FinishProduct.REPAIR_REPAIRED)
    if category == "repairTestingCount":
        return qs.filter(
            repair=FinishProduct.REPAIR_REPAIRED,
            status=FinishProduct.STATUS_TESTING,
        )
    if category == "repairPassCount":
        return qs.filter(
            repair=FinishProduct.REPAIR_REPAIRED,
            status=FinishProduct.STATUS_PASS,
        )
    if category == "pendingRepairCount":
        return qs.filter(
            repair=FinishProduct.REPAIR_REPAIRED,
            status=FinishProduct.STATUS_UNTESTED,
        )
    if category == "stockInCount":
        return qs.filter(stock_in_time__isnull=False, inventory_stock=FinishProduct.INVENTORY_IN)
    if category == "stockOutCount":
        return qs.filter(
            stock_out_time__isnull=False,
            inventory_stock__in=[FinishProduct.INVENTORY_OUT_SALE, FinishProduct.INVENTORY_OUT_DEV],
        )
    if category == "stockOutSaleCount":
        return qs.filter(stock_out_time__isnull=False, inventory_stock=FinishProduct.INVENTORY_OUT_SALE)
    if category == "stockOutDevCount":
        return qs.filter(stock_out_time__isnull=False, inventory_stock=FinishProduct.INVENTORY_OUT_DEV)
    if category == "currentStockInCount":
        return qs.filter(inventory_stock=FinishProduct.INVENTORY_IN)
    return qs.none()


def finish_product_board_detail(request):
    """看板统计项对应的成品明细列表"""
    category = (request.GET.get("category") or "").strip()
    if category not in BOARD_DETAIL_CATEGORIES:
        return JsonResponse({"code": "400", "msg": "无效的统计类别"})

    bom_type = (request.GET.get("bom_type") or request.GET.get("bomType") or "").strip()

    page_num, page_size = _parse_page_params(request)
    end_date = _parse_date_param(
        request.GET.get("end_date") or request.GET.get("endDate")
    )
    start_date = _parse_date_param(
        request.GET.get("start_date") or request.GET.get("startDate")
    )
    single_date = _parse_date_param(request.GET.get("date"))

    if single_date:
        start_date = end_date = single_date
    elif category != "currentStockInCount":
        if not end_date:
            end_date = timezone.localdate()
        if not start_date:
            start_date = end_date - timedelta(days=29)
        if start_date > end_date:
            return JsonResponse({"code": "400", "msg": "开始日期不能晚于结束日期"})

    qs = FinishProduct.objects.all()
    # 看板详情列表默认过滤已回退记录
    qs = qs.exclude(cons_status=FinishProduct.CONS_STATUS_ROLLED_BACK)
    qs = _apply_board_category_filter(qs, category)
    qs = _filter_by_bom_type(qs, bom_type)

    if category == "currentStockInCount":
        pass
    elif category == "newCount":
        qs = _apply_field_date_range(qs, "create_time", start_date, end_date)
    elif category in TEST_TIME_STAT_CATEGORIES:
        qs = _apply_field_date_range(qs, "test_time", start_date, end_date)
    elif category == "stockInCount":
        qs = _apply_field_date_range(qs, "stock_in_time", start_date, end_date)
    elif category == "stockOutCount" or category == "stockOutSaleCount" or category == "stockOutDevCount":
        qs = _apply_field_date_range(qs, "stock_out_time", start_date, end_date)
    else:
        qs = _apply_field_date_range(qs, "update_time", start_date, end_date)

    order_fields = ["-create_time", "-id"]
    if category in TEST_TIME_STAT_CATEGORIES:
        order_fields = ["-test_time", "-id"]
    elif category == "stockInCount":
        order_fields = ["-stock_in_time", "-id"]
    elif category in ("stockOutCount", "stockOutSaleCount", "stockOutDevCount"):
        order_fields = ["-stock_out_time", "-id"]

    total = qs.count()
    start = (page_num - 1) * page_size
    page_items = list(qs.order_by(*order_fields)[start : start + page_size])

    bom_ids = {item.bom_id for item in page_items if item.bom_id}
    bom_map = {}
    if bom_ids:
        bom_map = {bom.id: bom for bom in BomList.objects.filter(id__in=bom_ids, is_del=0)}

    return JsonResponse(
        {
            "code": "00000",
            "msg": "成功",
            "data": {
                "list": [
                    _serialize_finish_product(item, bom_map) for item in page_items
                ],
                "total": total,
                "pageNum": page_num,
                "pageSize": page_size,
                "category": category,
                "startDate": start_date.isoformat() if start_date else None,
                "endDate": end_date.isoformat() if end_date else None,
            },
        }
    )


def finish_product_list(request):
    page_num, page_size = _parse_page_params(request)
    sn_code = (request.GET.get("sn_code", "") or request.GET.get("sn", "") or "").strip()
    bom_model = (
        request.GET.get("bom_model", "") or request.GET.get("bomModel", "") or ""
    ).strip()
    bom_name = (
        request.GET.get("bom_name", "") or request.GET.get("bomName", "") or ""
    ).strip()
    bom_id = (request.GET.get("bom_id", "") or "").strip()
    status = (request.GET.get("status", "") or "").strip()
    inventory_stock = (request.GET.get("inventory_stock", "") or "").strip()
    repair = (request.GET.get("repair", "") or "").strip()
    bom_type = (request.GET.get("bom_type", "") or request.GET.get("type", "") or "").strip()
    parent_sn_code = (
        request.GET.get("parent_sn_code", "") or request.GET.get("parentSnCode", "") or ""
    ).strip()

    qs = FinishProduct.objects.all()
    # 默认过滤已回退记录（cons_status=2），include_rolled_back=1 时包含
    include_rolled_back = (request.GET.get("include_rolled_back") or "").strip().lower() in ("1", "true")
    if not include_rolled_back:
        qs = qs.exclude(cons_status=FinishProduct.CONS_STATUS_ROLLED_BACK)
    if sn_code:
        qs = qs.filter(sn_code__icontains=sn_code)
    if parent_sn_code:
        qs = qs.filter(parent_sn_code=parent_sn_code)
    if bom_id:
        try:
            qs = qs.filter(bom_id=int(bom_id))
        except (TypeError, ValueError):
            qs = qs.none()
    if status in ("0", "1", "2", "3"):
        qs = qs.filter(status=int(status))
    if inventory_stock:
        try:
            inv_val = int(inventory_stock)
        except (TypeError, ValueError):
            inv_val = None
        if inv_val is not None and inv_val in _get_valid_dict_int_values("storage_status"):
            qs = qs.filter(inventory_stock=inv_val)
        else:
            qs = qs.none()
    if repair in ("0", "1"):
        qs = qs.filter(repair=int(repair))

    bom_filter_needed = (
        bom_type in ("0", "1", "2") or bom_model or bom_name
    )
    if bom_filter_needed:
        bom_qs = BomList.objects.filter(is_del=0)
        if bom_type in ("0", "1", "2"):
            bom_qs = bom_qs.filter(type=int(bom_type))
        if bom_model:
            bom_qs = bom_qs.filter(bom_model__icontains=bom_model)
        if bom_name:
            bom_qs = bom_qs.filter(bom_name__icontains=bom_name)
        qs = qs.filter(bom_id__in=bom_qs.values_list("id", flat=True))

    qs = _apply_time_range_filter(qs, request)

    total = qs.count()
    start = (page_num - 1) * page_size
    page_items = list(qs[start : start + page_size])

    bom_ids = {item.bom_id for item in page_items if item.bom_id}
    bom_map = {}
    if bom_ids:
        bom_map = {bom.id: bom for bom in BomList.objects.filter(id__in=bom_ids, is_del=0)}

    return JsonResponse(
        {
            "code": "00000",
            "msg": "成功",
            "data": {
                "list": [
                    _serialize_finish_product(item, bom_map) for item in page_items
                ],
                "total": total,
                "pageNum": page_num,
                "pageSize": page_size,
            },
        }
    )


def _sync_product_inventory(bom, inventory_action):
    """同步成品库存到产品库存表
    
    Args:
        bom: BomList对象
        inventory_action: 'in' 入库, 'out' 出库
    """
    if not bom.material_code:
        return
    
    material_code = bom.material_code.strip()
    if not material_code:
        return
    
    bom_type = bom.type
    
    if bom_type == 0:
        product_type = 4
    elif bom_type == 1:
        product_type = 5
    else:
        product_type = 2
    
    quantity = 1
    
    try:
        product = Product.objects.get(material_code=material_code, is_del=0)
        current = product.quantity if product.quantity is not None else 0

        if inventory_action == "out" and current < quantity:
            raise ValueError(f"库存不足：物料编码「{material_code}」当前库存 {current}，需要出库 {quantity}")

        if inventory_action == "in":
            product.quantity = current + quantity
        else:
            product.quantity = current - quantity

        product.type = product_type
        product.save(update_fields=["quantity", "type", "updated_at"])
        logger.info(
            "[库存同步] material_code=%s, action=%s, 库存: %s → %s",
            material_code, inventory_action, current, product.quantity,
        )
    except Product.DoesNotExist:
        if inventory_action == "out":
            raise ValueError(f"物料编码「{material_code}」不存在，无法出库")
        
        Product.objects.create(
            name=bom.bom_name or bom.bom_model,
            type=product_type,
            material_code=material_code,
            quantity=quantity,
            procurement_cycle=1,
            is_del=0,
        )


@csrf_exempt
@require_http_methods(["POST"])
def create_finish_product(request):
    """创建成品（用于手动添加关节等场景）"""
    try:
        body = json.loads(request.body or "{}")
        bom_id = body.get("bom_id")
        if not bom_id:
            return JsonResponse({"code": "400", "msg": "缺少 BOM ID"})

        try:
            bom = BomList.objects.get(id=int(bom_id), is_del=0)
        except BomList.DoesNotExist:
            return JsonResponse({"code": "400", "msg": "关联的 BOM 不存在"})

        sn_code = (body.get("sn_code") or "").strip() or None
        if sn_code and FinishProduct.active_queryset().filter(sn_code=sn_code).exists():
            return JsonResponse({"code": "400", "msg": "SN码已存在"})

        now = timezone.now()
        item = FinishProduct.objects.create(
            sn_code=sn_code,
            bom_id=bom.id,
            name=bom.bom_name or bom.bom_model or "",
            status=FinishProduct.STATUS_UNTESTED,
            inventory_stock=FinishProduct.INVENTORY_NOT_IN,
            repair=FinishProduct.REPAIR_NEW,
            cons_status=FinishProduct.CONS_STATUS_NOT_CONSUMED,
            description=(body.get("description") or "").strip() or None,
            parent_sn_code=(body.get("parent_sn_code") or "").strip() or None,
            create_time=now,
            update_time=now,
            test_time=now,
        )

        _log_if_available(
            request,
            module='finish_product',
            module_name='成品管理',
            operation_type='create',
            target_id=item.id,
            target_name=item.sn_code or item.name,
            after_data=_serialize_finish_product(item),
            description=f"创建成品：{bom.bom_model} {bom.bom_name or ''}",
        )

        _log_finish_product_operation(
            request, item, FinishedProductLog.OPERATION_CREATE,
            after_data=_serialize_finish_product(item),
            description=f"创建成品：{bom.bom_model} {bom.bom_name or ''}",
        )

        return JsonResponse(
            {
                "code": "00000",
                "msg": "创建成功",
                "data": _serialize_finish_product(item),
            }
        )
    except (TypeError, ValueError):
        return JsonResponse({"code": "400", "msg": "参数格式错误"})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"创建失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["POST"])
def update_finish_product(request):
    try:
        body = json.loads(request.body or "{}")
        item_id = body.get("id")
        if not item_id:
            return JsonResponse({"code": "400", "msg": "缺少成品 ID"})

        item = FinishProduct.objects.get(id=int(item_id))

        # 已回退的成品不可编辑
        if item.cons_status == FinishProduct.CONS_STATUS_ROLLED_BACK:
            return JsonResponse({"code": "400", "msg": "该成品已回退，不可编辑"})

        before_data = _serialize_finish_product(item)

        old_inventory_stock = item.inventory_stock
        old_parent_sn_code = item.parent_sn_code

        logger.info(
            "[解除绑定-开始] finish_product_id=%s, sn_code=%s, old_inventory_stock=%s, old_parent_sn_code=%s, body=%s",
            item.id, item.sn_code, old_inventory_stock, old_parent_sn_code, body,
        )

        # 获取关联的BOM类型，用于判断是否为关节
        try:
            bom = BomList.objects.get(id=item.bom_id, is_del=0)
            bom_type = bom.type
        except BomList.DoesNotExist:
            bom_type = None

        if "sn_code" in body:
            sn_code = (body.get("sn_code") or "").strip()
            if sn_code and FinishProduct.active_queryset().filter(sn_code=sn_code).exclude(id=item.id).exists():
                return JsonResponse({"code": "400", "msg": "SN码已存在"})
            item.sn_code = sn_code or None

        if "status" in body:
            status = int(body.get("status"))
            if status not in VALID_STATUS:
                return JsonResponse({"code": "400", "msg": "测试状态值无效"})
            if status != item.status:
                if "test_time" not in body and "testTime" not in body:
                    item.test_time = timezone.now()
            item.status = status

        # 先处理父级SN码变更（影响后续库存状态验证）
        new_parent_sn_code = item.parent_sn_code
        if "parent_sn_code" in body or "parentSnCode" in body:
            new_parent_sn_code = (body.get("parent_sn_code", body.get("parentSnCode")) or "").strip() or None

        is_joint = (bom_type == 0)  # bom_type=0 表示关节

        # ========== 核心逻辑：关节有父级SN码时，强制设置为组件消耗状态 ==========
        # 先自动设置 inventory_stock，确保后续校验和同步使用正确的值
        if is_joint and new_parent_sn_code:
            if not old_parent_sn_code or item.inventory_stock != FinishProduct.INVENTORY_CONSUME:
                if "inventory_stock" in body:
                    body["inventory_stock"] = FinishProduct.INVENTORY_CONSUME
                inventory_stock = FinishProduct.INVENTORY_CONSUME
                item.inventory_stock = FinishProduct.INVENTORY_CONSUME
        # 清除父级SN码时，如果库存状态是组件消耗，需要恢复
        if is_joint and not new_parent_sn_code and item.inventory_stock == FinishProduct.INVENTORY_CONSUME:
            restored_stock = FinishProduct.INVENTORY_IN if old_inventory_stock == FinishProduct.INVENTORY_CONSUME else old_inventory_stock
            if "inventory_stock" in body:
                body["inventory_stock"] = restored_stock
            inventory_stock = restored_stock
            item.inventory_stock = inventory_stock
            logger.info(
                "[解除绑定-库存恢复] finish_product_id=%s, 组件消耗(%s) → 入库(%s), old_inventory_stock=%s",
                item.id, FinishProduct.INVENTORY_CONSUME, restored_stock, old_inventory_stock,
            )

        if "inventory_stock" in body:
            inventory_stock = int(body.get("inventory_stock"))
            valid_inventory = _get_valid_dict_int_values("storage_status")
            if inventory_stock not in valid_inventory:
                return JsonResponse({"code": "400", "msg": "库存状态值无效"})
            # 如果是关节（bom_type=0）且有父级SN码，库存状态只能为组件消耗
            if is_joint and new_parent_sn_code and inventory_stock != FinishProduct.INVENTORY_CONSUME:
                return JsonResponse({"code": "400", "msg": "关节有关联父级时，库存状态只能为「组件消耗」"})
            # 如果清除了父级SN码，库存状态不能为组件消耗
            if is_joint and not new_parent_sn_code and inventory_stock == FinishProduct.INVENTORY_CONSUME:
                return JsonResponse({"code": "400", "msg": "清除父级SN码后，库存状态不能为「组件消耗」"})
            # 状态流转校验：未入库的成品不能直接出库，必须先入库
            if (
                old_inventory_stock == FinishProduct.INVENTORY_NOT_IN
                and inventory_stock in (FinishProduct.INVENTORY_OUT_SALE, FinishProduct.INVENTORY_OUT_DEV)
            ):
                return JsonResponse({"code": "400", "msg": "未入库的成品不能直接出库，请先办理入库手续"})
            item.inventory_stock = inventory_stock

        if "repair" in body:
            repair = int(body.get("repair"))
            valid_repair = {c[0] for c in FinishProduct.REPAIR_CHOICES}
            if repair not in valid_repair:
                return JsonResponse({"code": "400", "msg": "返修状态值无效"})
            item.repair = repair

        if "description" in body:
            item.description = (body.get("description") or "").strip() or None

        if "parent_sn_code" in body or "parentSnCode" in body:
            item.parent_sn_code = new_parent_sn_code
            # 关节有父级SN码时，强制设置为组件消耗（已在上方核心逻辑处理，此处作为兜底）
            if is_joint and new_parent_sn_code and item.inventory_stock != FinishProduct.INVENTORY_CONSUME:
                item.inventory_stock = FinishProduct.INVENTORY_CONSUME

        if "create_time" in body or "createTime" in body:
            create_time_raw = body.get("create_time", body.get("createTime"))
            if create_time_raw is None or str(create_time_raw).strip() == "":
                item.create_time = None
            else:
                parsed = parse_local_datetime_text(create_time_raw)
                if parsed is None:
                    return JsonResponse({"code": "400", "msg": "创建时间格式无效，请使用 YYYY-MM-DD HH:MM:SS"})
                item.create_time = make_local_aware(parsed)

        datetime_fields = (
            ("test_time", ("test_time", "testTime"), "测试状态修改时间"),
            ("stock_in_time", ("stock_in_time", "stockInTime"), "入库时间"),
            ("stock_out_time", ("stock_out_time", "stockOutTime"), "出库时间"),
        )
        for model_field, body_keys, field_label in datetime_fields:
            try:
                parsed_value, should_update = _parse_optional_datetime(body, body_keys, field_label)
            except ValueError as exc:
                return JsonResponse({"code": "400", "msg": str(exc)})
            if should_update:
                setattr(item, model_field, parsed_value)

        # 自动同步出入库时间戳（作为显式字段的兜底）
        # 当用户改变库存状态为「入库/出库」但未显式填写对应时间时，自动记录当前时间
        if old_inventory_stock != item.inventory_stock:
            now = timezone.now()
            if item.inventory_stock == FinishProduct.INVENTORY_IN:
                if not item.stock_in_time:
                    item.stock_in_time = now
            elif item.inventory_stock in (
                FinishProduct.INVENTORY_OUT_SALE,
                FinishProduct.INVENTORY_OUT_DEV,
            ):
                if not item.stock_out_time:
                    item.stock_out_time = now

        if item.inventory_stock in (
            FinishProduct.INVENTORY_IN,
            FinishProduct.INVENTORY_OUT_SALE,
            FinishProduct.INVENTORY_OUT_DEV,
        ):
            if not item.sn_code:
                return JsonResponse(
                    {"code": "400", "msg": "入库或出库前必须先填写SN码"}
                )
            if item.status != FinishProduct.STATUS_PASS:
                return JsonResponse(
                    {"code": "400", "msg": "入库或出库时，测试状态必须为测试合格"}
                )
        elif item.inventory_stock == FinishProduct.INVENTORY_CONSUME:
            # 组件消耗状态：需要SN码，但不需要测试合格
            if not item.sn_code:
                return JsonResponse(
                    {"code": "400", "msg": "组件消耗状态必须填写SN码"}
                )

        inventory_action = None
        warehouse_log_type = None
        if old_inventory_stock != item.inventory_stock:
            if item.inventory_stock == FinishProduct.INVENTORY_IN:
                # 如果是从组件消耗变为入库，需要恢复库存
                if old_inventory_stock == FinishProduct.INVENTORY_CONSUME:
                    inventory_action = "in"
                    warehouse_log_type = WarehouseLog.STORAGE_IN
                else:
                    inventory_action = "in"
                    warehouse_log_type = WarehouseLog.STORAGE_IN
            elif item.inventory_stock in (FinishProduct.INVENTORY_OUT_SALE, FinishProduct.INVENTORY_OUT_DEV):
                inventory_action = "out"
                if item.inventory_stock == FinishProduct.INVENTORY_OUT_DEV:
                    warehouse_log_type = WarehouseLog.STORAGE_OUT_RANDD
                else:
                    warehouse_log_type = WarehouseLog.STORAGE_OUT_SALE
            # 变为组件消耗状态：减少库存
            elif item.inventory_stock == FinishProduct.INVENTORY_CONSUME:
                inventory_action = "out"
                warehouse_log_type = WarehouseLog.STORAGE_OUT_SALE
            # 变为未入库状态：如果之前是入库状态，需要记录出库日志
            elif item.inventory_stock == FinishProduct.INVENTORY_NOT_IN:
                if old_inventory_stock == FinishProduct.INVENTORY_IN:
                    # 从入库变为未入库，记录出库日志
                    inventory_action = "out"
                    warehouse_log_type = WarehouseLog.STORAGE_OUT_SALE
                elif old_inventory_stock == FinishProduct.INVENTORY_CONSUME:
                    pass  # 组件消耗已减少过一次
            # 从组件消耗变为其他状态（非入库/出库/组件消耗/未入库）：库存不变
            elif old_inventory_stock == FinishProduct.INVENTORY_CONSUME:
                pass

        if old_parent_sn_code != item.parent_sn_code:
            # 组件消耗状态的关节，不因为父级SN码变化而额外触发库存操作
            # 但如果库存状态不是组件消耗，才执行原有的逻辑
            if item.inventory_stock != FinishProduct.INVENTORY_CONSUME:
                if item.inventory_stock == FinishProduct.INVENTORY_IN:
                    if old_parent_sn_code is None and item.parent_sn_code:
                        inventory_action = "out"
                    elif old_parent_sn_code and item.parent_sn_code is None:
                        inventory_action = "in"

        if inventory_action:
            try:
                bom = BomList.objects.get(id=item.bom_id, is_del=0)
            except BomList.DoesNotExist:
                return JsonResponse({"code": "400", "msg": "关联 BOM 不存在，无法同步库存"})

            # 查看同步前的库存
            if bom.material_code:
                pre_product = Product.objects.filter(material_code=bom.material_code, is_del=0).first()
                pre_qty = pre_product.quantity if pre_product else "N/A"
            else:
                pre_qty = "无material_code"

            logger.info(
                "[解除绑定-库存操作] finish_product_id=%s, inventory_action=%s, warehouse_log_type=%s, material_code=%s, 同步前库存=%s",
                item.id, inventory_action, warehouse_log_type, bom.material_code, pre_qty,
            )

            with transaction.atomic():
                _sync_product_inventory(bom, inventory_action)
                
                if warehouse_log_type:
                    user_desc = (body.get("warehouse_log_description") or body.get("warehouseLogDescription") or "").strip()
                    action_desc = '入库' if inventory_action == 'in' else '出库'
                    
                    # 状态名称映射
                    stock_status_names = {
                        FinishProduct.INVENTORY_NOT_IN: '未入库',
                        FinishProduct.INVENTORY_IN: '入库',
                        FinishProduct.INVENTORY_OUT_SALE: '出库(外销)',
                        FinishProduct.INVENTORY_OUT_DEV: '出库(研发)',
                        FinishProduct.INVENTORY_CONSUME: '组件消耗',
                    }
                    old_status_name = stock_status_names.get(old_inventory_stock, str(old_inventory_stock))
                    new_status_name = stock_status_names.get(item.inventory_stock, str(item.inventory_stock))
                    
                    base_desc = f"BOM: {bom.bom_model or ''} {bom.bom_name or ''}, 操作: {action_desc} ({old_status_name} → {new_status_name})"
                    if user_desc:
                        full_desc = f"{base_desc} | {user_desc}"
                    else:
                        full_desc = base_desc
                    
                    # 构建操作详情
                    operation_detail = {
                        'action': action_desc,
                        'product_name': item.name,
                        'sn_code': item.sn_code,
                        'bom_id': bom.id,
                        'bom_name': bom.bom_name,
                        'bom_model': bom.bom_model,
                        'material_code': bom.material_code,
                        'old_stock_status': old_inventory_stock,
                        'old_stock_status_name': old_status_name,
                        'new_stock_status': item.inventory_stock,
                        'new_stock_status_name': new_status_name,
                    }
                    
                    # 使用新的日志记录逻辑
                    create_warehouse_log(
                        request=request,
                        storage_status=warehouse_log_type,
                        name=bom.bom_name or bom.bom_model or item.name,
                        sn_code=item.sn_code or "",
                        material_code=bom.material_code or "",
                        count=1,
                        description=full_desc,
                        module='finish_product',
                        action_type=f'product_{inventory_action}',
                        operation_detail=[operation_detail],
                    )

        item.update_time = timezone.now()
        item.save()

        after_data = _serialize_finish_product(item)
        _log_finish_product_operation(
            request, item, FinishedProductLog.OPERATION_UPDATE,
            before_data=before_data, after_data=after_data,
            description=f"修改成品：{item.sn_code or item.name}",
        )

        logger.info(
            "[解除绑定-完成] finish_product_id=%s, sn_code=%s, inventory_stock: %s → %s, parent_sn_code: %s → %s, inventory_action=%s",
            item.id, item.sn_code, old_inventory_stock, item.inventory_stock,
            old_parent_sn_code, item.parent_sn_code, inventory_action,
        )

        return JsonResponse(
            {
                "code": "00000",
                "msg": "更新成功",
                "data": _serialize_finish_product(item),
            }
        )
    except FinishProduct.DoesNotExist:
        return JsonResponse({"code": "404", "msg": "成品不存在"})
    except BomList.DoesNotExist:
        return JsonResponse({"code": "400", "msg": "关联 BOM 不存在"})
    except ValueError as e:
        return JsonResponse({"code": "400", "msg": str(e)})
    except (TypeError, ValueError):
        return JsonResponse({"code": "400", "msg": "参数格式错误"})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"更新失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["GET"])
def check_joint_stock_consistency(request):
    """检查关节库存数量与成品关节数量是否一致
    
    规则：
    - 库存关节数量（Product.type=4）应等于合格成品关节数量（测试通过+在库+无父级）
    - 绑定在机械臂上的关节（有parent_sn_code）不计入库存
    """
    try:
        from apps.product.products.models import Product
        from apps.product.products.constants import PRODUCT_TYPE_JOINT, PRODUCT_TYPE_ROBOT_ARM
        from apps.product.boms.models import BomList
        from django.db import models
        
        # 获取关节和机械臂的BOM ID列表
        joint_bom_ids = list(BomList.objects.filter(
            type=BomList.TYPE_JOINT,  # 0=关节
            is_del=0
        ).values_list('id', flat=True))
        
        robot_bom_ids = list(BomList.objects.filter(
            type=BomList.TYPE_ROBOT_ARM,  # 1=机械臂
            is_del=0
        ).values_list('id', flat=True))
        
        # ===== 关节统计 =====
        # 产品表中关节的总库存（通过 quantity 字段）
        product_joint_stock = Product.objects.filter(
            type=PRODUCT_TYPE_JOINT,
            is_del=0
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        
        # 成品表中符合条件的关节数量：测试合格 + 入库 + 无父级SN码（排除已回退）
        finish_joint_stock = FinishProduct.active_queryset().filter(
            bom_id__in=joint_bom_ids,
            parent_sn_code__isnull=True,
            status=FinishProduct.STATUS_PASS,  # 2=测试合格
            inventory_stock=FinishProduct.INVENTORY_IN,  # 1=入库
        ).count()

        # 绑定在机械臂上的关节数量（有parent_sn_code，排除已回退）
        bound_joint_count = FinishProduct.active_queryset().filter(
            bom_id__in=joint_bom_ids,
            parent_sn_code__isnull=False,
        ).count()
        
        # ===== 机械臂统计 =====
        product_robot_stock = Product.objects.filter(
            type=PRODUCT_TYPE_ROBOT_ARM,
            is_del=0
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        
        finish_robot_stock = FinishProduct.active_queryset().filter(
            bom_id__in=robot_bom_ids,
            parent_sn_code__isnull=True,
            status=FinishProduct.STATUS_PASS,
            inventory_stock=FinishProduct.INVENTORY_IN,
        ).count()
        
        # ===== 判断一致性 =====
        # 关节：产品表库存 + 绑定数量 = 成品表中测试合格+入库+无父级 的数量？
        # 实际上：产品表库存应该等于成品表中在库的数量（无父级）
        joint_consistent = product_joint_stock == finish_joint_stock
        robot_consistent = product_robot_stock == finish_robot_stock
        
        is_consistent = joint_consistent and robot_consistent
        
        return JsonResponse({
            "code": "00000",
            "msg": "成功",
            "data": {
                "joint": {
                    "product_stock": product_joint_stock,
                    "finish_stock": finish_joint_stock,
                    "bound_count": bound_joint_count,
                    "is_consistent": joint_consistent,
                },
                "robot": {
                    "product_stock": product_robot_stock,
                    "finish_stock": finish_robot_stock,
                    "is_consistent": robot_consistent,
                },
                "is_consistent": is_consistent,
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"code": "500", "msg": f"检查失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["POST"])
def rollback_finish_product(request):
    """成品回退：删除成品记录，并按 BOM 配方恢复对应零件库存"""
    try:
        body = json.loads(request.body or "{}")
        item_id = body.get("id")
        if not item_id:
            return JsonResponse({"code": "400", "msg": "缺少成品 ID"})

        item_snapshot = None
        restored_details = []
        restored_items = []

        with transaction.atomic():
            item = FinishProduct.objects.select_for_update().get(id=int(item_id))

            # 已回退的成品不能重复回退
            if item.cons_status == FinishProduct.CONS_STATUS_ROLLED_BACK:
                return JsonResponse({"code": "400", "msg": "该成品已回退，不能重复回退"})

            # 记录回退前的库存状态，用于后续同步
            old_inventory_stock = item.inventory_stock
            old_parent_sn_code = item.parent_sn_code

            item_snapshot = {
                "id": item.id,
                "sn_code": item.sn_code or "",
                "name": item.name,
                "bom_id": item.bom_id,
                "inventory_stock": old_inventory_stock,
                "parent_sn_code": old_parent_sn_code,
                "cons_status": item.cons_status,
            }

            before_data_rollback = _serialize_finish_product(item)

            if not BomList.objects.filter(id=item.bom_id, is_del=0).exists():
                return JsonResponse({"code": "400", "msg": "关联 BOM 不存在，无法回退"})

            # 获取BOM信息，用于后续成品库存同步
            bom = BomList.objects.get(id=item.bom_id, is_del=0)

            recipes = list(AssemblyRecipe.objects.filter(bom_id=item.bom_id).order_by("id"))
            if not recipes:
                return JsonResponse({"code": "400", "msg": "该 BOM 暂无零件明细，无法回退"})

            # 直接使用绑定的产品 ID（流程上禁止删除被引用产品，无需 material_code 回退）

            # 按 cons_status 决定是否恢复物料：
            # 0=组装已扣料 → 恢复；1=组装未扣料 → 不恢复；NULL=历史数据 → 按原逻辑恢复
            restore_materials = item.cons_status in (
                None, FinishProduct.CONS_STATUS_CONSUMED,
            )

            if restore_materials:
                for recipe in recipes:
                    part = _recipe_part_info(recipe)
                    bind_id = part["product_id"]
                    if not bind_id:
                        continue
                    per_unit = part["quantity"] or 0
                    if per_unit < 1:
                        raise ValueError(f"零件「{part['product_name']}」用量无效")

                    # 直接使用绑定的产品 ID
                    eff_id = bind_id
                    product = Product.objects.select_for_update().get(id=eff_id, is_del=0)
                    before_qty = product.quantity if product.quantity is not None else 0
                    product.quantity = before_qty + per_unit
                    product.save(update_fields=["quantity", "updated_at"])

                    restored_details.append(f"{product.name} +{per_unit}")
                    restored_items.append(
                        {
                            "product_id": product.id,
                            "product_name": product.name,
                            "before_quantity": before_qty,
                            "after_quantity": product.quantity,
                            "delta": per_unit,
                        }
                    )

            # 同步成品库存到产品表
            # 如果成品是入库状态，删除时需要减少产品库存
            if old_inventory_stock == FinishProduct.INVENTORY_IN:
                if bom.material_code:
                    try:
                        product = Product.objects.select_for_update().get(
                            material_code=bom.material_code, is_del=0
                        )
                        current = product.quantity if product.quantity is not None else 0
                        product.quantity = current - 1
                        product.save(update_fields=["quantity", "updated_at"])
                        logger.info(
                            "[回退-库存同步] 产品 %s 库存 %s → %s (成品已删除)",
                            bom.material_code, current, product.quantity
                        )
                    except Product.DoesNotExist:
                        pass
            
            # 如果成品是组件消耗状态，删除时需要恢复产品库存
            elif old_inventory_stock == FinishProduct.INVENTORY_CONSUME:
                if bom.material_code:
                    try:
                        product = Product.objects.select_for_update().get(
                            material_code=bom.material_code, is_del=0
                        )
                        current = product.quantity if product.quantity is not None else 0
                        product.quantity = current + 1
                        product.save(update_fields=["quantity", "updated_at"])
                        logger.info(
                            "[回退-库存同步] 产品 %s 库存 %s → %s (组件消耗成品已删除, 恢复库存)",
                            bom.material_code, current, product.quantity
                        )
                    except Product.DoesNotExist:
                        Product.objects.create(
                            name=bom.bom_name or bom.bom_model,
                            type=4 if bom.type == 0 else 5 if bom.type == 1 else 2,
                            material_code=bom.material_code,
                            quantity=1,
                            procurement_cycle=1,
                            is_del=0,
                        )

            # 回退不删除记录，仅标记为已回退
            item.cons_status = FinishProduct.CONS_STATUS_ROLLED_BACK
            item.save(update_fields=["cons_status"])

        _log_if_available(
            request,
            module="finishProduct",
            module_name="成品管理",
            operation_type="rollback",
            target_id=item_snapshot["id"],
            target_name=item_snapshot["name"],
            before_data=item_snapshot,
            after_data={"restored": restored_items},
            description=format_finish_product_rollback_description(
                item_snapshot["name"],
                item_snapshot["sn_code"],
                restored_details,
            ),
        )

        _log_finish_product_operation(
            request, None, FinishedProductLog.OPERATION_ROLLBACK,
            before_data=before_data_rollback, after_data=None,
            description=format_finish_product_rollback_description(
                item_snapshot["name"],
                item_snapshot["sn_code"],
                restored_details,
            ),
        )

        if not restore_materials:
            msg = "回退成功（组装未扣料，无需恢复零件），成品已标记为已回退"
        elif restored_details:
            msg = f"回退成功，已恢复零件库存（共{len(restored_details)}项），成品已标记为已回退"
        else:
            msg = "回退成功，成品已标记为已回退"

        return JsonResponse(
            {
                "code": "00000",
                "msg": msg,
                "data": {
                    "id": item_snapshot["id"],
                    "restored": restored_details,
                },
            }
        )
    except FinishProduct.DoesNotExist:
        return JsonResponse({"code": "404", "msg": "成品不存在"})
    except Product.DoesNotExist:
        return JsonResponse({"code": "400", "msg": "BOM 关联的零件不存在，无法回退"})
    except ValueError as e:
        return JsonResponse({"code": "400", "msg": str(e)})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"回退失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["GET"])
def warehouse_log_list(request):
    """库存操作日志列表（支持多条件筛选）"""
    try:
        sn_code = (request.GET.get("sn_code") or "").strip()
        material_code = (request.GET.get("material_code") or "").strip()
        storage_status = request.GET.get("storage_status")
        module = (request.GET.get("module") or "").strip()
        operator_name = (request.GET.get("operator_name") or "").strip()
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        
        from core.pagination import parse_page_params
        page_num, page_size = parse_page_params(request, default_size=20)

        qs = WarehouseLog.objects.all()
        
        if sn_code:
            qs = qs.filter(sn_code__icontains=sn_code)
        if material_code:
            qs = qs.filter(material_code__icontains=material_code)
        if storage_status:
            try:
                status_val = int(storage_status)
                qs = qs.filter(storage_status=status_val)
            except (TypeError, ValueError):
                pass
        if module:
            qs = qs.filter(module=module)
        if operator_name:
            qs = qs.filter(operator_name__icontains=operator_name)
        if start_date or end_date:
            # 用本地时区全天范围比较，避免 __date 查询依赖 MySQL 时区表（未加载时 CONVERT_TZ 返回 NULL 导致结果为空）
            start_day = _parse_date_param(start_date)
            end_day = _parse_date_param(end_date)
            if start_day and end_day and start_day > end_day:
                start_day, end_day = end_day, start_day
            if not start_day:
                start_day = end_day
            if not end_day:
                end_day = start_day
            range_start, range_end = local_day_range_datetimes(start_day, end_day)
            qs = qs.filter(created_at__gte=range_start, created_at__lte=range_end)

        total = qs.count()
        start = (page_num - 1) * page_size
        items = list(qs.order_by("-created_at")[start : start + page_size])
        
        data = [{
            "id": item.id,
            "name": item.name,
            "sn_code": item.sn_code,
            "material_code": item.material_code,
            "storage_status": item.storage_status,
            "storage_status_name": item.get_storage_status_display(),
            "count": item.count,
            "description": item.description,
            "operator_id": item.operator_id,
            "operator_name": item.operator_name,
            "module": item.module,
            "module_name": item.get_module_display() if hasattr(item, 'get_module_display') else item.module,
            "action_type": item.action_type,
            "operation_detail": item.operation_detail,
            "created_at": format_local_datetime(item.created_at),
        } for item in items]
        
        return JsonResponse({
            "code": "00000",
            "msg": "成功",
            "data": {
                "list": data,
                "total": total,
                "pageNum": page_num,
                "pageSize": page_size,
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"code": "500", "msg": f"获取库存操作日志失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["GET"])
def bindable_joints(request):
    """返回全部可绑定关节（不分页）。

    可绑定条件：bom_type=0（关节）、status=2（测试通过）、inventory_stock=1（已入库）、
    parent_sn_code 为空（未绑定）、sn_code 非空。
    专用接口，避免 finish_product_list 的 max_page_size=100 截断导致漏关节。
    """
    # 仅取关节对应的 BOM（type=0）
    joint_bom_ids = list(
        BomList.objects.filter(type=0, is_del=0).values_list("id", flat=True)
    )
    if not joint_bom_ids:
        return JsonResponse({"code": "00000", "msg": "成功", "data": {"list": []}})

    qs = (
        FinishProduct.objects.filter(
            bom_id__in=joint_bom_ids,
            status=FinishProduct.STATUS_PASS,
            inventory_stock=FinishProduct.INVENTORY_IN,
        )
        .filter(Q(parent_sn_code="") | Q(parent_sn_code__isnull=True))
        .exclude(sn_code__isnull=True)
        .exclude(sn_code="")
        # 已回退的关节不可绑定
        .exclude(cons_status=FinishProduct.CONS_STATUS_ROLLED_BACK)
        .order_by("-id")
    )

    items = list(qs)
    bom_ids = {item.bom_id for item in items if item.bom_id}
    bom_map = {bom.id: bom for bom in BomList.objects.filter(id__in=bom_ids, is_del=0)} if bom_ids else {}

    return JsonResponse(
        {
            "code": "00000",
            "msg": "成功",
            "data": {
                "list": [_serialize_finish_product(item, bom_map) for item in items],
                "total": len(items),
            },
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def bind_joints_to_arm(request):
    """批量绑定多个关节到指定机械臂"""
    try:
        body = json.loads(request.body or "{}")
        arm_id = body.get("arm_id")
        arm_sn_code = (body.get("arm_sn_code") or "").strip()
        joint_ids = body.get("joint_ids") or []

        if not arm_id:
            return JsonResponse({"code": "400", "msg": "缺少机械臂 ID"})
        if not arm_sn_code:
            return JsonResponse({"code": "400", "msg": "缺少机械臂 SN码"})
        if not joint_ids:
            return JsonResponse({"code": "400", "msg": "请至少选择一个关节"})

        # 验证机械臂
        try:
            arm = FinishProduct.objects.get(id=int(arm_id))
        except FinishProduct.DoesNotExist:
            return JsonResponse({"code": "400", "msg": "机械臂不存在"})
        if arm.cons_status == FinishProduct.CONS_STATUS_ROLLED_BACK:
            return JsonResponse({"code": "400", "msg": "该机械臂已回退，不可绑定关节"})

        try:
            arm_bom = BomList.objects.get(id=arm.bom_id, is_del=0)
            if arm_bom.type != 1:
                return JsonResponse({"code": "400", "msg": "目标不是机械臂类型"})
        except BomList.DoesNotExist:
            return JsonResponse({"code": "400", "msg": "机械臂关联的BOM不存在"})

        bound_count = 0
        errors = []
        bound_joints_info = []  # 收集绑定的关节信息用于日志

        with transaction.atomic():
            for joint_id in joint_ids:
                try:
                    joint = FinishProduct.objects.select_for_update().get(id=int(joint_id))

                    before_joint_data = _serialize_finish_product(joint)

                    # 验证关节类型
                    try:
                        joint_bom = BomList.objects.get(id=joint.bom_id, is_del=0)
                        if joint_bom.type != 0:
                            errors.append(f"ID={joint_id} 不是关节类型，已跳过")
                            continue
                    except BomList.DoesNotExist:
                        errors.append(f"ID={joint_id} 关联的BOM不存在，已跳过")
                        continue

                    # 已绑定的跳过
                    if joint.parent_sn_code:
                        errors.append(f"SN={joint.sn_code or '无SN'} 已有父级，已跳过")
                        continue

                    # 已回退的关节不可绑定
                    if joint.cons_status == FinishProduct.CONS_STATUS_ROLLED_BACK:
                        errors.append(f"SN={joint.sn_code or '无SN'} 已回退，已跳过")
                        continue

                    # 记录绑定前的状态
                    old_inventory = joint.inventory_stock
                    before_quantity = 0
                    if joint_bom.material_code:
                        try:
                            product = Product.objects.get(material_code=joint_bom.material_code, is_del=0)
                            before_quantity = product.quantity or 0
                        except Product.DoesNotExist:
                            pass

                    # 设置父级SN码和库存状态
                    joint.parent_sn_code = arm_sn_code
                    joint.inventory_stock = FinishProduct.INVENTORY_CONSUME

                    # 同步库存：如果之前是入库状态，减少库存
                    if old_inventory == FinishProduct.INVENTORY_IN:
                        try:
                            product = Product.objects.select_for_update().get(
                                material_code=joint_bom.material_code, is_del=0
                            )
                            current = product.quantity if product.quantity is not None else 0
                            product.quantity = current - 1
                            product.save(update_fields=["quantity", "updated_at"])
                        except Product.DoesNotExist:
                            pass

                    joint.save()
                    bound_count += 1

                    after_joint_data = _serialize_finish_product(joint)
                    _log_finish_product_operation(
                        request, joint, FinishedProductLog.OPERATION_BIND_JOINT,
                        before_data=before_joint_data, after_data=after_joint_data,
                        description=f"绑定关节到机械臂 {arm_sn_code}",
                    )

                    # 收集绑定的关节信息
                    bound_joints_info.append({
                        'joint_id': joint.id,
                        'joint_name': joint.name,
                        'joint_sn_code': joint.sn_code,
                        'joint_bom_id': joint.bom_id,
                        'joint_material_code': joint_bom.material_code,
                        'old_inventory_status': old_inventory,
                        'new_inventory_status': FinishProduct.INVENTORY_CONSUME,
                        'before_product_quantity': before_quantity,
                        'after_product_quantity': before_quantity - 1 if old_inventory == FinishProduct.INVENTORY_IN else before_quantity,
                    })

                except FinishProduct.DoesNotExist:
                    errors.append(f"ID={joint_id} 不存在，已跳过")
                except Exception as e:
                    errors.append(f"ID={joint_id} 绑定失败: {str(e)}")

        # 记录一条日志，包含所有绑定的关节信息
        if bound_joints_info:
            log_inventory_operation(
                request=request,
                operation_type='bind_joint',
                products=[{
                    'name': info['joint_name'],
                    'sn_code': info['joint_sn_code'],
                    'material_code': info['joint_material_code'],
                    'quantity_change': -1 if info['old_inventory_status'] == FinishProduct.INVENTORY_IN else 0,
                    'before_stock': info['before_product_quantity'],
                    'after_stock': info['after_product_quantity'],
                    'details': info,
                } for info in bound_joints_info],
                module='finish_product',
                description=f"绑定 {bound_count} 个关节到机械臂 {arm_sn_code}",
                extra_details={
                    'arm_id': arm_id,
                    'arm_sn_code': arm_sn_code,
                    'errors': errors,
                }
            )

        result = {"bound_count": bound_count}
        if errors:
            result["errors"] = errors

        return JsonResponse({
            "code": "00000",
            "msg": "绑定成功",
            "data": result,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"code": "500", "msg": f"绑定失败: {str(e)}"})


# ==================== 成品操作记录 API ====================


@csrf_exempt
@require_http_methods(["GET"])
def finished_product_log_list(request):
    """成品操作记录列表（支持按变更字段筛选）"""
    from core.pagination import parse_page_params

    page_num, page_size = parse_page_params(request, default_size=20)

    sn_code = (request.GET.get("sn_code") or "").strip()
    operation_type = (request.GET.get("operation_type") or "").strip()
    operator_name = (request.GET.get("operator_name") or "").strip()
    changed_field = (request.GET.get("changed_field") or "").strip()
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    # 变更前/变更后字段值筛选参数
    before_field = (request.GET.get("before_field") or "").strip()
    before_match = (request.GET.get("before_match") or "").strip()
    after_field = (request.GET.get("after_field") or "").strip()
    after_match = (request.GET.get("after_match") or "").strip()

    # JSON 快照中的枚举字段（值为数字，需精确匹配）
    json_enum_fields = {"status", "inventory_stock", "repair", "bom_type"}

    def _apply_value_filter(queryset, json_prefix, field, match):
        """按 before_data/after_data 中指定字段的值筛选：枚举精确匹配，文本模糊匹配"""
        if not field or match == "" or field not in TRACKABLE_FIELDS:
            return queryset
        if field in json_enum_fields:
            try:
                num = int(match)
            except (TypeError, ValueError):
                return queryset.none()
            return queryset.filter(**{f"{json_prefix}__{field}": num})
        return queryset.filter(**{f"{json_prefix}__{field}__icontains": match})

    qs = FinishedProductLog.objects.all()
    if sn_code:
        qs = qs.filter(sn_code__icontains=sn_code)
    if operation_type:
        qs = qs.filter(operation_type=operation_type)
    if operator_name:
        qs = qs.filter(operator_name__icontains=operator_name)
    if changed_field:
        qs = qs.filter(changed_fields__contains=changed_field)
    qs = _apply_value_filter(qs, "before_data", before_field, before_match)
    qs = _apply_value_filter(qs, "after_data", after_field, after_match)
    if start_date or end_date:
        start_day = parse_local_datetime_text(start_date) if start_date else None
        end_day = parse_local_datetime_text(end_date) if end_date else None
        if start_day and end_day:
            range_start, range_end = local_day_range_datetimes(start_day, end_day)
            qs = qs.filter(create_time__gte=range_start, create_time__lte=range_end)
        elif start_day:
            range_start = make_local_aware(datetime.combine(start_day, datetime.min.time()))
            qs = qs.filter(create_time__gte=range_start)
        elif end_day:
            range_end = make_local_aware(datetime.combine(end_day, datetime.max.time()))
            qs = qs.filter(create_time__lte=range_end)

    total = qs.count()
    start = (page_num - 1) * page_size
    items = list(qs.order_by("-create_time", "-id")[start:start + page_size])

    list_data = []
    for log in items:
        list_data.append({
            "id": log.id,
            "finishProductId": log.finish_product_id,
            "snCode": log.sn_code,
            "operationType": log.operation_type,
            "operationTypeName": log.get_operation_type_display(),
            "operatorId": log.operator_id,
            "operatorName": log.operator_name,
            "beforeData": log.before_data,
            "afterData": log.after_data,
            "changedFields": log.changed_fields,
            "description": log.description,
            "ip": log.ip,
            "createTime": format_local_datetime(log.create_time) or "",
        })

    return JsonResponse({
        "code": "00000",
        "msg": "成功",
        "data": {"list": list_data, "total": total},
    })


# ==================== 不合格项 API ====================

from .models import UnqualifiedItem


@csrf_exempt
@require_http_methods(["GET"])
def list_unqualified_items(request):
    """获取成品的不合格项列表"""
    try:
        finish_product_id = request.GET.get("finish_product_id")
        sn_code = (request.GET.get("sn_code") or "").strip()

        qs = UnqualifiedItem.objects.all()
        if finish_product_id:
            qs = qs.filter(finish_product_id=int(finish_product_id))
        if sn_code:
            qs = qs.filter(sn_code=sn_code)

        items = list(qs.order_by("-create_time"))

        # 查询字典项信息
        unqualified_values = list(set(item.unqualified_value for item in items))
        dict_items = {}
        if unqualified_values:
            # DictionaryItem.value 是 CharField，需要转为字符串查询
            str_values = [str(v) for v in unqualified_values]
            dict_item_list = DictionaryItem.objects.filter(
                dict_code="unqualified_status",
                value__in=str_values,
                status=1,
            )
            for di in dict_item_list:
                try:
                    dict_items[int(di.value)] = di.label
                except (ValueError, TypeError):
                    dict_items[di.value] = di.label

        data = [{
            "id": item.id,
            "finish_product_id": item.finish_product_id,
            "sn_code": item.sn_code,
            "unqualified_value": item.unqualified_value,
            "unqualified_label": dict_items.get(item.unqualified_value, f"未知({item.unqualified_value})"),
            "create_time": format_local_datetime(item.create_time),
        } for item in items]

        return JsonResponse({
            "code": "00000",
            "msg": "成功",
            "data": data,
        })
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"获取不合格项失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["POST"])
def save_unqualified_items(request):
    """保存成品的不合格项（覆盖保存：先删除旧的，再创建新的）"""
    try:
        body = json.loads(request.body or "{}")
        finish_product_id = body.get("finish_product_id")
        sn_code = (body.get("sn_code") or "").strip()
        unqualified_values = body.get("unqualified_values") or []

        if not finish_product_id:
            return JsonResponse({"code": "400", "msg": "缺少成品 ID"})

        # 验证成品存在
        try:
            product = FinishProduct.objects.get(id=int(finish_product_id))
        except FinishProduct.DoesNotExist:
            return JsonResponse({"code": "404", "msg": "成品不存在"})
        if product.cons_status == FinishProduct.CONS_STATUS_ROLLED_BACK:
            return JsonResponse({"code": "400", "msg": "该成品已回退，不可维护不良详情"})

        # 快照变更前不良项（用于操作日志）
        before_items = _snapshot_unqualified_items(int(finish_product_id))

        # 如果成品不是测试不良状态，清空不合格项
        if product.status != FinishProduct.STATUS_FAIL:
            UnqualifiedItem.objects.filter(finish_product_id=int(finish_product_id)).delete()
            after_items = _snapshot_unqualified_items(int(finish_product_id))
            _log_unqualified_operation(
                request, product.id, product.sn_code or "",
                before_items, after_items, "成品非测试不良状态，不良详情已清空",
            )
            return JsonResponse({
                "code": "00000",
                "msg": "成功",
                "data": [],
            })

        # 预查询字典标签
        dict_labels = {}
        if unqualified_values:
            str_values = list(set(str(int(v)) for v in unqualified_values))
            for di in DictionaryItem.objects.filter(
                dict_code="unqualified_status",
                value__in=str_values,
                status=1,
            ):
                try:
                    dict_labels[int(di.value)] = di.label
                except (ValueError, TypeError):
                    pass

        # 去重
        unique_values = list(set(int(v) for v in unqualified_values))

        with transaction.atomic():
            # 先删除旧的不合格项
            UnqualifiedItem.objects.filter(finish_product_id=int(finish_product_id)).delete()

            # 创建新的不合格项
            created_items = []
            for value in unique_values:
                item = UnqualifiedItem.objects.create(
                    finish_product_id=int(finish_product_id),
                    sn_code=sn_code or product.sn_code or "",
                    unqualified_value=value,
                )
                created_items.append({
                    "id": item.id,
                    "finish_product_id": item.finish_product_id,
                    "sn_code": item.sn_code,
                    "unqualified_value": item.unqualified_value,
                    "unqualified_label": dict_labels.get(value, f"未知({value})"),
                    "create_time": format_local_datetime(item.create_time),
                })

        # 记录不良详情操作日志
        after_items = _snapshot_unqualified_items(int(finish_product_id))
        _log_unqualified_operation(
            request, product.id, product.sn_code or "",
            before_items, after_items,
            "保存不良详情: " + ("、".join(i["label"] for i in after_items) or "（空）"),
        )

        return JsonResponse({
            "code": "00000",
            "msg": "保存成功",
            "data": created_items,
        })
    except ValueError:
        return JsonResponse({"code": "400", "msg": "参数格式错误"})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"保存不合格项失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["POST"])
def delete_unqualified_item(request):
    """删除单个不合格项"""
    try:
        body = json.loads(request.body or "{}")
        item_id = body.get("id")

        if not item_id:
            return JsonResponse({"code": "400", "msg": "缺少不合格项 ID"})

        try:
            item = UnqualifiedItem.objects.get(id=int(item_id))
        except UnqualifiedItem.DoesNotExist:
            return JsonResponse({"code": "404", "msg": "不合格项不存在"})

        # 快照并记录删除操作日志
        fp_id = item.finish_product_id
        before_items = _snapshot_unqualified_items(fp_id)
        deleted_label = next(
            (i["label"] for i in before_items if i["value"] == item.unqualified_value),
            f"未知({item.unqualified_value})",
        )
        item.delete()
        after_items = _snapshot_unqualified_items(fp_id)
        _log_unqualified_operation(
            request, fp_id, item.sn_code or "",
            before_items, after_items, f"删除不良项: {deleted_label}",
        )

        return JsonResponse({
            "code": "00000",
            "msg": "删除成功",
        })
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"删除不合格项失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["POST"])
def add_unqualified_item(request):
    """添加单个不合格项"""
    try:
        body = json.loads(request.body or "{}")
        finish_product_id = body.get("finish_product_id")
        sn_code = (body.get("sn_code") or "").strip()
        unqualified_value = body.get("unqualified_value")

        if not finish_product_id:
            return JsonResponse({"code": "400", "msg": "缺少成品 ID"})
        if unqualified_value is None:
            return JsonResponse({"code": "400", "msg": "缺少不良项值"})

        # 验证成品存在且为测试不良状态
        try:
            product = FinishProduct.objects.get(id=int(finish_product_id))
        except FinishProduct.DoesNotExist:
            return JsonResponse({"code": "404", "msg": "成品不存在"})
        if product.cons_status == FinishProduct.CONS_STATUS_ROLLED_BACK:
            return JsonResponse({"code": "400", "msg": "该成品已回退，不可添加不良项"})

        if product.status != FinishProduct.STATUS_FAIL:
            return JsonResponse({"code": "400", "msg": "只有测试不良的成品才能添加不合格项"})

        # 检查是否已存在相同的不良项
        if UnqualifiedItem.objects.filter(
            finish_product_id=int(finish_product_id),
            unqualified_value=int(unqualified_value),
        ).exists():
            return JsonResponse({"code": "400", "msg": "该不良项已存在，不可重复添加"})

        # 快照变更前不良项（用于操作日志）
        before_items = _snapshot_unqualified_items(int(finish_product_id))

        item = UnqualifiedItem.objects.create(
            finish_product_id=int(finish_product_id),
            sn_code=sn_code or product.sn_code or "",
            unqualified_value=int(unqualified_value),
        )

        # 查询字典标签
        unqualified_label = f"未知({unqualified_value})"
        try:
            dict_item = DictionaryItem.objects.filter(
                dict_code="unqualified_status",
                value=str(int(unqualified_value)),
                status=1,
            ).first()
            if dict_item:
                unqualified_label = dict_item.label
        except (ValueError, TypeError):
            pass

        # 记录不良详情操作日志
        after_items = _snapshot_unqualified_items(int(finish_product_id))
        _log_unqualified_operation(
            request, product.id, product.sn_code or "",
            before_items, after_items, f"添加不良项: {unqualified_label}",
        )

        return JsonResponse({
            "code": "00000",
            "msg": "添加成功",
            "data": {
                "id": item.id,
                "finish_product_id": item.finish_product_id,
                "sn_code": item.sn_code,
                "unqualified_value": item.unqualified_value,
                "unqualified_label": unqualified_label,
                "create_time": format_local_datetime(item.create_time),
            },
        })
    except ValueError:
        return JsonResponse({"code": "400", "msg": "参数格式错误"})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"添加不合格项失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["GET"])
def joint_test_report(request):
    """关节测试每日报表
    
    参数:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        bom_ids: BOM ID列表，逗号分隔 (可选，默认所有关节类型BOM)
    """
    try:
        start_date_str = (request.GET.get("start_date") or "").strip()
        end_date_str = (request.GET.get("end_date") or "").strip()
        bom_ids_str = (request.GET.get("bom_ids") or "").strip()
        
        if not start_date_str or not end_date_str:
            return JsonResponse({"code": "400", "msg": "请选择日期范围"})
        
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        if start_date > end_date:
            return JsonResponse({"code": "400", "msg": "开始日期不能晚于结束日期"})
        
        # 构建日期列表
        date_list = []
        current = start_date
        while current <= end_date:
            date_list.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        # 获取BOM列表
        if bom_ids_str:
            bom_ids = [int(x.strip()) for x in bom_ids_str.split(",") if x.strip()]
            boms = BomList.objects.filter(id__in=bom_ids, is_del=0)
        else:
            # 默认获取所有BOM
            boms = BomList.objects.filter(is_del=0)
        
        bom_list = list(boms.values("id", "bom_model", "bom_name", "material_code"))
        
        if not bom_list:
            return JsonResponse({
                "code": "00000",
                "msg": "成功",
                "data": {
                    "dates": date_list,
                    "boms": [],
                    "unqualified_items": [],
                    "summary": [],
                    "details": [],
                }
            })
        
        # 获取不合格项字典
        unqualified_items = list(
            DictionaryItem.objects.filter(
                dict_code="unqualified_status",
                status=1,
            ).values("value", "label", "sort")
        )
        # 按sort排序
        unqualified_items.sort(key=lambda x: (x.get("sort") or 0, int(x.get("value", 0))))
        
        # 构建日期查询范围
        start_dt = make_local_aware(datetime.combine(start_date, datetime.min.time()))
        end_dt = make_local_aware(datetime.combine(end_date + timedelta(days=1), datetime.min.time()))
        
        # 查询成品数据（排除已回退）
        products = FinishProduct.active_queryset().filter(
            bom_id__in=[b["id"] for b in bom_list],
            test_time__gte=start_dt,
            test_time__lt=end_dt,
        ).select_related()
        
        # 查询不合格项数据
        unqualified_records = UnqualifiedItem.objects.filter(
            finish_product_id__in=products.values("id"),
        ).select_related()
        
        # 构建产品ID到不合格项的映射
        product_unqualified_map = {}
        for record in unqualified_records:
            pid = record.finish_product_id
            if pid not in product_unqualified_map:
                product_unqualified_map[pid] = []
            product_unqualified_map[pid].append(int(record.unqualified_value))
        
        # 按日期和BOM统计数据
        # 结构: data[date][bom_id] = {test_count, fail_count, unqualified_counts: {value: count}}
        data = {}
        for date_str in date_list:
            data[date_str] = {}
            for bom in bom_list:
                data[date_str][bom["id"]] = {
                    "test_count": 0,
                    "fail_count": 0,
                    "unqualified_counts": {},
                }
        
        # 统计产品数据
        for product in products:
            if product.test_time:
                # 按北京时区取日期，直接对 UTC aware 的 test_time strftime
                # 会把北京 00:00-08:00 的测试归到前一天
                test_date = local_date_key(product.test_time)
                bom_id = product.bom_id
                
                if test_date in data and bom_id in data[test_date]:
                    # 测试数量（包括所有状态）
                    data[test_date][bom_id]["test_count"] += 1
                    
                    # 测试不良
                    if product.status == FinishProduct.STATUS_FAIL:
                        data[test_date][bom_id]["fail_count"] += 1
                    
                    # 不合格项计数
                    if product.id in product_unqualified_map:
                        for unq_val in product_unqualified_map[product.id]:
                            if unq_val not in data[test_date][bom_id]["unqualified_counts"]:
                                data[test_date][bom_id]["unqualified_counts"][unq_val] = 0
                            data[test_date][bom_id]["unqualified_counts"][unq_val] += 1
        
        # 构建汇总数据（按日期）
        summary = []
        for date_str in date_list:
            date_summary = {
                "date": date_str,
                "bom_summaries": {},
                "total_test": 0,
                "total_fail": 0,
            }
            
            for bom in bom_list:
                bom_id = bom["id"]
                day_data = data[date_str][bom_id]
                
                total_test = day_data["test_count"]
                total_fail = day_data["fail_count"]
                pass_count = total_test - total_fail
                pass_rate = round((pass_count / total_test * 100), 1) if total_test > 0 else 0
                
                date_summary["bom_summaries"][bom_id] = {
                    "test_count": total_test if total_test > 0 else None,
                    "fail_count": total_fail if total_fail > 0 else None,
                    "pass_rate": pass_rate if total_test > 0 else None,
                    "unqualified_counts": day_data["unqualified_counts"],
                }
                
                date_summary["total_test"] += total_test
                date_summary["total_fail"] += total_fail
            
            summary.append(date_summary)
        
        # 构建汇总行（所有日期合计）
        total_summary = {}
        for bom in bom_list:
            bom_id = bom["id"]
            total_test = 0
            total_fail = 0
            total_unqualified_counts = {}
            
            for date_str in date_list:
                day_data = data[date_str][bom_id]
                total_test += day_data["test_count"]
                total_fail += day_data["fail_count"]
                
                for unq_val, count in day_data["unqualified_counts"].items():
                    if unq_val not in total_unqualified_counts:
                        total_unqualified_counts[unq_val] = 0
                    total_unqualified_counts[unq_val] += count
            
            pass_count = total_test - total_fail
            pass_rate = round((pass_count / total_test * 100), 1) if total_test > 0 else 0
            
            total_summary[bom_id] = {
                "test_count": total_test if total_test > 0 else None,
                "fail_count": total_fail if total_fail > 0 else None,
                "pass_rate": pass_rate if total_test > 0 else None,
                "unqualified_counts": total_unqualified_counts,
            }
        
        return JsonResponse({
            "code": "00000",
            "msg": "成功",
            "data": {
                "dates": date_list,
                "boms": bom_list,
                "unqualified_items": [
                    {"value": int(item["value"]), "label": item["label"]}
                    for item in unqualified_items
                ],
                "summary": summary,
                "total_summary": total_summary,
            }
        })
    except ValueError as e:
        return JsonResponse({"code": "400", "msg": f"日期格式错误: {str(e)}"})
    except Exception as e:
        logger.error(f"获取关节测试报表失败: {str(e)}", exc_info=True)
        return JsonResponse({"code": "500", "msg": f"获取报表失败: {str(e)}"})
