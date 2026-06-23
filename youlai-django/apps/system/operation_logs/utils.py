PRODUCT_FIELD_LABELS = {
    "name": "名称",
    "type": "类型",
    "draw_code": "图号",
    "material_code": "物料编码",
    "quantity": "数量",
    "unit": "单位",
    "location": "位置",
    "description": "描述",
    "alert_quantity": "报警数量",
}

BOM_FIELD_LABELS = {
    "bom_model": "BOM型号",
    "bom_name": "BOM名称",
    "material_code": "物料编码",
    "type": "类型",
}

BOM_TYPE_LABELS = {
    0: "关节",
    1: "机械臂",
    2: "其他",
}

PRODUCT_TYPE_LABELS = {
    0: "自制",
    1: "外协",
    2: "外购",
}


def _display_value(value, value_formatters=None, field_key=None):
    if value_formatters and field_key in value_formatters:
        return value_formatters[field_key](value)
    if value is None or value == "":
        return "空"
    return value


def compare_changes(before_data, after_data):
    """比较修改前后的数据，返回变更信息。"""
    changes = {}
    before_dict = before_data or {}
    after_dict = after_data or {}

    for key in set(before_dict.keys()).union(set(after_dict.keys())):
        before_val = before_dict.get(key)
        after_val = after_dict.get(key)
        if before_val != after_val:
            changes[key] = {"before": before_val, "after": after_val}

    return changes


def format_changes_text(changes, field_labels=None, value_formatters=None):
    """将变更信息格式化为可读文本，例如：数量: 5 -> 6"""
    if not changes:
        return ""

    field_labels = field_labels or {}
    change_texts = []
    for key, val in changes.items():
        label = field_labels.get(key, key)
        before = _display_value(val.get("before"), value_formatters, key)
        after = _display_value(val.get("after"), value_formatters, key)
        change_texts.append(f"{label}: {before} -> {after}")

    return "; ".join(change_texts)


def format_target_update(prefix, target_name, before_data, after_data,
                         field_labels=None, value_formatters=None):
    """生成带具体变动明细的描述，例如：修改库存: 铜环 (数量: 10 -> 20)"""
    changes = compare_changes(before_data, after_data)
    if not changes:
        return f"{prefix}: {target_name}"

    detail = format_changes_text(changes, field_labels, value_formatters)
    return f"{prefix}: {target_name} ({detail})"


def format_product_type(value):
    if value is None or value == "":
        return "空"
    try:
        return PRODUCT_TYPE_LABELS.get(int(value), value)
    except (TypeError, ValueError):
        return value


def format_product_update_description(product_name, before_data, after_data):
    return format_target_update(
        "修改库存",
        product_name,
        before_data,
        after_data,
        field_labels=PRODUCT_FIELD_LABELS,
        value_formatters={"type": format_product_type},
    )


def format_product_create_description(product):
    type_label = format_product_type(product.type)
    quantity = product.quantity if product.quantity is not None else 0
    return f"新增库存: {product.name} (数量: {quantity}, 类型: {type_label})"


def format_stock_adjust_description(action, product_name, delta):
    return f"{action}: {product_name}, 数量: {delta}"


def format_bom_update_description(bom_name, before_data, after_data, recipe_change_texts=None):
    header_changes = compare_changes(before_data, after_data)
    detail_parts = []

    header_detail = format_changes_text(header_changes, BOM_FIELD_LABELS)
    if header_detail:
        detail_parts.append(header_detail)
    if recipe_change_texts:
        detail_parts.extend(recipe_change_texts)

    if not detail_parts:
        return f"修改BOM: {bom_name}"

    return f"修改BOM: {bom_name} ({'; '.join(detail_parts)})"


def format_bom_recipe_quantity_change(product_name, before_qty, after_qty):
    return f"{product_name}: {before_qty} -> {after_qty}"


def format_bom_recipe_added(product_name, quantity):
    return f"新增{product_name}: {quantity}"


def format_bom_recipe_removed(product_name):
    return f"删除{product_name}"


def format_bom_assemble_description(bom_name, assemble_qty, consumed_details):
    parts_text = ", ".join(consumed_details)
    return f"BOM组装: {bom_name}, 组装数量: {assemble_qty}, 扣减零件: {parts_text}"


def format_bom_assemble_deduct_description(product_name, quantity):
    return f"BOM组装扣减: {product_name}, 数量: {quantity}"


def format_finish_product_rollback_description(finish_name, sn_code, restored_details):
    sn_text = sn_code or "无SN"
    parts_text = ", ".join(restored_details) if restored_details else "无"
    return f"成品回退: {finish_name} (SN: {sn_text}), 恢复零件: {parts_text}"
