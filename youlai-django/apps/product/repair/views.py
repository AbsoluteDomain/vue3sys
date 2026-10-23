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
        result.sort(key=lambda x: x["last_repair_time"], reverse=True)

        # 搜索过滤（在聚合后做，保证分组计数不受搜索影响）
        if sn_code:
            result = [r for r in result if sn_code in (r.get("sn_code") or "")]
        if product_model:
            result = [r for r in result if product_model in (r.get("product_model") or "")]
        if bom_name:
            result = [r for r in result if bom_name in (r.get("bom_name") or "")]

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
        for repair in repairs:
            result.append({
                "id": repair.id,
                "repair_cnt": repair.repair_cnt,
                "repair_info": repair.repair_info,
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
        repair_info = body.get("repair_info")
        
        if not product_id:
            return JsonResponse({"code": "400", "msg": "请选择成品"})
        if not repair_info or str(repair_info).strip() == "":
            return JsonResponse({"code": "400", "msg": "请输入返修内容"})
        
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
            repair_info=repair_info.strip(),
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