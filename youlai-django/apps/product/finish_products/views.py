import json
from datetime import datetime, timedelta

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.product.boms.models import AssemblyRecipe, BomList
from apps.product.products.models import Product
from core.datetime import format_local_datetime, local_date_key, local_day_range_datetimes
from core.datetime import make_local_aware, parse_local_datetime_text

from apps.system.operation_logs.utils import format_finish_product_rollback_description

try:
    from apps.system.operation_logs.services import log_operation_from_request

    OPERATION_LOGS_AVAILABLE = True
except ImportError:
    OPERATION_LOGS_AVAILABLE = False

from .models import FinishProduct

VALID_STATUS = {
    FinishProduct.STATUS_UNTESTED,
    FinishProduct.STATUS_TESTING,
    FinishProduct.STATUS_PASS,
    FinishProduct.STATUS_FAIL,
}


def _log_if_available(request, **kwargs):
    if OPERATION_LOGS_AVAILABLE:
        log_operation_from_request(request, **kwargs)


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

    daily_map = {}
    current = start_date
    while current <= end_date:
        daily_map[current.isoformat()] = _empty_daily_bucket(current.isoformat())
        current += timedelta(days=1)

    summary = _empty_daily_bucket("")
    summary.pop("date", None)

    start_dt, end_dt = local_day_range_datetimes(start_date, end_date)

    create_qs = FinishProduct.objects.filter(
        create_time__isnull=False,
        create_time__gte=start_dt,
        create_time__lte=end_dt,
    )

    for item in create_qs:
        day = local_date_key(item.create_time)
        if not day:
            continue
        bucket = daily_map.get(day)
        if not bucket:
            continue

        bucket["newCount"] += 1
        summary["newCount"] += 1

    test_qs = FinishProduct.objects.filter(
        test_time__isnull=False,
        test_time__gte=start_dt,
        test_time__lte=end_dt,
    )
    for item in test_qs:
        _accumulate_test_time_stats(item, daily_map, summary)

    update_qs = FinishProduct.objects.filter(
        update_time__isnull=False,
        update_time__gte=start_dt,
        update_time__lte=end_dt,
    )

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

    stock_in_qs = FinishProduct.objects.filter(
        stock_in_time__isnull=False,
        stock_in_time__gte=start_dt,
        stock_in_time__lte=end_dt,
    )
    for item in stock_in_qs:
        day = local_date_key(item.stock_in_time)
        _increment_daily_count(daily_map, summary, day, "stockInCount")

    stock_out_qs = FinishProduct.objects.filter(
        stock_out_time__isnull=False,
        stock_out_time__gte=start_dt,
        stock_out_time__lte=end_dt,
    )
    for item in stock_out_qs:
        day = local_date_key(item.stock_out_time)
        _increment_daily_count(daily_map, summary, day, "stockOutCount")

    current_stock_in_count = FinishProduct.objects.filter(
        inventory_stock=FinishProduct.INVENTORY_IN
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
    try:
        page_num = int(request.GET.get("pageNum", 1))
    except (TypeError, ValueError):
        page_num = 1
    try:
        page_size = int(request.GET.get("pageSize", 10))
    except (TypeError, ValueError):
        page_size = 10
    if page_num < 1:
        page_num = 1
    if page_size < 1:
        page_size = 10
    return page_num, page_size


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
        "inventory_stock_name": item.get_inventory_stock_display(),
        "repair": item.repair,
        "repair_name": item.get_repair_display(),
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
        return qs.filter(stock_in_time__isnull=False)
    if category == "stockOutCount":
        return qs.filter(stock_out_time__isnull=False)
    if category == "currentStockInCount":
        return qs.filter(inventory_stock=FinishProduct.INVENTORY_IN)
    return qs.none()


def finish_product_board_detail(request):
    """看板统计项对应的成品明细列表"""
    category = (request.GET.get("category") or "").strip()
    if category not in BOARD_DETAIL_CATEGORIES:
        return JsonResponse({"code": "400", "msg": "无效的统计类别"})

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
    qs = _apply_board_category_filter(qs, category)

    if category == "currentStockInCount":
        pass
    elif category == "newCount":
        qs = _apply_field_date_range(qs, "create_time", start_date, end_date)
    elif category in TEST_TIME_STAT_CATEGORIES:
        qs = _apply_field_date_range(qs, "test_time", start_date, end_date)
    elif category == "stockInCount":
        qs = _apply_field_date_range(qs, "stock_in_time", start_date, end_date)
    elif category == "stockOutCount":
        qs = _apply_field_date_range(qs, "stock_out_time", start_date, end_date)
    else:
        qs = _apply_field_date_range(qs, "update_time", start_date, end_date)

    order_fields = ["-create_time", "-id"]
    if category in TEST_TIME_STAT_CATEGORIES:
        order_fields = ["-test_time", "-id"]
    elif category == "stockInCount":
        order_fields = ["-stock_in_time", "-id"]
    elif category == "stockOutCount":
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

    qs = FinishProduct.objects.all()
    if sn_code:
        qs = qs.filter(sn_code__icontains=sn_code)
    if bom_id:
        try:
            qs = qs.filter(bom_id=int(bom_id))
        except (TypeError, ValueError):
            qs = qs.none()
    if status in ("0", "1", "2", "3"):
        qs = qs.filter(status=int(status))
    if inventory_stock in ("0", "1", "2"):
        qs = qs.filter(inventory_stock=int(inventory_stock))
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


@csrf_exempt
@require_http_methods(["POST"])
def update_finish_product(request):
    try:
        body = json.loads(request.body or "{}")
        item_id = body.get("id")
        if not item_id:
            return JsonResponse({"code": "400", "msg": "缺少成品 ID"})

        item = FinishProduct.objects.get(id=int(item_id))

        if "sn_code" in body:
            sn_code = (body.get("sn_code") or "").strip()
            if sn_code and FinishProduct.objects.filter(sn_code=sn_code).exclude(id=item.id).exists():
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

        if "inventory_stock" in body:
            inventory_stock = int(body.get("inventory_stock"))
            valid_inventory = {c[0] for c in FinishProduct.INVENTORY_STOCK_CHOICES}
            if inventory_stock not in valid_inventory:
                return JsonResponse({"code": "400", "msg": "库存状态值无效"})
            item.inventory_stock = inventory_stock

        if "repair" in body:
            repair = int(body.get("repair"))
            valid_repair = {c[0] for c in FinishProduct.REPAIR_CHOICES}
            if repair not in valid_repair:
                return JsonResponse({"code": "400", "msg": "返修状态值无效"})
            item.repair = repair

        if "description" in body:
            item.description = (body.get("description") or "").strip() or None

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

        item.update_time = timezone.now()
        item.save()

        return JsonResponse(
            {
                "code": "00000",
                "msg": "更新成功",
                "data": _serialize_finish_product(item),
            }
        )
    except FinishProduct.DoesNotExist:
        return JsonResponse({"code": "404", "msg": "成品不存在"})
    except (TypeError, ValueError):
        return JsonResponse({"code": "400", "msg": "参数格式错误"})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"更新失败: {str(e)}"})


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
            item_snapshot = {
                "id": item.id,
                "sn_code": item.sn_code or "",
                "name": item.name,
                "bom_id": item.bom_id,
            }

            if not BomList.objects.filter(id=item.bom_id, is_del=0).exists():
                return JsonResponse({"code": "400", "msg": "关联 BOM 不存在，无法回退"})

            recipes = list(AssemblyRecipe.objects.filter(bom_id=item.bom_id).order_by("id"))
            if not recipes:
                return JsonResponse({"code": "400", "msg": "该 BOM 暂无零件明细，无法回退"})

            for recipe in recipes:
                part = _recipe_part_info(recipe)
                product_id = part["product_id"]
                if not product_id:
                    continue
                per_unit = part["quantity"] or 0
                if per_unit < 1:
                    raise ValueError(f"零件「{part['product_name']}」用量无效")

                product = Product.objects.select_for_update().get(id=product_id, is_del=0)
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

            item.delete()

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

        return JsonResponse(
            {
                "code": "00000",
                "msg": "回退成功，成品数据已删除，零件库存已恢复",
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
