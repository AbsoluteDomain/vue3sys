<template>
  <div class="app-container">
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="queryParams" class="search-form">
        <el-form-item label="SN码">
          <el-input
            v-model="queryParams.sn_code"
            placeholder="SN码"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select
            v-model="queryParams.operation_type"
            placeholder="全部"
            clearable
            style="width: 130px"
            @change="handleSearch"
            @clear="handleSearch"
          >
            <el-option label="新增" value="create" />
            <el-option label="修改" value="update" />
            <el-option label="回退" value="rollback" />
            <el-option label="绑定关节" value="bind_joint" />
            <el-option label="库存变更" value="stock_change" />
            <el-option label="不良详情" value="unqualified" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作人">
          <el-input
            v-model="queryParams.operator_name"
            placeholder="操作人"
            clearable
            style="width: 130px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
            @change="handleDateChange"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="resetQuery">
            <el-icon><Refresh /></el-icon> 重置
          </el-button          >
          <el-button @click="beforeDialogVisible = true">
            <el-icon><Back /></el-icon> 变更前
          </el-button          >
          <el-button @click="afterDialogVisible = true">
            <el-icon><Right /></el-icon> 变更后
          </el-button          >
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table
        :data="tableData"
        border
        stripe
        style="width: 100%"
        v-loading="loading"
      >
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="createTime" label="操作时间" width="170" />
        <el-table-column prop="snCode" label="SN码" width="150" show-overflow-tooltip />
        <el-table-column label="操作类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="operationTagType(row.operationType)" effect="light">
              {{ row.operationTypeName }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operatorName" label="操作人" width="120" />
        <el-table-column label="变更详情" min-width="300">
          <template #default="{ row }">
            <div v-for="c in changeDetails(row)" :key="c.field" class="change-line">
              <span class="change-label">{{ c.label }}：</span>
              <span class="change-before">{{ c.before }}</span>
              <span class="change-arrow">→</span>
              <span class="change-after">{{ c.after }}</span>
            </div>
            <span v-if="!(row.changedFields || []).length" class="no-change">—</span>
          </template>
        </el-table-column>
        <el-table-column
          v-if="selectedBeforeField"
          :label="'变更前(' + fieldLabel(selectedBeforeField) + (selectedBeforeValue !== '' ? '：' + beforeValueText : '') + ')'"
          width="180"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            {{ formatFieldValue(row.beforeData, selectedBeforeField) }}
          </template>
        </el-table-column>
        <el-table-column
          v-if="selectedAfterField"
          :label="'变更后(' + fieldLabel(selectedAfterField) + (selectedAfterValue !== '' ? '：' + afterValueText : '') + ')'"
          width="180"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            {{ formatFieldValue(row.afterData, selectedAfterField) }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="操作描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP地址" width="140" />
      </el-table>
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

    <!-- 变更前筛选弹窗：选字段 → 选/输字段值 -->
    <el-dialog v-model="beforeDialogVisible" title="筛选变更前数据" width="440px">
      <el-form label-width="80px">
        <el-form-item label="筛选字段">
          <el-select
            v-model="selectedBeforeField"
            placeholder="请选择字段"
            clearable
            filterable
            style="width: 100%"
            @change="selectedBeforeValue = ''"
          >
            <el-option
              v-for="col in fieldOptions"
              :key="col.key"
              :label="col.label"
              :value="col.key"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="selectedBeforeField" label="字段值">
          <el-select
            v-if="valueSelectOptions(selectedBeforeField)"
            v-model="selectedBeforeValue"
            placeholder="请选择值"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="opt in valueSelectOptions(selectedBeforeField)"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <el-input
            v-else
            v-model="selectedBeforeValue"
            placeholder="输入关键字模糊查询"
            clearable
            @keyup.enter="applyBeforeFilter"
          />
        </el-form-item>
        <div v-if="selectedBeforeField" class="filter-tip">
          只显示「{{ fieldLabel(selectedBeforeField) }}」发生变更、且变更前{{ valueHint(selectedBeforeField) }}{{ selectedBeforeValue !== '' ? '为 ' + beforeValueText : '' }}的记录
        </div>
      </el-form>
      <template #footer>
        <el-button @click="clearBeforeFilter">清空条件</el-button>
        <el-button @click="beforeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyBeforeFilter">确定</el-button>
      </template>
    </el-dialog>

    <!-- 变更后筛选弹窗：选字段 → 选/输字段值 -->
    <el-dialog v-model="afterDialogVisible" title="筛选变更后数据" width="440px">
      <el-form label-width="80px">
        <el-form-item label="筛选字段">
          <el-select
            v-model="selectedAfterField"
            placeholder="请选择字段"
            clearable
            filterable
            style="width: 100%"
            @change="selectedAfterValue = ''"
          >
            <el-option
              v-for="col in fieldOptions"
              :key="col.key"
              :label="col.label"
              :value="col.key"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="selectedAfterField" label="字段值">
          <el-select
            v-if="valueSelectOptions(selectedAfterField)"
            v-model="selectedAfterValue"
            placeholder="请选择值"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="opt in valueSelectOptions(selectedAfterField)"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <el-input
            v-else
            v-model="selectedAfterValue"
            placeholder="输入关键字模糊查询"
            clearable
            @keyup.enter="applyAfterFilter"
          />
        </el-form-item>
        <div v-if="selectedAfterField" class="filter-tip">
          只显示「{{ fieldLabel(selectedAfterField) }}」发生变更、且变更后{{ valueHint(selectedAfterField) }}{{ selectedAfterValue !== '' ? '为 ' + afterValueText : '' }}的记录
        </div>
      </el-form>
      <template #footer>
        <el-button @click="clearAfterFilter">清空条件</el-button>
        <el-button @click="afterDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyAfterFilter">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { getFinishedProductLogList } from '@/api/finish-product'
import { finishProductColumnOptions } from '@/composables/useFinishProductTableColumns'
import { Search, Refresh, Back, Right } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useDictStore } from '@/store'

defineOptions({
  name: 'FinishProductLog'
})

const dictStore = useDictStore()

const fieldOptions = finishProductColumnOptions

const fieldLabelMap = {}
fieldOptions.forEach(col => {
  fieldLabelMap[col.key] = col.label
})

const fieldLabel = (key) => fieldLabelMap[key] || key

// 不良项字段（变更详情中展示为标签列表）
fieldLabelMap['unqualified_items'] = '不良详情'

const queryParams = reactive({
  pageNum: 1,
  pageSize: 20,
  sn_code: '',
  operation_type: '',
  operator_name: '',
  changed_field: '',
  start_date: '',
  end_date: ''
})

const dateRange = ref([])
const tableData = ref([])
const loading = ref(false)
const total = ref(0)

const selectedBeforeField = ref('')
const selectedBeforeValue = ref('')
const selectedAfterField = ref('')
const selectedAfterValue = ref('')
const beforeDialogVisible = ref(false)
const afterDialogVisible = ref(false)

// 本地兜底映射表（筛选弹窗下拉选项 + formatFieldValue fallback）
// 优先使用后端序列化返回的 *_name 字段，此表仅作为兜底
const STATUS_MAP = { 0: '未测试', 1: '测试中', 2: '测试合格', 3: '测试不良', 4: '未组装' }
const REPAIR_MAP = { 0: '新品', 1: '返修品' }
const BOM_TYPE_MAP = { 0: '关节', 1: '机械臂' }

// 库存状态以字典 storage_status 为准
const stockStatusOptions = computed(() =>
  dictStore.getDictItems('storage_status').map(item => ({
    label: item.label,
    value: Number(item.value)
  }))
)
const getStockStatusLabel = (value) => {
  const item = dictStore
    .getDictItems('storage_status')
    .find(i => String(i.value) === String(value))
  return item ? item.label : value
}

const ENUM_FIELDS = new Set(['status', 'inventory_stock', 'repair', 'bom_type'])

// 枚举字段 → 下拉选项（值为数字）；其余字段为文本输入模糊查询
const ENUM_OPTION_MAPS = {
  status: STATUS_MAP,
  repair: REPAIR_MAP,
  bom_type: BOM_TYPE_MAP
}

const valueSelectOptions = (field) => {
  if (field === 'inventory_stock') return stockStatusOptions.value
  const m = ENUM_OPTION_MAPS[field]
  return m ? Object.keys(m).map(k => ({ label: m[k], value: Number(k) })) : null
}

const valueHint = (field) => (ENUM_FIELDS.has(field) ? '值' : '包含关键字')

// 弹窗提示文案中显示的值（枚举转中文）
const matchValueText = (field, value) => {
  if (field === 'inventory_stock') return getStockStatusLabel(value)
  const m = ENUM_OPTION_MAPS[field]
  if (m && m[String(value)] !== undefined) return m[String(value)]
  return value
}
const beforeValueText = computed(() => matchValueText(selectedBeforeField.value, selectedBeforeValue.value))
const afterValueText = computed(() => matchValueText(selectedAfterField.value, selectedAfterValue.value))

const formatFieldValue = (data, field) => {
  if (!data || data[field] === undefined || data[field] === null || data[field] === '') return '-'
  const val = data[field]
  // 不良项列表：拼接标签
  if (field === 'unqualified_items') {
    return Array.isArray(val) && val.length ? val.map(i => i.label).join('、') : '-'
  }
  // 优先使用后端序列化返回的 *_name 字段（status_name / inventory_stock_name / bom_type_name 等）
  // 这样后端新增任何枚举值/字典项，日志自动正确显示文本，前端无需同步
  const nameField = field + '_name'
  if (data[nameField] !== undefined && data[nameField] !== null && data[nameField] !== '') {
    return data[nameField]
  }
  // 回退：本地映射表兜底
  if (field === 'status') return STATUS_MAP[val] || val
  if (field === 'inventory_stock') return getStockStatusLabel(val)
  if (field === 'repair') return REPAIR_MAP[val] || val
  if (field === 'bom_type') return BOM_TYPE_MAP[val] || val
  return val
}

// 变更详情：每个变更字段渲染为「字段名：修改前 → 修改后」
const changeDetails = (row) => {
  return (row.changedFields || []).map(field => ({
    field,
    label: fieldLabel(field),
    before: formatFieldValue(row.beforeData, field),
    after: formatFieldValue(row.afterData, field)
  }))
}

const operationTagType = (type) => {
  const map = {
    create: 'success',
    update: 'primary',
    rollback: 'danger',
    bind_joint: 'warning',
    stock_change: 'info',
    unqualified: 'danger'
  }
  return map[type] || 'info'
}

const getList = () => {
  loading.value = true
  const params = { ...queryParams }
  // 变更前/变更后字段都作为 changed_field 筛选条件（优先后选的）
  params.changed_field = selectedAfterField.value || selectedBeforeField.value || ''
  // 变更前字段值筛选
  if (selectedBeforeField.value && selectedBeforeValue.value !== '') {
    params.before_field = selectedBeforeField.value
    params.before_match = String(selectedBeforeValue.value)
  }
  // 变更后字段值筛选
  if (selectedAfterField.value && selectedAfterValue.value !== '') {
    params.after_field = selectedAfterField.value
    params.after_match = String(selectedAfterValue.value)
  }
  getFinishedProductLogList(params)
    .then(response => {
      tableData.value = response?.data?.list || response?.list || []
      total.value = response?.data?.total || response?.total || 0
    })
    .catch(error => {
      console.error('获取数据失败', error)
      ElMessage.error('获取数据失败')
    })
    .finally(() => {
      loading.value = false
    })
}

const handleSearch = () => {
  queryParams.pageNum = 1
  getList()
}

const resetQuery = () => {
  queryParams.sn_code = ''
  queryParams.operation_type = ''
  queryParams.operator_name = ''
  queryParams.changed_field = ''
  queryParams.start_date = ''
  queryParams.end_date = ''
  dateRange.value = []
  selectedBeforeField.value = ''
  selectedBeforeValue.value = ''
  selectedAfterField.value = ''
  selectedAfterValue.value = ''
  queryParams.pageNum = 1
  getList()
}

const handleDateChange = (val) => {
  if (val && val.length === 2) {
    queryParams.start_date = val[0]
    queryParams.end_date = val[1]
  } else {
    queryParams.start_date = ''
    queryParams.end_date = ''
  }
  handleSearch()
}

const handleSizeChange = (val) => {
  queryParams.pageSize = val
  getList()
}

const handleCurrentChange = (val) => {
  queryParams.pageNum = val
  getList()
}

const applyBeforeFilter = () => {
  beforeDialogVisible.value = false
  handleSearch()
}

const clearBeforeFilter = () => {
  selectedBeforeField.value = ''
  selectedBeforeValue.value = ''
  beforeDialogVisible.value = false
  handleSearch()
}

const applyAfterFilter = () => {
  afterDialogVisible.value = false
  handleSearch()
}

const clearAfterFilter = () => {
  selectedAfterField.value = ''
  selectedAfterValue.value = ''
  afterDialogVisible.value = false
  handleSearch()
}

onMounted(() => {
  dictStore.loadDictItems('storage_status')
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
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.change-line {
  line-height: 22px;
  font-size: 13px;
}
.change-label {
  color: var(--el-text-color-secondary);
}
.change-before {
  color: var(--el-color-danger);
}
.change-arrow {
  margin: 0 6px;
  color: var(--el-text-color-secondary);
}
.change-after {
  color: var(--el-color-success);
}
.no-change {
  color: var(--el-text-color-secondary);
}
.filter-tip {
  margin: 0 0 8px 80px;
  font-size: 12px;
  line-height: 18px;
  color: var(--el-text-color-secondary);
}
</style>
