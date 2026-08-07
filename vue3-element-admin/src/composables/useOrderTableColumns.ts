import { ref } from "vue";
import { ElMessage } from "element-plus";

export const ORDER_COLUMN_STORAGE_KEY = "order-table-columns";

export interface OrderColumnOption {
  key: string;
  label: string;
  defaultVisible: boolean;
}

export const orderColumnOptions: OrderColumnOption[] = [
  { key: "order_no", label: "订单流水号", defaultVisible: true },
  { key: "contract_no", label: "合同编号", defaultVisible: true },
  { key: "customer_name", label: "客户名称", defaultVisible: true },
  { key: "customer_no", label: "客户编号", defaultVisible: false },
  { key: "material_no", label: "物料编号", defaultVisible: true },
  { key: "product_name", label: "商品名称", defaultVisible: true },
  { key: "product_model", label: "天链型号", defaultVisible: true },
  { key: "product_category", label: "商品类别", defaultVisible: false },
  { key: "quantity", label: "订单数量", defaultVisible: true },
  { key: "unit_price", label: "单价", defaultVisible: true },
  { key: "amount", label: "金额", defaultVisible: true },
  { key: "tax_unit_price", label: "含税单价", defaultVisible: false },
  { key: "tax_amount", label: "含税金额", defaultVisible: false },
  { key: "order_date", label: "订单日期", defaultVisible: true },
  { key: "delivery_date", label: "交付日期", defaultVisible: true },
  { key: "create_at", label: "创建日期", defaultVisible: false },
];

const getDefaultVisibleColumns = () =>
  Object.fromEntries(orderColumnOptions.map((col) => [col.key, col.defaultVisible]));

const getDefaultVisibleColumnKeys = () =>
  orderColumnOptions.filter((col) => col.defaultVisible).map((col) => col.key);

export function useOrderTableColumns(
  storageKey: string = ORDER_COLUMN_STORAGE_KEY
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
        orderColumnOptions.map((col) => [col.key, parsed[col.key] ?? col.defaultVisible])
      );
    } catch {
      visibleColumns.value = getDefaultVisibleColumns();
    }
  };

  const isColumnVisible = (key: string) => visibleColumns.value[key] !== false;

  const openColumnDialog = () => {
    columnDraftKeys.value = orderColumnOptions
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
      orderColumnOptions.map((col) => [col.key, columnDraftKeys.value.includes(col.key)])
    );
    localStorage.setItem(storageKey, JSON.stringify(visibleColumns.value));
    columnDialogVisible.value = false;
    ElMessage.success("列展示设置已保存");
  };

  return {
    columnOptions: orderColumnOptions,
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
