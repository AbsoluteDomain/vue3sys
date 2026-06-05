-- 全新库初始化：产品管理目录 + 库存管理 + 产品BOM管理
-- 侧栏：首页 > 产品管理 > [库存管理 | 产品BOM管理]

INSERT INTO `sys_menu` VALUES
(20, 0, '0', '产品管理', 'C', '', '/product', 'Layout', NULL, 1, 0, 1, 10, 'shopping', '/product/index', NOW(), NOW(), NULL);

INSERT INTO `sys_menu` VALUES
(201, 20, '0,20', '库存管理', 'M', 'ProductInventory', 'index', 'product/index', NULL, 0, 1, 1, 1, 'box', NULL, NOW(), NOW(), NULL);

INSERT INTO `sys_menu` VALUES
(202, 20, '0,20', '产品BOM管理', 'M', 'productBom', 'productBom', 'product/bom', NULL, 0, 1, 1, 2, 'tree', NULL, NOW(), NOW(), NULL);

INSERT INTO `sys_role_menu` (`role_id`, `menu_id`) VALUES
(2, 20), (2, 201), (2, 202);
