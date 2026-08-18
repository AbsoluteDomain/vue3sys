import { ref } from "vue";
import { ElMessage } from "element-plus";

export const PRODUCT_COLUMN_STORAGE_KEY = "product-table-columns";

export interface ProductColumnOption {
  key: string;
  label: string;
  defaultVisible: boolean;
}

export const productColumnOptions: ProductColumnOption[] = [
  { key: "id", label: "ID", defaultVisible: false },
  { key: "name", label: "零件名称", defaultVisible: true },
  { key: "draw_code", label: "图号", defaultVisible: true },
  { key: "material_code", label: "物料编码", defaultVisible: true },
  { key: "type", label: "类型", defaultVisible: true },
  { key: "quantity", label: "数量", defaultVisible: true },
  { key: "alert_quantity", label: "报警数量", defaultVisible: true },
  { key: "procurement_cycle", label: "采购周期(天)", defaultVisible: true },
  { key: "updated_at", label: "更新时间", defaultVisible: true },
];

const getDefaultVisibleColumns = () =>
  Object.fromEntries(productColumnOptions.map((col) => [col.key, col.defaultVisible]));

const getDefaultVisibleColumnKeys = () =>
  productColumnOptions.filter((col) => col.defaultVisible).map((col) => col.key);

export function useProductTableColumns(
  storageKey: string = PRODUCT_COLUMN_STORAGE_KEY
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
        productColumnOptions.map((col) => [col.key, parsed[col.key] ?? col.defaultVisible])
      );
    } catch {
      visibleColumns.value = getDefaultVisibleColumns();
    }
  };

  const isColumnVisible = (key: string) => visibleColumns.value[key] !== false;

  const openColumnDialog = () => {
    columnDraftKeys.value = productColumnOptions
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
      productColumnOptions.map((col) => [col.key, columnDraftKeys.value.includes(col.key)])
    );
    localStorage.setItem(storageKey, JSON.stringify(visibleColumns.value));
    columnDialogVisible.value = false;
    ElMessage.success("列展示设置已保存");
  };

  return {
    columnOptions: productColumnOptions,
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
