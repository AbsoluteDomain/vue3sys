-- BOM 主表 bom_list + 明细表 assembly_recipes（bom_id 外键逻辑关联 bom_list.id）



/*

CREATE TABLE `bom_list` (

  `id` int NOT NULL AUTO_INCREMENT,

  `bom_model` varchar(255) NOT NULL COMMENT 'BOM型号',

  `bom_name` varchar(255) DEFAULT NULL COMMENT 'BOM名称',

  `material_code` varchar(255) DEFAULT NULL COMMENT '物料编码',

  `is_del` int NOT NULL DEFAULT 0,

  `type` int NOT NULL DEFAULT 0 COMMENT '成品类型 0：关节，1：机械臂，2：其他',

  PRIMARY KEY (`id`)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;



ALTER TABLE `assembly_recipes`

  ADD COLUMN `bom_id` int DEFAULT NULL COMMENT '关联 bom_list.id';

*/


