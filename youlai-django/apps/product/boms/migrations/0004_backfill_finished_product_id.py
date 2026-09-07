# 数据回填：按现有 material_code 为 BomList 回填 finished_product_id

import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def backfill_finished_product_id(apps, schema_editor):
    """按 BomList.material_code 查 products_product 回填 finished_product_id。

    - 仅处理 finished_product_id 为空且 material_code 非空的记录
    - 查不到匹配产品的留空并打印 warning，待人工补全
    - 幂等可重入
    """
    BomList = apps.get_model('boms', 'BomList')
    Product = apps.get_model('products', 'Product')

    qs = BomList.objects.filter(
        finished_product_id__isnull=True,
    ).exclude(material_code__isnull=True).exclude(material_code="")

    for bom in qs:
        code = (bom.material_code or "").strip()
        if not code:
            continue
        product = Product.objects.filter(material_code=code, is_del=0).first()
        if product:
            bom.finished_product_id = product.id
            bom.save(update_fields=["finished_product_id"])
        else:
            logger.warning(
                "BomList id=%s material_code=%s 无法匹配成品产品，请人工补全 finished_product_id",
                bom.id, code,
            )


def reverse_backfill(apps, schema_editor):
    """反向迁移：不删除已回填的数据，仅 noop。"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('boms', '0003_bomlist_finished_product_id'),
        ('products', '0004_alter_warehouselog_options_warehouselog_action_type_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_finished_product_id, reverse_backfill),
    ]
