# apps/system/users/views.py
import json
# 1. 引入 Django 的核心响应类 (相当于 Flask 的 jsonify)
from core.datetime import format_local_datetime
from django.db.models import F, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Product, WarehouseLog
from .constants import normalize_product_type, product_type_label

from apps.system.operation_logs.utils import (
    format_product_create_description,
    format_product_update_description,
    format_stock_adjust_description,
)

# 安全地引入操作日志模块
try:
    from apps.system.operation_logs.services import log_operation_from_request
    OPERATION_LOGS_AVAILABLE = True
except ImportError:
    OPERATION_LOGS_AVAILABLE = False


def _log_if_available(request, **kwargs):
    if OPERATION_LOGS_AVAILABLE:
        log_operation_from_request(request, **kwargs)


def _alert_filter_q():
    """报警行：报警数量与数量均有值，且报警数量 >= 数量（与前端标红逻辑一致）"""
    return Q(
        alert_quantity__isnull=False,
        quantity__isnull=False,
        alert_quantity__gte=F("quantity"),
    )
# 2. (可选) 引入你自己写的工具函数
# 假设你在同级目录下写了一个 utils.py，你可以这样引入:
# from .utils import my_custom_function 

def hello_world(request):
    """
    这是一个视图函数
    request: 相当于 Flask 里的 request 对象
    """
    # 模拟业务逻辑
    user_name = request.GET.get('name', '陌生人')
    
    data = {
        "code": '00000',
        "msg": f"你好, {user_name}! 这是我在 Django 写的第一个接口。",
        "data": {"id": 1, "role": "admin"}
    }
    
    # 返回 JSON 响应
    return JsonResponse(data)


def _optional_text(value):
    text = (value or "").strip() if value is not None else ""
    return text or None


def _validate_product_uniqueness(name, material_code, product_id=None, exclude_id=None):
    """校验物料编码、产品 ID 在未删除记录中唯一；产品名称允许重复。"""
    name = (name or "").strip()
    if not name:
        raise ValueError("产品名称不能为空")

    material_code = (material_code or "").strip()
    if not material_code:
        raise ValueError("物料编码不能为空")

    active_qs = Product.objects.filter(is_del=0)
    if exclude_id is not None:
        active_qs = active_qs.exclude(id=exclude_id)

    if active_qs.filter(material_code=material_code).exists():
        raise ValueError(f"物料编码「{material_code}」已存在")

    if product_id is not None and exclude_id is None:
        try:
            pid = int(product_id)
        except (TypeError, ValueError):
            raise ValueError("产品ID无效")
        if Product.objects.filter(id=pid).exists():
            raise ValueError(f"产品ID「{pid}」已存在")

    return name, material_code


def _serialize_product(product):
    return {
        "id": product.id,
        "name": product.name,
        "type": product.type,
        "type_name": product_type_label(product.type),
        "draw_code": product.draw_code or "",
        "material_code": product.material_code or "",
        "quantity": product.quantity,
        "unit": product.unit,
        "location": product.location,
        "description": product.description,
        "updated_at": format_local_datetime(product.updated_at),
        "alert_quantity": product.alert_quantity,
        "procurement_cycle": float(product.procurement_cycle or 0),
    }


def _product_snapshot(product):
    return {
        "name": product.name,
        "type": product.type,
        "draw_code": product.draw_code or "",
        "material_code": product.material_code or "",
        "quantity": product.quantity,
        "unit": product.unit,
        "location": product.location,
        "description": product.description,
        "alert_quantity": product.alert_quantity,
        "procurement_cycle": float(product.procurement_cycle or 0),
    }


def product_list(request):
    # 1. 读取分页和查询参数
    try:
        page_num = int(request.GET.get("pageNum", 1))
    except (TypeError, ValueError):
        page_num = 1
    try:
        page_size = int(request.GET.get("pageSize", 10))
    except (TypeError, ValueError):
        page_size = 10
    product_id = (request.GET.get("productId", "") or "").strip()
    product_name = (request.GET.get("productName", "") or "").strip()
    # 兼容旧参数 keyword（按产品名称搜索）
    if not product_name:
        product_name = (request.GET.get("keyword", "") or "").strip()
    material_code = (
        request.GET.get("materialCode", "")
        or request.GET.get("material_code", "")
        or ""
    ).strip()
    product_type = (
        request.GET.get("type", "")
        if request.GET.get("type", "") != ""
        else request.GET.get("productType", "")
    )
    product_type = str(product_type).strip() if product_type != "" and product_type is not None else ""
    is_alert = (request.GET.get("isAlert", "") or "").strip()
    sort_prop = (request.GET.get("sortProp", "") or "").strip()
    sort_order = (request.GET.get("sortOrder", "") or "").strip()


    if page_num < 1:
        page_num = 1
    if page_size < 1:
        page_size = 10

    # 2. 组装查询条件
    products = Product.objects.filter(is_del=0)
    if product_id:
        try:
            products = products.filter(id=int(product_id))
        except (TypeError, ValueError):
            products = products.none()
    if product_name:
        products = products.filter(name__icontains=product_name)
    if material_code:
        products = products.filter(material_code__icontains=material_code)
    if product_type in ("0", "1", "2", "4", "5"):
        products = products.filter(type=int(product_type))
    if is_alert == "1":
        products = products.filter(_alert_filter_q())
    elif is_alert == "0":
        products = products.exclude(_alert_filter_q())

    # 3. 处理排序（白名单，防止任意字段注入）
    sort_field_map = {
        "id": "id",
        "name": "name",
        "type": "type",
        "draw_code": "draw_code",
        "material_code": "material_code",
        "quantity": "quantity",
        "alert_quantity": "alert_quantity",
        "updated_at": "updated_at",
    }
    db_sort_field = sort_field_map.get(sort_prop, "id")
    # 默认升序；只有前端明确传 descending 才降序
    db_sort_prefix = "-" if sort_order == "descending" else ""
    products = products.order_by(f"{db_sort_prefix}{db_sort_field}")

    # 4. 计算分页范围
    total = products.count()
    start = (page_num - 1) * page_size
    end = start + page_size
    page_items = products[start:end]

    # 5. 将当前页数据转换为 JSON
    data = [_serialize_product(p) for p in page_items]

    # 6. 返回分页结构
    return JsonResponse(
        {
            "code": "00000",
            "msg": "成功",
            "data": {
                "list": data,
                "total": total,
                "pageNum": page_num,
                "pageSize": page_size,
            },
        }
    )


# --- 2. 新增产品 ---
@csrf_exempt
@require_http_methods(["POST"])
def create_product(request):
    try:
        # 1. 解析前端传来的 JSON 数据
        body = json.loads(request.body or "{}")

        # 2. 创建对象（主键 id 让数据库自增；仅当前端显式传了 id 才使用）
        product_type = normalize_product_type(body.get("type"))
        if product_type is None:
            return JsonResponse({"code": "400", "msg": "请选择产品类型"})

        material_code_raw = body.get("material_code") or body.get("materialCode")
        name, material_code = _validate_product_uniqueness(
            body.get("name"),
            material_code_raw,
            product_id=body.get("id"),
        )

        create_kwargs = {
            "name": name,
            "type": product_type,
            "draw_code": _optional_text(body.get("draw_code") or body.get("drawCode")),
            "material_code": material_code,
            "quantity": body.get("quantity"),
            "unit": body.get("unit"),
            "location": body.get("location"),
            "description": body.get("description"),
            "alert_quantity": body.get("alert_quantity"),
            "procurement_cycle": body.get("procurement_cycle", 1),
            "is_del": 0,
        }
        if body.get("id") is not None:
            create_kwargs["id"] = body.get("id")

        product = Product.objects.create(**create_kwargs)
        
        # 记录操作日志
        _log_if_available(
            request,
            module='product',
            module_name='库存管理',
            operation_type='create',
            target_id=product.id,
            target_name=product.name,
            after_data=_product_snapshot(product),
            description=format_product_create_description(product),
        )
        
        return JsonResponse({"code": '00000', "msg": "新增成功", "data": {"id": product.id}})
    except ValueError as e:
        return JsonResponse({"code": "400", "msg": str(e)})
    except Exception as e:
        return JsonResponse({"code": '500', "msg": f"新增失败: {str(e)}"})

# --- 3. 修改产品 ---
@csrf_exempt
@require_http_methods(["POST"])
def update_product(request):
    try:
        # 1. 解析 JSON
        body = json.loads(request.body or "{}")
        product_id = body.get('id') # 前端必须传 id

        # 2. 查找对象
        product = Product.objects.get(id=product_id, is_del=0)
        
        # 保存修改前的数据
        before_data = _product_snapshot(product)

        # 3. 更新字段
        product_type = normalize_product_type(body.get('type'))
        if product_type is None:
            return JsonResponse({"code": "400", "msg": "请选择产品类型"})

        material_code_raw = body.get("material_code") or body.get("materialCode")
        name, material_code = _validate_product_uniqueness(
            body.get("name"),
            material_code_raw,
            exclude_id=product.id,
        )

        product.name = name
        product.type = product_type
        product.draw_code = _optional_text(body.get("draw_code") or body.get("drawCode"))
        product.material_code = material_code
        product.quantity = body.get('quantity')
        product.unit = body.get('unit')
        product.location = body.get('location')
        product.description = body.get('description')
        product.alert_quantity = body.get('alert_quantity')
        product.procurement_cycle = body.get('procurement_cycle', 0)
        product.save()
        
        # 保存修改后的数据
        after_data = _product_snapshot(product)
        
        description = format_product_update_description(product.name, before_data, after_data)

        _log_if_available(
            request,
            module='product',
            module_name='库存管理',
            operation_type='update',
            target_id=product.id,
            target_name=product.name,
            before_data=before_data,
            after_data=after_data,
            description=description,
        )

        return JsonResponse({"code": '00000', "msg": "更新成功", "data": {"id": product.id}})
    except Product.DoesNotExist:
        return JsonResponse({"code": '404', "msg": "产品不存在"})
    except ValueError as e:
        return JsonResponse({"code": "400", "msg": str(e)})
    except Exception as e:
        return JsonResponse({"code": '500', "msg": f"更新失败: {str(e)}"})

# --- 4. 产品出入库 ---
@csrf_exempt
@require_http_methods(["POST"])
def stock_adjust_product(request):
    """产品出入库：type=in 入库，type=out 出库"""
    try:
        body = json.loads(request.body or "{}")
        product_id = body.get("id")
        adjust_type = (body.get("type") or "").strip().lower()
        if not product_id:
            return JsonResponse({"code": "400", "msg": "缺少产品 ID"})
        if adjust_type not in ("in", "out"):
            return JsonResponse({"code": "400", "msg": "type 须为 in（入库）或 out（出库）"})
        try:
            delta = int(body.get("quantity"))
        except (TypeError, ValueError):
            return JsonResponse({"code": "400", "msg": "数量必须为整数"})
        if delta < 1:
            return JsonResponse({"code": "400", "msg": "数量必须大于 0"})

        product = Product.objects.get(id=product_id, is_del=0)
        current = product.quantity if product.quantity is not None else 0
        if adjust_type == "out" and current < delta:
            return JsonResponse(
                {"code": "400", "msg": f"库存不足：当前 {current}，出库 {delta}"}
            )
        
        # 保存修改前的数据
        before_data = {"quantity": current}
        
        product.quantity = current + delta if adjust_type == "in" else current - delta
        product.save(update_fields=["quantity", "updated_at"])
        action = "入库" if adjust_type == "in" else "出库"
        
        # 保存修改后的数据
        after_data = {"quantity": product.quantity}
        
        # 记录操作日志
        _log_if_available(
            request,
            module='productStock',
            module_name='库存',
            operation_type='stock_in' if adjust_type == 'in' else 'stock_out',
            target_id=product.id,
            target_name=product.name,
            before_data=before_data,
            after_data=after_data,
            description=format_stock_adjust_description(action, product.name, delta),
        )
        
        return JsonResponse(
            {
                "code": "00000",
                "msg": f"{action}成功",
                "data": {
                    "id": product.id,
                    "quantity": product.quantity,
                    "type": adjust_type,
                    "delta": delta,
                },
            }
        )
    except Product.DoesNotExist:
        return JsonResponse({"code": "404", "msg": "产品不存在"})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"操作失败: {str(e)}"})

# --- 5. 删除产品 ---
@csrf_exempt
@require_http_methods(["POST"])
def delete_product(request):
    try:
        # 1. 解析 JSON
        body = json.loads(request.body or "{}")
        product_id = body.get('id')

        # 2. 删除
        product = Product.objects.get(id=product_id, is_del=0)
        
        # 保存删除前的数据
        before_data = _product_snapshot(product)
        
        product.is_del = 1
        product.save(update_fields=["is_del", "updated_at"])
        
        # 记录操作日志
        _log_if_available(
            request,
            module='product',
            module_name='库存管理',
            operation_type='delete',
            target_id=product.id,
            target_name=product.name,
            before_data=before_data,
            description=f"删除库存: {product.name}",
        )

        return JsonResponse({"code": '00000', "msg": "删除成功", "data": {"id": product_id}})
    except Product.DoesNotExist:
        return JsonResponse({"code": '404', "msg": "产品不存在"})
    except Exception as e:
        return JsonResponse({"code": '500', "msg": f"删除失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["GET"])
def warehouse_log_list(request):
    """出入库日志列表"""
    try:
        page_num = int(request.GET.get("pageNum", 1))
    except (TypeError, ValueError):
        page_num = 1
    try:
        page_size = int(request.GET.get("pageSize", 10))
    except (TypeError, ValueError):
        page_size = 10

    sn_code = (request.GET.get("sn_code", "") or "").strip()
    material_code = (request.GET.get("material_code", "") or "").strip()
    name = (request.GET.get("name", "") or "").strip()
    storage_status = (request.GET.get("storage_status", "") or "").strip()
    start_date = (request.GET.get("start_date", "") or "").strip()
    end_date = (request.GET.get("end_date", "") or "").strip()

    qs = WarehouseLog.objects.all()
    if sn_code:
        qs = qs.filter(sn_code__icontains=sn_code)
    if material_code:
        qs = qs.filter(material_code__icontains=material_code)
    if name:
        qs = qs.filter(name__icontains=name)
    if storage_status:
        try:
            storage_status_int = int(storage_status)
            if storage_status_int in (1, 2, 3):
                qs = qs.filter(storage_status=storage_status_int)
        except (TypeError, ValueError):
            pass
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)

    total = qs.count()
    start = (page_num - 1) * page_size
    end = start + page_size
    page_items = qs.order_by("-created_at")[start:end]

    data = []
    for item in page_items:
        data.append({
            "id": item.id,
            "name": item.name or "",
            "sn_code": item.sn_code or "",
            "material_code": item.material_code or "",
            "storage_status": item.storage_status,
            "storage_status_name": item.get_storage_status_display(),
            "count": item.count,
            "description": item.description or "",
            "created_at": format_local_datetime(item.created_at),
        })

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


@csrf_exempt
@require_http_methods(["POST"])
def create_warehouse_log(request):
    """创建出入库日志"""
    try:
        body = json.loads(request.body or "{}")
        
        sn_code = (body.get("sn_code") or "").strip() or None
        material_code = (body.get("material_code") or "").strip() or None
        name = (body.get("name") or "").strip() or None
        storage_status = body.get("storage_status")
        count = body.get("count", 1)
        description = (body.get("description") or "").strip() or None
        
        valid_statuses = (WarehouseLog.STORAGE_IN, WarehouseLog.STORAGE_OUT_SALE, WarehouseLog.STORAGE_OUT_RANDD)
        if storage_status not in valid_statuses:
            return JsonResponse({"code": "400", "msg": "出入库状态无效"})
        
        try:
            count = int(count)
        except (TypeError, ValueError):
            return JsonResponse({"code": "400", "msg": "数量必须为整数"})
        
        if count < 1:
            return JsonResponse({"code": "400", "msg": "数量必须大于 0"})
        
        if not sn_code and not material_code:
            return JsonResponse({"code": "400", "msg": "SN码和物料编码不能同时为空"})
        
        warehouse_log = WarehouseLog.objects.create(
            name=name,
            sn_code=sn_code,
            material_code=material_code,
            storage_status=storage_status,
            count=count,
            description=description,
        )
        
        return JsonResponse({
            "code": "00000",
            "msg": "创建成功",
            "data": {"id": warehouse_log.id}
        })
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"创建失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["GET"])
def stock_alert_list(request):
    """库存预警列表 - 统一3种缺料类型
    
    缺料类型 (shortage_type):
    - actual: 库存缺料 - 所有未来计划总需求 > 当前库存
    - plan: 计划缺料 - 2倍采购周期内需求 > 当前库存
    - alert: 缺料警告 - 当前库存 <= 预警数量(alert_quantity)
    
    优先级: actual(3) > plan(2) > alert(1)
    """
    try:
        from datetime import date, timedelta
        from apps.product.production_plan.models import ProductionPlan
        from apps.product.boms.models import BomList, AssemblyRecipe

        # 预留库存倍率 (默认1.5)
        try:
            multiplier = float(request.GET.get("multiplier", 1.5))
        except (ValueError, TypeError):
            multiplier = 1.5

        today = date.today()
        # 收集所有未来的生产计划
        future_plans = list(ProductionPlan.objects.filter(plan_date__gte=today).order_by("plan_date"))
        future_bom_ids = list({p.bom_id for p in future_plans})

        # 收集所有在未来计划的BOM中使用到的产品ID
        bom_product_ids = set()
        if future_bom_ids:
            for recipe in AssemblyRecipe.objects.filter(bom_id__in=future_bom_ids):
                if recipe.raw_material_id:
                    bom_product_ids.add(recipe.raw_material_id)
                if recipe.component_id:
                    bom_product_ids.add(recipe.component_id)

        # 收集需要纳入监控的产品
        products = Product.objects.filter(is_del=0).filter(
            Q(procurement_cycle__gt=0)
            | Q(alert_quantity__gt=0)
            | Q(id__in=bom_product_ids)
        )

        # 预先计算每个 bom 的所需量: {bom_id: {product_id: required_qty}}
        bom_requirements = {}
        if future_bom_ids:
            for recipe in AssemblyRecipe.objects.filter(bom_id__in=future_bom_ids):
                pid = recipe.raw_material_id or recipe.component_id
                unit_qty = float(recipe.raw_material_quantity if recipe.raw_material_id else recipe.component_quantity or 1)
                if pid:
                    bom_requirements.setdefault(recipe.bom_id, {})
                    bom_requirements[recipe.bom_id][pid] = float(bom_requirements[recipe.bom_id].get(pid, 0)) + unit_qty

        # 预先计算每个产品在所有未来计划中的总需求和涉及天数
        product_future_demand = {}
        product_plan_days = {}
        for plan in future_plans:
            bom_req = bom_requirements.get(plan.bom_id, {})
            for pid, unit_qty in bom_req.items():
                product_future_demand[pid] = float(product_future_demand.get(pid, 0)) + float(plan.quantity) * float(unit_qty)
                if pid not in product_plan_days:
                    product_plan_days[pid] = set()
                product_plan_days[pid].add(plan.plan_date)

        # 计算每个产品的计划缺料数据 (平均日需求 * 采购周期 * 2)
        product_plan_shortage = {}
        for product in products:
            cycle_days = float(product.procurement_cycle or 0)
            if cycle_days > 0:
                total_demand = product_future_demand.get(product.id, 0)
                distinct_days = len(product_plan_days.get(product.id, set()))
                if distinct_days > 0 and total_demand > 0:
                    avg_daily = total_demand / distinct_days
                    required_stock = avg_daily * cycle_days * multiplier
                    product_plan_shortage[product.id] = {
                        "avg_daily": avg_daily,
                        "required_stock": required_stock,
                        "distinct_days": distinct_days,
                        "multiplier": multiplier,
                    }

        alerts = []
        for product in products:
            cycle_days = float(product.procurement_cycle or 0)
            current_stock = float(product.quantity or 0)
            alert_quantity = float(product.alert_quantity or 0)

            total_demand = product_future_demand.get(product.id, 0)
            plan_data = product_plan_shortage.get(product.id, {})
            required_stock = plan_data.get("required_stock", 0)
            avg_daily = plan_data.get("avg_daily", 0)
            distinct_days = plan_data.get("distinct_days", 0)

            # 1. 库存缺料: 所有未来计划总需求 > 当前库存
            actual_shortage = max(0, total_demand - current_stock)
            actual_is_alert = actual_shortage > 0

            # 2. 计划缺料: 当前库存 < 平均日需求 * 采购周期 * 2
            plan_shortage = 0
            plan_is_alert = False
            if required_stock > 0 and current_stock < required_stock:
                plan_shortage = required_stock - current_stock
                plan_is_alert = plan_shortage > 0

            # 3. 缺料警告: 当前库存 <= 预警数量
            alert_shortage = 0
            alert_is_alert = False
            if alert_quantity > 0 and current_stock <= alert_quantity:
                alert_shortage = alert_quantity - current_stock
                alert_is_alert = alert_shortage > 0

            is_alert = actual_is_alert or plan_is_alert or alert_is_alert

            # 按优先级取最严重类型: actual > plan > alert
            shortage_type = ""
            shortage = 0
            suggested_order = 0
            if actual_is_alert:
                shortage_type = "actual"
                shortage = actual_shortage
                suggested_order = actual_shortage
            elif plan_is_alert:
                shortage_type = "plan"
                shortage = plan_shortage
                suggested_order = plan_shortage
            elif alert_is_alert:
                shortage_type = "alert"
                shortage = alert_shortage
                suggested_order = alert_shortage

            alerts.append({
                "product_id": product.id,
                "product_name": product.name,
                "material_code": product.material_code or "",
                "current_stock": current_stock,
                "alert_quantity": alert_quantity,
                "procurement_cycle": cycle_days,
                "total_demand": total_demand,
                "cycle_demand": required_stock,
                "avg_daily": avg_daily,
                "distinct_days": distinct_days,
                "is_alert": is_alert,
                "shortage_type": shortage_type,
                "shortage": shortage,
                "actual_shortage": actual_shortage,
                "plan_shortage": plan_shortage,
                "alert_shortage": alert_shortage,
                "suggested_order": suggested_order,
            })

        # 排序: 有预警的在前, 按优先级排序
        type_priority = {"actual": 3, "plan": 2, "alert": 1}
        alerts.sort(key=lambda x: (
            not x["is_alert"],
            -(type_priority.get(x["shortage_type"], 0)),
            x["product_id"],
        ))

        # 统计各类型数量
        actual_count = sum(1 for a in alerts if a["shortage_type"] == "actual")
        plan_count = sum(1 for a in alerts if a["shortage_type"] == "plan")
        alert_count = sum(1 for a in alerts if a["shortage_type"] == "alert")

        # 分页处理
        try:
            page_num = int(request.GET.get("pageNum", 1))
            page_size = int(request.GET.get("pageSize", 20))
        except (ValueError, TypeError):
            page_num = 1
            page_size = 20
        if page_num < 1:
            page_num = 1
        if page_size < 1:
            page_size = 20

        total = len(alerts)
        start = (page_num - 1) * page_size
        end = start + page_size
        paged_list = alerts[start:end]

        return JsonResponse({
            "code": "00000",
            "msg": "成功",
            "data": {
                "list": paged_list,
                "total": total,
                "pageNum": page_num,
                "pageSize": page_size,
                "alert_count": sum(1 for a in alerts if a["is_alert"]),
                "actual_count": actual_count,
                "plan_count": plan_count,
                "alert_count_by_type": alert_count,
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"code": "500", "msg": f"获取预警列表失败: {str(e)}"})
