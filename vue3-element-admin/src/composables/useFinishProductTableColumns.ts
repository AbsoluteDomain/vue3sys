import { ref } from "vue";
import { ElMessage } from "element-plus";

export const FINISH_PRODUCT_COLUMN_STORAGE_KEY = "finish-product-table-columns";
export const FINISH_PRODUCT_BOARD_DETAIL_COLUMN_STORAGE_KEY = "finish-product-board-detail-columns";

export interface FinishProductColumnOption {
  key: string;
  label: string;
  defaultVisible: boolean;
}

export const finishProductColumnOptions: FinishProductColumnOption[] = [
  { key: "sn_code", label: "SN码", defaultVisible: true },
  { key: "bom_type", label: "BOM类型", defaultVisible: true },
  { key: "bom_model", label: "BOM型号", defaultVisible: true },
  { key: "bom_name", label: "BOM名称", defaultVisible: true },
  { key: "material_code", label: "物料编码", defaultVisible: false },
  { key: "status", label: "测试状态", defaultVisible: true },
  { key: "inventory_stock", label: "库存状态", defaultVisible: true },
  { key: "repair", label: "返修", defaultVisible: true },
  { key: "test_time", label: "测试状态修改时间", defaultVisible: false },
  { key: "stock_in_time", label: "入库时间", defaultVisible: false },
  { key: "stock_out_time", label: "出库时间", defaultVisible: false },
  { key: "create_time", label: "创建时间", defaultVisible: false },
  { key: "update_time", label: "更新时间", defaultVisible: true },
  { key: "description", label: "描述", defaultVisible: false },
];

const getDefaultVisibleColumns = () =>
  Object.fromEntries(finishProductColumnOptions.map((col) => [col.key, col.defaultVisible]));

const getDefaultVisibleColumnKeys = () =>
  finishProductColumnOptions.filter((col) => col.defaultVisible).map((col) => col.key);

export function useFinishProductTableColumns(
  storageKey: string = FINISH_PRODUCT_COLUMN_STORAGE_KEY
) {
  const visibleColumns = ref<Record<string, boolean>>(getDefaultVisibleColumns());
  const columnDialogVisible = ref(false);
  const columnDraftKeys = ref<string[]>([]);

  const loadColumnSettings = () => {
    const saved = localStorage.getItem(storageKey);
    if (!saved) {
      visibleColumns.value = getDefaultVisibleColumns();
      return;
    }
    try {
      const parsed = JSON.parse(saved) as Record<string, boolean>;
      visibleColumns.value = Object.fromEntries(
        finishProductColumnOptions.map((col) => [col.key, parsed[col.key] ?? col.defaultVisible])
      );
    } catch {
      visibleColumns.value = getDefaultVisibleColumns();
    }
  };

  const isColumnVisible = (key: string) => visibleColumns.value[key] !== false;

  const openColumnDialog = () => {
    columnDraftKeys.value = finishProductColumnOptions
      .filter((col) => isColumnVisible(col.key))
      .map((col) => col.key);
    columnDialogVisible.value = true;
  };

  const resetColumnDraft = () => {
    columnDraftKeys.value = getDefaultVisibleColumnKeys();
  };

  const saveColumnSettings = () => {
    if (!columnDraftKeys.value.length) {
      ElMessage.warning("请至少勾选一列");
      return;
    }
    visibleColumns.value = Object.fromEntries(
      finishProductColumnOptions.map((col) => [col.key, columnDraftKeys.value.includes(col.key)])
    );
    localStorage.setItem(storageKey, JSON.stringify(visibleColumns.value));
    columnDialogVisible.value = false;
    ElMessage.success("列展示设置已保存");
  };

  return {
    columnOptions: finishProductColumnOptions,
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
