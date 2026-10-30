import { ref } from "vue";
import { ElMessage } from "element-plus";

export const FINISH_PRODUCT_COLUMN_STORAGE_KEY = "finish-product-table-columns";
export const FINISH_PRODUCT_BOARD_DETAIL_COLUMN_STORAGE_KEY = "finish-product-board-detail-columns";
export const BOM_STOCK_COLUMN_STORAGE_KEY = "bom-stock-table-columns";

export interface FinishProductColumnOption {
  key: string;
  label: string;
  defaultVisible: boolean;
}

export const finishProductColumnOptions: FinishProductColumnOption[] = [
  { key: "sn_code", label: "SN码", defaultVisible: true },
  { key: "sn_code_time", label: "SN码录入时间", defaultVisible: false },
  { key: "sn_code_binder", label: "SN码绑定人", defaultVisible: false },
  { key: "bom_type", label: "BOM类型", defaultVisible: true },
  { key: "bom_model", label: "BOM型号", defaultVisible: true },
  { key: "bom_name", label: "BOM名称", defaultVisible: true },
  { key: "material_code", label: "物料编码", defaultVisible: false },
  { key: "parent_sn_code", label: "父级SN码", defaultVisible: false },
  { key: "status", label: "测试状态", defaultVisible: true },
  { key: "inventory_stock", label: "库存状态", defaultVisible: true },
  { key: "repair", label: "返修", defaultVisible: true },
  { key: "test_time", label: "测试状态修改时间", defaultVisible: false },
  { key: "stock_in_time", label: "入库时间", defaultVisible: false },
  { key: "stock_out_time", label: "出库时间", defaultVisible: false },
  { key: "create_time", label: "创建时间", defaultVisible: false },
  { key: "update_time", label: "更新时间", defaultVisible: true },
  { key: "creator_name", label: "创建人", defaultVisible: true },
  { key: "editor_name", label: "最后操作人", defaultVisible: true },
  { key: "description", label: "描述", defaultVisible: false },
];

/** 库存看板 - BOM 型号出入库明细表列定义 */
export const bomStockColumnOptions: FinishProductColumnOption[] = [
  { key: "bom_model", label: "BOM型号", defaultVisible: true },
  { key: "bom_name", label: "名称", defaultVisible: true },
  { key: "stockCount", label: "当前剩余库存", defaultVisible: true },
  { key: "inCount", label: "入库数", defaultVisible: true },
  { key: "inPercent", label: "入库占比", defaultVisible: true },
  { key: "outCount", label: "出库数", defaultVisible: true },
  { key: "outPercent", label: "出库占比", defaultVisible: true },
  { key: "outSaleCount", label: "出库(外销)", defaultVisible: true },
  { key: "outDevCount", label: "出库(研发)", defaultVisible: true },
  { key: "outScrapCount", label: "出库(报废)", defaultVisible: true },
  { key: "outExchangeCount", label: "出库(换货)", defaultVisible: true },
];

/** 返修管理列表存储 key 与列定义 */
export const REPAIR_COLUMN_STORAGE_KEY = "repair-table-columns";
export const repairColumnOptions: FinishProductColumnOption[] = [
  { key: "sn_code", label: "SN码", defaultVisible: true },
  { key: "product_model", label: "产品型号", defaultVisible: true },
  { key: "bom_name", label: "BOM名称", defaultVisible: true },
  { key: "repair_cnt", label: "返修次数", defaultVisible: true },
  { key: "unqualified_labels_1", label: "不良项1", defaultVisible: true },
  { key: "repair_desc_1", label: "描述1", defaultVisible: true },
  { key: "unqualified_labels_2", label: "不良项2", defaultVisible: true },
  { key: "repair_desc_2", label: "描述2", defaultVisible: true },
  { key: "repair_status", label: "返修状态", defaultVisible: true },
  { key: "create_time", label: "创建时间", defaultVisible: true },
  { key: "last_repair_time", label: "最后返修时间", defaultVisible: true },
];

/** 测试记录表存储 key 与列定义 */
export const TEST_RECORD_COLUMN_STORAGE_KEY = "test-record-table-columns";
export const testRecordColumnOptions: FinishProductColumnOption[] = [
  { key: "sn_code", label: "SN码", defaultVisible: true },
  { key: "product_model", label: "产品型号", defaultVisible: true },
  { key: "bom_type", label: "BOM类型", defaultVisible: true },
  { key: "bom_name", label: "BOM名称", defaultVisible: true },
  { key: "test_cnt", label: "测试次数", defaultVisible: true },
  { key: "unqualified_labels_1", label: "不良项1", defaultVisible: true },
  { key: "test_desc_1", label: "描述1", defaultVisible: true },
  { key: "test_status_1", label: "测试状态1", defaultVisible: true },
  { key: "unqualified_labels_2", label: "不良项2", defaultVisible: true },
  { key: "test_desc_2", label: "描述2", defaultVisible: true },
  { key: "test_status_2", label: "测试状态2", defaultVisible: true },
  { key: "create_time", label: "创建时间", defaultVisible: true },
  { key: "last_test_time", label: "最后测试时间", defaultVisible: true },
];

const getDefaultVisibleColumns = (options: FinishProductColumnOption[]) =>
  Object.fromEntries(options.map((col) => [col.key, col.defaultVisible]));

const getDefaultVisibleColumnKeys = (options: FinishProductColumnOption[]) =>
  options.filter((col) => col.defaultVisible).map((col) => col.key);

export function useFinishProductTableColumns(
  storageKey: string = FINISH_PRODUCT_COLUMN_STORAGE_KEY,
  options: FinishProductColumnOption[] = finishProductColumnOptions
) {
  const visibleColumns = ref<Record<string, boolean>>(getDefaultVisibleColumns(options));
  const columnDialogVisible = ref(false);
  const columnDraftKeys = ref<string[]>([]);

  const loadColumnSettings = () => {
    const saved = localStorage.getItem(storageKey);
    if (!saved) {
      visibleColumns.value = getDefaultVisibleColumns(options);
      return;
    }
    try {
      const parsed = JSON.parse(saved) as Record<string, boolean>;
      visibleColumns.value = Object.fromEntries(
        options.map((col) => [col.key, parsed[col.key] ?? col.defaultVisible])
      );
    } catch {
      visibleColumns.value = getDefaultVisibleColumns(options);
    }
  };

  const isColumnVisible = (key: string) => visibleColumns.value[key] !== false;

  const openColumnDialog = () => {
    columnDraftKeys.value = options.filter((col) => isColumnVisible(col.key)).map((col) => col.key);
    columnDialogVisible.value = true;
  };

  const resetColumnDraft = () => {
    columnDraftKeys.value = getDefaultVisibleColumnKeys(options);
  };

  const saveColumnSettings = () => {
    if (!columnDraftKeys.value.length) {
      ElMessage.warning("请至少勾选一列");
      return;
    }
    visibleColumns.value = Object.fromEntries(
      options.map((col) => [col.key, columnDraftKeys.value.includes(col.key)])
    );
    localStorage.setItem(storageKey, JSON.stringify(visibleColumns.value));
    columnDialogVisible.value = false;
    ElMessage.success("列展示设置已保存");
  };

  return {
    columnOptions: options,
    visibleColumns,
    columnDialogVisible,
    columnDraftKeys,
    isColumnVisible,
    loadColumnSettings,
    openColumnDialog,
    resetColumnDraft,
    saveColumnSettings,
  };
}
