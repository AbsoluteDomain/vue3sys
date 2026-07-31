import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import connection

# 创建 warehouse_log 表
create_table_sql = """
CREATE TABLE IF NOT EXISTS warehouse_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sn_code VARCHAR(255) NULL,
    material_code VARCHAR(255) NULL,
    storage_status INT NOT NULL,
    count INT DEFAULT 1,
    description TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sn_code (sn_code),
    INDEX idx_material_code (material_code),
    INDEX idx_storage_status (storage_status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

with connection.cursor() as cursor:
    cursor.execute(create_table_sql)
    print('warehouse_log table created successfully!')
