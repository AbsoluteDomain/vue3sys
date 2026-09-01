import json
from datetime import datetime

from django.db.models import Max, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.product.finish_products.models import FinishProduct

from .models import Repair


@csrf_exempt
@require_http_methods(["GET"])
def list_repair_products(request):
    try:
        repair_records = Repair.objects.filter(is_del=0).order_by("-create_time")
        
        product_ids = {r.product_id for r in repair_records}
        product_map = {}
        if product_ids:
            for product in FinishProduct.objects.filter(id__in=product_ids):
                product_map[product.id] = product
        
        sn_map = {}
        for record in repair_records:
            # 复合 key：product_id + sn_code，避免不同产品空 SN 码被合并
            group_key = (record.product_id, record.sn_code or "")
            if group_key not in sn_map:
                product = product_map.get(record.product_id)
                bom_name = ""
                if product:
                    from apps.product.boms.models import BomList
                    try:
                        bom = BomList.objects.get(id=product.bom_id, is_del=0)
                        bom_name = bom.bom_name or ""
                    except:
                        pass
                
                sn_map[group_key] = {
                    "product_id": record.product_id,
                    "sn_code": record.sn_code or "",
                    "bom_name": bom_name,
                    "repair_cnt": 0,
                    "last_repair_time": "",
                }
            sn_map[group_key]["repair_cnt"] += 1
            if record.create_time:
                time_str = record.create_time.strftime("%Y-%m-%d %H:%M:%S")
                if time_str > sn_map[group_key]["last_repair_time"]:
                    sn_map[group_key]["last_repair_time"] = time_str
        
        result = list(sn_map.values())
        result.sort(key=lambda x: x["last_repair_time"], reverse=True)
        
        return JsonResponse({"code": "00000", "msg": "成功", "data": result})
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
                "create_time": repair.create_time.strftime("%Y-%m-%d %H:%M:%S") if repair.create_time else "",
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
        
        Repair.objects.create(
            product_id=product.id,
            sn_code=sn_code,
            repair_cnt=max_repair_cnt + 1,
            repair_info=repair_info.strip(),
        )
        
        return JsonResponse({"code": "00000", "msg": "创建成功", "data": None})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"创建失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["GET"])
def get_products_with_sn(request):
    try:
        products = FinishProduct.objects.filter(
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