-- ==============================================================
-- 线上数据库变更脚本（自提交 f5a5893 之后）
-- 内容：审批模块（审批配置/申请单/审核人明细）、BOM 附件、文件管理
-- 说明：项目不使用 migrations，数据库结构由本脚本手动维护
-- 执行方式：mysql -u<user> -p <db_name> < approval_and_file_manager.sql
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
INSERT INTO `sys_menu` VALUES
(2938, 0, '0', '文件管理', 'C', NULL, '/file', 'Layout', NULL, 0, 0, 1, 1, 'file', NULL, NOW(), NOW(), NULL);

INSERT INTO `sys_menu` VALUES
(2939, 2938, '0,2938', '文件管理', 'M', 'FileManager', 'index', 'file/index', NULL, 0, 1, 1, 1, 'el-icon-Folder', NULL, NOW(), NOW(), NULL);

INSERT INTO `sys_menu` VALUES
(2940, 0, '0', '审核管理', 'C', NULL, '/approval', 'Layout', NULL, 0, 0, 1, 1, 'el-icon-Checked', NULL, NOW(), NOW(), NULL);

INSERT INTO `sys_menu` VALUES
(2941, 2940, '0,2940', '审核管理', 'M', 'ApprovalManager', 'index', 'approval/index', NULL, 0, 1, 1, 1, 'el-icon-Checked', NULL, NOW(), NOW(), NULL);

INSERT INTO `sys_menu` VALUES
(2942, 2912, '0,2912', '审批记录', 'M', 'ApprovalRecords', 'approvalRecord', 'approval/records', NULL, 0, 0, 1, 5, 'Document', NULL, NOW(), NOW(), NULL);

-- ---------------- 7. 角色菜单授权 ----------------
-- 系统管理员（role_id=2）：文件管理、审核管理、审批记录
-- 部门成员（role_id=5）：仅审批记录
INSERT INTO `sys_role_menu` (`role_id`, `menu_id`) VALUES
(2, 2938), (2, 2939), (2, 2940), (2, 2941), (2, 2942),
(5, 2942);
