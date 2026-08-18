"""BOM 物料绑定解析工具。

核心目标：解决"产品删除后重建导致 ID 变化，BOM 明细(assembly_recipes)
仍引用旧 ID"的问题。

策略：
- assembly_recipes 表冗余存储 material_code（物料编码）
- 解析 recipe 对应的"当前有效产品"时：
  1. 优先按 component_id / raw_material_id 查未删除(is_del=0)的产品
  2. 若该 ID 对应产品已删除或不存在，则按 material_code 在未删除产品中回退查找
- 这样删除 A 物料后重建同名同编码的 A 物料，BOM 仍能正确组装新产品

使用方式：
    from apps.product.boms.utils import build_effective_pid_map

    recipes = list(AssemblyRecipe.objects.filter(bom_id__in=bom_ids))
    pid_map = build_effective_pid_map(recipes)  # {bind_id: effective_product_id}

    # 后续库存查询用 effective id
    effective_ids = set(pid_map.values())
    stock_map = {p.id: p.quantity for p in Product.objects.filter(id__in=effective_ids, is_del=0)}

    # 消耗库存时把 bind_id 转成 effective id
    for recipe in recipes:
        bind_id = recipe.component_id or recipe.raw_material_id
        eff_id = pid_map.get(bind_id, bind_id)
        stock_map[eff_id] = ...
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from apps.product.products.models import Product


def _recipe_bind_id(recipe) -> Optional[int]:
    """获取 recipe 绑定的产品 ID（优先 component_id，其次 raw_material_id）。"""
    if getattr(recipe, "component_id", None):
        return recipe.component_id
    if getattr(recipe, "raw_material_id", None):
        return recipe.raw_material_id
    return None


def _recipe_material_code(recipe) -> str:
    """获取 recipe 冗余存储的 material_code。"""
    return (getattr(recipe, "material_code", None) or "").strip()


def resolve_effective_product(recipe) -> Optional[Product]:
    """解析单条 recipe 对应的当前有效产品。

    优先按 ID 查未删除产品；ID 失效时按 material_code 回退查找。
    返回 None 表示无法定位有效产品。
    """
    bind_id = _recipe_bind_id(recipe)
    if bind_id:
        product = Product.objects.filter(id=bind_id, is_del=0).first()
        if product:
            return product

    code = _recipe_material_code(recipe)
    if code:
        return Product.objects.filter(material_code=code, is_del=0).first()

    return None


def build_effective_pid_map(recipes: Iterable) -> Dict[int, int]:
    """批量构建 {bind_id: effective_product_id} 映射。

    - bind_id 仍有效(is_del=0) 时，effective_id == bind_id
    - bind_id 失效时，按 material_code 回退找到的有效产品 id
    - 既失效又无法回退的 bind_id 不放入映射（调用方应自行处理）

    一次批量查询完成，避免在循环里逐条查库。
    """
    recipes = list(recipes)
    bind_ids = [pid for pid in (_recipe_bind_id(r) for r in recipes) if pid]
    if not bind_ids:
        return {}

    # 1. 查询哪些 bind_id 仍有效
    valid_products = Product.objects.filter(id__in=bind_ids, is_del=0)
    valid_id_set = {p.id for p in valid_products}
    pid_map: Dict[int, int] = {pid: pid for pid in valid_id_set}

    # 2. 收集失效 bind_id 对应的 material_code
    invalid_codes: Dict[str, List[int]] = {}
    for r in recipes:
        bid = _recipe_bind_id(r)
        if bid and bid not in valid_id_set:
            code = _recipe_material_code(r)
            if code:
                invalid_codes.setdefault(code, []).append(bid)

    # 3. 按 material_code 批量回退查找
    if invalid_codes:
        fallback_products = Product.objects.filter(
            material_code__in=list(invalid_codes.keys()), is_del=0
        )
        code_to_pid = {p.material_code: p.id for p in fallback_products}
        for code, bid_list in invalid_codes.items():
            eff_id = code_to_pid.get(code)
            if eff_id:
                for bid in bid_list:
                    pid_map[bid] = eff_id

    return pid_map


def effective_pid(pid_map: Dict[int, int], bind_id) -> Optional[int]:
    """从映射中取 effective id，找不到则原样返回 bind_id（兼容旧逻辑）。"""
    if not bind_id:
        return None
    return pid_map.get(bind_id, bind_id)


def collect_effective_product_ids(recipes: Iterable) -> List[int]:
    """收集 recipes 解析后的所有有效产品 ID（去重）。"""
    pid_map = build_effective_pid_map(recipes)
    return list(set(pid_map.values()))


def build_bom_requirements(bom_ids):
    """构建 {bom_id: {effective_product_id: qty}} 映射。

    通过 material_code 回退解析有效产品 ID，确保产品删除重建后
    库存计算仍指向当前有效记录。
    返回 (bom_requirements, pid_map)。
    """
    bom_requirements = {}
    pid_map = {}
    bom_ids = list(bom_ids)
    if not bom_ids:
        return bom_requirements, pid_map

    # 延迟导入避免循环依赖
    from .models import AssemblyRecipe

    recipes_by_bom = {}
    all_recipes = []
    for r in AssemblyRecipe.objects.filter(bom_id__in=bom_ids):
        recipes_by_bom.setdefault(r.bom_id, []).append(r)
        all_recipes.append(r)

    pid_map = build_effective_pid_map(all_recipes)

    for bom_id, recipes in recipes_by_bom.items():
        for r in recipes:
            bind_id = r.raw_material_id or r.component_id
            if not bind_id:
                continue
            eff_id = pid_map.get(bind_id, bind_id)
            qty = float(
                r.raw_material_quantity if r.raw_material_id else r.component_quantity or 1
            )
            bom_requirements.setdefault(bom_id, {})
            bom_requirements[bom_id][eff_id] = float(
                bom_requirements[bom_id].get(eff_id, 0)
            ) + qty

    return bom_requirements, pid_map
