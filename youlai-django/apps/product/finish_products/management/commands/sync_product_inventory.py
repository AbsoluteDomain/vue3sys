"""
修复脚本：同步 Product.quantity 与 FinishProduct 表的实际数据
使用方法：python manage.py sync_product_inventory
"""
from django.core.management.base import BaseCommand
from apps.product.products.models import Product
from apps.product.products.constants import PRODUCT_TYPE_JOINT, PRODUCT_TYPE_ROBOT_ARM
from apps.product.finish_products.models import FinishProduct
from apps.product.boms.models import BomList
from django.db import models


class Command(BaseCommand):
    help = '同步产品库存与成品表数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅检查不修复',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write("=" * 80)
        self.stdout.write("同步产品库存与成品表数据")
        if dry_run:
            self.stdout.write("（DRY RUN 模式 - 仅检查不修复）")
        self.stdout.write("=" * 80)

        # 获取关节和机械臂的BOM列表
        joint_boms = BomList.objects.filter(type=BomList.TYPE_JOINT, is_del=0)
        robot_boms = BomList.objects.filter(type=BomList.TYPE_ROBOT_ARM, is_del=0)

        # 处理关节
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("处理关节 (bom_type=0)")
        self.stdout.write("=" * 80)

        self._process_bom_list(joint_boms, PRODUCT_TYPE_JOINT, dry_run)

        # 处理机械臂
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("处理机械臂 (bom_type=1)")
        self.stdout.write("=" * 80)

        self._process_bom_list(robot_boms, PRODUCT_TYPE_ROBOT_ARM, dry_run)

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("同步完成")
        self.stdout.write("=" * 80)

    def _process_bom_list(self, boms, expected_type, dry_run):
        """处理一组BOM，同步产品库存"""
        for bom in boms:
            if not bom.material_code:
                self.stdout.write(f"\n跳过 BOM {bom.bom_name} (无 material_code)")
                continue

            material_code = bom.material_code.strip()
            if not material_code:
                continue

            # 计算成品表中实际在库的数量
            actual_stock = FinishProduct.objects.filter(
                bom_id=bom.id,
                parent_sn_code__isnull=True,
                status=FinishProduct.STATUS_PASS,
                inventory_stock=FinishProduct.INVENTORY_IN,
            ).count()

            # 获取产品表记录
            products = Product.objects.filter(
                material_code=material_code,
                is_del=0
            )

            if not products.exists():
                self.stdout.write(f"\nBOM: {bom.bom_name} ({material_code})")
                self.stdout.write(f"  产品表无记录，需要创建新记录 (quantity={actual_stock})")
                if not dry_run:
                    Product.objects.create(
                        name=bom.bom_name or bom.bom_model,
                        type=expected_type,
                        material_code=material_code,
                        quantity=actual_stock,
                        procurement_cycle=1,
                        is_del=0,
                    )
                continue

            # 如果有多条记录，合并它们
            if products.count() > 1:
                self.stdout.write(f"\nBOM: {bom.bom_name} ({material_code})")
                self.stdout.write(f"  产品表有多条记录 ({products.count()}条)，需要合并")
                
                if not dry_run:
                    # 保留第一条，删除其他
                    primary = products.first()
                    for p in products[1:]:
                        p.is_del = 1
                        p.save()
                    
                    # 更新主记录
                    old_qty = primary.quantity or 0
                    if old_qty != actual_stock:
                        self.stdout.write(f"  数量修正: {old_qty} → {actual_stock}")
                        primary.quantity = actual_stock
                        primary.type = expected_type
                        primary.save(update_fields=["quantity", "type", "updated_at"])
                    else:
                        self.stdout.write(f"  数量已正确: {old_qty}")
                continue

            # 单条记录，直接更新
            product = products.first()
            old_qty = product.quantity or 0
            
            if old_qty != actual_stock:
                self.stdout.write(f"\nBOM: {bom.bom_name} ({material_code})")
                self.stdout.write(f"  数量修正: {old_qty} → {actual_stock}")
                if not dry_run:
                    product.quantity = actual_stock
                    product.type = expected_type
                    product.save(update_fields=["quantity", "type", "updated_at"])
                    self.stdout.write(f"  ✅ 已更新")
                else:
                    self.stdout.write(f"  (DRY RUN - 未更新)")
            else:
                self.stdout.write(f"\nBOM: {bom.bom_name} ({material_code})")
                self.stdout.write(f"  数量已正确: {old_qty}")
