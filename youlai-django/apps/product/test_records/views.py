from datetime import datetime

from django.db.models import Max
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.product.finish_products.models import FinishProduct
from apps.system.dicts.models import DictionaryItem
from core.datetime import format_local_datetime, local_day_range_datetimes

from .models import TestRecord

# 测试记录列表可排序字段及类型（排序作用于按SN聚合计后的结果）
TEST_RECORD_SORT_FIELDS = {
    "sn_code": "text",
    "product_model": "text",
    "bom_type": "number",
    "bom_name": "text",
    "test_cnt": "number",
    "unqualified_labels_1": "text",
    "test_desc_1": "text",
    "test_status_1": "number",
    "unqualified_labels_2": "text",
    "test_desc_2": "text",
    "test_status_2": "number",
    "create_time": "text",
    "last_test_time": "text",
}

TEST_STATUS_LABELS = {
    TestRecord.STATUS_PASS: "测试合格",
    TestRecord.STATUS_FAIL: "测试不良",
}


def _parse_date_param(value):
    """解析 YYYY-MM-DD 日期参数"""
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _get_unqualified_label_map():
    """一次性读取不良项字典，避免列表逐条查询数据库"""
    return {
        str(item.value): item.label
        for item in DictionaryItem.objects.filter(
            dict_code="unqualified_status", status=1
        )
    }


def _get_unqualified_labels(values, label_map):
    labels = [
        label_map.get(str(value).strip(), str(value).strip())
        for value in (values or "").split(",")
        if value.strip()
    ]
    return "、".join(labels)


@csrf_exempt
@require_http_methods(["GET"])
def list_test_records(request):
    try:
        sn_code = (request.GET.get("sn_code") or "").strip()
        product_model = (request.GET.get("product_model") or "").strip()
        bom_type = (request.GET.get("bom_type") or "").strip()
        bom_name = (request.GET.get("bom_name") or "").strip()
        test_status_raw = (request.GET.get("test_status") or "").strip()
        test_status = int(test_status_raw) if test_status_raw.isdigit() else None

        start_date = _parse_date_param(
            request.GET.get("start_date") or request.GET.get("startDate")
        )
        end_date = _parse_date_param(
            request.GET.get("end_date") or request.GET.get("endDate")
        )

        try:
            page = int(request.GET.get("page") or 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.GET.get("page_size") or 10)
        except (TypeError, ValueError):
            page_size = 10
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10

        sort_field = (request.GET.get("sort_field") or "").strip()
        sort_order = (request.GET.get("sort_order") or "").strip().lower()

        record_qs = TestRecord.objects.filter(is_del=0)
        # 时间筛选在聚合前过滤，与返修管理口径一致
        if start_date or end_date:
            if start_date and end_date and start_date > end_date:
                record_qs = record_qs.none()
            else:
                range_start = start_date or end_date
                range_end = end_date or start_date
                range_start_dt, range_end_dt = local_day_range_datetimes(range_start, range_end)
                record_qs = record_qs.filter(
                    create_time__gte=range_start_dt,
                    create_time__lte=range_end_dt,
                )

        records = list(record_qs.order_by("create_time"))
        if not records:
            return JsonResponse({
                "code": "00000",
                "msg": "成功",
                "data": {
                    "list": [],
                    "total": 0,
                    "summary": {
                        "total": 0,
                        "first_pass_count": 0,
                        "first_fail_count": 0,
                        "pass_rate": 0,
                    },
                },
            })

        product_ids = {r.product_id for r in records}
        product_map = {
            product.id: product
            for product in FinishProduct.objects.filter(id__in=product_ids)
        }
        bom_ids = {p.bom_id for p in product_map.values() if p.bom_id}
        bom_map = {}
        if bom_ids:
            from apps.product.boms.models import BomList
            bom_map = {
                bom.id: bom
                for bom in BomList.objects.filter(id__in=bom_ids, is_del=0)
            }

        label_map = _get_unqualified_label_map()
        sn_map = {}
        for record in records:
            # 复合 key：product_id + sn_code，避免不同产品空 SN 码被合并
            group_key = (record.product_id, record.sn_code or "")
            if group_key not in sn_map:
                product = product_map.get(record.product_id)
                bom = bom_map.get(product.bom_id) if product else None
                sn_map[group_key] = {
                    "product_id": record.product_id,
                    "sn_code": record.sn_code or "",
                    "product_model": "",
                    "bom_type": bom.type if bom else None,
                    "bom_type_name": bom.get_type_display() if bom else "",
                    "bom_name": (bom.bom_name or "") if bom else "",
                    "test_cnt": 0,
                    "create_time": "",
                    "last_test_time": "",
                    "unqualified_labels_1": "",
                    "test_desc_1": "",
                    "test_status_1": 0,
                    "test_status_name_1": "",
                    "unqualified_labels_2": "",
                    "test_desc_2": "",
                    "test_status_2": 0,
                    "test_status_name_2": "",
                    "_seen": 0,
                    "_statuses": set(),
                }

            row = sn_map[group_key]
            product = product_map.get(record.product_id)
            bom = bom_map.get(product.bom_id) if product else None
            product_model_val = (record.product_model or "").strip()
            if not product_model_val and bom:
                product_model_val = bom.bom_model or ""
            if product_model_val:
                row["product_model"] = product_model_val

            row["test_cnt"] += 1
            row["_seen"] += 1
            row["_statuses"].add(record.test_status)

            create_time_str = format_local_datetime(record.create_time) or ""
            if create_time_str and (
                not row["create_time"] or create_time_str < row["create_time"]
            ):
                row["create_time"] = create_time_str
            if create_time_str and create_time_str > row["last_test_time"]:
                row["last_test_time"] = create_time_str

            # 按测试次数填充第 1、2 次测试信息；第三次及以后进入详情查看
            seq = record.test_cnt if record.test_cnt > 0 else row["_seen"]
            if seq in (1, 2):
                suffix = str(seq)
                row[f"unqualified_labels_{suffix}"] = _get_unqualified_labels(
                    record.unqualified_values, label_map
                )
                row[f"test_desc_{suffix}"] = record.test_desc or ""
                row[f"test_status_{suffix}"] = record.test_status
                row[f"test_status_name_{suffix}"] = TEST_STATUS_LABELS.get(
                    record.test_status, str(record.test_status)
                )

        result = list(sn_map.values())
        # 测试状态筛选：保留存在该状态记录的 SN 分组
        if test_status in TEST_STATUS_LABELS:
            result = [r for r in result if test_status in r["_statuses"]]

        if sort_field in TEST_RECORD_SORT_FIELDS:
            reverse = sort_order == "desc"
            if TEST_RECORD_SORT_FIELDS[sort_field] == "number":
                result.sort(key=lambda item: item.get(sort_field) or 0, reverse=reverse)
            else:
                result.sort(key=lambda item: item.get(sort_field) or "", reverse=reverse)
        else:
            result.sort(key=lambda item: item["last_test_time"], reverse=True)

        if sn_code:
            result = [r for r in result if sn_code in r["sn_code"]]
        if bom_type in ("0", "1", "2"):
            result = [r for r in result if str(r.get("bom_type")) == bom_type]
        if product_model:
            result = [r for r in result if product_model in r["product_model"]]
        if bom_name:
            result = [r for r in result if bom_name in r["bom_name"]]

        for row in result:
            row.pop("_seen", None)
            row.pop("_statuses", None)

        total = len(result)
        # 首测统计：合格数、不良数、合格率均按第一次测试结果计算
        first_pass_count = sum(1 for row in result if row.get("test_status_1") == 2)
        first_fail_count = sum(1 for row in result if row.get("test_status_1") == 3)
        pass_rate = (
            round(first_pass_count / total * 100, 2) if total else 0
        )
        start = (page - 1) * page_size
        end = start + page_size

        return JsonResponse({
            "code": "00000",
            "msg": "成功",
            "data": {
                "list": result[start:end],
                "total": total,
                "summary": {
                    "total": total,
                    "first_pass_count": first_pass_count,
                    "first_fail_count": first_fail_count,
                    "pass_rate": pass_rate,
                },
            },
        })
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"查询失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["GET"])
def get_test_record_history(request):
    try:
        product_id = request.GET.get("product_id")
        if not product_id:
            return JsonResponse({"code": "400", "msg": "请提供成品ID"})

        records = TestRecord.objects.filter(
            product_id=int(product_id),
            is_del=0,
        )
        # 按 SN 分组时传入 sn_code；不传则返回该成品全部测试记录
        if "sn_code" in request.GET:
            records = records.filter(sn_code=request.GET.get("sn_code") or "")
        records = records.order_by("test_cnt", "create_time")

        label_map = _get_unqualified_label_map()
        result = []
        for record in records:
            result.append({
                "id": record.id,
                "test_cnt": record.test_cnt,
                "unqualified_values": record.unqualified_values or "",
                "unqualified_labels": _get_unqualified_labels(
                    record.unqualified_values, label_map
                ),
                "test_desc": record.test_desc or "",
                "test_status": record.test_status,
                "test_status_name": TEST_STATUS_LABELS.get(
                    record.test_status, str(record.test_status)
                ),
                "create_time": format_local_datetime(record.create_time) or "",
            })
        return JsonResponse({"code": "00000", "msg": "成功", "data": result})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"查询失败: {str(e)}"})
