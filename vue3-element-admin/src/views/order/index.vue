<template>
  <div class="app-container">
    <!-- 搜索区域 -->
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="queryParams" class="search-form">
        <el-form-item label="关键字">
          <el-input
            v-model="queryParams.keyword"
            placeholder="订单号/合同号/客户/商品/型号/物料"
            clearable
            style="width: 280px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="订单号">
          <el-input
            v-model="queryParams.order_no"
            placeholder="订单流水号"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="合同编号">
          <el-input
            v-model="queryParams.contract_no"
            placeholder="合同编号"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input
            v-model="queryParams.customer_name"
            placeholder="客户名称"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="商品名称">
          <el-input
            v-model="queryParams.product_name"
            placeholder="商品名称"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="天链型号">
          <el-input
            v-model="queryParams.product_model"
            placeholder="天链型号"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="订单日期">
          <el-date-picker
            v-model="queryParams.orderDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 260px"
            @change="handleSearch"
            @clear="handleSearch"
          />
        </el-form-item>
        <el-form-item label="交付日期">
          <el-date-picker
            v-model="queryParams.deliveryDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 260px"
            @change="handleSearch"
            @clear="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="resetQuery">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格区域 -->
    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <div class="toolbar-info">
          <span class="toolbar-title">{{ isExternalData ? externalDataTitle : '订单列表' }}</span>
          <el-tag v-if="isExternalData" type="warning" size="small">外部数据</el-tag>
          <span class="toolbar-total">共 {{ total }} 条</span>
        </div>
        <div class="toolbar-actions">
          <el-button v-if="isExternalData" type="info" @click="handleBackToDbList">
            <el-icon><Back /></el-icon> 返回数据库列表
          </el-button>
          <el-button type="success" :loading="healthLoading" @click="handleHealthCheck">
            <el-icon><CircleCheck /></el-icon> 健康检查
          </el-button>
          <el-button type="primary" @click="openSyncAllDialog">
            <el-icon><Download /></el-icon> 全量查询
          </el-button>
          <el-button type="primary" :loading="loading" @click="handleSyncToday">
            <el-icon><Calendar /></el-icon> 查询当天
          </el-button>
          <el-button type="warning" @click="openSyncSinceDialog">
            <el-icon><RefreshRight /></el-icon> 增量查询
          </el-button>
          <el-button type="info" @click="openOrderByNoDialog">
            <el-icon><Search /></el-icon> 按订单号查询
          </el-button>
          <el-button @click="openColumnDialog">
            <el-icon><Setting /></el-icon> 列展示
          </el-button>
        </div>
      </div>

      <el-table
        :data="tableData"
        border
        stripe
        style="width: 100%"
        height="600"
        v-loading="loading"
        element-loading-text="正在请求外部接口，请稍候..."
        @sort-change="handleSortChange"
      >
        <el-table-column type="index" label="序号" width="60" align="center" fixed="left" />

        <el-table-column
          v-if="isColumnVisible('order_no')"
          prop="order_no"
          label="订单流水号"
          min-width="160"
          sortable="custom"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('contract_no')"
          prop="contract_no"
          label="合同编号"
          min-width="140"
          sortable="custom"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('customer_name')"
          prop="customer_name"
          label="客户名称"
          min-width="160"
          sortable="custom"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('customer_no')"
          prop="customer_no"
          label="客户编号"
          width="100"
          align="center"
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('material_no')"
          prop="material_no"
          label="物料编号"
          min-width="140"
          sortable="custom"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('product_name')"
          prop="product_name"
          label="商品名称"
          min-width="160"
          sortable="custom"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('product_model')"
          prop="product_model"
          label="天链型号"
          min-width="140"
          sortable="custom"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('product_category')"
          prop="product_category"
          label="商品类别"
          min-width="120"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('quantity')"
          prop="quantity"
          label="订单数量"
          width="110"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            <span>{{ formatNumber(row.quantity) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('unit_price')"
          prop="unit_price"
          label="单价"
          width="110"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            <span>{{ formatNumber(row.unit_price) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('amount')"
          prop="amount"
          label="金额"
          width="120"
          align="right"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('tax_unit_price')"
          prop="tax_unit_price"
          label="含税单价"
          width="110"
          align="right"
          sortable="custom"
        >
          <template #default="{ row }">
            <span>{{ formatNumber(row.tax_unit_price) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('tax_amount')"
          prop="tax_amount"
          label="含税金额"
          width="120"
          align="right"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('order_date')"
          prop="order_date"
          label="订单日期"
          width="170"
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('delivery_date')"
          prop="delivery_date"
          label="交付日期"
          width="170"
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('create_at')"
          prop="create_at"
          label="创建日期"
          width="170"
          sortable="custom"
        />
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-if="!isExternalData"
          v-model:current-page="queryParams.pageNum"
          v-model:page-size="queryParams.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
        <el-pagination
          v-else
          v-model:current-page="externalPageNum"
          v-model:page-size="externalPageSize"
          :page-sizes="[10, 20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleExternalSizeChange"
          @current-change="handleExternalCurrentChange"
        />
      </div>
    </el-card>

    <!-- 列展示设置对话框 -->
    <el-dialog v-model="columnDialogVisible" title="列展示设置" width="480px" destroy-on-close>
      <div class="column-setting-tip">勾选需要在表格中展示的字段（序号列始终显示）</div>
      <el-checkbox-group v-model="columnDraftKeys" class="column-checkbox-group">
        <el-checkbox v-for="col in columnOptions" :key="col.key" :label="col.key">
          {{ col.label }}
        </el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="resetColumnDraft">恢复默认</el-button>
        <el-button @click="columnDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveColumnSettings">确定</el-button>
      </template>
    </el-dialog>

    <!-- 全量查询对话框 -->
    <el-dialog v-model="syncAllDialogVisible" title="全量查询" width="480px" destroy-on-close>
      <div class="dialog-tip">选择时间段（可选，不选则查询全部）：</div>
      <el-date-picker
        v-model="syncAllDateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="width: 100%"
      />
      <template #footer>
        <el-button @click="syncAllDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleSyncAll">查询</el-button>
      </template>
    </el-dialog>

    <!-- 增量查询对话框 -->
    <el-dialog v-model="syncSinceDialogVisible" title="增量查询" width="420px" destroy-on-close>
      <div class="dialog-tip">选择日期，查询该日期之后的订单：</div>
      <el-date-picker
        v-model="syncSinceDate"
        type="date"
        placeholder="请选择日期"
        value-format="YYYY-MM-DD"
        style="width: 100%"
      />
      <template #footer>
        <el-button @click="syncSinceDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleSyncSince">查询</el-button>
      </template>
    </el-dialog>

    <!-- 按订单号查询对话框 -->
    <el-dialog v-model="orderByNoDialogVisible" title="按订单号查询" width="420px" destroy-on-close>
      <div class="dialog-tip">输入订单号进行精确查询：</div>
      <el-input
        v-model="orderByNoInput"
        placeholder="请输入订单号，如 SO20260801001"
        clearable
        @keyup.enter="handleOrderByNo"
      />
      <template #footer>
        <el-button @click="orderByNoDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleOrderByNo">查询</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import {
  Search, Refresh, Setting, Back, CircleCheck,
  Download, Calendar, RefreshRight
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getOrderList, orderHealthCheck, orderSyncAll,
  orderSyncToday, orderSyncSince, orderByNo
} from '@/api/order'
import { useOrderTableColumns } from '@/composables/useOrderTableColumns'

const {
  columnOptions,
  columnDialogVisible,
  columnDraftKeys,
  isColumnVisible,
  loadColumnSettings,
  openColumnDialog,
  resetColumnDraft,
  saveColumnSettings,
} = useOrderTableColumns()

const queryParams = reactive({
  pageNum: 1,
  pageSize: 20,
  keyword: '',
  order_no: '',
  contract_no: '',
  customer_name: '',
  product_name: '',
  product_model: '',
  material_no: '',
  orderDateRange: null,
  deliveryDateRange: null,
  sortProp: '',
  sortOrder: ''
})

// 数据库查询数据
const dbTableData = ref([])
// 外部接口全部数据（用于前端分页）
const allExternalData = ref([])
const total = ref(0)
const loading = ref(false)
const healthLoading = ref(false)

// 外部数据状态
const isExternalData = ref(false)
const externalDataTitle = ref('')
const externalPageNum = ref(1)
const externalPageSize = ref(20)

// 表格数据：数据库模式直接显示，外部数据模式前端分页切片
const tableData = computed(() => {
  if (isExternalData.value) {
    const start = (externalPageNum.value - 1) * externalPageSize.value
    return allExternalData.value.slice(start, start + externalPageSize.value)
  }
  return dbTableData.value
})

// 对话框状态
const syncAllDialogVisible = ref(false)
const syncAllDateRange = ref(null)
const syncSinceDialogVisible = ref(false)
const syncSinceDate = ref(null)
const orderByNoDialogVisible = ref(false)
const orderByNoInput = ref('')

const appendDateRangeParams = (params, range, startKey, endKey) => {
  if (range?.[0] && range?.[1]) {
    params[startKey] = range[0]
    params[endKey] = range[1]
  }
}

const buildListParams = () => {
  const params = {
    pageNum: queryParams.pageNum,
    pageSize: queryParams.pageSize,
    keyword: queryParams.keyword,
    order_no: queryParams.order_no,
    contract_no: queryParams.contract_no,
    customer_name: queryParams.customer_name,
    product_name: queryParams.product_name,
    product_model: queryParams.product_model,
    material_no: queryParams.material_no,
    sortProp: queryParams.sortProp,
    sortOrder: queryParams.sortOrder
  }
  appendDateRangeParams(params, queryParams.orderDateRange, 'order_start_date', 'order_end_date')
  appendDateRangeParams(params, queryParams.deliveryDateRange, 'delivery_start_date', 'delivery_end_date')
  return params
}

const getList = () => {
  loading.value = true
  const params = buildListParams()
  getOrderList(params)
    .then((response) => {
      dbTableData.value = response?.list || []
      total.value = response?.total || 0
    })
    .catch(() => {
      ElMessage.error('获取订单列表失败')
    })
    .finally(() => {
      loading.value = false
    })
}

const handleSearch = () => {
  if (isExternalData.value) {
    handleBackToDbList()
    return
  }
  queryParams.pageNum = 1
  getList()
}

const resetQuery = () => {
  queryParams.keyword = ''
  queryParams.order_no = ''
  queryParams.contract_no = ''
  queryParams.customer_name = ''
  queryParams.product_name = ''
  queryParams.product_model = ''
  queryParams.material_no = ''
  queryParams.orderDateRange = null
  queryParams.deliveryDateRange = null
  queryParams.sortProp = ''
  queryParams.sortOrder = ''
  queryParams.pageNum = 1
  if (isExternalData.value) {
    handleBackToDbList()
    return
  }
  getList()
}

const handleSizeChange = () => {
  queryParams.pageNum = 1
  getList()
}

const handleCurrentChange = () => {
  getList()
}

// 外部数据前端分页事件
const handleExternalSizeChange = () => {
  externalPageNum.value = 1
}
const handleExternalCurrentChange = () => {
  // tableData 为 computed，分页参数变化时自动更新
}

const handleSortChange = ({ prop, order }) => {
  if (isExternalData.value) return
  queryParams.sortProp = prop || ''
  queryParams.sortOrder = order === 'ascending' ? 'ascending' : order === 'descending' ? 'descending' : ''
  getList()
}

const formatNumber = (value) => {
  if (value === null || value === undefined || value === '') return '—'
  const num = Number(value)
  if (isNaN(num)) return value
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ==================== 外部接口操作 ====================

// 将外部数据显示到表格（全部数据存入 allExternalData，由 computed 自动分页）
const displayExternalData = (data, title) => {
  allExternalData.value = data?.list || []
  total.value = allExternalData.value.length
  externalPageNum.value = 1
  isExternalData.value = true
  externalDataTitle.value = title
}

// 健康检查
const handleHealthCheck = () => {
  healthLoading.value = true
  orderHealthCheck()
    .then((data) => {
      const content = typeof data === 'object'
        ? JSON.stringify(data, null, 2)
        : String(data)
      ElMessageBox.alert(
        `<pre style="max-height:400px;overflow:auto;text-align:left;background:#f5f7fa;padding:12px;border-radius:4px;font-size:13px;">${content}</pre>`,
        '健康检查结果',
        { confirmButtonText: '确定', type: 'success', dangerouslyUseHTMLString: true }
      )
    })
    .catch((err) => {
      ElMessage.error(err?.message || '健康检查失败，请检查外部接口是否可用')
    })
    .finally(() => {
      healthLoading.value = false
    })
}

// 全量查询
const openSyncAllDialog = () => {
  syncAllDateRange.value = null
  syncAllDialogVisible.value = true
}

const handleSyncAll = () => {
  const params = {}
  if (syncAllDateRange.value?.[0] && syncAllDateRange.value?.[1]) {
    params.start_date = syncAllDateRange.value[0]
    params.end_date = syncAllDateRange.value[1]
  }
  syncAllDialogVisible.value = false
  loading.value = true
  orderSyncAll(params)
    .then((data) => {
      displayExternalData(data, '全量查询结果')
      ElMessage.success(`查询成功，共 ${total.value} 条数据`)
    })
    .catch((err) => {
      ElMessage.error(err?.message || '全量查询失败')
    })
    .finally(() => {
      loading.value = false
    })
}

// 查询当天
const handleSyncToday = () => {
  loading.value = true
  orderSyncToday()
    .then((data) => {
      displayExternalData(data, '当天订单')
      ElMessage.success(`查询成功，共 ${total.value} 条数据`)
    })
    .catch((err) => {
      ElMessage.error(err?.message || '查询当天失败')
    })
    .finally(() => {
      loading.value = false
    })
}

// 增量查询
const openSyncSinceDialog = () => {
  syncSinceDate.value = null
  syncSinceDialogVisible.value = true
}

const handleSyncSince = () => {
  if (!syncSinceDate.value) {
    ElMessage.warning('请选择日期')
    return
  }
  syncSinceDialogVisible.value = false
  loading.value = true
  orderSyncSince(syncSinceDate.value)
    .then((data) => {
      displayExternalData(data, `增量查询（自 ${syncSinceDate.value}）`)
      ElMessage.success(`查询成功，共 ${total.value} 条数据`)
    })
    .catch((err) => {
      ElMessage.error(err?.message || '增量查询失败')
    })
    .finally(() => {
      loading.value = false
    })
}

// 按订单号查询
const openOrderByNoDialog = () => {
  orderByNoInput.value = ''
  orderByNoDialogVisible.value = true
}

const handleOrderByNo = () => {
  const orderNo = orderByNoInput.value?.trim()
  if (!orderNo) {
    ElMessage.warning('请输入订单号')
    return
  }
  orderByNoDialogVisible.value = false
  loading.value = true
  orderByNo(orderNo)
    .then((data) => {
      displayExternalData(data, `订单号查询：${orderNo}`)
      if (total.value > 0) {
        ElMessage.success(`查询成功，共 ${total.value} 条数据`)
      } else {
        ElMessage.warning('未找到该订单号的记录')
      }
    })
    .catch((err) => {
      ElMessage.error(err?.message || '按订单号查询失败')
    })
    .finally(() => {
      loading.value = false
    })
}

// 返回数据库列表
const handleBackToDbList = () => {
  isExternalData.value = false
  externalDataTitle.value = ''
  allExternalData.value = []
  total.value = 0
  queryParams.pageNum = 1
  getList()
}

onMounted(() => {
  loadColumnSettings()
  getList()
})
</script>

<style scoped>
.app-container {
  padding: 20px;
}
.search-card {
  margin-bottom: 20px;
}
.search-form {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}
.table-card {
  margin-bottom: 20px;
}
.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}
.toolbar-info {
  display: flex;
  align-items: center;
  gap: 12px;
}
.toolbar-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.toolbar-total {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.column-setting-tip,
.dialog-tip {
  margin-bottom: 12px;
  color: #909399;
  font-size: 13px;
}
.column-checkbox-group {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px 12px;
}
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
