"""BOM 物料绑定解析工具。

设计说明：
- BOM 明细(assembly_recipes)通过 raw_material_id / component_id 直接绑定产品
- BOM 成品关联通过 BomList.finished_product_id 直接绑定产品
- 流程上禁止删除被 BOM/生产计划引用的产品（products 视图 delete_product 校验）
- 因此不再需要 material_code 回退逻辑，物料编码可自由变更而不影响关联

使用方式：
    from apps.product.boms.utils import build_bom_requirements

    bom_requirements = build_bom_requirements(bom_ids)
    # bom_requirements: {bom_id: {product_id: qty}}

    for bom_id, req_map in bom_requirements.items():
        for product_id, unit_qty in req_map.items():
            stock_map[product_id] = stock_map.get(product_id, 0) - unit_qty * plan_qty
"""

from __future__ import annotations

from typing import Dict


def build_bom_requirements(bom_ids) -> Dict[int, Dict[int, float]]:
    """构建 {bom_id: {product_id: qty}} 映射。

    直接使用 assembly_recipes.raw_material_id / component_id 作为产品 ID
    （流程上禁止删除被引用产品，无需 material_code 回退）。

    返回: dict[bom_id, dict[product_id, float_qty]]
    """
    bom_requirements: Dict[int, Dict[int, float]] = {}
    bom_ids = list(bom_ids)
    if not bom_ids:
        return bom_requirements

    # 延迟导入避免循环依赖
    from .models import AssemblyRecipe

    recipes_by_bom = {}
    for r in AssemblyRecipe.objects.filter(bom_id__in=bom_ids):
        recipes_by_bom.setdefault(r.bom_id, []).append(r)

    for bom_id, recipes in recipes_by_bom.items():
        for r in recipes:
            # 直接用绑定的产品 ID（优先 raw_material_id，其次 component_id）
            product_id = r.raw_material_id or r.component_id
            if not product_id:
                continue
            qty = float(
                r.raw_material_quantity if r.raw_material_id else r.component_quantity or 1
            )
            bom_requirements.setdefault(bom_id, {})
            bom_requirements[bom_id][product_id] = float(
                bom_requirements[bom_id].get(product_id, 0)
            ) + qty

    return bom_requirements
