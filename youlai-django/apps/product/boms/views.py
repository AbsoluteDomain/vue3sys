import json

from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.product.products.models import Product
from .models import AssemblyRecipe, BomList

# 安全地引入操作日志模块
try:
    from apps.system.operation_logs.services import log_operation
    from apps.system.operation_logs.utils import compare_changes, format_changes_text
    from rest_framework_simplejwt.authentication import JWTAuthentication
    from rest_framework.exceptions import AuthenticationFailed
    OPERATION_LOGS_AVAILABLE = True
except ImportError:
    OPERATION_LOGS_AVAILABLE = False


def _get_user_from_request(request):
    """从请求中获取用户信息"""
    if not OPERATION_LOGS_AVAILABLE:
        return None
    try:
        jwt_auth = JWTAuthentication()
        user, token = jwt_auth.authenticate(request)
        return user
    except (AuthenticationFailed, Exception):
        return None


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
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


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
        "bom_name": bom.bom_name,
        "recipe_count": recipe_count,
    }


def _serialize_recipe(row):
    part = _recipe_part_info(row)
    return {
        "id": row.id,
        "bom_id": row.bom_id,
        "bom_name": row.bom_name,
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
        "bom_name": bom.bom_name,
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
    bom_name = (request.GET.get("bom_name", "") or "").strip()
    sort_prop = (request.GET.get("sort_prop", "") or "").strip()
    sort_order = (request.GET.get("sort_order", "") or "").strip()

    qs = BomList.objects.filter(is_del=0)

    if bom_id:
        try:
            qs = qs.filter(id=int(bom_id))
        except (TypeError, ValueError):
            qs = qs.none()
    if bom_name:
        qs = qs.filter(bom_name__icontains=bom_name)

    sort_field_map = {"id": "id", "bom_name": "bom_name"}
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
    payload["recipes"] = [_serialize_recipe(r) for r in recipes]
    return JsonResponse({"code": "00000", "msg": "成功", "data": payload})


@csrf_exempt
@require_http_methods(["POST"])
def create_bom(request):
    try:
        body = json.loads(request.body or "{}")
        bom_name = (body.get("bom_name") or "").strip()
        if not bom_name:
            return JsonResponse({"code": "400", "msg": "BOM 名称不能为空"})

        with transaction.atomic():
            bom = BomList.objects.create(bom_name=bom_name, is_del=0)
            old_recipes, new_recipes = _save_recipes(bom, body.get("recipes"))
        
        # 构建明细描述
        recipe_descriptions = []
        for recipe in new_recipes:
            part_info = _recipe_part_info(recipe)
            if part_info["product_name"]:
                recipe_descriptions.append(f"{part_info['product_name']}: {part_info['quantity']}")
        
        # 记录操作日志
        if OPERATION_LOGS_AVAILABLE:
            user = _get_user_from_request(request)
            if user:
                description = f"新增BOM：{bom.bom_name}"
                if recipe_descriptions:
                    description += f"（明细：{', '.join(recipe_descriptions)}）"
                log_operation(
                    user_id=user.id,
                    user_name=user.username,
                    module='productBom',
                    operation_type='create',
                    target_id=bom.id,
                    target_name=bom.bom_name,
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
        bom_name = (body.get("bom_name") or "").strip()
        if not bom_name:
            return JsonResponse({"code": "400", "msg": "BOM 名称不能为空"})

        with transaction.atomic():
            bom = BomList.objects.get(id=int(bom_id), is_del=0)
            
            # 保存修改前的数据
            before_data = {
                "bom_name": bom.bom_name,
            }
            
            old_bom_name = bom.bom_name
            bom.bom_name = bom_name
            bom.save(update_fields=["bom_name"])
            old_recipes, new_recipes = _save_recipes(bom, body.get("recipes"))
            
            # 保存修改后的数据
            after_data = {
                "bom_name": bom.bom_name,
            }
            
            # 对比变更
            description = f"修改BOM：{bom.bom_name}"
            recipe_changes = []
            
            if OPERATION_LOGS_AVAILABLE:
                changes = compare_changes(before_data, after_data)
                changes_text = format_changes_text(changes)
                
                # 对比配方变更
                old_products = set()
                new_products = set()
                
                # 获取旧配方的产品
                for recipe in old_recipes:
                    part_info = _recipe_part_info(recipe)
                    old_products.add(part_info["product_id"])
                
                # 获取新配方的产品
                for recipe in new_recipes:
                    part_info = _recipe_part_info(recipe)
                    new_products.add(part_info["product_id"])
                
                # 找出新增和删除的产品
                added_products = new_products - old_products
                removed_products = old_products - new_products
                
                # 找出变更的产品
                common_products = old_products & new_products
                
                # 处理新增
                for product_id in added_products:
                    recipe = next((r for r in new_recipes if _recipe_part_info(r)["product_id"] == product_id), None)
                    if recipe:
                        part_info = _recipe_part_info(recipe)
                        recipe_changes.append(f"新增{part_info['product_name']}: {part_info['quantity']}")
                
                # 处理删除
                for product_id in removed_products:
                    recipe = next((r for r in old_recipes if _recipe_part_info(r)["product_id"] == product_id), None)
                    if recipe:
                        part_info = _recipe_part_info(recipe)
                        recipe_changes.append(f"删除{part_info['product_name']}")
                
                # 处理变更
                for product_id in common_products:
                    old_recipe = next((r for r in old_recipes if _recipe_part_info(r)["product_id"] == product_id), None)
                    new_recipe = next((r for r in new_recipes if _recipe_part_info(r)["product_id"] == product_id), None)
                    if old_recipe and new_recipe:
                        old_info = _recipe_part_info(old_recipe)
                        new_info = _recipe_part_info(new_recipe)
                        if old_info["quantity"] != new_info["quantity"]:
                            recipe_changes.append(f"{new_info['product_name']}: {old_info['quantity']} → {new_info['quantity']}")
                
                # 合并所有变更
                all_changes = []
                if changes_text:
                    all_changes.append(changes_text)
                all_changes.extend(recipe_changes)
                
                if all_changes:
                    description += f"（{'; '.join(all_changes)}）"
                
                # 记录操作日志
                user = _get_user_from_request(request)
                if user:
                    log_operation(
                        user_id=user.id,
                        user_name=user.username,
                        module='productBom',
                        operation_type='update',
                        target_id=bom.id,
                        target_name=bom.bom_name,
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

        with transaction.atomic():
            bom = BomList.objects.get(id=int(bom_id), is_del=0)
            recipes = list(AssemblyRecipe.objects.filter(bom_id=bom.id).order_by("id"))
            if not recipes:
                return JsonResponse({"code": "400", "msg": "该 BOM 暂无零件明细，无法组装"})

            requirements = _collect_assembly_requirements(recipes, assemble_qty)
            consumed = []
            consumed_details = []

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
                consumed_details.append(f"{product.name}: {needed}")
                
                # 记录每个零件的库存扣减日志
                if OPERATION_LOGS_AVAILABLE:
                    user = _get_user_from_request(request)
                    if user:
                        log_operation(
                            user_id=user.id,
                            user_name=user.username,
                            module='product',
                            operation_type='update',
                            target_id=product.id,
                            target_name=product.name,
                            before_data=before_data,
                            after_data=after_data,
                            description=f"BOM组装扣减：{product.name}，数量：{needed}",
                        )
            
            # 记录BOM组装操作日志
            if OPERATION_LOGS_AVAILABLE:
                user = _get_user_from_request(request)
                if user:
                    log_operation(
                        user_id=user.id,
                        user_name=user.username,
                        module='productBom',
                        operation_type='update',
                        target_id=bom.id,
                        target_name=bom.bom_name,
                        before_data={"bom_name": bom.bom_name},
                        description=f"BOM组装：{bom.bom_name}，组装数量：{assemble_qty}，扣减零件：{', '.join(consumed_details)}",
                    )

        return JsonResponse(
            {
                "code": "00000",
                "msg": "组装成功",
                "data": {
                    "bom_id": bom.id,
                    "bom_name": bom.bom_name,
                    "assemble_quantity": assemble_qty,
                    "consumed": consumed,
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
            before_data = {"bom_name": bom.bom_name}
            
            bom.is_del = 1
            bom.save(update_fields=["is_del"])
            AssemblyRecipe.objects.filter(bom_id=bom.id).delete()
            
            # 记录操作日志
            if OPERATION_LOGS_AVAILABLE:
                user = _get_user_from_request(request)
                if user:
                    log_operation(
                        user_id=user.id,
                        user_name=user.username,
                        module='productBom',
                        operation_type='delete',
                        target_id=bom.id,
                        target_name=bom.bom_name,
                        before_data=before_data,
                        description=f"删除BOM：{bom.bom_name}",
                    )

        return JsonResponse(
            {"code": "00000", "msg": "删除成功", "data": {"id": bom_id}}
        )
    except BomList.DoesNotExist:
        return JsonResponse({"code": "404", "msg": "BOM 不存在"})
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"删除失败: {str(e)}"})
