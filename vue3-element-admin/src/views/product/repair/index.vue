<template>
  <div class="app-container">
    <el-card shadow="never" class="search-card">
      <div class="search-bar">
        <el-form :inline="true" :model="queryParams" class="search-form">
          <el-form-item label="SN码">
            <el-input
              v-model="queryParams.sn_code"
              placeholder="SN码"
              clearable
              style="width: 160px"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="产品型号">
            <el-input
              v-model="queryParams.product_model"
              placeholder="产品型号"
              clearable
              style="width: 160px"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="BOM名称">
            <el-input
              v-model="queryParams.bom_name"
              placeholder="BOM名称"
              clearable
              style="width: 160px"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="返修时间">
            <el-date-picker
              v-model="queryParams.dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              style="width: 260px"
            />
          </el-form-item>
          <el-form-item label="创建时间">
            <el-date-picker
              v-model="queryParams.createDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              style="width: 260px"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="resetSearch">重置</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <el-card shadow="never" class="data-card">
      <div class="table-toolbar">
        <el-button @click="openColumnDialog">
          <el-icon><Setting /></el-icon> 列展示
        </el-button>
      </div>
      <el-table 
        :data="tableData" 
        border 
        stripe 
        style="width: 100%" 
        v-loading="loading"
        @row-click="handleViewDetail"
        @sort-change="handleSortChange"
        :default-sort="{ prop: 'last_repair_time', order: 'descending' }"
        highlight-current-row
      >
        <el-table-column
          v-if="isColumnVisible('sn_code')"
          prop="sn_code"
          label="SN码"
          min-width="150"
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('product_model')"
          prop="product_model"
          label="产品型号"
          min-width="160"
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('bom_name')"
          prop="bom_name"
          label="BOM名称"
          min-width="180"
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('repair_cnt')"
          prop="repair_cnt"
          label="返修次数"
          width="100"
          align="center"
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('unqualified_labels_1')"
          prop="unqualified_labels_1"
          label="不良项1"
          min-width="140"
          show-overflow-tooltip
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('repair_desc_1')"
          prop="repair_desc_1"
          label="描述1"
          min-width="180"
          show-overflow-tooltip
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('unqualified_labels_2')"
          prop="unqualified_labels_2"
          label="不良项2"
          min-width="140"
          show-overflow-tooltip
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('repair_desc_2')"
          prop="repair_desc_2"
          label="描述2"
          min-width="180"
          show-overflow-tooltip
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('repair_status')"
          prop="repair_status"
          label="返修状态"
          width="110"
          align="center"
          sortable="custom"
        >
          <template #default="{ row }">
            <el-tag :type="Number(row.repair_status) === 1 ? 'success' : 'warning'">
              {{ row.repair_status_name || repairStatusLabels[row.repair_status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('create_time')"
          prop="create_time"
          label="创建时间"
          min-width="170"
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('last_repair_time')"
          prop="last_repair_time"
          label="最后返修时间"
          min-width="170"
          sortable="custom"
        />
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button size="small" @click.stop="handleViewDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="tableData.length === 0 && !loading" description="暂无返修数据" />

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="queryParams.pageNum"
          v-model:page-size="queryParams.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="historyDialogVisible" title="返修历史记录" width="1100px">
      <div v-if="currentRow">
        <p><strong>SN码：</strong>{{ currentRow.sn_code }}</p>
        <p><strong>产品型号：</strong>{{ currentRow.product_model }}</p>
        <p><strong>BOM名称：</strong>{{ currentRow.bom_name }}</p>
        <p><strong>返修次数：</strong>{{ currentRow.repair_cnt }}</p>
      </div>
      <el-table :data="historyData" border stripe style="width: 100%; margin-top: 15px" v-loading="historyLoading">
        <el-table-column prop="repair_cnt" label="第几次返修" width="110" align="center" />
        <el-table-column prop="unqualified_labels" label="不良项" min-width="160" show-overflow-tooltip />
        <el-table-column prop="repair_desc" label="返修描述" min-width="260" show-overflow-tooltip />
        <el-table-column prop="create_time" label="返修时间" min-width="170" />
        <el-table-column label="返修状态" width="180" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.repair_status"
              :active-value="1"
              :inactive-value="0"
              :active-text="repairStatusLabels[1]"
              :inactive-text="repairStatusLabels[0]"
              inline-prompt
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              :loading="statusSavingId === row.id"
              @click="handleSaveRepairStatus(row)"
            >
              保存
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog v-model="columnDialogVisible" title="列展示设置" width="480px" destroy-on-close>
      <div class="column-setting-tip">勾选需要在表格中展示的字段（操作列始终显示）</div>
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Setting } from '@element-plus/icons-vue'
import { listRepairProducts, getProductRepairHistory, deleteRepair, updateRepairStatus } from '@/api/product'
import {
  useFinishProductTableColumns,
  repairColumnOptions,
  REPAIR_COLUMN_STORAGE_KEY,
} from '@/composables/useFinishProductTableColumns'
import { useDictStore } from '@/store'

const dictStore = useDictStore()

const {
  columnOptions,
  columnDialogVisible,
  columnDraftKeys,
  isColumnVisible,
  loadColumnSettings,
  openColumnDialog,
  resetColumnDraft,
  saveColumnSettings,
} = useFinishProductTableColumns(REPAIR_COLUMN_STORAGE_KEY, repairColumnOptions)

const loading = ref(false)
const historyDialogVisible = ref(false)
const historyLoading = ref(false)
const tableData = ref([])
const historyData = ref([])
const currentRow = ref(null)
const total = ref(0)
const statusSavingId = ref(null)

const queryParams = reactive({
  sn_code: '',
  product_model: '',
  bom_name: '',
  dateRange: [],
  createDateRange: [],
  pageNum: 1,
  pageSize: 10,
  sortField: '',
  sortOrder: '',
})

// 返修状态文案：优先取字典管理中的配置，字典缺失时回退默认文案
const repairStatusLabels = computed(() => {
  const labels = { 0: '待返修', 1: '已返修' }
  dictStore.getDictItems('repair_status').forEach(item => {
    labels[Number(item.value)] = item.label
  })
  return labels
})

onMounted(() => {
  loadColumnSettings()
  dictStore.loadDictItems('repair_status')
  getList()
})

async function getList() {
  loading.value = true
  try {
    const [startDate, endDate] = queryParams.dateRange || []
    const [createStartDate, createEndDate] = queryParams.createDateRange || []
    const res = await listRepairProducts({
      sn_code: queryParams.sn_code,
      product_model: queryParams.product_model,
      bom_name: queryParams.bom_name,
      start_date: startDate || '',
      end_date: endDate || '',
      create_start_date: createStartDate || '',
      create_end_date: createEndDate || '',
      page: queryParams.pageNum,
      page_size: queryParams.pageSize,
      sort_field: queryParams.sortField,
      sort_order: queryParams.sortOrder,
    })
    tableData.value = res?.list || []
    total.value = res?.total || 0
  } catch (error) {
    ElMessage.error('加载失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  queryParams.pageNum = 1
  getList()
}

// 服务端排序：排序作用于聚合后的全部数据，避免只排当前页
const handleSortChange = ({ prop, order }) => {
  queryParams.sortField = prop || ''
  queryParams.sortOrder = order === 'ascending' ? 'asc' : order === 'descending' ? 'desc' : ''
  queryParams.pageNum = 1
  getList()
}

const handleSizeChange = () => {
  queryParams.pageNum = 1
  getList()
}

const handleCurrentChange = () => {
  getList()
}

function resetSearch() {
  queryParams.sn_code = ''
  queryParams.product_model = ''
  queryParams.bom_name = ''
  queryParams.dateRange = []
  queryParams.createDateRange = []
  handleSearch()
}

async function handleViewDetail(row) {
  currentRow.value = row
  historyDialogVisible.value = true
  historyLoading.value = true
  try {
    const res = await getProductRepairHistory({ product_id: row.product_id })
    // 记录已保存的状态，取消或保存失败时用于回退滑块
    historyData.value = (res || []).map(item => ({
      ...item,
      _saved_repair_status: item.repair_status,
    }))
  } catch (error) {
    ElMessage.error('加载返修历史失败: ' + error.message)
  } finally {
    historyLoading.value = false
  }
}

async function handleSaveRepairStatus(row) {
  const targetLabel = repairStatusLabels.value[row.repair_status]
  const confirmText = Number(row.repair_status) === 1
    ? `确认将返修状态保存为「${targetLabel}」吗？保存后该 SN 的成品状态将变为「返修品 + 未测试」。`
    : `确认将返修状态保存为「${targetLabel}」吗？`
  try {
    await ElMessageBox.confirm(confirmText, '保存确认', {
      type: 'warning',
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    })
  } catch {
    // 取消保存，回退滑块到已保存的状态
    row.repair_status = row._saved_repair_status
    return
  }

  statusSavingId.value = row.id
  try {
    const res = await updateRepairStatus({
      id: row.id,
      repair_status: row.repair_status,
    })
    row._saved_repair_status = row.repair_status
    row.repair_status_name = repairStatusLabels.value[row.repair_status]
    if (res?.product_updated) {
      ElMessage.success('保存成功，成品状态已更新为「返修品 + 未测试」')
    } else {
      ElMessage.success('保存成功')
    }
    await getList()
  } catch (error) {
    // 保存失败时回退滑块状态
    row.repair_status = row._saved_repair_status
    ElMessage.error('保存失败: ' + error.message)
  } finally {
    statusSavingId.value = null
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除第 ${row.repair_cnt} 次返修记录吗？删除后不可恢复。`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      }
    )
  } catch {
    return
  }
  try {
    await deleteRepair({ id: row.id })
    ElMessage.success('删除成功')
    if (historyData.value) {
      historyData.value = historyData.value.filter(r => r.id !== row.id)
    }
    if (historyData.value.length === 0 && currentRow.value) {
      historyDialogVisible.value = false
    } else if (currentRow.value) {
      currentRow.value.repair_cnt = historyData.value.length
    }
    await getList()
  } catch (error) {
    ElMessage.error('删除失败: ' + error.message)
  }
}
</script>

<style scoped>
.search-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.table-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}
.column-setting-tip {
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
