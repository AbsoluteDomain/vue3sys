"""
测试脚本：验证关节/机械臂库存一致性检查逻辑
使用方法：python manage.py test_stock_consistency
"""
from django.core.management.base import BaseCommand
from apps.product.products.models import Product
from apps.product.products.constants import PRODUCT_TYPE_JOINT, PRODUCT_TYPE_ROBOT_ARM
from apps.product.finish_products.models import FinishProduct
from apps.product.boms.models import BomList
from django.db import models


class Command(BaseCommand):
    help = '验证关节/机械臂库存一致性'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("验证关节/机械臂库存一致性")
        self.stdout.write("=" * 60)

        # 获取关节和机械臂的BOM ID列表
        joint_bom_ids = list(BomList.objects.filter(
            type=BomList.TYPE_JOINT,
            is_del=0
        ).values_list('id', flat=True))

        robot_bom_ids = list(BomList.objects.filter(
            type=BomList.TYPE_ROBOT_ARM,
            is_del=0
        ).values_list('id', flat=True))

        self.stdout.write(f"\n关节BOM ID: {joint_bom_ids}")
        self.stdout.write(f"机械臂BOM ID: {robot_bom_ids}")

        # ===== 关节统计 =====
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("关节统计")
        self.stdout.write("=" * 60)

        # 产品表中关节的总库存
        product_joint_stock = Product.objects.filter(
            type=PRODUCT_TYPE_JOINT,
            is_del=0
        ).aggregate(total=models.Sum('quantity'))['total'] or 0

        # 成品表中符合条件的关节数量
        finish_joint_stock = FinishProduct.objects.filter(
            bom_id__in=joint_bom_ids,
            parent_sn_code__isnull=True,
            status=FinishProduct.STATUS_PASS,
            inventory_stock=FinishProduct.INVENTORY_IN,
        ).count()

        # 绑定在机械臂上的关节数量
        bound_joint_count = FinishProduct.objects.filter(
            bom_id__in=joint_bom_ids,
            parent_sn_code__isnull=False,
        ).count()

        # 其他状态的关节数量
        other_joint_count = FinishProduct.objects.filter(
            bom_id__in=joint_bom_ids,
        ).exclude(
            parent_sn_code__isnull=False,
            status=FinishProduct.STATUS_PASS,
            inventory_stock=FinishProduct.INVENTORY_IN,
        ).count()

        self.stdout.write(f"\n产品表关节库存 (Product.quantity汇总): {product_joint_stock}")
        self.stdout.write(f"成品表在库关节 (测试合格+入库+无父级): {finish_joint_stock}")
        self.stdout.write(f"已绑定关节 (有parent_sn_code): {bound_joint_count}")
        self.stdout.write(f"其他状态关节: {other_joint_count}")

        # 一致性检查
        joint_consistent = product_joint_stock == finish_joint_stock
        self.stdout.write(f"\n关节库存一致性: {'✅ 一致' if joint_consistent else '❌ 不一致'}")

        if not joint_consistent:
            self.stdout.write(f"  差异: {product_joint_stock} vs {finish_joint_stock}")

            # 分析原因
            self.stdout.write("\n分析关节明细...")
            for bom_id in joint_bom_ids:
                bom = BomList.objects.get(id=bom_id)
                # 产品表中的库存
                products = Product.objects.filter(
                    material_code=bom.material_code,
                    is_del=0
                )
                product_qty = sum(p.quantity or 0 for p in products)

                # 成品表中的在库数量
                finish_count = FinishProduct.objects.filter(
                    bom_id=bom_id,
                    parent_sn_code__isnull=True,
                    status=FinishProduct.STATUS_PASS,
                    inventory_stock=FinishProduct.INVENTORY_IN,
                ).count()

                if product_qty != finish_count:
                    self.stdout.write(f"  BOM {bom.bom_name} ({bom.material_code}):")
                    self.stdout.write(f"    产品表: {product_qty}, 成品表: {finish_count}")

        # ===== 机械臂统计 =====
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("机械臂统计")
        self.stdout.write("=" * 60)

        product_robot_stock = Product.objects.filter(
            type=PRODUCT_TYPE_ROBOT_ARM,
            is_del=0
        ).aggregate(total=models.Sum('quantity'))['total'] or 0

        finish_robot_stock = FinishProduct.objects.filter(
            bom_id__in=robot_bom_ids,
            parent_sn_code__isnull=True,
            status=FinishProduct.STATUS_PASS,
            inventory_stock=FinishProduct.INVENTORY_IN,
        ).count()

        robot_consistent = product_robot_stock == finish_robot_stock
        self.stdout.write(f"\n产品表机械臂库存: {product_robot_stock}")
        self.stdout.write(f"成品表在库机械臂: {finish_robot_stock}")
        self.stdout.write(f"\n机械臂库存一致性: {'✅ 一致' if robot_consistent else '❌ 不一致'}")

        if not robot_consistent:
            self.stdout.write(f"  差异: {product_robot_stock} vs {finish_robot_stock}")

        # 总结
        self.stdout.write("\n" + "=" * 60)
        all_consistent = joint_consistent and robot_consistent
        self.stdout.write(f"总体一致性: {'✅ 全部一致' if all_consistent else '❌ 存在不一致'}")
        self.stdout.write("=" * 60)
