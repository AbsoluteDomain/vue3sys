PRODUCT_TYPE_SELF_MADE = 0
PRODUCT_TYPE_OUTSOURCE = 1
PRODUCT_TYPE_PURCHASE = 2
PRODUCT_TYPE_JOINT = 4
PRODUCT_TYPE_ROBOT_ARM = 5

PRODUCT_TYPE_CHOICES = (
    (PRODUCT_TYPE_SELF_MADE, "自制"),
    (PRODUCT_TYPE_OUTSOURCE, "外协"),
    (PRODUCT_TYPE_PURCHASE, "外购"),
    (PRODUCT_TYPE_JOINT, "关节"),
    (PRODUCT_TYPE_ROBOT_ARM, "机械臂"),
)

PRODUCT_TYPE_LABELS = dict(PRODUCT_TYPE_CHOICES)

PRODUCT_TYPE_TEXT_MAP = {
    "自制": PRODUCT_TYPE_SELF_MADE,
    "外协": PRODUCT_TYPE_OUTSOURCE,
    "外购": PRODUCT_TYPE_PURCHASE,
    "关节": PRODUCT_TYPE_JOINT,
    "机械臂": PRODUCT_TYPE_ROBOT_ARM,
    "0": PRODUCT_TYPE_SELF_MADE,
    "1": PRODUCT_TYPE_OUTSOURCE,
    "2": PRODUCT_TYPE_PURCHASE,
    "4": PRODUCT_TYPE_JOINT,
    "5": PRODUCT_TYPE_ROBOT_ARM,
}


def normalize_product_type(value):
    if value is None or value == "":
        return None
    if isinstance(value, str):
        text = value.strip()
        if text in PRODUCT_TYPE_TEXT_MAP:
            return PRODUCT_TYPE_TEXT_MAP[text]
    try:
        product_type = int(value)
    except (TypeError, ValueError):
        raise ValueError("产品类型无效，须为 0（自制）、1（外协）、2（外购）、4（关节）或 5（机械臂）")
    if product_type not in PRODUCT_TYPE_LABELS:
        raise ValueError("产品类型无效，须为 0（自制）、1（外协）、2（外购）、4（关节）或 5（机械臂）")
    return product_type


def product_type_label(value):
    if value is None or value == "":
        return ""
    try:
        return PRODUCT_TYPE_LABELS.get(int(value), str(value))
    except (TypeError, ValueError):
        return str(value)
