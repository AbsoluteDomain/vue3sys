<template>
  <div class="app-container">
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="queryParams" class="search-form">
        <el-form-item label="名称">
          <el-input
            v-model="queryParams.name"
            placeholder="名称"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
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
        <el-form-item label="物料编码">
          <el-input
            v-model="queryParams.material_code"
            placeholder="物料编码"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="库存类型">
          <el-select
            v-model="queryParams.product_type"
            placeholder="全部"
            clearable
            style="width: 120px"
            @change="handleSearch"
          >
            <el-option label="关节" value="关节" />
            <el-option label="机械臂" value="机械臂" />
            <el-option label="自制" value="自制" />
            <el-option label="外协" value="外协" />
            <el-option label="外购" value="外购" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <DictSelect
            v-model="queryParams.storage_status"
            code="storage_status"
            placeholder="全部"
            style="width: 140px"
            @change="handleSearch"
          />
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="dateRange"
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

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <el-button type="info" :loading="exportLoading" @click="handleExportExcel">
          <el-icon><Download /></el-icon> 导出Excel
        </el-button>
      </div>
      <el-table :data="tableData" border stripe style="width: 100%" v-loading="loading">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="name" label="名称" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.name || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sn_code" label="SN码" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.sn_code || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="material_code" label="物料编码" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.material_code || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="product_type_name" label="库存类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.product_type_name" size="small">{{ row.product_type_name }}</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="storage_status" label="状态" width="120" align="center">
          <template #default="{ row }">
            <DictTag :code="'storage_status'" :model-value="row.storage_status" size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="count" label="数量" width="80" align="center" />
        <el-table-column prop="description" label="出入库信息" min-width="250" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.description || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="operator_name" label="操作人" width="120" align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.operator_name || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ExcelJS from 'exceljs'
import { listWarehouseLog } from '@/api/product'
import DictSelect from '@/components/DictSelect/index.vue'
import DictTag from '@/components/DictTag/index.vue'
import { useDictStore } from '@/store'

const dictStore = useDictStore()

const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  name: '',
  sn_code: '',
  material_code: '',
  product_type: '',
  storage_status: '',
  start_date: '',
  end_date: ''
})

const dateRange = ref(null)

const buildListParams = () => {
  const params = {
    pageNum: queryParams.pageNum,
    pageSize: queryParams.pageSize,
    name: queryParams.name,
    sn_code: queryParams.sn_code,
    material_code: queryParams.material_code,
    product_type: queryParams.product_type,
    storage_status: queryParams.storage_status
  }
  if (dateRange.value?.[0]) {
    params.start_date = dateRange.value[0]
  }
  if (dateRange.value?.[1]) {
    params.end_date = dateRange.value[1]
  }
  return params
}

const tableData = ref([])
const loading = ref(false)
const total = ref(0)

const getList = () => {
  loading.value = true
  listWarehouseLog(buildListParams())
    .then((response) => {
      tableData.value = response?.list || []
      total.value = response?.total || 0
    })
    .catch(() => {
      ElMessage.error('获取出入库记录失败')
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
  queryParams.name = ''
  queryParams.sn_code = ''
  queryParams.material_code = ''
  queryParams.product_type = ''
  queryParams.storage_status = ''
  dateRange.value = null
  queryParams.pageNum = 1
  getList()
}

const handleSizeChange = () => getList()
const handleCurrentChange = () => getList()

// ==================== 导出 Excel ====================
const exportLoading = ref(false)

const EXPORT_COLUMNS = [
  { header: '名称', key: 'name' },
  { header: 'SN码', key: 'sn_code' },
  { header: '物料编码', key: 'material_code' },
  { header: '库存类型', key: 'product_type_name' },
  { header: '状态', key: 'storage_status' },
  { header: '数量', key: 'count' },
  { header: '出入库信息', key: 'description' },
  { header: '操作人', key: 'operator_name' },
  { header: '创建时间', key: 'created_at' },
]

const resolveDictLabel = (code, value) => {
  if (value === null || value === undefined || value === '') return ''
  const items = dictStore.getDictItems(code)
  const item = items.find(i => String(i.value) === String(value))
  return item?.label || String(value)
}

const getExportCellValue = (row, key) => {
  if (key === 'storage_status') return resolveDictLabel('storage_status', row.storage_status)
  return row[key] ?? ''
}

// 循环拉取所有页（后端单页上限 100）
const loadAllPages = async (baseParams) => {
  const pageSize = 100
  let pageNum = 1
  const allList = []
  let total = 0
  while (true) {
    const resp = await listWarehouseLog({ ...baseParams, pageNum, pageSize })
    const list = resp?.list || []
    total = resp?.total || 0
    allList.push(...list)
    if (allList.length >= total || list.length < pageSize) break
    pageNum++
  }
  return { allList, total }
}

const handleExportExcel = async () => {
  exportLoading.value = true
  try {
    const params = buildListParams()
    const { allList } = await loadAllPages({ ...params, pageNum: 1, pageSize: 100 })

    if (!allList || allList.length === 0) {
      ElMessage.warning('没有可导出的数据')
      return
    }

    const workbook = new ExcelJS.Workbook()
    const sheet = workbook.addWorksheet('出入库记录')

    sheet.columns = EXPORT_COLUMNS.map(col => ({
      header: col.header,
      key: col.key,
      width: 22,
    }))

    const headerRow = sheet.getRow(1)
    headerRow.font = { bold: true }
    headerRow.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE0E0E0' } }
    headerRow.alignment = { vertical: 'middle', horizontal: 'center' }

    allList.forEach(row => {
      const rowData = {}
      EXPORT_COLUMNS.forEach(col => {
        rowData[col.key] = getExportCellValue(row, col.key)
      })
      sheet.addRow(rowData)
    })

    // 自动筛选
    const lastCol = String.fromCharCode(64 + EXPORT_COLUMNS.length)
    const lastRow = allList.length + 1
    sheet.autoFilter = `A1:${lastCol}${lastRow}`

    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=utf-8',
    })
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    const now = new Date()
    const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
    link.href = downloadUrl
    link.download = `出入库记录_${dateStr}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)

    ElMessage.success(`已导出 ${allList.length} 条数据`)
  } catch (e) {
    console.error('导出失败', e)
    ElMessage.error('导出失败')
  } finally {
    exportLoading.value = false
  }
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
.table-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
