"""
详细分析关节/机械臂库存差异
使用方法：python manage.py analyze_stock_diff
"""
from django.core.management.base import BaseCommand
from apps.product.products.models import Product
from apps.product.products.constants import PRODUCT_TYPE_JOINT, PRODUCT_TYPE_ROBOT_ARM
from apps.product.finish_products.models import FinishProduct
from apps.product.boms.models import BomList
from django.db import models


class Command(BaseCommand):
    help = '详细分析关节/机械臂库存差异'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("详细分析关节/机械臂库存差异")
        self.stdout.write("=" * 80)

        # 获取关节BOM ID列表
        joint_bom_ids = list(BomList.objects.filter(
            type=BomList.TYPE_JOINT,
            is_del=0
        ).values_list('id', flat=True))

        # 分析每个关节BOM的情况
        for bom_id in joint_bom_ids:
            bom = BomList.objects.get(id=bom_id)
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"BOM: {bom.bom_name} ({bom.material_code})")
            self.stdout.write(f"{'='*60}")

            # 产品表中的库存
            products = Product.objects.filter(
                material_code=bom.material_code,
                is_del=0
            )
            product_qty = sum(p.quantity or 0 for p in products)
            self.stdout.write(f"产品表库存: {product_qty}")

            # 成品表的详细状态
            all_finish = FinishProduct.objects.filter(bom_id=bom_id)
            
            status_counts = {}
            inventory_counts = {}
            
            for fp in all_finish:
                status = fp.status
                inventory = fp.inventory_stock
                has_parent = fp.parent_sn_code is not None and fp.parent_sn_code != ''
                
                if status not in status_counts:
                    status_counts[status] = 0
                status_counts[status] += 1
                
                key = f"{inventory}{'_with_parent' if has_parent else ''}"
                if key not in inventory_counts:
                    inventory_counts[key] = 0
                inventory_counts[key] += 1

            self.stdout.write(f"\n成品表统计 (共{all_finish.count()}条):")
            self.stdout.write(f"  状态分布:")
            status_names = {0: '未测试', 1: '测试中', 2: '测试合格', 3: '测试不良'}
            for status, count in sorted(status_counts.items()):
                self.stdout.write(f"    {status_names.get(status, status)}: {count}")

            self.stdout.write(f"  库存状态分布:")
            inventory_names = {
                0: '未入库', 
                1: '入库', 
                2: '出库(外销)', 
                3: '出库(研发)',
                4: '组件消耗'
            }
            for key, count in sorted(inventory_counts.items()):
                base_status = int(key.split('_')[0])
                with_parent = '有父级' if 'with_parent' in key else '无父级'
                self.stdout.write(f"    {inventory_names.get(base_status, base_status)}({with_parent}): {count}")

            # 计算在库数量
            finish_in_stock = FinishProduct.objects.filter(
                bom_id=bom_id,
                parent_sn_code__isnull=True,
                status=FinishProduct.STATUS_PASS,
                inventory_stock=FinishProduct.INVENTORY_IN,
            ).count()

            self.stdout.write(f"\n在库成品数量 (测试合格+入库+无父级): {finish_in_stock}")
            
            if product_qty != finish_in_stock:
                self.stdout.write(f"❌ 差异: 产品表={product_qty} vs 成品表={finish_in_stock}")
                
                # 分析可能原因
                self.stdout.write(f"\n可能原因分析:")
                
                # 检查是否有组件消耗状态的
                consume_count = FinishProduct.objects.filter(
                    bom_id=bom_id,
                    inventory_stock=FinishProduct.INVENTORY_CONSUME,
                ).count()
                self.stdout.write(f"  - 组件消耗状态: {consume_count}")
                
                # 检查是否有出库状态的
                out_count = FinishProduct.objects.filter(
                    bom_id=bom_id,
                    inventory_stock__in=[
                        FinishProduct.INVENTORY_OUT_SALE,
                        FinishProduct.INVENTORY_OUT_DEV
                    ],
                ).count()
                self.stdout.write(f"  - 出库状态: {out_count}")
                
                # 检查是否有未入库的合格产品
                pass_not_in = FinishProduct.objects.filter(
                    bom_id=bom_id,
                    status=FinishProduct.STATUS_PASS,
                    inventory_stock=FinishProduct.INVENTORY_NOT_IN,
                ).count()
                self.stdout.write(f"  - 测试合格但未入库: {pass_not_in}")
                
                # 检查是否有不合格的入库产品
                fail_in = FinishProduct.objects.filter(
                    bom_id=bom_id,
                    status__ne=FinishProduct.STATUS_PASS,
                    inventory_stock=FinishProduct.INVENTORY_IN,
                ).count()
                self.stdout.write(f"  - 测试不合格但已入库: {fail_in}")
                
                # 检查有父级的入库产品
                in_with_parent = FinishProduct.objects.filter(
                    bom_id=bom_id,
                    parent_sn_code__isnull=False,
                    inventory_stock=FinishProduct.INVENTORY_IN,
                ).count()
                self.stdout.write(f"  - 有父级但状态为入库: {in_with_parent}")
                
            else:
                self.stdout.write(f"✅ 一致")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("分析完成")
        self.stdout.write("=" * 80)
