import json
from datetime import datetime

from django.db.models import Max, Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.datetime import format_local_datetime, local_day_range_datetimes
from apps.product.finish_products.models import FinishProduct
from apps.system.dicts.models import DictionaryItem
from apps.system.operation_logs.request_user import get_request_operator

from .models import Repair


def _parse_date_param(value):
    """解析 YYYY-MM-DD 日期参数"""
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _get_repair_status_label(value):
    """根据字典 repair_status 获取返修状态文本，字典缺失时回退内置文案"""
    try:
        item = DictionaryItem.objects.filter(
            dict_code="repair_status", status=1, value=str(value)
        ).first()
        if item:
            return item.label
    except Exception:
        pass
    return dict(Repair.STATUS_CHOICES).get(value, str(value))


def _get_unqualified_label(value):
    """根据字典 unqualified_status 获取不良项文本，字典缺失时回退原值"""
    try:
        item = DictionaryItem.objects.filter(
            dict_code="unqualified_status", status=1, value=str(value)
        ).first()
        if item:
            return item.label
    except Exception:
        pass
    return str(value)


def _normalize_unqualified_values(raw):
    """把列表或逗号分隔字符串统一成去重后的逗号分隔字符串"""
    if isinstance(raw, (list, tuple)):
        items = [str(item).strip() for item in raw]
    else:
        items = [item.strip() for item in str(raw or "").split(",")]
    result = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return ",".join(result)


def _get_unqualified_label_map():
    """一次性读取不良项字典，避免列表逐条查询数据库"""
    return {
        str(item.value): item.label
        for item in DictionaryItem.objects.filter(
            dict_code="unqualified_status", status=1
        )
    }


def _get_unqualified_labels(values, label_map=None):
    """把逗号分隔的字典值转换成中文标签，多个标签用顿号连接"""
    if label_map is None:
        label_map = _get_unqualified_label_map()
    labels = [
        label_map.get(str(value).strip(), str(value).strip())
        for value in (values or "").split(",")
        if value.strip()
    ]
    return "、".join(labels)


def _compose_repair_info(unqualified_values, repair_desc, label_map=None):
    """按「不良项：xxx + 描述」的旧格式拼接返修内容，兼容历史展示"""
    parts = []
    labels = _get_unqualified_labels(unqualified_values, label_map)
    if labels:
        parts.append(f"不良项：{labels}")
    desc = (repair_desc or "").strip()
    if desc:
        parts.append(desc)
    return "\n".join(parts)


def _split_legacy_repair_info(text):
    """解析未拆分的旧返修内容：首行「不良项：xxx」，其余为描述"""
    text = (text or "").strip()
    first_line, _, rest = text.partition("\n")
    if first_line.startswith("不良项："):
        return first_line[len("不良项："):].strip(), rest.strip()
    return "", text


def _build_repair_display(record, label_map=None):
    """统一返回拆分后的不良项与描述，未回填的历史数据按旧格式兜底解析"""
    values = record.unqualified_values or ""
    desc = record.repair_desc or ""
    if values or desc:
        return {
            "unqualified_values": values,
            "unqualified_labels": _get_unqualified_labels(values, label_map),
            "repair_desc": desc,
            "repair_info": _compose_repair_info(values, desc, label_map),
        }
    labels, legacy_desc = _split_legacy_repair_info(record.repair_info)
    return {
        "unqualified_values": "",
        "unqualified_labels": labels,
        "repair_desc": legacy_desc,
        "repair_info": record.repair_info or "",
    }


# 返修列表可排序字段及类型（排序作用于聚合后的结果，先排序再分页）
REPAIR_SORT_FIELDS = {
    "sn_code": "text",
    "product_model": "text",
    "bom_name": "text",
    "repair_cnt": "number",
    "unqualified_labels": "text",
    "repair_desc": "text",
    "unqualified_labels_1": "text",
    "repair_desc_1": "text",
    "unqualified_labels_2": "text",
    "repair_desc_2": "text",
    "repair_status": "number",
    "create_time": "text",
    "last_repair_time": "text",
}


@csrf_exempt
@require_http_methods(["GET"])
def list_repair_products(request):
    try:
        # 搜索参数
        sn_code = (request.GET.get("sn_code") or "").strip()
        product_model = (request.GET.get("product_model") or "").strip()
        bom_name = (request.GET.get("bom_name") or "").strip()
        start_date = _parse_date_param(request.GET.get("start_date") or request.GET.get("startDate"))
        end_date = _parse_date_param(request.GET.get("end_date") or request.GET.get("endDate"))
        # 创建时间筛选：作用于聚合后每行的创建时间（该SN首次返修创建时间）
        create_start_date = _parse_date_param(
            request.GET.get("create_start_date") or request.GET.get("createStartDate")
        )
        create_end_date = _parse_date_param(
            request.GET.get("create_end_date") or request.GET.get("createEndDate")
        )
        # 分页参数
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
        # 排序参数：sort_field 限定白名单，sort_order 支持 asc/desc
        sort_field = (request.GET.get("sort_field") or "").strip()
        sort_order = (request.GET.get("sort_order") or "").strip().lower()

        repair_qs = Repair.objects.filter(is_del=0)
        # 时间筛选（含首尾日全天），在分组聚合前过滤
        if start_date or end_date:
            if start_date and end_date and start_date > end_date:
                repair_qs = repair_qs.none()
            else:
                range_start = start_date or end_date
                range_end = end_date or start_date
                range_start_dt, range_end_dt = local_day_range_datetimes(range_start, range_end)
                repair_qs = repair_qs.filter(
                    create_time__gte=range_start_dt,
                    create_time__lte=range_end_dt,
                )
        repair_records = list(repair_qs.order_by("-create_time"))
        if not repair_records:
            return JsonResponse({
                "code": "00000",
                "msg": "成功",
                "data": {"list": [], "total": 0},
            })

        product_ids = {r.product_id for r in repair_records}
        product_map = {}
        if product_ids:
            for product in FinishProduct.objects.filter(id__in=product_ids):
                product_map[product.id] = product

        bom_map = {}
        bom_ids = {p.bom_id for p in product_map.values() if p.bom_id}
        if bom_ids:
            from apps.product.boms.models import BomList
            bom_map = {
                bom.id: bom
                for bom in BomList.objects.filter(id__in=bom_ids, is_del=0)
            }

        unqualified_label_map = _get_unqualified_label_map()
        sn_map = {}
        for record in repair_records:
            # 复合 key：product_id + sn_code，避免不同产品空 SN 码被合并
            group_key = (record.product_id, record.sn_code or "")
            if group_key not in sn_map:
                product = product_map.get(record.product_id)
                bom = bom_map.get(product.bom_id) if product else None
                bom_name_val = (bom.bom_name or "") if bom else ""
                # 新记录取创建时快照，旧记录回退到当前 BOM 型号
                product_model_val = (record.product_model or "").strip()
                if not product_model_val and bom:
                    product_model_val = bom.bom_model or ""

                sn_map[group_key] = {
                    "product_id": record.product_id,
                    "sn_code": record.sn_code or "",
                    "product_model": product_model_val,
                    "bom_name": bom_name_val,
                    "repair_cnt": 0,
                    "create_time": "",
                    "last_repair_time": "",
                    # 记录列表按创建时间倒序，首条即最近一次返修的不良项与描述
                    **_build_repair_display(record, unqualified_label_map),
                    # 第一次/第二次返修信息，第三次及以后需进入详情查看
                    "unqualified_labels_1": "",
                    "repair_desc_1": "",
                    "unqualified_labels_2": "",
                    "repair_desc_2": "",
                    # 记录列表按创建时间倒序，首条即最近一次返修的状态
                    "repair_status": record.repair_status,
                    "repair_status_name": _get_repair_status_label(record.repair_status),
                }
            sn_map[group_key]["repair_cnt"] += 1
            # 同一SN码存在任意待返修记录时，整体展示为待返修
            if record.repair_status == Repair.STATUS_PENDING:
                sn_map[group_key]["repair_status"] = Repair.STATUS_PENDING
                sn_map[group_key]["repair_status_name"] = _get_repair_status_label(
                    Repair.STATUS_PENDING
                )
            # 按返修次序填充第 1、2 次返修的不良项与描述
            if record.repair_cnt in (1, 2):
                display = _build_repair_display(record, unqualified_label_map)
                suffix = str(record.repair_cnt)
                sn_map[group_key][f"unqualified_labels_{suffix}"] = display["unqualified_labels"]
                sn_map[group_key][f"repair_desc_{suffix}"] = display["repair_desc"]
            # ORM 读出的时间字段是 UTC aware datetime，必须转北京时间，
            # 直接 strftime 会少 8 小时
            create_time_str = format_local_datetime(record.create_time) or ""
            if create_time_str and (
                not sn_map[group_key]["create_time"]
                or create_time_str < sn_map[group_key]["create_time"]
            ):
                sn_map[group_key]["create_time"] = create_time_str
            # 最后返修时间取 update_time，状态修改后会同步刷新
            update_time_str = (
                format_local_datetime(record.update_time) or create_time_str
            )
            if update_time_str and update_time_str > sn_map[group_key]["last_repair_time"]:
                sn_map[group_key]["last_repair_time"] = update_time_str

        result = list(sn_map.values())
        if sort_field in REPAIR_SORT_FIELDS:
            reverse = sort_order == "desc"
            if REPAIR_SORT_FIELDS[sort_field] == "number":
                result.sort(key=lambda item: item.get(sort_field) or 0, reverse=reverse)
            else:
                result.sort(key=lambda item: item.get(sort_field) or "", reverse=reverse)
        else:
            result.sort(key=lambda item: item["last_repair_time"], reverse=True)

        # 搜索过滤（在聚合后做，保证分组计数不受搜索影响）
        if sn_code:
            result = [r for r in result if sn_code in (r.get("sn_code") or "")]
        if product_model:
            result = [r for r in result if product_model in (r.get("product_model") or "")]
        if bom_name:
            result = [r for r in result if bom_name in (r.get("bom_name") or "")]
        # 创建时间筛选：按聚合行展示的创建时间过滤
        if create_start_date or create_end_date:
            create_start_str = create_start_date.isoformat() if create_start_date else ""
            create_end_str = create_end_date.isoformat() if create_end_date else ""

            def _created_in_range(value):
                date_str = (value or "")[:10]
                if not date_str:
                    return False
                if create_start_str and date_str < create_start_str:
                    return False
                if create_end_str and date_str > create_end_str:
                    return False
                return True

            result = [r for r in result if _created_in_range(r.get("create_time"))]

        total = len(result)
        start = (page - 1) * page_size
        end = start + page_size
        page_data = result[start:end]

        return JsonResponse({
            "code": "00000",
            "msg": "成功",
            "data": {"list": page_data, "total": total},
        })
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"查询失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["GET"])
def get_product_repair_history(request):
    try:
        product_id = request.GET.get("product_id")
        if not product_id:
            return JsonResponse({"code": "400", "msg": "请提供成品ID"})
        
        repairs = Repair.objects.filter(
            product_id=int(product_id),
            is_del=0
        ).order_by("repair_cnt")
        
        result = []
        unqualified_label_map = _get_unqualified_label_map()
        for repair in repairs:
            result.append({
                "id": repair.id,
                "repair_cnt": repair.repair_cnt,
                **_build_repair_display(repair, unqualified_label_map),
                "repair_status": repair.repair_status,
                "repair_status_name": _get_repair_status_label(repair.repair_status),
                "create_time": format_local_datetime(repair.create_time) or "",
            })
        
        return JsonResponse({"code": "00000", "msg": "成功", "data": result})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"查询失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["POST"])
def create_repair(request):
    try:
        body = json.loads(request.body or "{}")
        product_id = body.get("product_id")
        # 新格式：不良项字典值 + 返修描述分开接收；repair_info 仅作为旧调用方式的兜底
        unqualified_values = _normalize_unqualified_values(body.get("unqualified_values"))
        repair_desc = str(body.get("repair_desc") or "").strip()
        legacy_info = str(body.get("repair_info") or "").strip()

        if not product_id:
            return JsonResponse({"code": "400", "msg": "请选择成品"})
        if not unqualified_values and not repair_desc and not legacy_info:
            return JsonResponse({"code": "400", "msg": "请输入返修内容或选择不良项"})
        
        try:
            product = FinishProduct.objects.get(id=int(product_id))
        except FinishProduct.DoesNotExist:
            return JsonResponse({"code": "400", "msg": "成品不存在"})
        if product.cons_status == FinishProduct.CONS_STATUS_ROLLED_BACK:
            return JsonResponse({"code": "400", "msg": "该成品已回退，不可创建返修记录"})
        
        # sn_code 可选：请求体里显式传了(哪怕空字符串)就用传的；
        # 没传则从 product 自动取（兼容成品管理页的调用方式）
        if "sn_code" in body:
            sn_code = (body.get("sn_code") or "").strip()
        else:
            sn_code = product.sn_code or ""
        
        max_repair_cnt = Repair.objects.filter(
            product_id=product.id,
            is_del=0
        ).aggregate(max_cnt=Max("repair_cnt"))["max_cnt"] or 0

        # 创建返修记录时同步获取该成品关联 BOM 的产品型号
        from apps.product.boms.models import BomList
        bom = BomList.objects.filter(id=product.bom_id, is_del=0).first()
        product_model = (bom.bom_model or "") if bom else ""

        Repair.objects.create(
            product_id=product.id,
            sn_code=sn_code,
            product_model=product_model,
            repair_cnt=max_repair_cnt + 1,
            repair_info=_compose_repair_info(unqualified_values, repair_desc) or legacy_info,
            unqualified_values=unqualified_values,
            repair_desc=repair_desc,
            repair_status=Repair.STATUS_PENDING,
        )
        
        return JsonResponse({"code": "00000", "msg": "创建成功", "data": None})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"创建失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["GET"])
def get_products_with_sn(request):
    try:
        products = FinishProduct.active_queryset().filter(
            Q(sn_code__isnull=False) & ~Q(sn_code="")
        ).order_by("-create_time")
        
        result = []
        for product in products:
            bom_name = ""
            try:
                from apps.product.boms.models import BomList
                bom = BomList.objects.get(id=product.bom_id, is_del=0)
                bom_name = bom.bom_name or ""
            except:
                pass
            
            result.append({
                "id": product.id,
                "sn_code": product.sn_code,
                "bom_name": bom_name,
            })
        
        return JsonResponse({"code": "00000", "msg": "成功", "data": result})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"查询失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["POST"])
def delete_repair(request):
    try:
        body = json.loads(request.body or "{}")
        repair_id = body.get("id")
        
        if not repair_id:
            return JsonResponse({"code": "400", "msg": "请提供返修记录ID"})
        
        repair = Repair.objects.get(id=int(repair_id))
        repair.is_del = 1
        repair.save()
        
        return JsonResponse({"code": "00000", "msg": "删除成功", "data": None})
    except Repair.DoesNotExist:
        return JsonResponse({"code": "404", "msg": "返修记录不存在"})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"删除失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["POST"])
def update_repair_status(request):
    """更新返修状态；置为已返修时同步成品为「返修品 + 未测试」"""
    try:
        body = json.loads(request.body or "{}")
        repair_id = body.get("id")
        repair_status = body.get("repair_status")

        if repair_id in (None, ""):
            return JsonResponse({"code": "400", "msg": "请提供返修记录ID"})
        try:
            repair_status = int(repair_status)
        except (TypeError, ValueError):
            return JsonResponse({"code": "400", "msg": "返修状态值无效"})
        if repair_status not in (Repair.STATUS_PENDING, Repair.STATUS_REPAIRED):
            return JsonResponse({"code": "400", "msg": "返修状态值无效"})

        repair = Repair.objects.filter(id=int(repair_id), is_del=0).first()
        if not repair:
            return JsonResponse({"code": "404", "msg": "返修记录不存在"})

        repair.repair_status = repair_status
        repair.save(update_fields=["repair_status", "update_time"])

        product_updated = False
        if repair_status == Repair.STATUS_REPAIRED:
            product = FinishProduct.objects.filter(id=repair.product_id).first()
            if product is None and repair.sn_code:
                product = (
                    FinishProduct.active_queryset()
                    .filter(sn_code=repair.sn_code)
                    .order_by("-create_time")
                    .first()
                )
            if product and product.cons_status != FinishProduct.CONS_STATUS_ROLLED_BACK:
                now = timezone.now()
                if product.status != FinishProduct.STATUS_UNTESTED:
                    product.test_time = now
                product.status = FinishProduct.STATUS_UNTESTED
                product.repair = FinishProduct.REPAIR_REPAIRED
                editor = get_request_operator(request)
                if editor:
                    product.editor_id, product.editor_name = editor[0], editor[1] or ""
                product.update_time = now
                product.save()
                product_updated = True

        return JsonResponse({
            "code": "00000",
            "msg": "更新成功",
            "data": {"product_updated": product_updated},
        })
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"更新失败: {str(e)}"})