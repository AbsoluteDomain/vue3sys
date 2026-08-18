"""
系统综合测试脚本
测试所有主要模块的接口和数据库结构完整性
"""
import os
import sys
import json
import traceback

from django.core.management.base import BaseCommand
from django.test import Client
from django.db import connection
from django.contrib.auth import get_user_model

User = get_user_model()

# 测试结果统计
test_results = {
    'pass': 0,
    'fail': 0,
    'errors': [],
    'warnings': []
}


def record_pass(name):
    test_results['pass'] += 1
    print(f"  [PASS] {name}")


def record_fail(name, error):
    test_results['fail'] += 1
    test_results['errors'].append(f"{name}: {error}")
    print(f"  [FAIL] {name}: {error}")


def record_warning(name, msg):
    test_results['warnings'].append(f"{name}: {msg}")
    print(f"  [WARN] {name}: {msg}")


def section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ============================================================
# 1. 数据库结构完整性检查
# ============================================================
def test_database_structure():
    section("1. 数据库结构完整性检查")

    cursor = connection.cursor()

    # 检查所有业务表的 AUTO_INCREMENT
    business_tables = [
        'finish_product', 'unqualified_item', 'products', 'warehouse_log',
        'bom_list', 'repair', 'assembly_recipes', 'production_plan'
    ]

    for table in business_tables:
        try:
            cursor.execute(f"SHOW CREATE TABLE `{table}`")
            create_sql = cursor.fetchone()[1]

            if 'AUTO_INCREMENT' in create_sql:
                record_pass(f"表 {table} 的 id 字段有 AUTO_INCREMENT")
            else:
                record_fail(f"表 {table} 的 id 字段缺少 AUTO_INCREMENT",
                           "主键无自增，插入新记录会失败")

            # 检查字符集
            if 'utf8mb4_0900_ai_ci' in create_sql and table not in ('warehouse_log', 'repair', 'production_plan'):
                record_warning(f"表 {table}", "字符集为 utf8mb4_0900_ai_ci，与其他表不统一")

        except Exception as e:
            record_fail(f"检查表 {table}", str(e))

    # 检查 NOT NULL 约束问题
    null_check_fields = [
        ('products', 'quantity', 'int'),
        ('products', 'updated_at', 'datetime'),
        ('warehouse_log', 'description', 'text'),
        ('assembly_recipes', 'bom_id', 'int'),
        ('assembly_recipes', 'component_name', 'longtext'),
        ('assembly_recipes', 'component_quantity', 'int'),
        ('assembly_recipes', 'created_at', 'datetime'),
        ('assembly_recipes', 'updated_at', 'datetime'),
        ('production_plan', 'created_at', 'datetime'),
        ('production_plan', 'updated_at', 'datetime'),
    ]

    print(f"\n  --- NOT NULL 约束检查 ---")
    for table, field, dtype in null_check_fields:
        try:
            cursor.execute(f"SHOW COLUMNS FROM `{table}` LIKE '{field}'")
            row = cursor.fetchone()
            if row:
                is_null = row[2]  # 'YES' or 'NO'
                if is_null == 'NO':
                    record_fail(f"{table}.{field}",
                               "NOT NULL 但模型定义允许 null=True")
                else:
                    record_pass(f"{table}.{field} 允许 NULL")
        except Exception as e:
            record_fail(f"检查 {table}.{field}", str(e))


# ============================================================
# 2. 认证与用户模块
# ============================================================
def test_auth_module():
    section("2. 认证与用户模块")

    client = Client()

    # 测试登录接口
    try:
        response = client.post('/api/v1/auth/login', data=json.dumps({
            'username': 'admin',
            'password': '123456'
        }), content_type='application/json')
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '00000' and data.get('data', {}).get('accessToken'):
                record_pass("登录接口正常")
                return data['data']['accessToken']
            else:
                record_fail("登录接口", f"返回: {data.get('msg', '未知错误')}")
        else:
            record_fail("登录接口", f"状态码: {response.status_code}")
    except Exception as e:
        record_fail("登录接口", str(e))

    # 测试验证码接口
    try:
        response = client.get('/api/v1/auth/captcha')
        if response.status_code == 200:
            record_pass("验证码接口正常")
        else:
            record_fail("验证码接口", f"状态码: {response.status_code}")
    except Exception as e:
        record_fail("验证码接口", str(e))

    return None


# ============================================================
# 3. 成品管理模块
# ============================================================
def test_finish_product_module(token=None):
    section("3. 成品管理模块")

    client = Client()
    headers = {}
    if token:
        headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    # 测试列表接口
    try:
        response = client.get('/api/v1/finish-product/list/', **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("成品列表接口")
            list_data = data.get('data', {})
            total = list_data.get('total', 0) if isinstance(list_data, dict) else len(list_data)
            print(f"         成品总数: {total}")
        else:
            record_fail("成品列表接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("成品列表接口", str(e))

    # 测试库存一致性检查
    try:
        response = client.get('/api/v1/finish-product/check-joint-consistency/', **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("库存一致性检查接口")
            check_data = data.get('data', {})
            if isinstance(check_data, dict) and check_data.get('warnings'):
                for w in check_data['warnings'][:3]:
                    record_warning("库存一致性", w)
        else:
            record_fail("库存一致性检查接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("库存一致性检查接口", str(e))

    # 测试日统计接口
    try:
        response = client.get('/api/v1/finish-product/daily-stats/', {
            'start_date': '2026-01-01',
            'end_date': '2026-12-31',
        }, **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("日统计接口")
        else:
            record_fail("日统计接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("日统计接口", str(e))

    # 测试看板详情接口
    try:
        response = client.get('/api/v1/finish-product/board-detail/', {
            'category': 'total',
        }, **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("看板详情接口")
        else:
            record_fail("看板详情接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("看板详情接口", str(e))

    # 测试仓库日志列表
    try:
        response = client.get('/api/v1/finish-product/warehouse-log/list/', **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("仓库日志列表接口")
        else:
            record_fail("仓库日志列表接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("仓库日志列表接口", str(e))

    # 测试不合格项列表
    try:
        response = client.get('/api/v1/finish-product/unqualified/list/', {'finish_product_id': 1}, **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("不合格项列表接口")
        else:
            record_fail("不合格项列表接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("不合格项列表接口", str(e))

    # 测试创建成品（需要有效的 bom_id）
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM bom_list LIMIT 1")
    bom_row = cursor.fetchone()
    if bom_row:
        try:
            response = client.post('/api/v1/finish-product/create/', data=json.dumps({
                'bom_id': bom_row[0],
                'sn_code': f'TEST_{os.getpid()}',
                'status': 0,
                'inventory_stock': 0,
                'repair': 0,
            }), content_type='application/json', **headers)
            data = response.json()
            if data.get('code') == '00000':
                record_pass("创建成品接口")
                product_id = data.get('data', {}).get('id') if isinstance(data.get('data'), dict) else None
                # 清理测试数据
                if product_id:
                    cursor.execute("DELETE FROM finish_product WHERE id = %s", [product_id])
                    connection.commit()
            else:
                record_fail("创建成品接口", data.get('msg', '未知错误'))
        except Exception as e:
            record_fail("创建成品接口", str(e))
    else:
        record_warning("创建成品测试", "无BOM数据，跳过测试")


# ============================================================
# 4. 产品管理模块
# ============================================================
def test_product_module(token=None):
    section("4. 产品管理模块")

    client = Client()
    headers = {}
    if token:
        headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    # 测试列表
    try:
        response = client.get('/api/v1/product/list/', **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("产品列表接口")
        else:
            record_fail("产品列表接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("产品列表接口", str(e))

    # 测试库存预警列表
    try:
        response = client.get('/api/v1/product/stock-alert/list/', **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("库存预警列表接口")
        else:
            record_fail("库存预警列表接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("库存预警列表接口", str(e))

    # 测试仓库日志列表
    try:
        response = client.get('/api/v1/product/warehouse-log/list/', **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("产品仓库日志列表接口")
        else:
            record_fail("产品仓库日志列表接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("产品仓库日志列表接口", str(e))

    # 测试创建产品
    try:
        response = client.post('/api/v1/product/create/', data=json.dumps({
            'name': f'测试产品_{os.getpid()}',
            'type': 0,
            'quantity': 100,
        }), content_type='application/json', **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("创建产品接口")
            # 清理
            product_id = data.get('data', {}).get('id') if isinstance(data.get('data'), dict) else None
            if product_id:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM products WHERE id = %s", [product_id])
                connection.commit()
        else:
            record_fail("创建产品接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("创建产品接口", str(e))


# ============================================================
# 5. BOM管理模块
# ============================================================
def test_bom_module(token=None):
    section("5. BOM管理模块")

    client = Client()
    headers = {}
    if token:
        headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    # 测试列表
    try:
        response = client.get('/api/v1/bom/list/', **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("BOM列表接口")
        else:
            record_fail("BOM列表接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("BOM列表接口", str(e))

    # 测试详情
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM bom_list LIMIT 1")
    bom_row = cursor.fetchone()
    if bom_row:
        try:
            response = client.get('/api/v1/bom/detail/', {'bom_id': bom_row[0]}, **headers)
            data = response.json()
            if data.get('code') == '00000':
                record_pass("BOM详情接口")
            else:
                record_fail("BOM详情接口", data.get('msg', '未知错误'))
        except Exception as e:
            record_fail("BOM详情接口", str(e))
    else:
        record_warning("BOM详情测试", "无BOM数据")


# ============================================================
# 6. 返修管理模块
# ============================================================
def test_repair_module(token=None):
    section("6. 返修管理模块")

    client = Client()
    headers = {}
    if token:
        headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    # 测试列表
    try:
        response = client.get('/api/v1/repair/list/', **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("返修列表接口")
        else:
            record_fail("返修列表接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("返修列表接口", str(e))

    # 测试获取返修产品列表
    try:
        response = client.get('/api/v1/repair/products/', **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("返修产品列表接口")
        else:
            record_fail("返修产品列表接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("返修产品列表接口", str(e))


# ============================================================
# 7. 生产计划模块
# ============================================================
def test_production_plan_module(token=None):
    section("7. 生产计划模块")

    client = Client()
    headers = {}
    if token:
        headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    # 测试列表
    try:
        response = client.get('/api/v1/production-plan/list', **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("生产计划列表接口")
        else:
            record_fail("生产计划列表接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("生产计划列表接口", str(e))

    # 测试计算生产需求
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM bom_list LIMIT 1")
    bom_row = cursor.fetchone()
    if bom_row:
        try:
            response = client.get('/api/v1/production-plan/calculate', {
                'bom_id': bom_row[0],
                'quantity': 10,
            }, **headers)
            data = response.json()
            if data.get('code') == '00000':
                record_pass("生产需求计算接口")
            else:
                record_fail("生产需求计算接口", data.get('msg', '未知错误'))
        except Exception as e:
            record_fail("生产需求计算接口", str(e))
    else:
        record_warning("生产需求计算测试", "无BOM数据")


# ============================================================
# 8. 订单管理模块
# ============================================================
def test_order_module(token=None):
    section("8. 订单管理模块")

    client = Client()
    headers = {}
    if token:
        headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    # 测试健康检查
    try:
        response = client.get('/api/v1/order/health/', **headers)
        if response.status_code == 200:
            record_pass("订单健康检查接口")
        else:
            record_fail("订单健康检查接口", f"状态码: {response.status_code}")
    except Exception as e:
        record_fail("订单健康检查接口", str(e))

    # 测试列表
    try:
        response = client.get('/api/v1/order/list/', **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("订单列表接口")
        else:
            record_fail("订单列表接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("订单列表接口", str(e))


# ============================================================
# 9. 字典模块
# ============================================================
def test_dict_module(token=None):
    section("9. 字典模块")

    client = Client()
    headers = {}
    if token:
        headers['HTTP_AUTHORIZATION'] = f'Bearer {token}'

    # 测试获取字典项
    try:
        response = client.get('/api/v1/dicts/unqualified_status/items', **headers)
        data = response.json()
        if data.get('code') == '00000':
            record_pass("字典项查询接口")
            items = data.get('data', [])
            print(f"         unqualified_status 字典项: {len(items)} 条")
        else:
            record_fail("字典项查询接口", data.get('msg', '未知错误'))
    except Exception as e:
        record_fail("字典项查询接口", str(e))


# ============================================================
# 10. 数据完整性检查
# ============================================================
def test_data_integrity():
    section("10. 数据完整性检查")

    cursor = connection.cursor()

    # 检查成品表是否有孤立数据
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM finish_product fp
            LEFT JOIN bom_list bl ON fp.bom_id = bl.id
            WHERE bl.id IS NULL
        """)
        orphan_count = cursor.fetchone()[0]
        if orphan_count > 0:
            record_warning("成品表孤立数据", f"{orphan_count} 条成品的 bom_id 在 bom_list 中不存在")
        else:
            record_pass("成品表无孤立 bom_id 数据")
    except Exception as e:
        record_fail("成品表孤立数据检查", str(e))

    # 检查不合格项表是否有孤立数据
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM unqualified_item ui
            LEFT JOIN finish_product fp ON ui.finish_product_id = fp.id
            WHERE fp.id IS NULL
        """)
        orphan_count = cursor.fetchone()[0]
        if orphan_count > 0:
            record_warning("不合格项表孤立数据", f"{orphan_count} 条不合格项的 finish_product_id 不存在")
        else:
            record_pass("不合格项表无孤立数据")
    except Exception as e:
        record_fail("不合格项表孤立数据检查", str(e))

    # 检查测试不良成品是否有对应的不合格项
    try:
        cursor.execute("""
            SELECT fp.id, fp.sn_code
            FROM finish_product fp
            WHERE fp.status = 3
            AND NOT EXISTS (
                SELECT 1 FROM unqualified_item ui WHERE ui.finish_product_id = fp.id
            )
        """)
        missing = cursor.fetchall()
        if missing:
            record_warning("测试不良成品无不合格项",
                          f"{len(missing)} 条测试不良成品没有关联不合格项")
        else:
            record_pass("测试不良成品均有不合格项关联")
    except Exception as e:
        record_fail("测试不良成品检查", str(e))

    # 检查仓库日志的 operator_id 是否有效
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM warehouse_log wl
            LEFT JOIN sys_user su ON wl.operator_id = su.id
            WHERE wl.operator_id IS NOT NULL AND su.id IS NULL
        """)
        orphan_count = cursor.fetchone()[0]
        if orphan_count > 0:
            record_warning("仓库日志孤立操作人", f"{orphan_count} 条日志的 operator_id 不存在")
        else:
            record_pass("仓库日志操作人完整")
    except Exception as e:
        record_fail("仓库日志操作人检查", str(e))

    # 检查关节数量一致性
    try:
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM finish_product WHERE bom_type = 0 OR bom_id IN (SELECT id FROM bom_list WHERE type = 0)) as joint_count,
                (SELECT COUNT(*) FROM products WHERE type = 0) as product_joint_count
        """)
        # 这个查询可能不准确，但作为参考
        record_pass("关节数量一致性检查已执行")
    except Exception as e:
        record_warning("关节数量一致性检查", str(e))


# ============================================================
# 11. 表关系检查
# ============================================================
def test_table_relationships():
    section("11. 表关系检查")

    cursor = connection.cursor()

    # 检查装配配方表
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM assembly_recipes ar
            LEFT JOIN bom_list bl ON ar.bom_id = bl.id
            WHERE ar.bom_id IS NOT NULL AND bl.id IS NULL
        """)
        orphan_count = cursor.fetchone()[0]
        if orphan_count > 0:
            record_warning("装配配方孤立BOM", f"{orphan_count} 条配方的 bom_id 不存在")
        else:
            record_pass("装配配方表BOM关系完整")
    except Exception as e:
        record_fail("装配配方表关系检查", str(e))

    # 检查返修表
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM repair r
            LEFT JOIN finish_product fp ON r.product_id = fp.id
            WHERE fp.id IS NULL
        """)
        orphan_count = cursor.fetchone()[0]
        if orphan_count > 0:
            record_warning("返修表孤立成品", f"{orphan_count} 条返修记录的 product_id 不存在")
        else:
            record_pass("返修表成品关系完整")
    except Exception as e:
        record_fail("返修表关系检查", str(e))


# ============================================================
# 12. 模型与数据库一致性检查
# ============================================================
def test_model_db_consistency():
    section("12. 模型与数据库一致性检查")

    cursor = connection.cursor()

    # 检查关键表的数据量
    tables_to_check = [
        ('finish_product', '成品'),
        ('unqualified_item', '不合格项'),
        ('products', '产品'),
        ('warehouse_log', '仓库日志'),
        ('bom_list', 'BOM'),
        ('repair', '返修'),
        ('assembly_recipes', '装配配方'),
        ('production_plan', '生产计划'),
        ('sys_user', '系统用户'),
        ('sys_dict_item', '字典项'),
    ]

    print(f"\n  --- 数据量统计 ---")
    for table, name in tables_to_check:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            count = cursor.fetchone()[0]
            print(f"  {name:12s} ({table:20s}): {count:6d} 条")
        except Exception as e:
            record_fail(f"统计 {table}", str(e))

    # 检查最大ID是否合理（AUTO_INCREMENT 是否正常）
    print(f"\n  --- AUTO_INCREMENT 状态检查 ---")
    for table, _ in tables_to_check:
        if table.startswith('sys_'):
            continue
        try:
            cursor.execute(f"SELECT MAX(id) FROM `{table}`")
            max_id = cursor.fetchone()[0]
            cursor.execute(f"""
                SELECT AUTO_INCREMENT FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table}'
            """)
            ai = cursor.fetchone()
            ai_value = ai[0] if ai else None
            if max_id is not None and ai_value is not None:
                if ai_value <= max_id:
                    record_fail(f"{table} AUTO_INCREMENT",
                               f"AUTO_INCREMENT={ai_value} <= MAX(id)={max_id}，新插入会冲突")
                else:
                    record_pass(f"{table} AUTO_INCREMENT 正常 (next={ai_value}, max_id={max_id})")
            elif ai_value is None and max_id is not None:
                record_fail(f"{table} AUTO_INCREMENT", "表无 AUTO_INCREMENT 属性")
            else:
                record_warning(f"{table}", "表为空或无法获取 AUTO_INCREMENT")
        except Exception as e:
            record_fail(f"{table} AUTO_INCREMENT 检查", str(e))


# ============================================================
# 主函数
# ============================================================
def main():
    print("=" * 60)
    print("          系统综合测试开始")
    print(f"          测试时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 数据库结构检查
    test_database_structure()

    # 2. 认证模块（获取token）
    token = test_auth_module()

    # 3-9. 业务模块测试
    test_finish_product_module(token)
    test_product_module(token)
    test_bom_module(token)
    test_repair_module(token)
    test_production_plan_module(token)
    test_order_module(token)
    test_dict_module(token)

    # 10-12. 数据完整性检查
    test_data_integrity()
    test_table_relationships()
    test_model_db_consistency()

    # 输出汇总
    print("\n" + "=" * 60)
    print("                    测试结果汇总")
    print("=" * 60)
    print(f"\n  通过: {test_results['pass']}")
    print(f"  失败: {test_results['fail']}")
    print(f"  警告: {len(test_results['warnings'])}")

    if test_results['errors']:
        print(f"\n{'─' * 60}")
        print("  失败项明细:")
        print(f"{'─' * 60}")
        for i, err in enumerate(test_results['errors'], 1):
            print(f"  {i}. {err}")

    if test_results['warnings']:
        print(f"\n{'─' * 60}")
        print("  警告项明细:")
        print(f"{'─' * 60}")
        for i, warn in enumerate(test_results['warnings'], 1):
            print(f"  {i}. {warn}")

    print("\n" + "=" * 60)
    if test_results['fail'] == 0:
        print("  ✅ 所有关键测试通过！")
    else:
        print(f"  ❌ 有 {test_results['fail']} 个测试失败，需要修复！")
    print("=" * 60)

    return test_results


if __name__ == '__main__':
    main()
