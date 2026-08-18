"""
手动添加 WarehouseLog 表的新字段
使用方法：python manage.py add_warehouse_log_fields
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = '手动添加 WarehouseLog 表的新字段'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("手动添加 WarehouseLog 表的新字段")
        self.stdout.write("=" * 60)

        with connection.cursor() as cursor:
            # 检查字段是否存在，如果不存在则添加
            new_fields = [
                ('operator_id', 'ALTER TABLE warehouse_log ADD COLUMN operator_id BIGINT NULL COMMENT "操作人ID" AFTER id;'),
                ('operator_name', 'ALTER TABLE warehouse_log ADD COLUMN operator_name VARCHAR(64) NULL COMMENT "操作人昵称" AFTER operator_id;'),
                ('module', 'ALTER TABLE warehouse_log ADD COLUMN module VARCHAR(32) NULL COMMENT "操作来源模块" AFTER operator_name;'),
                ('operation_detail', 'ALTER TABLE warehouse_log ADD COLUMN operation_detail JSON NULL COMMENT "操作详情" AFTER module;'),
                ('action_type', 'ALTER TABLE warehouse_log ADD COLUMN action_type VARCHAR(32) NULL COMMENT "具体操作类型" AFTER operation_detail;'),
            ]

            for field_name, alter_sql in new_fields:
                try:
                    # 检查字段是否存在
                    cursor.execute(f"SHOW COLUMNS FROM warehouse_log LIKE '{field_name}';")
                    result = cursor.fetchone()
                    if result:
                        self.stdout.write(f"  字段 {field_name} 已存在，跳过")
                    else:
                        cursor.execute(alter_sql)
                        self.stdout.write(f"  ✅ 添加字段 {field_name} 成功")
                except Exception as e:
                    self.stderr.write(f"  ❌ 添加字段 {field_name} 失败: {str(e)}")

        # 更新 storage_status 的注释
        self.stdout.write("\n更新 storage_status 字段的选项...")
        self.stdout.write("  (需要通过迁移文件完成，已创建迁移文件 0004)")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("完成！")
        self.stdout.write("=" * 60)
        self.stdout.write("\n已添加的字段:")
        self.stdout.write("  - operator_id: 操作人ID")
        self.stdout.write("  - operator_name: 操作人昵称")
        self.stdout.write("  - module: 操作来源模块")
        self.stdout.write("  - operation_detail: 操作详情 (JSON格式)")
        self.stdout.write("  - action_type: 具体操作类型")
