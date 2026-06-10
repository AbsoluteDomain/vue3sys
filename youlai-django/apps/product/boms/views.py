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
from .models import AssemblyRecipe, BomList

from apps.system.operation_logs.utils import (
    format_bom_assemble_deduct_description,
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
            "product_type": "finished",
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


def _serialize_recipe(row, bom_name=None):
    part = _recipe_part_info(row)
    return {
        "id": row.id,
        "bom_id": row.bom_id,
        "bom_name": bom_name,
        "part_product_id": part["product_id"],
        "part_product_name": part["product_name"],
        "part_product_type": part["product_type"],
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
        "component_id": None,
        "component_name": None,
        "component_quantity": None,
    }
    if product.type == "raw":
        fields["raw_material_id"] = product.id
        fields["raw_material_name"] = product.name
        fields["raw_material_quantity"] = qty
    else:
        fields["component_id"] = product.id
        fields["component_name"] = product.name
        fields["component_quantity"] = qty
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


def bom_list(request):
    page_num, page_size = _parse_page_params(request)
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
    sort_prop = (request.GET.get("sort_prop", "") or "").strip()
    sort_order = (request.GET.get("sort_order", "") or "").strip()

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
    qs = qs.order_by(f"{db_sort_prefix}{db_sort_field}")

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


def bom_detail(request):
    bom_id = (request.GET.get("id", "") or request.GET.get("bom_id", "") or "").strip()
    if not bom_id:
        return JsonResponse({"code": "400", "msg": "缺少 BOM ID"})
    try:
        bom = BomList.objects.get(id=int(bom_id), is_del=0)
    except (BomList.DoesNotExist, TypeError, ValueError):
        return JsonResponse({"code": "404", "msg": "BOM 不存在"})

    recipes = AssemblyRecipe.objects.filter(bom_id=bom.id).order_by("id")
    payload = _serialize_bom_header(bom, recipes.count())
    payload["recipes"] = [
        _serialize_recipe(r, _bom_display_name(bom)) for r in recipes
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
            requirements[product_id] = {
                "product_id": product_id,
                "product_name": part["product_name"],
                "product_type": part["product_type"],
                "required": needed,
            }
    return list(requirements.values())


@csrf_exempt
@require_http_methods(["POST"])
def assemble_bom(request):
    """按 BOM 组装产品，扣减关联零件库存"""
    try:
        body = json.loads(request.body or "{}")
        bom_id = body.get("bom_id") or body.get("id")
        if not bom_id:
            return JsonResponse({"code": "400", "msg": "请选择 BOM"})
        assemble_qty = _int_or_none(body.get("quantity"), "组装数量")
        if assemble_qty is None or assemble_qty < 1:
            return JsonResponse({"code": "400", "msg": "组装数量必须大于 0"})

        # 先检查BOM是否存在
        bom = BomList.objects.get(id=int(bom_id), is_del=0)
        recipes = list(AssemblyRecipe.objects.filter(bom_id=bom.id).order_by("id"))
        if not recipes:
            return JsonResponse({"code": "400", "msg": "该 BOM 暂无零件明细，无法组装"})

        # 收集日志记录所需数据
        log_entries = []
        consumed = []
        consumed_details = []
        finish_products_created = []

        with transaction.atomic():
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
                
                # 保存修改前的数据
                before_data = {"quantity": current}
                
                product.quantity = current - needed
                product.save(update_fields=["quantity", "updated_at"])
                
                # 保存修改后的数据
                after_data = {"quantity": product.quantity}
                
                consumed.append(
                    {
                        "product_id": product.id,
                        "product_name": product.name,
                        "product_type": product.type,
                        "consumed": needed,
                        "remaining": product.quantity,
                    }
                )
                consumed_details.append(f"{product.name} - {needed}")

                log_entries.append({
                    "type": "product_update",
                    "product_id": product.id,
                    "product_name": product.name,
                    "before_data": before_data,
                    "after_data": after_data,
                    "description": format_bom_assemble_deduct_description(product.name, needed),
                })

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
        
        # 事务成功后记录操作日志（在事务外执行）
        for entry in log_entries:
            _log_if_available(
                request,
                module='productStock',
                module_name='库存',
                operation_type='update',
                target_id=entry["product_id"],
                target_name=entry["product_name"],
                before_data=entry["before_data"],
                after_data=entry["after_data"],
                description=entry["description"],
            )

        _log_if_available(
            request,
            module='bom',
            module_name='产品BOM管理',
            operation_type='update',
            target_id=bom.id,
            target_name=_bom_log_label(bom),
            before_data=_bom_header_snapshot(bom),
            description=format_bom_assemble_description(
                _bom_log_label(bom),
                assemble_qty,
                consumed_details,
            ),
        )

        return JsonResponse(
            {
                "code": "00000",
                "msg": "组装成功",
                "data": {
                    "bom_id": bom.id,
                    "bom_model": bom.bom_model,
                    "bom_name": bom.bom_name or "",
                    "material_code": bom.material_code or "",
                    "assemble_quantity": assemble_qty,
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