// WebSocket 服务
export { setupWebSocket, cleanupWebSocket } from "./websocket";
export { useStomp, useDictSync, useOnlineCount } from "./websocket";
export type { DictMessage, DictChangeMessage, DictChangeCallback } from "./websocket";

// 表格相关
export { useTableSelection } from "./useTableSelection";

// 最近访问菜单
export { useRecentMenus } from "./useRecentMenus";
export type { RecentMenuItem } from "./useRecentMenus";

// 成品表格列展示
export { useFinishProductTableColumns, finishProductColumnOptions, FINISH_PRODUCT_COLUMN_STORAGE_KEY, FINISH_PRODUCT_BOARD_DETAIL_COLUMN_STORAGE_KEY } from "./useFinishProductTableColumns";
export type { FinishProductColumnOption } from "./useFinishProductTableColumns";

// 订单表格列展示
export { useOrderTableColumns, orderColumnOptions, ORDER_COLUMN_STORAGE_KEY } from "./useOrderTableColumns";
export type { OrderColumnOption } from "./useOrderTableColumns";

// 库存管理表格列展示
export { useProductTableColumns, productColumnOptions, PRODUCT_COLUMN_STORAGE_KEY } from "./useProductTableColumns";
export type { ProductColumnOption } from "./useProductTableColumns";
