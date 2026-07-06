-- =============================================================================
-- 版本更新公告（方案 B）
-- 表：sys_release / sys_release_item / sys_user_release_read
-- 执行后请退出登录并重新登录，以刷新动态路由
-- =============================================================================

CREATE TABLE IF NOT EXISTS `sys_release` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `version` varchar(32) NOT NULL COMMENT '版本号，如 v1.2.0',
  `title` varchar(100) NOT NULL COMMENT '公告标题',
  `summary` varchar(500) DEFAULT NULL COMMENT '摘要',
  `release_type` tinyint NOT NULL DEFAULT 1 COMMENT '发布类型（1: 常规, 2: 重要, 3: 紧急）',
  `publish_status` tinyint NOT NULL DEFAULT 0 COMMENT '发布状态（0: 未发布, 1: 已发布, -1: 已撤回）',
  `publish_time` datetime DEFAULT NULL COMMENT '发布时间',
  `revoke_time` datetime DEFAULT NULL COMMENT '撤回时间',
  `force_notify` tinyint NOT NULL DEFAULT 1 COMMENT '是否登录弹窗提醒（1: 是, 0: 否）',
  `create_by` bigint DEFAULT NULL COMMENT '创建人ID',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新人ID',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `is_deleted` tinyint NOT NULL DEFAULT 0 COMMENT '是否删除（0: 否, 1: 是）',
  PRIMARY KEY (`id`),
  KEY `idx_release_publish` (`publish_status`, `publish_time`),
  KEY `idx_release_version` (`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统版本更新公告';

CREATE TABLE IF NOT EXISTS `sys_release_item` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `release_id` bigint NOT NULL COMMENT '公告ID',
  `item_type` tinyint NOT NULL DEFAULT 1 COMMENT '条目类型（1: 新功能, 2: 优化, 3: 修复, 4: 其他）',
  `content` varchar(500) NOT NULL COMMENT '条目内容',
  `sort` int NOT NULL DEFAULT 0 COMMENT '排序',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_release_item_release` (`release_id`, `sort`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='版本更新公告明细';

CREATE TABLE IF NOT EXISTS `sys_user_release_read` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `release_id` bigint NOT NULL COMMENT '公告ID',
  `is_read` tinyint NOT NULL DEFAULT 0 COMMENT '是否已读（0: 未读, 1: 已读）',
  `read_time` datetime DEFAULT NULL COMMENT '阅读时间',
  `create_time` datetime NOT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_release` (`user_id`, `release_id`),
  KEY `idx_user_release_read` (`user_id`, `is_read`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户版本公告阅读记录';

-- 菜单：版本公告（系统管理下，sort=10）
INSERT INTO sys_menu (
  id, parent_id, tree_path, name, type, route_name, route_path, component,
  perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time
)
SELECT
  290, 1, '0,1', '版本公告', 'M', 'Release', 'release', 'system/release/index',
  NULL, 0, 1, 1, 10, 'document', NULL, NOW(), NOW()
FROM DUAL
WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE id = 290 OR component = 'system/release/index');

INSERT INTO sys_menu (id, parent_id, tree_path, name, type, route_name, route_path, component, perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time)
SELECT 2901, 290, '0,1,290', '版本查询', 'B', NULL, '', NULL, 'sys:release:list', NULL, NULL, 1, 1, '', NULL, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE id = 2901);

INSERT INTO sys_menu (id, parent_id, tree_path, name, type, route_name, route_path, component, perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time)
SELECT 2902, 290, '0,1,290', '版本新增', 'B', NULL, '', NULL, 'sys:release:create', NULL, NULL, 1, 2, '', NULL, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE id = 2902);

INSERT INTO sys_menu (id, parent_id, tree_path, name, type, route_name, route_path, component, perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time)
SELECT 2903, 290, '0,1,290', '版本编辑', 'B', NULL, '', NULL, 'sys:release:update', NULL, NULL, 1, 3, '', NULL, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE id = 2903);

INSERT INTO sys_menu (id, parent_id, tree_path, name, type, route_name, route_path, component, perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time)
SELECT 2904, 290, '0,1,290', '版本删除', 'B', NULL, '', NULL, 'sys:release:delete', NULL, NULL, 1, 4, '', NULL, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE id = 2904);

INSERT INTO sys_menu (id, parent_id, tree_path, name, type, route_name, route_path, component, perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time)
SELECT 2905, 290, '0,1,290', '版本发布', 'B', NULL, '', NULL, 'sys:release:publish', NULL, NULL, 1, 5, '', NULL, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE id = 2905);

INSERT INTO sys_menu (id, parent_id, tree_path, name, type, route_name, route_path, component, perm, always_show, keep_alive, visible, sort, icon, redirect, create_time, update_time)
SELECT 2906, 290, '0,1,290', '版本撤回', 'B', NULL, '', NULL, 'sys:release:revoke', NULL, NULL, 1, 6, '', NULL, NOW(), NOW()
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM sys_menu WHERE id = 2906);

-- 管理员角色授权
INSERT INTO sys_role_menu (role_id, menu_id)
SELECT 2, m.id
FROM sys_menu m
WHERE m.id IN (290, 2901, 2902, 2903, 2904, 2905, 2906)
  AND NOT EXISTS (SELECT 1 FROM sys_role_menu rm WHERE rm.role_id = 2 AND rm.menu_id = m.id);
