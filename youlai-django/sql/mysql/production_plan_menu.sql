INSERT INTO `sys_menu` VALUES
(203, 20, '0,20', '生产计划', 'M', 'ProductionPlan', 'index', 'product/productionPlan', NULL, 0, 1, 1, 3, 'calendar', NULL, NOW(), NOW(), NULL);

INSERT INTO `sys_role_menu` (`role_id`, `menu_id`) VALUES
(2, 203);