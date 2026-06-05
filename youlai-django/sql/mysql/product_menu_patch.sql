-- =============================================================================
-- 侧栏结构：首页 > 产品管理 > 产品BOM管理（与「库存管理」同级）
-- 执行后请退出登录并重新登录，以刷新动态路由
-- =============================================================================

-- 1) 确保存在「产品管理」目录（顶级 Layout）
INSERT INTO sys_menu (
  parent_id, tree_path, name, type, route_name, route_path, component,
  perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time
)
SELECT
  0, '0', '产品管理', 'C', '', '/product', 'Layout',
  NULL, 1, 0, 1,
  IFNULL((SELECT MAX(sort) FROM sys_menu WHERE parent_id = 0), 0) + 1,
  'shopping', '/product/index', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM sys_menu WHERE type = 'C' AND route_path = '/product'
);

-- 目录始终展开子菜单（避免只授权一个子项时被折叠成单页）
UPDATE sys_menu
SET always_show = 1, visible = 1
WHERE type = 'C' AND route_path = '/product';

-- 2) 确保「库存管理」挂在产品管理下
INSERT INTO sys_menu (
  parent_id, tree_path, name, type, route_name, route_path, component,
  perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time
)
SELECT
  p.id, CONCAT(p.tree_path, ',', p.id), '库存管理', 'M',
  'ProductInventory', 'index', 'product/index',
  NULL, 0, 1, 1, 1, 'box', NULL, NOW(), NOW()
FROM sys_menu p
WHERE p.type = 'C' AND p.route_path = '/product'
  AND NOT EXISTS (
    SELECT 1 FROM sys_menu x WHERE x.component = 'product/index'
  )
LIMIT 1;

UPDATE sys_menu inv
INNER JOIN sys_menu p ON p.type = 'C' AND p.route_path = '/product'
SET
  inv.parent_id = p.id,
  inv.tree_path = CONCAT(p.tree_path, ',', p.id),
  inv.visible = 1,
  inv.type = 'M',
  inv.route_path = 'index',
  inv.route_name = IFNULL(NULLIF(inv.route_name, ''), 'ProductInventory'),
  inv.component = 'product/index'
WHERE inv.component = 'product/index';

-- 3) 确保「产品BOM管理」挂在产品管理下（组件 product/bom，路由 productBom）
INSERT INTO sys_menu (
  parent_id, tree_path, name, type, route_name, route_path, component,
  perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time
)
SELECT
  p.id, CONCAT(p.tree_path, ',', p.id), '产品BOM管理', 'M',
  'productBom', 'productBom', 'product/bom',
  NULL, 0, 1, 1, 2, 'tree', NULL, NOW(), NOW()
FROM sys_menu p
WHERE p.type = 'C' AND p.route_path = '/product'
  AND NOT EXISTS (
    SELECT 1 FROM sys_menu x
    WHERE x.component = 'product/bom' OR x.route_name = 'productBom'
  )
LIMIT 1;

UPDATE sys_menu bom
INNER JOIN sys_menu p ON p.type = 'C' AND p.route_path = '/product'
SET
  bom.parent_id = p.id,
  bom.tree_path = CONCAT(p.tree_path, ',', p.id),
  bom.name = '产品BOM管理',
  bom.type = 'M',
  bom.route_name = 'productBom',
  bom.route_path = 'productBom',
  bom.component = 'product/bom',
  bom.visible = 1,
  bom.sort = IF(bom.sort IS NULL OR bom.sort < 2, 2, bom.sort)
WHERE bom.component = 'product/bom'
   OR bom.route_name = 'productBom';

-- 4) 角色授权：管理员(role_id=2) + 已有「库存管理」权限的所有角色
INSERT INTO sys_role_menu (role_id, menu_id)
SELECT 2, m.id
FROM sys_menu m
WHERE (
    m.route_path = '/product'
    OR m.component IN ('product/index', 'product/bom')
    OR m.route_name IN ('ProductInventory', 'productBom')
  )
  AND NOT EXISTS (
    SELECT 1 FROM sys_role_menu rm WHERE rm.role_id = 2 AND rm.menu_id = m.id
  );



-- 6) 添加库存看板菜单
INSERT INTO sys_menu (
  parent_id, tree_path, name, type, route_name, route_path, component,
  perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time
)
SELECT
  0, '0', '库存看板', 'C', '', '/inventory', 'Layout',
  NULL, 0, 0, 1,
  IFNULL((SELECT MAX(sort) FROM sys_menu WHERE parent_id = 0), 0) + 1,
  'monitor', '/inventory/stock-board', NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (
  SELECT 1 FROM sys_menu WHERE type = 'C' AND route_path = '/inventory'
);

INSERT INTO sys_menu (
  parent_id, tree_path, name, type, route_name, route_path, component,
  perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time
)
SELECT
  p.id, CONCAT(p.tree_path, ',', p.id), '库存看板', 'M',
  'StockBoard', 'stock-board', 'inventory/stock-board/index',
  NULL, 0, 1, 1, 1, 'monitor', NULL, NOW(), NOW()
FROM sys_menu p
WHERE p.type = 'C' AND p.route_path = '/inventory'
  AND NOT EXISTS (
    SELECT 1 FROM sys_menu x WHERE x.component = 'inventory/stock-board/index' OR x.route_name = 'StockBoard'
  )
LIMIT 1;

UPDATE sys_menu sb
INNER JOIN sys_menu p ON p.type = 'C' AND p.route_path = '/inventory'
SET
  sb.parent_id = p.id,
  sb.tree_path = CONCAT(p.tree_path, ',', p.id),
  sb.visible = 1,
  sb.type = 'M',
  sb.route_path = 'stock-board',
  sb.route_name = IFNULL(NULLIF(sb.route_name, ''), 'StockBoard'),
  sb.component = 'inventory/stock-board/index',
  sb.sort = IF(sb.sort IS NULL OR sb.sort < 1, 1, sb.sort),
  sb.icon = IFNULL(NULLIF(sb.icon, ''), 'monitor')
WHERE sb.component = 'inventory/stock-board/index'
   OR sb.route_name = 'StockBoard';

INSERT INTO sys_role_menu (role_id, menu_id)
SELECT 2, m.id
FROM sys_menu m
WHERE (
    m.route_path = '/inventory'
    OR m.component = 'inventory/stock-board/index'
    OR m.route_name = 'StockBoard'
  )
  AND NOT EXISTS (
    SELECT 1 FROM sys_role_menu rm WHERE rm.role_id = 2 AND rm.menu_id = m.id
  );
INSERT INTO sys_role_menu (role_id, menu_id)
SELECT DISTINCT rm.role_id, bom.id
FROM sys_role_menu rm
INNER JOIN sys_menu inv ON inv.id = rm.menu_id AND inv.component = 'product/index'
INNER JOIN sys_menu bom ON bom.component = 'product/bom' OR bom.route_name = 'productBom'
WHERE NOT EXISTS (
  SELECT 1 FROM sys_role_menu x WHERE x.role_id = rm.role_id AND x.menu_id = bom.id
);

-- 5) 校验（执行后应能看到 1 条 BOM 菜单记录）
-- SELECT id, parent_id, name, route_name, route_path, component, visible, always_show
-- FROM sys_menu WHERE route_path = '/product' OR component LIKE 'product/%' OR route_name = 'productBom';
