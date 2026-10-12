# apps/system/users/views.py
import json
# 1. 引入 Django 的核心响应类 (相当于 Flask 的 jsonify)
from datetime import datetime
from core.datetime import format_local_datetime, local_day_range_datetimes
from django.db.models import F, Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Product, WarehouseLog
from .constants import normalize_product_type, product_type_label, PRODUCT_TYPE_LABELS
from apps.product.utils.warehouse_logger import create_warehouse_log as create_log_with_operator, get_operator_info

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
    from core.pagination import parse_page_params
    page_num, page_size = parse_page_params(request)
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

        # 引用校验：被 BOM/生产计划引用的产品不允许删除（请使用编辑功能替代删除）
        from django.db.models import Q
        from apps.product.boms.models import AssemblyRecipe, BomList
        from apps.product.production_plan.models import ProductionPlan
        if AssemblyRecipe.objects.filter(
            Q(raw_material_id=product.id) | Q(component_id=product.id)
        ).exists():
            return JsonResponse(
                {"code": "400", "msg": "该产品被 BOM 明细引用，不能删除（请先解除 BOM 引用或编辑产品代替删除）"}
            )
        finished_bom_ids = list(
            BomList.objects.filter(
                finished_product_id=product.id, is_del=0
            ).values_list("id", flat=True)
        )
        if finished_bom_ids:
            if ProductionPlan.objects.filter(bom_id__in=finished_bom_ids).exists():
                return JsonResponse(
                    {"code": "400", "msg": "该产品作为 BOM 成品被生产计划引用，不能删除"}
                )
            return JsonResponse(
                {"code": "400", "msg": "该产品作为 BOM 成品被引用，不能删除"}
            )

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
    from core.pagination import parse_page_params
    page_num, page_size = parse_page_params(request)

    sn_code = (request.GET.get("sn_code", "") or "").strip()
    material_code = (request.GET.get("material_code", "") or "").strip()
    name = (request.GET.get("name", "") or "").strip()
    storage_status = (request.GET.get("storage_status", "") or "").strip()
    product_type = (request.GET.get("product_type", "") or "").strip()
    description = (request.GET.get("description", "") or "").strip()
    user_description = (request.GET.get("user_description", "") or "").strip()
    operator_name = (request.GET.get("operator_name", "") or "").strip()
    start_date = (request.GET.get("start_date", "") or "").strip()
    end_date = (request.GET.get("end_date", "") or "").strip()

    qs = WarehouseLog.objects.all()
    if sn_code:
        qs = qs.filter(sn_code__icontains=sn_code)
    if material_code:
        qs = qs.filter(material_code__icontains=material_code)
    if name:
        qs = qs.filter(name__icontains=name)
    if description:
        qs = qs.filter(description__icontains=description)
    if user_description:
        from django.db.models import Q
        # 描述列来源：warehouse_log.user_description + Product.description + FinishProduct.description
        desc_q = Q(user_description__icontains=user_description)
        # 按 material_code 查 Product.description 包含关键词的
        matched_mcs = set(Product.objects.filter(description__icontains=user_description).values_list('material_code', flat=True))
        if matched_mcs:
            desc_q |= Q(material_code__in=list(matched_mcs))
        # 按 sn_code 查 FinishProduct.description 包含关键词的
        from apps.product.finish_products.models import FinishProduct
        matched_sns = set(FinishProduct.objects.filter(description__icontains=user_description).values_list('sn_code', flat=True))
        if matched_sns:
            desc_q |= Q(sn_code__in=list(matched_sns))
        qs = qs.filter(desc_q)
    if operator_name:
        qs = qs.filter(operator_name__icontains=operator_name)
    if product_type:
        # 按库存类型过滤：反查 Product.type 和 BomList.type 对应的 material_code
        from apps.product.boms.models import BomList
        # 标签 → 各表 type 值映射
        product_type_value = None
        bom_type_value = None
        label_to_product_type = {v: k for k, v in PRODUCT_TYPE_LABELS.items()}  # {"自制":0, "外协":1, ...}
        label_to_bom_type = {"关节": 0, "机械臂": 1, "其他": 2}
        if product_type in label_to_product_type:
            product_type_value = label_to_product_type[product_type]
        if product_type in label_to_bom_type:
            bom_type_value = label_to_bom_type[product_type]
        # 收集匹配的 material_code
        matched_mcs = set()
        if product_type_value is not None:
            matched_mcs.update(
                Product.objects.filter(type=product_type_value)
                .values_list('material_code', flat=True)
            )
        if bom_type_value is not None:
            matched_mcs.update(
                BomList.objects.filter(type=bom_type_value)
                .values_list('material_code', flat=True)
            )
        if matched_mcs:
            qs = qs.filter(material_code__in=list(matched_mcs))
        else:
            # 没有匹配的 material_code，返回空集
            qs = qs.filter(id__in=[])
    if storage_status:
        try:
            storage_status_int = int(storage_status)
            if storage_status_int in (1, 2, 3):
                qs = qs.filter(storage_status=storage_status_int)
        except (TypeError, ValueError):
            pass

    def _parse_date(value):
        try:
            return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None

    start_day = _parse_date(start_date)
    end_day = _parse_date(end_date)
    if start_day or end_day:
        # 用本地时区全天范围比较，避免 __date 查询依赖 MySQL 时区表（未加载时 CONVERT_TZ 返回 NULL 导致结果为空）
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
    end = start + page_size
    page_items = list(qs.order_by("-created_at")[start:end])

    # 批量查询本页涉及的操作人，修复历史记录中 operator_name 为空或为占位'系统'的问题
    operator_ids = {
        item.operator_id for item in page_items
        if item.operator_id is not None
    }
    operator_name_map = {}
    if operator_ids:
        from apps.system.users.models import User
        for u in User.objects.filter(id__in=operator_ids).only('id', 'username', 'nickname'):
            display = (u.nickname or '').strip() or (u.username or '').strip()
            operator_name_map[u.id] = display

    # 批量查询本页涉及的库存类型（机械臂/关节等）
    material_codes = {item.material_code for item in page_items if item.material_code}
    # 按 material_code 查 Product.type 和 description
    product_type_map = {}
    product_desc_map = {}
    if material_codes:
        for p in Product.objects.filter(material_code__in=material_codes).only('material_code', 'type', 'description'):
            product_type_map[p.material_code] = p.type
            if p.description:
                product_desc_map[p.material_code] = p.description
    # 按 material_code 查 BomList.type（0=关节, 1=机械臂, 2=其他）
    bom_type_map = {}
    if material_codes:
        from apps.product.boms.models import BomList
        bom_type_names = {0: "关节", 1: "机械臂", 2: "其他"}
        for b in BomList.objects.filter(material_code__in=material_codes).only('material_code', 'type'):
            bom_type_map[b.material_code] = bom_type_names.get(b.type, "")

    # 按 sn_code 查 FinishProduct.description（成品自身的描述）
    sn_codes = {item.sn_code for item in page_items if item.sn_code}
    finish_desc_map = {}
    if sn_codes:
        from apps.product.finish_products.models import FinishProduct
        for f in FinishProduct.objects.filter(sn_code__in=sn_codes).only('sn_code', 'description'):
            if f.description:
                finish_desc_map[f.sn_code] = f.description

    def _resolve_product_description(item):
        """优先按 material_code 查 Product.description，其次按 sn_code 查 FinishProduct.description"""
        mc = item.material_code
        if mc and mc in product_desc_map:
            return product_desc_map[mc]
        sn = item.sn_code
        if sn and sn in finish_desc_map:
            return finish_desc_map[sn]
        return ""

    def _resolve_type_name(item):
        """优先按 material_code 查 Product.type，其次查 BomList.type"""
        mc = item.material_code
        if not mc:
            return ""
        if mc in product_type_map:
            return PRODUCT_TYPE_LABELS.get(product_type_map[mc], "")
        if mc in bom_type_map:
            return bom_type_map[mc]
        return ""

    data = []
    for item in page_items:
        # 优先以查库得到的真实昵称/用户名展示；DB 中的 operator_name 仅作兜底
        operator_display = operator_name_map.get(item.operator_id) or item.operator_name or ""
        data.append({
            "id": item.id,
            "name": item.name or "",
            "sn_code": item.sn_code or "",
            "material_code": item.material_code or "",
            "product_model": item.product_model or "",
            "product_type_name": _resolve_type_name(item),
            "storage_status": item.storage_status,
            "storage_status_name": item.get_storage_status_display(),
            "count": item.count,
            "description": item.description or "",
            "user_description": item.user_description or "",
            "product_description": _resolve_product_description(item),
            "operator_name": operator_display,
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
    """创建出入库日志（包含操作人信息）"""
    try:
        body = json.loads(request.body or "{}")
        
        sn_code = (body.get("sn_code") or "").strip() or None
        material_code = (body.get("material_code") or "").strip() or None
        name = (body.get("name") or "").strip() or None
        product_model = (body.get("product_model") or "").strip() or None
        storage_status = body.get("storage_status")
        count = body.get("count", 1)
        description = (body.get("description") or "").strip() or None
        user_description = (body.get("user_description") or "").strip() or None
        module = (body.get("module") or "manual").strip() or None
        action_type = (body.get("action_type") or "").strip() or None
        operation_detail = body.get("operation_detail")

        valid_statuses = (WarehouseLog.STORAGE_IN, WarehouseLog.STORAGE_OUT_SALE,
                         WarehouseLog.STORAGE_OUT_RANDD, WarehouseLog.MANUAL_ADJUST)
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

        # 若未提供系统描述，自动生成操作摘要
        if not description:
            status_names = {
                WarehouseLog.STORAGE_IN: '入库',
                WarehouseLog.STORAGE_OUT_SALE: '出库(外销)',
                WarehouseLog.STORAGE_OUT_RANDD: '出库(研发)',
                WarehouseLog.MANUAL_ADJUST: '手动调整',
            }
            action_name = status_names.get(storage_status, str(storage_status))
            description = f"产品: {name or sn_code or material_code or ''}, 操作: {action_name}, 数量: {count}"

        # 使用新的日志记录逻辑，自动获取操作人信息
        warehouse_log = create_log_with_operator(
            request=request,
            storage_status=storage_status,
            name=name,
            sn_code=sn_code,
            material_code=material_code,
            product_model=product_model or "",
            count=count,
            description=description,
            user_description=user_description,
            module=module,
            action_type=action_type,
            operation_detail=operation_detail,
        )
        
        if warehouse_log is None:
            return JsonResponse({"code": "500", "msg": "创建日志失败"})
        
        return JsonResponse({
            "code": "00000",
            "msg": "创建成功",
            "data": {"id": warehouse_log.id}
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
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

        # 通过共享辅助函数构建 BOM 需求映射（使用有效产品 ID，支持物料编码回退）
        from apps.product.boms.utils import build_bom_requirements
        bom_requirements = build_bom_requirements(future_bom_ids)

        # 收集所有在未来计划的BOM中使用到的有效产品ID
        bom_product_ids = set()
        for req_map in bom_requirements.values():
            bom_product_ids.update(req_map.keys())

        # 收集需要纳入监控的产品
        products = Product.objects.filter(is_del=0).filter(
            Q(procurement_cycle__gt=0)
            | Q(alert_quantity__gt=0)
            | Q(id__in=bom_product_ids)
        )

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
        from core.pagination import parse_page_params
        page_num, page_size = parse_page_params(request, default_size=20)

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
