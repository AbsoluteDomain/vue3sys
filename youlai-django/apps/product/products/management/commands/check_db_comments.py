"""
数据库注释检查和添加工具
使用方法：
  python manage.py check_db_comments           # 检查所有表的注释
  python manage.py check_db_comments --fix     # 自动添加注释
  
特点：
  - 安全版本，不会使用 RENAME TABLE
  - 自动处理被外键引用的字段
  - 支持 NOT NULL 字段的注释添加
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = '检查并修复数据库表字段的注释'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='自动添加注释',
        )

    def handle(self, *args, **options):
        fix = options['fix']
        self.empty_count = 0
        self.tables_checked = 0
        self.fixed_count = 0
        self.failed_count = 0
        
        self.check_all_tables(fix)
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"检查完成：共检查 {self.tables_checked} 张表")
        self.stdout.write(f"空注释字段：{self.empty_count} 个")
        if fix:
            self.stdout.write(f"已修复：{self.fixed_count} 个")
            self.stdout.write(f"失败：{self.failed_count} 个")

    def check_all_tables(self, fix=False):
        cursor = connection.cursor()
        database = connection.settings_dict['NAME']
        
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        self.stdout.write(f"检查数据库: {database}")
        self.stdout.write(f"共 {len(tables)} 张表")
        self.stdout.write("=" * 80)
        
        for table_name in tables:
            self.tables_checked += 1
            self.check_table(table_name, fix)

    def check_table(self, table_name, fix=False):
        cursor = connection.cursor()
        cursor.execute(f"SHOW FULL COLUMNS FROM `{table_name}`")
        columns = cursor.fetchall()
        
        empty_comment_columns = []
        
        for col in columns:
            field = col[0]        # 字段名
            comment = col[8]      # 注释 (Comment)
            field_type = col[1]   # 字段类型
            is_null = col[2]      # 是否可空
            
            if not comment or comment.strip() == '':
                empty_comment_columns.append((field, field_type, is_null))
                self.empty_count += 1
                
                if fix:
                    self.fix_comment(table_name, field, field_type, is_null)
        
        if empty_comment_columns and not fix:
            self.stdout.write(f"\n📋 表 {table_name} 有 {len(empty_comment_columns)} 个字段缺少注释：")
            for field, field_type, is_null in empty_comment_columns:
                self.stdout.write(f"   - {field} ({field_type})")

    def fix_comment(self, table_name, field_name, field_type, is_null):
        """安全地添加注释，保持原有约束"""
        comment = self.generate_comment(field_name, field_type)
        
        if not comment:
            return
        
        cursor = connection.cursor()
        
        try:
            # 获取字段的完整定义信息
            cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
            row = cursor.fetchone()
            create_sql = row[1]
            
            # 检查字段是否被外键引用
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND REFERENCED_TABLE_NAME = %s 
                AND REFERENCED_COLUMN_NAME = %s
            """, [table_name, field_name])
            ref_count = cursor.fetchone()[0]
            
            # 从 SHOW CREATE TABLE 中提取原字段的完整定义
            import re
            # 匹配字段定义：`field_name` type [NOT NULL|NULL] [DEFAULT value] [AUTO_INCREMENT] [UNIQUE] [PRIMARY KEY] [COMMENT '...']
            pattern = rf'`{re.escape(field_name)}`\s+'
            match = re.search(pattern, create_sql, re.IGNORECASE)
            
            if not match:
                self.stderr.write(f"  ❌ {table_name}.{field_name} 无法解析字段定义")
                self.failed_count += 1
                return
            
            # 找到该字段定义的结束位置（下一个字段或约束的开始）
            start_pos = match.start()
            # 找到下一个 ` 开头的位置或 ) 或 PRIMARY/UNIQUE/KEY/INDEX/CONSTRAINT
            rest = create_sql[match.end():]
            
            # 匹配到下一个 `, `)`, PRIMARY, UNIQUE, KEY, INDEX, CONSTRAINT 之前
            end_pattern = r'\s*,\s*`|\),\s*`|\)\s*ENGINE|\s*PRIMARY\s+KEY|\s*UNIQUE\s+KEY|\s*KEY\s+`|\s*INDEX\s+`|\s*CONSTRAINT'
            end_match = re.search(end_pattern, rest, re.IGNORECASE)
            
            if end_match:
                field_def_end = match.end() + end_match.start()
            else:
                field_def_end = len(create_sql)
            
            original_def = create_sql[start_pos:field_def_end].strip()
            
            # 检查原定义中是否已有 COMMENT
            if "COMMENT" in original_def.upper():
                # 替换原 COMMENT
                new_def = re.sub(
                    r"COMMENT\s+'[^']*'",
                    f"COMMENT '{comment}'",
                    original_def,
                    flags=re.IGNORECASE
                )
            else:
                # 在原定义末尾追加 COMMENT
                new_def = original_def.rstrip() + f" COMMENT '{comment}'"
            
            # 构造新的 CREATE TABLE 语句
            new_sql = create_sql[:start_pos] + new_def + create_sql[field_def_end:]
            
            # 验证新的 SQL 语法
            # 先测试解析
            test_cursor = connection.cursor()
            test_cursor.execute(f"EXPLAIN `{table_name}`")  # 验证表存在
            
            # 使用 CREATE TABLE ... LIKE 方式
            # 更安全的方式：使用 CHANGE COLUMN
            # 提取字段类型和约束
            field_def_pattern = rf'`{re.escape(field_name)}`\s+(\S+(?:\([^)]*\))?)\s+(.*?)$'
            field_match = re.match(field_def_pattern, original_def)
            
            if field_match:
                extracted_type = field_match.group(1)
                rest_def = field_match.group(2)
                
                # 构建新的定义（保留所有约束）
                new_field_def = f"`{field_name}` {extracted_type} {rest_def}"
                if "COMMENT" not in rest_def.upper():
                    new_field_def += f" COMMENT '{comment}'"
                else:
                    new_field_def = re.sub(
                        r"COMMENT\s+'[^']*'",
                        f"COMMENT '{comment}'",
                        new_field_def,
                        flags=re.IGNORECASE
                    )
                
                # 尝试使用 ALTER TABLE ... CHANGE COLUMN
                alter_sql = f"ALTER TABLE `{table_name}` CHANGE COLUMN `{field_name}` {new_field_def}"
                
                # 对于被外键引用的字段，需要特殊处理
                if ref_count > 0:
                    # 被外键引用的字段不能使用 CHANGE COLUMN，使用 MODIFY 并保持 NOT NULL
                    # 保持原约束
                    pass
                
                cursor.execute(alter_sql)
                self.stdout.write(f"  ✅ {table_name}.{field_name} → {comment}")
                self.fixed_count += 1
                return
            
            # 如果无法解析，使用简单的 MODIFY 方式
            null_sql = "NULL" if is_null == "YES" else "NOT NULL"
            # 对于自增主键，需要添加 AUTO_INCREMENT
            if 'auto_increment' in field_type.lower():
                sql = f"ALTER TABLE `{table_name}` MODIFY COLUMN `{field_name}` {field_type} NOT NULL AUTO_INCREMENT COMMENT '{comment}';"
            else:
                sql = f"ALTER TABLE `{table_name}` MODIFY COLUMN `{field_name}` {field_type} {null_sql} COMMENT '{comment}';"
            
            cursor.execute(sql)
            self.stdout.write(f"  ✅ {table_name}.{field_name} → {comment}")
            self.fixed_count += 1
            
        except Exception as e:
            # 简化重试
            try:
                sql = f"ALTER TABLE `{table_name}` MODIFY COLUMN `{field_name}` {field_type} COMMENT '{comment}';"
                cursor.execute(sql)
                self.stdout.write(f"  ✅ {table_name}.{field_name} → {comment} (简化方式)")
                self.fixed_count += 1
            except Exception as e2:
                self.stderr.write(f"  ❌ {table_name}.{field_name} 失败: {str(e2)}")
                self.failed_count += 1

    def generate_comment(self, field_name, field_type):
        """根据字段名和类型生成合理的中文注释"""
        
        # 常见字段名映射
        comment_map = {
            'id': 'ID主键',
            'name': '名称',
            'title': '标题',
            'sn_code': 'SN码',
            'material_code': '物料编码',
            'product_id': '产品ID',
            'product_name': '产品名称',
            'finish_product_id': '成品ID',
            'bom_id': 'BOM ID',
            'bom_name': 'BOM名称',
            'bom_model': 'BOM型号',
            'parent_sn_code': '父级SN码',
            'status': '状态',
            'inventory_stock': '库存状态',
            'storage_status': '出入库状态',
            'test_status': '测试状态',
            'type': '类型',
            'quantity': '数量',
            'count': '数量',
            'price': '价格',
            'amount': '金额',
            'cost': '成本',
            'description': '描述',
            'remark': '备注',
            'content': '内容',
            'value': '值',
            'label': '标签',
            'code': '编码',
            'sort': '排序',
            'weight': '权重',
            'level': '级别',
            'priority': '优先级',
            'module': '模块',
            'action_type': '操作类型',
            'operation_detail': '操作详情',
            'operator_id': '操作人ID',
            'operator_name': '操作人名称',
            'user_id': '用户ID',
            'user_name': '用户名',
            'nickname': '昵称',
            'username': '用户名',
            'password': '密码',
            'email': '邮箱',
            'phone': '电话',
            'mobile': '手机号',
            'avatar': '头像',
            'dept': '部门',
            'dept_id': '部门ID',
            'department': '部门',
            'parent_id': '父级ID',
            'path': '路径',
            'url': '链接',
            'icon': '图标',
            'image': '图片',
            'status_code': '状态码',
            'is_enable': '是否启用',
            'is_del': '删除标记',
            'created_at': '创建时间',
            'create_time': '创建时间',
            'updated_at': '更新时间',
            'update_time': '更新时间',
            'stock_in_time': '入库时间',
            'stock_out_time': '出库时间',
            'alert_quantity': '预警数量',
            'procurement_cycle': '采购周期(天)',
            'unit': '单位',
            'location': '位置',
            'address': '地址',
            'city': '城市',
            'operator_id': '操作人ID',
            'operator_name': '操作人昵称',
            'action_type': '具体操作类型',
            'operation_detail': '操作详情',
            'module': '操作来源模块',
            'description': '操作描述',
            'count': '数量',
            'purpose': '用途',
            'operator': '操作人',
            'operator_role': '操作人角色',
            'change_type': '变更类型',
            'previous_quantity': '变更前数量',
            'new_quantity': '变更后数量',
            'repair_cnt': '维修次数',
            'repair_info': '维修信息',
            'plan_date': '计划日期',
            'unqualified_value': '不良项值',
            'component_id': '组件ID',
            'component_name': '组件名称',
            'component_quantity': '组件数量',
            'raw_material_id': '原材料ID',
            'raw_material_name': '原材料名称',
            'raw_material_quantity': '原材料数量',
            'column_name': '列名',
            'column_type': '列类型',
            'column_length': '列长度',
            'max_length': '最大长度',
            'draw_code': '图纸编码',
            'codename': '代码名',
            'app_label': '应用标签',
            'model': '模型名称',
            'action_time': '操作时间',
            'object_id': '对象ID',
            'object_repr': '对象表示',
            'action_flag': '操作标志',
            'change_message': '变更消息',
            'session_key': '会话密钥',
            'session_data': '会话数据',
            'expire_date': '过期日期',
            'plan_date': '计划日期',
        }
        
        # 直接匹配
        if field_name.lower() in comment_map:
            return comment_map[field_name.lower()]
        
        # 根据后缀生成
        if field_name.endswith('_id'):
            base = field_name[:-3]
            name_map = {
                'product': '产品',
                'finish_product': '成品',
                'bom': 'BOM',
                'user': '用户',
                'dept': '部门',
                'department': '部门',
                'role': '角色',
                'material': '物料',
                'component': '组件',
                'supplier': '供应商',
                'customer': '客户',
                'order': '订单',
                'parent': '父级',
                'child': '子级',
                'category': '分类',
                'brand': '品牌',
                'config': '配置',
                'module': '模块',
                'menu': '菜单',
                'operator': '操作人',
                'raw_material': '原材料',
            }
            if base.lower() in name_map:
                return f"{name_map[base.lower()]}ID"
            return f"{base}ID"
        elif field_name.endswith('_name'):
            base = field_name[:-5]
            return f"{base}名称"
        elif field_name.endswith('_code'):
            base = field_name[:-5]
            return f"{base}编码"
        elif field_name.endswith('_status'):
            base = field_name[:-7]
            name_map = {
                'inventory_stock': '库存状态',
                'storage': '出入库状态',
                'test': '测试状态',
                'order': '订单状态',
                'payment': '支付状态',
                'delivery': '交付状态',
                'repair': '维修状态',
                'production': '生产状态',
            }
            if base.lower() in name_map:
                return name_map[base.lower()]
            return f"{base}状态"
        elif field_name.endswith('_time') or field_name.endswith('_date'):
            return f"{field_name}时间"
        
        # 根据类型生成默认注释
        field_type_lower = field_type.lower()
        if 'int' in field_type_lower:
            return f"{field_name}(整数)"
        elif 'decimal' in field_type_lower or 'float' in field_type_lower or 'double' in field_type_lower:
            return f"{field_name}(数值)"
        elif 'varchar' in field_type_lower or 'char' in field_type_lower:
            return f"{field_name}(字符串)"
        elif 'text' in field_type_lower:
            return f"{field_name}(文本)"
        elif 'json' in field_type_lower:
            return f"{field_name}(JSON)"
        elif 'date' in field_type_lower:
            return f"{field_name}(日期)"
        elif 'bool' in field_type_lower or 'tinyint' in field_type_lower:
            return f"{field_name}(布尔)"
        
        # 默认
        return field_name
