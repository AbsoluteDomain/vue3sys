-- BOM 主表 bom_list + 明细表 assembly_recipes（bom_id 外键逻辑关联 bom_list.id）

/*
CREATE TABLE `bom_list` (
  `id` int NOT NULL AUTO_INCREMENT,
  `bom_name` varchar(255) NOT NULL,
  `is_del` int NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE `assembly_recipes`
  ADD COLUMN `bom_id` int DEFAULT NULL COMMENT '关联 bom_list.id';
*/
