-- 成品管理表（BOM 组装成功后写入）
CREATE TABLE IF NOT EXISTS `finish_product` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `sn_code` varchar(255) DEFAULT NULL COMMENT 'SN码，产品唯一标识',
  `bom_id` int NOT NULL COMMENT 'BOM ID，对应 bom_list.id',
  `name` varchar(255) NOT NULL COMMENT '成品名称，对应 bom_list.bom_name',
  `status` int NOT NULL DEFAULT 0 COMMENT '测试状态：0未测试，1测试中，2测试合格，3测试不良',
  `description` varchar(255) DEFAULT NULL COMMENT '描述',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `inventory_stock` int NOT NULL DEFAULT 0 COMMENT '库存状态：0未入库，1入库，2出库',
  `repair` int NOT NULL DEFAULT 0 COMMENT '是否返修：0新品，1返修品',
  PRIMARY KEY (`id`),
  KEY `idx_bom_id` (`bom_id`),
  KEY `idx_sn_code` (`sn_code`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='成品管理表';
