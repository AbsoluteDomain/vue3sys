"""
测试命令：构造已绑定不良项的产品测试数据
使用方法：python manage.py test_unqualified_data
"""
from django.core.management.base import BaseCommand
from apps.product.finish_products.models import UnqualifiedItem, FinishProduct
from apps.system.dicts.models import DictionaryItem


class Command(BaseCommand):
    help = '构造已绑定不良项的产品测试数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='是否清理旧的绑定数据',
        )
        parser.add_argument(
            '--product-id',
            type=int,
            help='指定产品ID',
        )

    def handle(self, *args, **options):
        clear = options['clear']
        product_id = options['product_id']

        self.stdout.write("=" * 60)
        self.stdout.write("构造已绑定不良项的产品测试数据")
        self.stdout.write("=" * 60)

        # ============================================
        # 步骤1：查找字典项
        # ============================================
        self.stdout.write("\n步骤1：查找字典项（unqualified_status）")
        self.stdout.write("-" * 40)

        dict_items = list(DictionaryItem.objects.filter(
            dict_code="unqualified_status",
            status=1,
        ).order_by('sort'))

        self.stdout.write(f"共找到 {len(dict_items)} 个不良项字典：")
        for item in dict_items:
            self.stdout.write(f"  - value={item.value}, label={item.label}")

        if not dict_items:
            self.stderr.write("\n❌ 错误：没有找到 unqualified_status 字典项")
            return

        # ============================================
        # 步骤2：查找有SN码的成品
        # ============================================
        self.stdout.write("\n步骤2：查找有SN码的成品")
        self.stdout.write("-" * 40)

        if product_id:
            products = FinishProduct.objects.filter(id=product_id)
        else:
            products = FinishProduct.objects.filter(
                sn_code__isnull=False,
            ).exclude(sn_code='')[:10]

        self.stdout.write(f"找到 {products.count()} 个有SN码的成品：")
        status_map = {0: '未测试', 1: '测试中', 2: '测试合格', 3: '测试不良'}
        for p in products:
            self.stdout.write(f"  - id={p.id}, sn_code={p.sn_code}, status={status_map.get(p.status, p.status)}, name={p.name}")

        if not products:
            self.stderr.write("\n❌ 错误：没有找到有SN码的成品")
            return

        # ============================================
        # 步骤3：清理旧数据
        # ============================================
        self.stdout.write("\n步骤3：清理旧的不良项绑定")
        self.stdout.write("-" * 40)

        if clear:
            old_count = UnqualifiedItem.objects.count()
            UnqualifiedItem.objects.all().delete()
            self.stdout.write(f"已清理 {old_count} 条旧的不良项绑定")
        else:
            self.stdout.write("未清理旧数据（使用 --clear 参数可清理）")

        # ============================================
        # 步骤4：绑定不良项
        # ============================================
        self.stdout.write("\n步骤4：为产品绑定不良项")
        self.stdout.write("-" * 40)

        for target_product in products:
            # 选前3个不良项绑定
            selected_items = dict_items[:3]
            self.stdout.write(f"\n产品 {target_product.sn_code} ({target_product.id}) 绑定 {len(selected_items)} 个不良项：")

            for dict_item in selected_items:
                item = UnqualifiedItem.objects.create(
                    finish_product_id=target_product.id,
                    sn_code=target_product.sn_code,
                    unqualified_value=int(dict_item.value),
                )
                self.stdout.write(f"  ✅ id={item.id}, value={item.unqualified_value}, label={dict_item.label}")

        # ============================================
        # 步骤5：验证结果
        # ============================================
        self.stdout.write("\n步骤5：验证绑定结果")
        self.stdout.write("-" * 40)

        for target_product in products:
            bound_items = UnqualifiedItem.objects.filter(
                finish_product_id=target_product.id
            ).order_by('-create_time')

            self.stdout.write(f"\n产品 {target_product.sn_code} 已绑定 {bound_items.count()} 个不良项：")
            for item in bound_items:
                dict_item = DictionaryItem.objects.filter(
                    dict_code="unqualified_status",
                    value=str(item.unqualified_value),
                    status=1,
                ).first()
                label = dict_item.label if dict_item else f"未知({item.unqualified_value})"
                self.stdout.write(f"  - id={item.id}, value={item.unqualified_value}, label={label}")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("✅ 测试数据构造完成！")
        self.stdout.write("=" * 60)
        self.stdout.write("\n请在返修计划页面选择上述产品，打开新增返修计划对话框时，应该能看到已预选的不良项")
