-- ==============================================================
-- 线上数据库变更脚本（自提交 f5a5893 之后）
-- 内容：审批模块（审批配置/申请单/审核人明细）、BOM 附件、文件管理
-- 说明：项目不使用 migrations，数据库结构由本脚本手动维护
-- 执行方式（必须指定数据库，否则会报 No database selected）：
--   mysql -u<user> -p -D <db_name> < approval_and_file_manager.sql
-- 或在脚本开头手动加入：USE `<db_name>`;
-- 脚本可重复执行（建表用 IF NOT EXISTS，菜单/授权用 INSERT IGNORE）
-- 执行前请先备份数据库
-- ==============================================================

-- ---------------- 1. 审批配置表 ----------------
CREATE TABLE IF NOT EXISTS `approval_config` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `biz_type` varchar(32) NOT NULL UNIQUE COMMENT '业务类型编码',
  `perm_code` varchar(128) NOT NULL UNIQUE COMMENT '权限标识（按钮权限编码）',
  `menu_id` bigint NULL COMMENT '按钮权限对应的菜单ID',
  `name` varchar(64) NOT NULL COMMENT '功能名称',
  `enabled` smallint NOT NULL COMMENT '审核状态（1-已启用, 0-未启用）',
  `approval_mode` varchar(16) NOT NULL COMMENT '审批模式（single-单人审批, multi-多人审批）',
  `approver_ids` varchar(500) NOT NULL COMMENT '审核人ID列表（英文逗号分隔）',
  `approver_names` varchar(500) NOT NULL COMMENT '审核人名称列表（英文逗号分隔）',
  `editor_id` bigint NULL COMMENT '最近修改人ID',
  `editor_name` varchar(64) NULL COMMENT '最近修改人',
  `created_at` datetime(6) NULL COMMENT '创建时间',
  `updated_at` datetime(6) NULL COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审批配置表';

-- ---------------- 2. 审批申请单表 ----------------
CREATE TABLE IF NOT EXISTS `approval_request` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `biz_type` varchar(32) NOT NULL COMMENT '业务类型编码',
  `name` varchar(64) NOT NULL COMMENT '功能名称',
  `target_id` bigint NOT NULL COMMENT '业务对象ID',
  `target_name` varchar(255) NOT NULL COMMENT '业务对象名称',
  `summary` varchar(500) NOT NULL COMMENT '申请内容摘要',
  `payload` longtext NOT NULL COMMENT '业务参数（JSON文本，审批通过后据此执行）',
  `applicant_id` bigint NULL COMMENT '申请人ID',
  `applicant_name` varchar(64) NOT NULL COMMENT '申请人名称',
  `approval_mode` varchar(16) NOT NULL COMMENT '审批模式（single-单人审批, multi-多人审批）',
  `status` smallint NOT NULL COMMENT '审批状态（0-待审批, 1-已通过, 2-已驳回, 3-执行失败）',
  `execute_error` varchar(500) NOT NULL COMMENT '执行失败原因',
  `created_at` datetime(6) NULL COMMENT '提交时间',
  `finished_at` datetime(6) NULL COMMENT '完成时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审批申请单表';

-- ---------------- 3. 审批申请审核人明细表 ----------------
CREATE TABLE IF NOT EXISTS `approval_request_approver` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `request_id` bigint NOT NULL COMMENT '审批申请ID',
  `approver_id` bigint NOT NULL COMMENT '审核人ID',
  `approver_name` varchar(64) NOT NULL COMMENT '审核人名称',
  `decision` smallint NOT NULL COMMENT '审批结果（0-待处理, 1-同意, 2-拒绝）',
  `comment` varchar(500) NOT NULL COMMENT '审批意见',
  `decided_at` datetime(6) NULL COMMENT '处理时间',
  CONSTRAINT `approval_request_app_request_id_2e46465c_fk_approval_`
    FOREIGN KEY (`request_id`) REFERENCES `approval_request` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审批申请审核人明细表';

-- ---------------- 4. 文件管理条目表 ----------------
CREATE TABLE IF NOT EXISTS `file_manager_item` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `parent_id` bigint NOT NULL COMMENT '父目录ID（0表示根目录）',
  `name` varchar(255) NOT NULL COMMENT '文件或文件夹名称',
  `is_dir` smallint NOT NULL COMMENT '是否文件夹（1-是, 0-否）',
  `storage_path` varchar(500) NULL COMMENT '存储服务中的相对路径',
  `file_url` varchar(500) NULL COMMENT '文件访问地址',
  `file_size` bigint NOT NULL COMMENT '文件大小（字节）',
  `mime_type` varchar(128) NULL COMMENT '文件MIME类型',
  `file_type` varchar(32) NULL COMMENT '文件类型（小写扩展名，文件夹为 folder）',
  `uploader_id` bigint NULL COMMENT '上传人ID',
  `uploader_name` varchar(64) NULL COMMENT '上传人名称',
  `download_count` integer NOT NULL COMMENT '下载次数',
  `is_del` smallint NOT NULL COMMENT '删除标记（0-正常, 1-回收站）',
  `deleted_at` datetime(6) NULL COMMENT '删除时间',
  `created_at` datetime(6) NULL COMMENT '创建时间',
  `updated_at` datetime(6) NULL COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件管理条目表';

-- ---------------- 5. BOM 附件表 ----------------
CREATE TABLE IF NOT EXISTS `bom_attachment` (
  `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `bom_id` integer NOT NULL COMMENT 'BOM ID',
  `file_type` varchar(20) NOT NULL COMMENT '文件类型（excel/pdf/urdf）',
  `file_name` varchar(255) NOT NULL COMMENT '原始文件名',
  `file_url` varchar(500) NOT NULL COMMENT '访问地址',
  `storage_path` varchar(500) NOT NULL COMMENT '对象存储路径',
  `file_size` bigint NOT NULL COMMENT '文件大小（字节）',
  `mime_type` varchar(100) NULL COMMENT 'MIME类型',
  `uploader_id` integer NULL COMMENT '上传人ID',
  `uploader_name` varchar(100) NULL COMMENT '上传人姓名',
  `is_del` integer NOT NULL COMMENT '删除标记',
  `created_at` datetime(6) NULL COMMENT '创建时间',
  `updated_at` datetime(6) NULL COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='BOM附件表';

CREATE INDEX `bom_attachment_bom_id_4cee33fe` ON `bom_attachment` (`bom_id`);
CREATE INDEX `bom_attachment_file_type_f269ee36` ON `bom_attachment` (`file_type`);

-- ---------------- 6. 新增菜单 ----------------
INSERT IGNORE INTO `sys_menu` VALUES
(2938, 0, '0', '文件管理', 'C', NULL, '/file', 'Layout', NULL, 0, 0, 1, 1, 'file', NULL, NOW(), NOW(), NULL);

INSERT IGNORE INTO `sys_menu` VALUES
(2939, 2938, '0,2938', '文件管理', 'M', 'FileManager', 'index', 'file/index', NULL, 0, 1, 1, 1, 'el-icon-Folder', NULL, NOW(), NOW(), NULL);

INSERT IGNORE INTO `sys_menu` VALUES
(2940, 0, '0', '审核管理', 'C', NULL, '/approval', 'Layout', NULL, 0, 0, 1, 1, 'el-icon-Checked', NULL, NOW(), NOW(), NULL);

INSERT IGNORE INTO `sys_menu` VALUES
(2941, 2940, '0,2940', '审核管理', 'M', 'ApprovalManager', 'index', 'approval/index', NULL, 0, 1, 1, 1, 'el-icon-Checked', NULL, NOW(), NOW(), NULL);

INSERT IGNORE INTO `sys_menu` VALUES
(2942, 2912, '0,2912', '审批记录', 'M', 'ApprovalRecords', 'approvalRecord', 'approval/records', NULL, 0, 0, 1, 5, 'Document', NULL, NOW(), NOW(), NULL);

-- ---------------- 7. 角色菜单授权 ----------------
-- 系统管理员（role_id=2）：文件管理、审核管理、审批记录
-- 部门成员（role_id=5）：仅审批记录
INSERT IGNORE INTO `sys_role_menu` (`role_id`, `menu_id`) VALUES
(2, 2938), (2, 2939), (2, 2940), (2, 2941), (2, 2942),
(5, 2942);

-- ---------------- 8. 产品管理按钮权限菜单（缺失时补齐） ----------------
-- 审核管理页按「模块 -> 按钮权限」树展示，按钮菜单缺失会导致审核项不显示、无法点击
INSERT IGNORE INTO `sys_menu` VALUES (2915,2813,'0,2807,2813','成品组装','B',NULL,'','','product:finish:assemble',0,0,1,1,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2916,2813,'0,2807,2813','成品编辑','B',NULL,'','','product:finish:update',0,0,1,2,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2917,2813,'0,2807,2813','成品回退','B',NULL,'','','product:finish:rollback',0,0,1,3,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2918,2813,'0,2807,2813','关节绑定','B',NULL,'','','product:finish:bind',0,0,1,4,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2919,2813,'0,2807,2813','不良详情','B',NULL,'','','product:finish:defect',0,0,1,5,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2920,2813,'0,2807,2813','导出Excel','B',NULL,'','','product:finish:export',0,0,1,6,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2921,2813,'0,2807,2813','快捷操作-测试合格','B',NULL,'','','product:finish:test-pass',0,0,1,7,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2922,2813,'0,2807,2813','快捷操作-测试不良','B',NULL,'','','product:finish:test-fail',0,0,1,8,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2923,2813,'0,2807,2813','快捷操作-批量绑定SN码','B',NULL,'','','product:finish:batch-sn',0,0,1,9,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2924,2813,'0,2807,2813','快捷操作-添加关节','B',NULL,'','','product:finish:add-joint',0,0,1,10,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2925,2808,'0,2807,2808','库存新增','B',NULL,'','','product:stock:create',0,0,1,1,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2926,2808,'0,2807,2808','库存编辑','B',NULL,'','','product:stock:update',0,0,1,2,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2927,2808,'0,2807,2808','库存删除','B',NULL,'','','product:stock:delete',0,0,1,3,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2928,2808,'0,2807,2808','入库','B',NULL,'','','product:stock:inbound',0,0,1,4,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2929,2808,'0,2807,2808','出库','B',NULL,'','','product:stock:outbound',0,0,1,5,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2930,203,'0,2807,203','保存计划','B',NULL,'','','production:plan:save',0,0,1,1,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2931,2809,'0,2807,2809','查看BOM明细','B',NULL,'','','product:bom:detail',0,0,1,1,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2932,2809,'0,2807,2809','新增/导入BOM','B',NULL,'','','product:bom:create',0,0,1,2,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2933,2809,'0,2807,2809','导出/编辑BOM','B',NULL,'','','product:bom:update',0,0,1,3,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2934,2809,'0,2807,2809','删除BOM','B',NULL,'','','product:bom:delete',0,0,1,4,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2935,2907,'0,2807,2907','返修保存','B',NULL,'','','product:repair:save',0,0,1,1,NULL,NULL,NOW(),NOW(),NULL);
INSERT IGNORE INTO `sys_menu` VALUES (2936,2907,'0,2807,2907','返修删除','B',NULL,'','','product:repair:delete',0,0,1,2,NULL,NULL,NOW(),NOW(),NULL);

-- 按钮权限授权：系统管理员、部门成员均保留原有业务操作能力
INSERT IGNORE INTO `sys_role_menu` (`role_id`, `menu_id`) VALUES
(2,2915),(5,2915),(2,2916),(5,2916),(2,2917),(5,2917),(2,2918),(5,2918),
(2,2919),(5,2919),(2,2920),(5,2920),(2,2921),(5,2921),(2,2922),(5,2922),
(2,2923),(5,2923),(2,2924),(5,2924),(2,2925),(5,2925),(2,2926),(5,2926),
(2,2927),(5,2927),(2,2928),(5,2928),(2,2929),(5,2929),(2,2930),(5,2930),
(2,2931),(5,2931),(2,2932),(5,2932),(2,2933),(5,2933),(2,2934),(5,2934),
(2,2935),(5,2935),(2,2936),(5,2936);

-- ---------------- 9. 修复出入库审批配置的业务类型 ----------------
-- 出入库接口按 biz_type=inbound/outbound 匹配配置；
-- 若配置保存时把 perm_code 写进了 biz_type，会导致审批不拦截
UPDATE `approval_config` SET `biz_type`='inbound'
WHERE `perm_code`='product:stock:inbound' AND `biz_type`<>'inbound';
UPDATE `approval_config` SET `biz_type`='outbound'
WHERE `perm_code`='product:stock:outbound' AND `biz_type`<>'outbound';
