import json

from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.datetime import format_local_datetime
from core.datetime import format_local_datetime
from apps.product.finish_products.models import FinishProduct
from apps.product.products.models import Product
from apps.product.products.constants import product_type_label
from .models import AssemblyRecipe, BomList

from apps.system.operation_logs.utils import (
    format_bom_assemble_description,
    format_bom_recipe_added,
    format_bom_recipe_quantity_change,
    format_bom_recipe_removed,
    format_bom_update_description,
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


def _dt_str(value):
    return format_local_datetime(value)


def _build_product_meta_map(product_ids):
    ids = [pid for pid in product_ids if pid]
    if not ids:
        return {}
    products = Product.objects.filter(id__in=ids, is_del=0)
    return {
        p.id: {
            "part_product_type": p.type,
            "part_product_type_name": product_type_label(p.type),
            "part_material_code": p.material_code or "",
            "unit": p.unit or "",
            "name": p.name,
        }
        for p in products
    }


def _product_meta_from_map(product_meta_map, product_id):
    if not product_id:
        return {
            "part_product_type": None,
            "part_product_type_name": "",
            "part_material_code": "",
            "unit": "",
            "name": "",
        }
    if product_meta_map is not None:
        return product_meta_map.get(
            product_id,
            {
                "part_product_type": None,
                "part_product_type_name": "",
                "part_material_code": "",
                "unit": "",
                "name": "",
            },
        )
    return _lookup_product_part_meta(product_id)


def _lookup_product_part_meta(product_id):
    if not product_id:
        return {
            "part_product_type": None,
            "part_product_type_name": "",
            "part_material_code": "",
        }
    product = Product.objects.filter(id=product_id, is_del=0).first()
    if not product:
        return {
            "part_product_type": None,
            "part_product_type_name": "",
            "part_material_code": "",
        }
    return {
        "part_product_type": product.type,
        "part_product_type_name": product_type_label(product.type),
        "part_material_code": product.material_code or "",
    }


def _recipe_part_info(row):
    """从明细行解析绑定的产品零件信息"""
    if row.raw_material_id:
        return {
            "product_id": row.raw_material_id,
            "product_name": row.raw_material_name or "",
            "product_type": "raw",
            "quantity": row.raw_material_quantity,
        }
    if row.component_id:
        return {
            "product_id": row.component_id,
            "product_name": row.component_name or "",
            "product_type": "component",
            "quantity": row.component_quantity,
        }
    return {
        "product_id": None,
        "product_name": "",
        "product_type": "",
        "quantity": None,
    }


def _serialize_bom_header(bom, recipe_count=0):
    return {
        "id": bom.id,
        "bom_model": bom.bom_model,
        "bom_name": bom.bom_name or "",
        "material_code": bom.material_code or "",
        "type": bom.type,
        "type_name": bom.get_type_display(),
        "recipe_count": recipe_count,
    }


def _bom_display_name(bom):
    return bom.bom_name or bom.bom_model


def _bom_log_label(bom):
    if bom.bom_name:
        return f"{bom.bom_model}({bom.bom_name})"
    return bom.bom_model


def _bom_header_snapshot(bom):
    return {
        "bom_model": bom.bom_model,
        "bom_name": bom.bom_name or "",
        "material_code": bom.material_code or "",
        "type": bom.type,
    }


def _parse_bom_header_fields(body):
    bom_model = (body.get("bom_model") or body.get("bomModel") or "").strip()
    if not bom_model:
        raise ValueError("BOM型号不能为空")
    bom_name = (body.get("bom_name") or body.get("bomName") or "").strip() or None
    material_code = (
        body.get("material_code") or body.get("materialCode") or ""
    ).strip() or None
    return bom_model, bom_name, material_code


def _parse_bom_type(value, required=False):
    if value is None or value == "":
        if required:
            raise ValueError("请选择 BOM 类型")
        return None
    try:
        bom_type = int(value)
    except (TypeError, ValueError):
        raise ValueError("BOM 类型无效")
    valid_types = {choice[0] for choice in BomList.TYPE_CHOICES}
    if bom_type not in valid_types:
        raise ValueError("BOM 类型无效")
    return bom_type


def _serialize_recipe(row, bom_name=None, product_meta_map=None):
    part = _recipe_part_info(row)
    meta = _product_meta_from_map(product_meta_map, part["product_id"])
    return {
        "id": row.id,
        "bom_id": row.bom_id,
        "bom_name": bom_name,
        "part_product_id": part["product_id"],
        "part_product_name": part["product_name"] or meta.get("name") or "",
        "part_material_code": meta["part_material_code"],
        "part_product_type": meta["part_product_type"],
        "part_product_type_name": meta["part_product_type_name"],
        "part_unit": meta.get("unit") or "",
        "part_quantity": part["quantity"],
        "raw_material_id": row.raw_material_id,
        "raw_material_name": row.raw_material_name,
        "raw_material_quantity": row.raw_material_quantity,
        "component_id": row.component_id,
        "component_name": row.component_name,
        "component_quantity": row.component_quantity,
        "created_at": _dt_str(row.created_at),
        "updated_at": _dt_str(row.updated_at),
    }


def _int_or_none(value, field_name="数值"):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name}必须为整数")


def _bool_param(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() not in ("0", "false", "no", "")
    return bool(value)


def _recipe_fields_from_product(bom, product_id, quantity):
    product = Product.objects.filter(id=product_id, is_del=0).first()
    if not product:
        raise ValueError(f"产品不存在（ID={product_id}")

    qty = _int_or_none(quantity, "用量")
    if qty is None or qty < 1:
        raise ValueError("用量必须大于 0")

    fields = {
        "bom_id": bom.id,
        "product_name": product.name,
        "raw_material_id": None,
        "raw_material_name": None,
        "raw_material_quantity": None,
        "component_id": product.id,
        "component_name": product.name,
        "component_quantity": qty,
    }
    return fields


def _save_recipes(bom, recipes_body):
    if recipes_body is None:
        return [], []
    if not isinstance(recipes_body, list):
        raise ValueError("明细格式错误")
    
    # 先获取旧的明细用于比较
    old_recipes = list(AssemblyRecipe.objects.filter(bom_id=bom.id))
    
    product_ids = []
    parsed = []
    for item in recipes_body:
        if not isinstance(item, dict):
            continue
        product_id = item.get("product_id") or item.get("part_product_id")
        if not product_id:
            raise ValueError("明细中存在未选择的产品")
        product_id = int(product_id)
        if product_id in product_ids:
            raise ValueError("同一 BOM 不能重复绑定相同产品")
        product_ids.append(product_id)
        parsed.append(_recipe_fields_from_product(bom, product_id, item.get("quantity") or item.get("part_quantity")))
    
    now = timezone.now()
    with transaction.atomic():
        AssemblyRecipe.objects.filter(bom_id=bom.id).delete()
        for fields in parsed:
            AssemblyRecipe.objects.create(
                **fields,
                created_at=now,
                updated_at=now,
            )
    
    # 返回变更信息
    new_recipes = list(AssemblyRecipe.objects.filter(bom_id=bom.id))
    return old_recipes, new_recipes


def _build_bom_queryset(request):
    bom_id = (request.GET.get("id", "") or request.GET.get("bom_id", "") or "").strip()
    bom_model = (
        request.GET.get("bom_model", "") or request.GET.get("bomModel", "") or ""
    ).strip()
    bom_name = (
        request.GET.get("bom_name", "") or request.GET.get("bomName", "") or ""
    ).strip()
    material_code = (
        request.GET.get("material_code", "")
        or request.GET.get("materialCode", "")
        or ""
    ).strip()
    bom_type = (request.GET.get("type", "") or request.GET.get("bom_type", "") or "").strip()
    sort_prop = (
        request.GET.get("sort_prop", "")
        or request.GET.get("sortProp", "")
        or ""
    ).strip()
    sort_order = (
        request.GET.get("sort_order", "")
        or request.GET.get("sortOrder", "")
        or ""
    ).strip()

    qs = BomList.objects.filter(is_del=0)

    if bom_id:
        try:
            qs = qs.filter(id=int(bom_id))
        except (TypeError, ValueError):
            qs = qs.none()
    if bom_model:
        qs = qs.filter(bom_model__icontains=bom_model)
    if bom_name:
        qs = qs.filter(bom_name__icontains=bom_name)
    if material_code:
        qs = qs.filter(material_code__icontains=material_code)
    if bom_type in ("0", "1", "2"):
        qs = qs.filter(type=int(bom_type))

    sort_field_map = {
        "id": "id",
        "bom_model": "bom_model",
        "bom_name": "bom_name",
        "material_code": "material_code",
        "type": "type",
    }
    db_sort_field = sort_field_map.get(sort_prop, "id")
    db_sort_prefix = "-" if sort_order == "descending" else ""
    return qs.order_by(f"{db_sort_prefix}{db_sort_field}")


def _export_row_from_bom_recipe(bom, recipe=None):
    if recipe:
        part = _recipe_part_info(recipe)
        meta = _lookup_product_part_meta(part["product_id"])
    else:
        part = {
            "product_id": None,
            "product_name": "",
            "quantity": None,
        }
        meta = _lookup_product_part_meta(None)
    return {
        "bom_id": bom.id,
        "bom_model": bom.bom_model,
        "bom_name": bom.bom_name or "",
        "material_code": bom.material_code or "",
        "type": bom.type,
        "type_name": bom.get_type_display(),
        "part_product_id": part["product_id"] or "",
        "part_product_name": part["product_name"],
        "part_product_type": meta["part_product_type"],
        "part_product_type_name": meta["part_product_type_name"],
        "part_quantity": part["quantity"] if part["quantity"] is not None else "",
    }


def bom_list(request):
    page_num, page_size = _parse_page_params(request)
    qs = _build_bom_queryset(request)

    total = qs.count()
    start = (page_num - 1) * page_size
    end = start + page_size
    page_items = list(qs[start:end])

    bom_ids = [b.id for b in page_items]
    recipe_counts = {}
    if bom_ids:
        counts = (
            AssemblyRecipe.objects.filter(bom_id__in=bom_ids)
            .values("bom_id")
            .annotate(cnt=Count("id"))
        )
        recipe_counts = {c["bom_id"]: c["cnt"] for c in counts}

    data = [_serialize_bom_header(bom, recipe_counts.get(bom.id, 0)) for bom in page_items]

    return JsonResponse(
        {
            "code": "00000",
            "msg": "成功",
            "data": {
                "list": data,
                "total": total,
                "page_num": page_num,
                "page_size": page_size,
            },
        }
    )


def _serialize_bom_export_item(bom):
    recipes = list(AssemblyRecipe.objects.filter(bom_id=bom.id).order_by("id"))
    product_ids = [_recipe_part_info(r)["product_id"] for r in recipes]
    meta_map = _build_product_meta_map(product_ids)
    recipe_items = []
    for recipe in recipes:
        part = _recipe_part_info(recipe)
        meta = _product_meta_from_map(meta_map, part["product_id"])
        recipe_items.append(
            {
                "part_product_id": part["product_id"],
                "part_product_name": part["product_name"] or meta.get("name") or "",
                "part_material_code": meta["part_material_code"],
                "part_product_type": meta["part_product_type"],
                "part_product_type_name": meta["part_product_type_name"],
                "part_quantity": part["quantity"],
            }
        )
    return {
        "id": bom.id,
        "bom_model": bom.bom_model,
        "bom_name": bom.bom_name or "",
        "material_code": bom.material_code or "",
        "type": bom.type,
        "type_name": bom.get_type_display(),
        "recipes": recipe_items,
    }


def _resolve_product_for_import(product_id=None, material_code=None, product_name=None):
    """导入零件：通过产品 ID、产品名称、物料编码组合匹配（各字段可空，非空则须一致）。"""
    pid = product_id
    code = (material_code or "").strip()
    name = (product_name or "").strip()

    if pid in (None, "") and not code and not name:
        raise ValueError("零件明细需填写产品ID、产品名称或物料编码至少一项")

    qs = Product.objects.filter(is_del=0)

    if pid not in (None, ""):
        try:
            qs = qs.filter(id=int(pid))
        except (TypeError, ValueError):
            raise ValueError(f"产品ID无效（ID={pid}）")

    if code:
        qs = qs.filter(material_code=code)

    if name:
        qs = qs.filter(name=name)

    count = qs.count()
    if count == 0:
        criteria = []
        if pid not in (None, ""):
            criteria.append(f"ID={pid}")
        if name:
            criteria.append(f"名称「{name}」")
        if code:
            criteria.append(f"物料编码「{code}」")
        raise ValueError(f"未找到匹配的产品（{'、'.join(criteria)}）")
    if count > 1:
        raise ValueError("匹配到多个产品，请补充更精确的匹配条件")

    return qs.first()


def _normalize_import_recipes(recipes_data):
    if not isinstance(recipes_data, list) or not recipes_data:
        raise ValueError("BOM 至少需绑定一条零件明细")

    normalized = []
    seen_product_ids = set()
    for index, item in enumerate(recipes_data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index} 条零件明细格式错误")

        product = _resolve_product_for_import(
            product_id=item.get("product_id") or item.get("part_product_id"),
            material_code=item.get("material_code")
            or item.get("part_material_code"),
            product_name=item.get("product_name")
            or item.get("part_product_name"),
        )
        if product.id in seen_product_ids:
            raise ValueError(f"同一 BOM 不能重复绑定产品「{product.name}」")
        seen_product_ids.add(product.id)

        qty = _int_or_none(item.get("quantity") or item.get("part_quantity"), "用量")
        if qty is None or qty < 1:
            raise ValueError(f"产品「{product.name}」的用量必须大于 0")

        normalized.append({"product_id": product.id, "quantity": qty})
    return normalized


def bom_export(request):
    """导出 BOM 清单（结构化：主表 + 零件明细）"""
    qs = _build_bom_queryset(request)
    items = [_serialize_bom_export_item(bom) for bom in qs]

    return JsonResponse(
        {
            "code": "00000",
            "msg": "成功",
            "data": {"items": items, "total": len(items)},
        }
    )


def _assert_bom_not_exists_for_import(bom_model, material_code):
    if BomList.objects.filter(is_del=0, bom_model=bom_model).exists():
        raise ValueError(f"BOM型号「{bom_model}」已存在，不允许重复导入")
    if material_code and BomList.objects.filter(is_del=0, material_code=material_code).exists():
        raise ValueError(f"BOM物料编码「{material_code}」已存在，不允许重复导入")


def _create_bom_from_import_item(item):
    if item.get("id"):
        raise ValueError("导入仅支持新增 BOM，请勿填写 BOM ID")

    body = {
        "bom_model": item.get("bom_model"),
        "bom_name": item.get("bom_name"),
        "material_code": item.get("material_code"),
        "type": item.get("type"),
        "recipes": item.get("recipes") or [],
    }
    bom_model, bom_name, material_code = _parse_bom_header_fields(body)
    _assert_bom_not_exists_for_import(bom_model, material_code)

    bom_type = _parse_bom_type(body.get("type"))
    if bom_type is None:
        bom_type = BomList.TYPE_JOINT

    recipes_data = _normalize_import_recipes(body.get("recipes"))

    with transaction.atomic():
        bom = BomList.objects.create(
            bom_model=bom_model,
            bom_name=bom_name,
            material_code=material_code,
            is_del=0,
            type=bom_type,
        )
        _save_recipes(bom, recipes_data)
    return bom


@csrf_exempt
@require_http_methods(["POST"])
def import_bom_batch(request):
    """批量导入 BOM（仅新增，逐条提交，部分成功）"""
    try:
        body = json.loads(request.body or "{}")
        items = body.get("items")
        if items is None and isinstance(body.get("item"), dict):
            items = [body.get("item")]
        if not isinstance(items, list) or not items:
            return JsonResponse({"code": "400", "msg": "导入数据不能为空"})

        success_count = 0
        fail_list = []
        seen_models = set()
        seen_codes = set()

        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                fail_list.append({"index": index, "bom_model": "", "msg": "数据格式错误"})
                continue

            bom_model = (item.get("bom_model") or "").strip()
            material_code = (item.get("material_code") or "").strip()

            if bom_model in seen_models:
                fail_list.append(
                    {
                        "index": index,
                        "bom_model": bom_model,
                        "msg": f"Excel 中 BOM型号「{bom_model}」重复",
                    }
                )
                continue
            if material_code and material_code in seen_codes:
                fail_list.append(
                    {
                        "index": index,
                        "bom_model": bom_model,
                        "msg": f"Excel 中 BOM物料编码「{material_code}」重复",
                    }
                )
                continue

            try:
                bom = _create_bom_from_import_item(item)
                seen_models.add(bom_model)
                if material_code:
                    seen_codes.add(material_code)
                success_count += 1
            except ValueError as e:
                fail_list.append(
                    {
                        "index": index,
                        "bom_model": bom_model,
                        "msg": str(e),
                    }
                )
            except Exception as e:
                fail_list.append(
                    {
                        "index": index,
                        "bom_model": bom_model,
                        "msg": f"导入失败: {str(e)}",
                    }
                )

        msg = f"导入完成：成功 {success_count} 条"
        if fail_list:
            msg += f"，失败 {len(fail_list)} 条"

        if success_count:
            _log_if_available(
                request,
                module="bom",
                module_name="产品BOM管理",
                operation_type="create",
                target_id=0,
                target_name="BOM批量导入",
                description=msg,
            )

        return JsonResponse(
            {
                "code": "00000",
                "msg": msg,
                "data": {
                    "success_count": success_count,
                    "fail_count": len(fail_list),
                    "fail_list": fail_list,
                },
            }
        )
    except json.JSONDecodeError:
        return JsonResponse({"code": "400", "msg": "请求体不是合法 JSON"})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"导入失败: {str(e)}"})


def bom_detail(request):
    bom_id = (request.GET.get("id", "") or request.GET.get("bom_id", "") or "").strip()
    if not bom_id:
        return JsonResponse({"code": "400", "msg": "缺少 BOM ID"})
    try:
        bom = BomList.objects.get(id=int(bom_id), is_del=0)
    except (BomList.DoesNotExist, TypeError, ValueError):
        return JsonResponse({"code": "404", "msg": "BOM 不存在"})

    recipes = list(AssemblyRecipe.objects.filter(bom_id=bom.id).order_by("id"))
    product_ids = [_recipe_part_info(r)["product_id"] for r in recipes]
    meta_map = _build_product_meta_map(product_ids)
    payload = _serialize_bom_header(bom, len(recipes))
    payload["recipes"] = [
        _serialize_recipe(r, _bom_display_name(bom), meta_map) for r in recipes
    ]
    return JsonResponse({"code": "00000", "msg": "成功", "data": payload})


@csrf_exempt
@require_http_methods(["POST"])
def create_bom(request):
    try:
        body = json.loads(request.body or "{}")
        bom_model, bom_name, material_code = _parse_bom_header_fields(body)

        bom_type = _parse_bom_type(body.get("type"))
        if bom_type is None:
            bom_type = BomList.TYPE_JOINT

        with transaction.atomic():
            bom = BomList.objects.create(
                bom_model=bom_model,
                bom_name=bom_name,
                material_code=material_code,
                is_del=0,
                type=bom_type,
            )
            old_recipes, new_recipes = _save_recipes(bom, body.get("recipes"))
        
        # 构建明细描述
        recipe_descriptions = []
        for recipe in new_recipes:
            part_info = _recipe_part_info(recipe)
            if part_info["product_name"]:
                recipe_descriptions.append(
                    f"{part_info['product_name']}: {part_info['quantity']}"
                )

        description = f"新增BOM: {_bom_log_label(bom)}"
        if recipe_descriptions:
            description += f" (明细: {', '.join(recipe_descriptions)})"
        _log_if_available(
            request,
            module='bom',
            module_name='产品BOM管理',
            operation_type='create',
            target_id=bom.id,
            target_name=_bom_log_label(bom),
            description=description,
        )

        return JsonResponse(
            {"code": "00000", "msg": "新增成功", "data": {"id": bom.id}}
        )
    except ValueError as e:
        return JsonResponse({"code": "400", "msg": str(e)})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"新增失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["POST"])
def update_bom(request):
    try:
        body = json.loads(request.body or "{}")
        bom_id = body.get("id")
        if not bom_id:
            return JsonResponse({"code": "400", "msg": "缺少 BOM ID"})
        bom_model, bom_name, material_code = _parse_bom_header_fields(body)

        bom_type = _parse_bom_type(body.get("type"))

        recipes_data = body.get("recipes")
        print(f"[DEBUG] update_bom: bom_id={bom_id}, recipes_data={recipes_data}")

        with transaction.atomic():
            bom = BomList.objects.get(id=int(bom_id), is_del=0)
            
            # 保存修改前的数据
            before_data = _bom_header_snapshot(bom)

            bom.bom_model = bom_model
            bom.bom_name = bom_name
            bom.material_code = material_code
            update_fields = ["bom_model", "bom_name", "material_code"]
            if bom_type is not None:
                bom.type = bom_type
                update_fields.append("type")
            bom.save(update_fields=update_fields)
            old_recipes, new_recipes = _save_recipes(bom, recipes_data)
            
            # 验证保存结果
            after_count = AssemblyRecipe.objects.filter(bom_id=bom.id).count()
            print(f"[DEBUG] After _save_recipes: count={after_count}")
        
        # 事务成功提交后的验证
        final_count = AssemblyRecipe.objects.filter(bom_id=bom.id).count()
        print(f"[DEBUG] Final count after commit: {final_count}")
        
        # 保存修改后的数据
        after_data = _bom_header_snapshot(bom)

        recipe_changes = []
        old_products = set()
        new_products = set()

        for recipe in old_recipes:
            part_info = _recipe_part_info(recipe)
            old_products.add(part_info["product_id"])

        for recipe in new_recipes:
            part_info = _recipe_part_info(recipe)
            new_products.add(part_info["product_id"])

        added_products = new_products - old_products
        removed_products = old_products - new_products
        common_products = old_products & new_products

        for product_id in added_products:
            recipe = next(
                (r for r in new_recipes if _recipe_part_info(r)["product_id"] == product_id),
                None,
            )
            if recipe:
                part_info = _recipe_part_info(recipe)
                recipe_changes.append(
                    format_bom_recipe_added(part_info["product_name"], part_info["quantity"])
                )

        for product_id in removed_products:
            recipe = next(
                (r for r in old_recipes if _recipe_part_info(r)["product_id"] == product_id),
                None,
            )
            if recipe:
                part_info = _recipe_part_info(recipe)
                recipe_changes.append(format_bom_recipe_removed(part_info["product_name"]))

        for product_id in common_products:
            old_recipe = next(
                (r for r in old_recipes if _recipe_part_info(r)["product_id"] == product_id),
                None,
            )
            new_recipe = next(
                (r for r in new_recipes if _recipe_part_info(r)["product_id"] == product_id),
                None,
            )
            if old_recipe and new_recipe:
                old_info = _recipe_part_info(old_recipe)
                new_info = _recipe_part_info(new_recipe)
                if old_info["quantity"] != new_info["quantity"]:
                    recipe_changes.append(
                        format_bom_recipe_quantity_change(
                            new_info["product_name"],
                            old_info["quantity"],
                            new_info["quantity"],
                        )
                    )

        description = format_bom_update_description(
            _bom_log_label(bom),
            before_data,
            after_data,
            recipe_changes,
        )

        _log_if_available(
            request,
            module='bom',
            module_name='产品BOM管理',
            operation_type='update',
            target_id=bom.id,
            target_name=_bom_log_label(bom),
            before_data=before_data,
            after_data=after_data,
            description=description,
        )

        return JsonResponse(
            {"code": "00000", "msg": "更新成功", "data": {"id": bom.id}}
        )
    except BomList.DoesNotExist:
        return JsonResponse({"code": "404", "msg": "BOM 不存在"})
    except ValueError as e:
        return JsonResponse({"code": "400", "msg": str(e)})
    except Exception as e:
        print(f"[ERROR] update_bom failed: {str(e)}")
        return JsonResponse({"code": "500", "msg": f"更新失败: {str(e)}"})


def _collect_assembly_requirements(recipes, assemble_qty):
    """汇总组装所需各零件数量"""
    requirements = {}
    for recipe in recipes:
        part = _recipe_part_info(recipe)
        product_id = part["product_id"]
        if not product_id:
            continue
        per_unit = part["quantity"] or 0
        if per_unit < 1:
            raise ValueError(f"零件「{part['product_name']}」用量无效")
        needed = per_unit * assemble_qty
        if product_id in requirements:
            requirements[product_id]["required"] += needed
        else:
            meta = _lookup_product_part_meta(product_id)
            requirements[product_id] = {
                "product_id": product_id,
                "product_name": part["product_name"],
                "product_type": meta["part_product_type"],
                "product_type_name": meta["part_product_type_name"],
                "required": needed,
            }
    return list(requirements.values())


@csrf_exempt
@require_http_methods(["POST"])
def assemble_bom(request):
    """按 BOM 组装产品，可选是否扣减关联零件库存"""
    try:
        body = json.loads(request.body or "{}")
        bom_id = body.get("bom_id") or body.get("id")
        if not bom_id:
            return JsonResponse({"code": "400", "msg": "请选择 BOM"})
        assemble_qty = _int_or_none(body.get("quantity"), "组装数量")
        if assemble_qty is None or assemble_qty < 1:
            return JsonResponse({"code": "400", "msg": "组装数量必须大于 0"})
        deduct_materials = _bool_param(
            body.get("deduct_materials", body.get("deductMaterials")),
            default=True,
        )

        bom = BomList.objects.get(id=int(bom_id), is_del=0)
        recipes = list(AssemblyRecipe.objects.filter(bom_id=bom.id).order_by("id"))
        if deduct_materials and not recipes:
            return JsonResponse({"code": "400", "msg": "该 BOM 暂无零件明细，无法组装"})

        consumed = []
        consumed_details = []
        finish_products_created = []

        with transaction.atomic():
            if deduct_materials:
                requirements = _collect_assembly_requirements(recipes, assemble_qty)

                for req in requirements:
                    product = Product.objects.select_for_update().get(
                        id=req["product_id"], is_del=0
                    )
                    current = product.quantity if product.quantity is not None else 0
                    needed = req["required"]
                    if current < needed:
                        raise ValueError(
                            f"「{product.name}」库存不足：需要 {needed}，当前 {current}"
                        )

                    product.quantity = current - needed
                    product.save(update_fields=["quantity", "updated_at"])

                    consumed.append(
                        {
                            "product_id": product.id,
                            "product_name": product.name,
                            "product_type": product.type,
                            "product_type_name": product_type_label(product.type),
                            "consumed": needed,
                            "remaining": product.quantity,
                        }
                    )
                    consumed_details.append(f"{product.name} - {needed}")

            now = timezone.now()
            for idx in range(assemble_qty):
                finish_product = FinishProduct.objects.create(
                    sn_code=None,
                    bom_id=bom.id,
                    name=_bom_display_name(bom),
                    status=FinishProduct.STATUS_UNTESTED,
                    description="",
                    inventory_stock=FinishProduct.INVENTORY_NOT_IN,
                    repair=FinishProduct.REPAIR_NEW,
                    create_time=now,
                    update_time=now,
                )
                finish_products_created.append(
                    {
                        "id": finish_product.id,
                        "sn_code": finish_product.sn_code,
                        "bom_id": finish_product.bom_id,
                        "name": finish_product.name,
                        "status": finish_product.status,
                        "create_time": format_local_datetime(finish_product.create_time) or "",
                    }
                )

        _log_if_available(
            request,
            module='bom',
            module_name='产品BOM管理',
            operation_type='assemble',
            target_id=bom.id,
            target_name=_bom_log_label(bom),
            after_data={
                "consumed": consumed,
                "assemble_quantity": assemble_qty,
                "deduct_materials": deduct_materials,
            },
            description=format_bom_assemble_description(
                _bom_log_label(bom),
                assemble_qty,
                consumed_details,
                deduct_materials=deduct_materials,
            ),
        )

        msg = "组装成功，已生成成品"
        if deduct_materials:
            msg += "并扣减库存"
        else:
            msg += "（未扣减物料）"

        return JsonResponse(
            {
                "code": "00000",
                "msg": msg,
                "data": {
                    "bom_id": bom.id,
                    "bom_model": bom.bom_model,
                    "bom_name": bom.bom_name or "",
                    "material_code": bom.material_code or "",
                    "assemble_quantity": assemble_qty,
                    "deduct_materials": deduct_materials,
                    "consumed": consumed,
                    "finish_products": finish_products_created,
                },
            }
        )
    except BomList.DoesNotExist:
        return JsonResponse({"code": "404", "msg": "BOM 不存在"})
    except Product.DoesNotExist:
        return JsonResponse({"code": "404", "msg": "零件产品不存在或已删除"})
    except ValueError as e:
        return JsonResponse({"code": "400", "msg": str(e)})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"组装失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["POST"])
def delete_bom(request):
    try:
        body = json.loads(request.body or "{}")
        bom_id = body.get("id")
        if not bom_id:
            return JsonResponse({"code": "400", "msg": "缺少 BOM ID"})

        with transaction.atomic():
            bom = BomList.objects.get(id=int(bom_id), is_del=0)
            
            # 保存删除前的数据
            before_data = _bom_header_snapshot(bom)
            
            bom.is_del = 1
            bom.save(update_fields=["is_del"])
            AssemblyRecipe.objects.filter(bom_id=bom.id).delete()
            
            # 记录操作日志
            _log_if_available(
                request,
                module='bom',
                module_name='产品BOM管理',
                operation_type='delete',
                target_id=bom.id,
                target_name=_bom_log_label(bom),
                before_data=before_data,
                description=f"删除BOM: {_bom_log_label(bom)}",
            )

        return JsonResponse(
            {"code": "00000", "msg": "删除成功", "data": {"id": bom_id}}
        )
    except BomList.DoesNotExist:
        return JsonResponse({"code": "404", "msg": "BOM 不存在"})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"删除失败: {str(e)}"})