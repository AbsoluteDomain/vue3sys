"""
测试脚本：构造已绑定不良项的产品测试数据
使用方法：python manage.py shell < test_repair_unqualified.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.product.finish_products.models import UnqualifiedItem, FinishProduct
from apps.system.dicts.models import DictionaryItem

# ============================================
# 步骤1：查找字典项（不良项）
# ============================================
print("=" * 60)
print("步骤1：查找字典项（unqualified_status）")
print("=" * 60)

dict_items = DictionaryItem.objects.filter(
    dict_code="unqualified_status",
    status=1,
)
print(f"共找到 {dict_items.count()} 个不良项字典：")
for item in dict_items:
    print(f"  - value={item.value}, label={item.label}")

if dict_items.count() == 0:
    print("\n❌ 错误：没有找到 unqualified_status 字典项，请先在字典管理中添加不良项字典。")
    sys.exit(1)

# ============================================
# 步骤2：查找有SN码的成品
# ============================================
print("\n" + "=" * 60)
print("步骤2：查找有SN码的成品")
print("=" * 60)

products = FinishProduct.objects.filter(
    sn_code__isnull=False,
).exclude(
    sn_code=''
)[:10]

print(f"找到 {products.count()} 个有SN码的成品（显示前10条）：")
for p in products:
    status_map = {0: '未测试', 1: '测试中', 2: '测试合格', 3: '测试不良'}
    print(f"  - id={p.id}, sn_code={p.sn_code}, status={status_map.get(p.status, p.status)}, name={p.name}")

if products.count() == 0:
    print("\n❌ 错误：没有找到有SN码的成品，请先创建成品。")
    sys.exit(1)

# ============================================
# 步骤3：清理旧的不良项绑定（可选）
# ============================================
print("\n" + "=" * 60)
print("步骤3：清理旧的不良项绑定")
print("=" * 60)

old_count = UnqualifiedItem.objects.count()
print(f"当前共有 {old_count} 条不良项绑定记录")

# 清理所有旧数据（可选，根据需要注释）
# UnqualifiedItem.objects.all().delete()
# print("已清理所有旧的不良项绑定")

# ============================================
# 步骤4：为产品绑定不良项
# ============================================
print("\n" + "=" * 60)
print("步骤4：为产品绑定不良项")
print("=" * 60)

# 选择一个产品进行绑定（选第一个有SN码的）
target_product = products[0]
print(f"目标产品：id={target_product.id}, sn_code={target_product.sn_code}, name={target_product.name}")

# 选择要绑定的不良项（取前2-3个）
selected_dict_items = list(dict_items[:3])
print(f"要绑定的不良项：")
for item in selected_dict_items:
    print(f"  - value={item.value}, label={item.label}")

# 创建绑定
created_items = []
for dict_item in selected_dict_items:
    item = UnqualifiedItem.objects.create(
        finish_product_id=target_product.id,
        sn_code=target_product.sn_code,
        unqualified_value=int(dict_item.value),
    )
    created_items.append(item)
    print(f"  ✅ 创建绑定：id={item.id}, value={item.unqualified_value}")

# ============================================
# 步骤5：验证数据
# ============================================
print("\n" + "=" * 60)
print("步骤5：验证绑定结果")
print("=" * 60)

bound_items = UnqualifiedItem.objects.filter(
    finish_product_id=target_product.id
).order_by('-create_time')

print(f"产品 {target_product.sn_code} 已绑定 {bound_items.count()} 个不良项：")
for item in bound_items:
    # 查询字典标签
    dict_item = DictionaryItem.objects.filter(
        dict_code="unqualified_status",
        value=str(item.unqualified_value),
        status=1,
    ).first()
    label = dict_item.label if dict_item else f"未知({item.unqualified_value})"
    print(f"  - id={item.id}, value={item.unqualified_value}, label={label}")

# ============================================
# 步骤6：模拟API调用
# ============================================
print("\n" + "=" * 60)
print("步骤6：模拟API调用验证")
print("=" * 60)

# 模拟 list_unqualified_items 返回数据
simulated_data = [{
    "id": item.id,
    "finish_product_id": item.finish_product_id,
    "sn_code": item.sn_code,
    "unqualified_value": item.unqualified_value,
    "unqualified_label": DictionaryItem.objects.filter(
        dict_code="unqualified_status",
        value=str(item.unqualified_value),
        status=1,
    ).first().label if DictionaryItem.objects.filter(
        dict_code="unqualified_status",
        value=str(item.unqualified_value),
        status=1,
    ).exists() else f"未知({item.unqualified_value})",
    "create_time": item.create_time.strftime('%Y-%m-%d %H:%M:%S'),
} for item in bound_items]

print("API 返回数据格式：")
print(f"  code: '00000'")
print(f"  msg: '成功'")
print(f"  data: {len(simulated_data)} 条记录")
for data in simulated_data:
    print(f"    - {data['unqualified_value']}: {data['unqualified_label']}")

print("\n" + "=" * 60)
print("✅ 测试数据构造完成！")
print("=" * 60)
print(f"\n请在返修计划页面选择产品：{target_product.sn_code}")
print("打开新增返修计划对话框时，应该能看到已预选的不良项")
