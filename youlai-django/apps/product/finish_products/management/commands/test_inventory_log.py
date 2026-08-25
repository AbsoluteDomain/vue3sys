"""
测试成品状态变更时的出入库日志记录功能
使用方法: python manage.py test_inventory_log
"""
from django.core.management.base import BaseCommand
from apps.product.finish_products.models import FinishProduct
from apps.product.boms.models import BomList
from apps.product.products.models import WarehouseLog


class Command(BaseCommand):
    help = '测试成品状态变更日志记录功能'
    
    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("  成品状态变更日志记录测试")
        self.stdout.write("=" * 60)
        
        # 查找入库状态的成品
        products = FinishProduct.objects.filter(
            inventory_stock=FinishProduct.INVENTORY_IN,
            status=FinishProduct.STATUS_PASS,
            sn_code__isnull=False
        ).exclude(sn_code='').order_by('-id')[:5]
        
        if not products.exists():
            self.stdout.write("未找到入库状态的成品，创建测试数据...")
            bom, _ = BomList.objects.get_or_create(
                material_code='TEST_LOG_001',
                defaults={
                    'bom_model': 'TEST_LOG_MODEL',
                    'bom_name': '日志测试产品',
                    'type': 1,
                    'status': 1,
                    'is_del': 0
                }
            )
            product = FinishProduct.objects.create(
                sn_code='TEST_LOG_001',
                bom_id=bom.id,
                bom_type=1,
                status=FinishProduct.STATUS_PASS,
                inventory_stock=FinishProduct.INVENTORY_IN,
                repair=0,
                name='日志测试产品',
                description='测试日志记录功能'
            )
            self.stdout.write(f"创建测试成品: ID={product.id}, SN={product.sn_code}")
        else:
            product = products.first()
            self.stdout.write(f"找到入库成品: ID={product.id}, SN={product.sn_code}")
        
        # 状态名称映射
        stock_status_names = {
            FinishProduct.INVENTORY_NOT_IN: '未入库',
            FinishProduct.INVENTORY_IN: '入库',
            FinishProduct.INVENTORY_OUT_SALE: '出库(外销)',
            FinishProduct.INVENTORY_OUT_DEV: '出库(研发)',
            FinishProduct.INVENTORY_CONSUME: '组件消耗',
        }
        storage_type_names = {1: '入库', 2: '出库(外销)', 3: '出库(研发)', 4: '绑定关节', 5: '解除绑定', 6: '成品回退', 7: '手动调整'}
        
        # 测试: 入库 → 未入库
        self.stdout.write(f"\n测试: 入库 → 未入库 (SN={product.sn_code})")
        old_stock = product.inventory_stock
        bom = BomList.objects.get(id=product.bom_id)
        old_name = stock_status_names.get(old_stock, str(old_stock))
        new_name = stock_status_names.get(FinishProduct.INVENTORY_NOT_IN, '未入库')
        
        product.inventory_stock = FinishProduct.INVENTORY_NOT_IN
        product.description = '测试: 从入库改为未入库'
        product.save()
        
        log = WarehouseLog.objects.create(
            storage_status=WarehouseLog.STORAGE_OUT_SALE,
            name=bom.bom_name or bom.bom_model or product.name,
            sn_code=product.sn_code or '',
            material_code=bom.material_code or '',
            count=1,
            description=f"BOM: {bom.bom_model or ''} {bom.bom_name or ''}, 操作: 出库 ({old_name} → {new_name})",
            module='finish_product',
            action_type='product_out',
            operator_id=1,
            operator_name='测试用户',
            operation_detail=[{
                'action': '出库',
                'sn_code': product.sn_code,
                'old_stock_status': old_stock,
                'old_stock_status_name': old_name,
                'new_stock_status': FinishProduct.INVENTORY_NOT_IN,
                'new_stock_status_name': new_name,
            }]
        )
        self.stdout.write(f"✅ 状态更新成功，日志已创建: ID={log.id}")
        self.stdout.write(f"   描述: {log.description}")
        
        # 恢复状态
        self.stdout.write(f"\n恢复状态: 未入库 → 入库 (SN={product.sn_code})")
        old_stock2 = product.inventory_stock
        old_name2 = stock_status_names.get(old_stock2, str(old_stock2))
        new_name2 = stock_status_names.get(FinishProduct.INVENTORY_IN, '入库')
        
        product.inventory_stock = FinishProduct.INVENTORY_IN
        product.description = '恢复: 从未入库改为入库'
        product.save()
        
        log2 = WarehouseLog.objects.create(
            storage_status=WarehouseLog.STORAGE_IN,
            name=bom.bom_name or bom.bom_model or product.name,
            sn_code=product.sn_code or '',
            material_code=bom.material_code or '',
            count=1,
            description=f"BOM: {bom.bom_model or ''} {bom.bom_name or ''}, 操作: 入库 ({old_name2} → {new_name2})",
            module='finish_product',
            action_type='product_in',
            operator_id=1,
            operator_name='测试用户',
            operation_detail=[{
                'action': '入库',
                'sn_code': product.sn_code,
                'old_stock_status': old_stock2,
                'old_stock_status_name': old_name2,
                'new_stock_status': FinishProduct.INVENTORY_IN,
                'new_stock_status_name': new_name2,
            }]
        )
        self.stdout.write(f"✅ 恢复成功，日志已创建: ID={log2.id}")
        
        # 查看日志
        self.stdout.write(f"\n查看所有出入库日志 (SN={product.sn_code})")
        logs = WarehouseLog.objects.filter(
            sn_code=product.sn_code,
            module='finish_product'
        ).order_by('-created_at')[:5]
        
        for i, l in enumerate(logs):
            type_name = storage_type_names.get(l.storage_status, '未知')
            self.stdout.write(f"{i+1}. [{type_name}] {l.description[:80]}")
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  测试完成 ✅")
        self.stdout.write("=" * 60)