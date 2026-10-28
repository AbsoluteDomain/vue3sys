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
          <el-form-item label="测试状态">
            <el-select
              v-model="queryParams.test_status"
              placeholder="全部"
              clearable
              style="width: 140px"
            >
              <el-option label="测试合格" :value="2" />
              <el-option label="测试不良" :value="3" />
            </el-select>
          </el-form-item>
          <el-form-item label="测试时间">
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
        :default-sort="{ prop: 'last_test_time', order: 'descending' }"
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
          v-if="isColumnVisible('test_cnt')"
          prop="test_cnt"
          label="测试次数"
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
          v-if="isColumnVisible('test_desc_1')"
          prop="test_desc_1"
          label="描述1"
          min-width="170"
          show-overflow-tooltip
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('test_status_1')"
          prop="test_status_1"
          label="测试状态1"
          width="120"
          align="center"
          sortable="custom"
        >
          <template #default="{ row }">
            <el-tag
              v-if="row.test_status_1"
              :type="Number(row.test_status_1) === 2 ? 'success' : 'danger'"
            >
              {{ row.test_status_name_1 || testStatusLabels[row.test_status_1] }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('unqualified_labels_2')"
          prop="unqualified_labels_2"
          label="不良项2"
          min-width="140"
          show-overflow-tooltip
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('test_desc_2')"
          prop="test_desc_2"
          label="描述2"
          min-width="170"
          show-overflow-tooltip
          sortable="custom"
        />
        <el-table-column
          v-if="isColumnVisible('test_status_2')"
          prop="test_status_2"
          label="测试状态2"
          width="120"
          align="center"
          sortable="custom"
        >
          <template #default="{ row }">
            <el-tag
              v-if="row.test_status_2"
              :type="Number(row.test_status_2) === 2 ? 'success' : 'danger'"
            >
              {{ row.test_status_name_2 || testStatusLabels[row.test_status_2] }}
            </el-tag>
            <span v-else>-</span>
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
          v-if="isColumnVisible('last_test_time')"
          prop="last_test_time"
          label="最后测试时间"
          min-width="170"
          sortable="custom"
        />
      </el-table>

      <el-empty v-if="tableData.length === 0 && !loading" description="暂无测试记录" />

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

    <el-dialog v-model="historyDialogVisible" title="测试历史记录" width="1000px">
      <div v-if="currentRow">
        <p><strong>SN码：</strong>{{ currentRow.sn_code }}</p>
        <p><strong>产品型号：</strong>{{ currentRow.product_model }}</p>
        <p><strong>BOM名称：</strong>{{ currentRow.bom_name }}</p>
        <p><strong>测试次数：</strong>{{ currentRow.test_cnt }}</p>
      </div>
      <el-table
        :data="historyData"
        border
        stripe
        style="width: 100%; margin-top: 15px"
        v-loading="historyLoading"
      >
        <el-table-column prop="test_cnt" label="第几次测试" width="110" align="center" />
        <el-table-column prop="unqualified_labels" label="不良项" min-width="160" show-overflow-tooltip />
        <el-table-column prop="test_desc" label="描述" min-width="260" show-overflow-tooltip />
        <el-table-column label="测试状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="Number(row.test_status) === 2 ? 'success' : 'danger'">
              {{ row.test_status_name || testStatusLabels[row.test_status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="测试时间" min-width="170" />
      </el-table>
    </el-dialog>

    <el-dialog v-model="columnDialogVisible" title="列展示设置" width="520px" destroy-on-close>
      <div class="column-setting-tip">勾选需要在表格中展示的字段</div>
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting } from '@element-plus/icons-vue'
import { listTestRecords, getTestRecordHistory } from '@/api/product'
import {
  useFinishProductTableColumns,
  testRecordColumnOptions,
  TEST_RECORD_COLUMN_STORAGE_KEY,
} from '@/composables/useFinishProductTableColumns'

const {
  columnOptions,
  columnDialogVisible,
  columnDraftKeys,
  isColumnVisible,
  loadColumnSettings,
  openColumnDialog,
  resetColumnDraft,
  saveColumnSettings,
} = useFinishProductTableColumns(TEST_RECORD_COLUMN_STORAGE_KEY, testRecordColumnOptions)

const testStatusLabels = { 2: '测试合格', 3: '测试不良' }

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const historyDialogVisible = ref(false)
const historyLoading = ref(false)
const historyData = ref([])
const currentRow = ref(null)

const queryParams = reactive({
  sn_code: '',
  product_model: '',
  bom_name: '',
  test_status: '',
  dateRange: [],
  pageNum: 1,
  pageSize: 10,
  sortField: '',
  sortOrder: '',
})

onMounted(() => {
  loadColumnSettings()
  getList()
})

async function getList() {
  loading.value = true
  try {
    const [startDate, endDate] = queryParams.dateRange || []
    const res = await listTestRecords({
      sn_code: queryParams.sn_code,
      product_model: queryParams.product_model,
      bom_name: queryParams.bom_name,
      test_status: queryParams.test_status,
      start_date: startDate || '',
      end_date: endDate || '',
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
  queryParams.test_status = ''
  queryParams.dateRange = []
  handleSearch()
}

async function handleViewDetail(row) {
  currentRow.value = row
  historyDialogVisible.value = true
  historyLoading.value = true
  try {
    const res = await getTestRecordHistory({
      product_id: row.product_id,
      sn_code: row.sn_code || '',
    })
    historyData.value = res || []
  } catch (error) {
    ElMessage.error('加载测试历史失败: ' + error.message)
  } finally {
    historyLoading.value = false
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
