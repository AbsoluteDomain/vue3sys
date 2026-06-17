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
        <el-form-item label="BOM型号">
          <el-input
            v-model="queryParams.bom_model"
            placeholder="BOM型号"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="BOM名称">
          <el-input
            v-model="queryParams.bom_name"
            placeholder="BOM名称"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="BOM类型">
          <el-select
            v-model="queryParams.bom_type"
            placeholder="全部"
            clearable
            style="width: 120px"
            @change="handleSearch"
            @clear="handleSearch"
          >
            <el-option label="关节" value="0" />
            <el-option label="机械臂" value="1" />
            <el-option label="其他" value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="测试状态">
          <el-select
            v-model="queryParams.status"
            placeholder="全部"
            clearable
            style="width: 120px"
            @change="handleSearch"
            @clear="handleSearch"
          >
            <el-option label="未测试" value="0" />
            <el-option label="测试中" value="1" />
            <el-option label="测试合格" value="2" />
            <el-option label="测试不良" value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="库存状态">
          <el-select
            v-model="queryParams.inventory_stock"
            placeholder="全部"
            clearable
            style="width: 110px"
            @change="handleSearch"
            @clear="handleSearch"
          >
            <el-option label="未入库" value="0" />
            <el-option label="入库" value="1" />
            <el-option label="出库" value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="返修">
          <el-select
            v-model="queryParams.repair"
            placeholder="全部"
            clearable
            style="width: 100px"
            @change="handleSearch"
            @clear="handleSearch"
          >
            <el-option label="新品" value="0" />
            <el-option label="返修品" value="1" />
          </el-select>
        </el-form-item>
        <el-form-item label="创建时间">
          <el-date-picker
            v-model="queryParams.createDateRange"
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
        <el-form-item label="更新时间">
          <el-date-picker
            v-model="queryParams.updateDateRange"
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
        <el-button @click="openColumnDialog">
          <el-icon><Setting /></el-icon> 列展示
        </el-button>
      </div>

      <el-table
        :data="tableData"
        border
        stripe
        style="width: 100%"
        height="500"
        v-loading="loading"
      >
        <el-table-column type="index" label="序号" width="60" align="center" fixed="left" />
        <el-table-column
          v-if="isColumnVisible('sn_code')"
          prop="sn_code"
          label="SN码"
          min-width="180"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span v-if="row.sn_code">{{ row.sn_code }}</span>
            <span v-else class="text-muted">待填写</span>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('bom_type')"
          prop="bom_type_name"
          label="BOM类型"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <el-tag :type="bomTypeTagType(row.bom_type)" size="small">
              {{ row.bom_type_name || '—' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('bom_model')"
          prop="bom_model"
          label="BOM型号"
          min-width="120"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('bom_name')"
          prop="bom_name"
          label="BOM名称"
          min-width="120"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('material_code')"
          prop="material_code"
          label="物料编码"
          min-width="110"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('status')"
          prop="status"
          label="测试状态"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ row.status_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('inventory_stock')"
          prop="inventory_stock"
          label="库存状态"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <el-tag :type="inventoryTagType(row.inventory_stock)" size="small">
              {{ row.inventory_stock_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('repair')"
          prop="repair"
          label="返修"
          width="90"
          align="center"
        >
          <template #default="{ row }">
            <el-tag :type="row.repair === 1 ? 'warning' : 'info'" size="small">
              {{ row.repair_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('create_time')"
          prop="create_time"
          label="创建时间"
          width="170"
        />
        <el-table-column
          v-if="isColumnVisible('update_time')"
          prop="update_time"
          label="更新时间"
          width="170"
        />
        <el-table-column
          v-if="isColumnVisible('description')"
          prop="description"
          label="描述"
          min-width="140"
          show-overflow-tooltip
        />
        <el-table-column label="操作" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleRollback(row)">回退</el-button>
          </template>
        </el-table-column>
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

    <el-dialog v-model="dialogVisible" title="编辑成品" width="520px" destroy-on-close>
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="90px">
        <el-form-item label="SN码" prop="sn_code">
          <el-input
            v-model="formData.sn_code"
            maxlength="255"
            clearable
            placeholder="请填写产品 SN 码"
          />
        </el-form-item>
        <el-form-item label="BOM型号">
          <el-input v-model="formData.bom_model" disabled />
        </el-form-item>
        <el-form-item label="BOM名称">
          <el-input v-model="formData.bom_name" disabled />
        </el-form-item>
        <el-form-item label="创建时间">
          <el-input v-model="formData.create_time" disabled />
        </el-form-item>
        <el-form-item label="测试状态">
          <el-radio-group v-model="formData.status">
            <el-radio :value="0">未测试</el-radio>
            <el-radio :value="1">测试中</el-radio>
            <el-radio :value="2">测试合格</el-radio>
            <el-radio :value="3">测试不良</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="库存状态">
          <el-radio-group v-model="formData.inventory_stock">
            <el-radio :value="0">未入库</el-radio>
            <el-radio :value="1">入库</el-radio>
            <el-radio :value="2">出库</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="返修">
          <el-radio-group v-model="formData.repair">
            <el-radio :value="0">新品</el-radio>
            <el-radio :value="1">返修品</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            maxlength="255"
            show-word-limit
            placeholder="请输入描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="columnDialogVisible" title="列展示设置" width="480px" destroy-on-close>
      <div class="column-setting-tip">勾选需要在表格中展示的字段（序号、操作列始终显示）</div>
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
import { Search, Refresh, Setting } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getFinishProductList, updateFinishProduct, rollbackFinishProduct } from '@/api/finish-product'
import { useFinishProductTableColumns } from '@/composables/useFinishProductTableColumns'

const {
  columnOptions,
  columnDialogVisible,
  columnDraftKeys,
  isColumnVisible,
  loadColumnSettings,
  openColumnDialog,
  resetColumnDraft,
  saveColumnSettings,
} = useFinishProductTableColumns()

const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  sn_code: '',
  bom_model: '',
  bom_name: '',
  bom_type: '',
  status: '',
  inventory_stock: '',
  repair: '',
  createDateRange: null,
  updateDateRange: null
})

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
    sn_code: queryParams.sn_code,
    bom_model: queryParams.bom_model,
    bom_name: queryParams.bom_name,
    bom_type: queryParams.bom_type,
    status: queryParams.status,
    inventory_stock: queryParams.inventory_stock,
    repair: queryParams.repair
  }
  appendDateRangeParams(params, queryParams.createDateRange, 'create_start_date', 'create_end_date')
  appendDateRangeParams(params, queryParams.updateDateRange, 'update_start_date', 'update_end_date')
  return params
}

const tableData = ref([])
const loading = ref(false)
const total = ref(0)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref(null)

const formRules = {
  sn_code: [{ max: 255, message: 'SN码不能超过255个字符', trigger: 'blur' }]
}

const formData = reactive({
  id: null,
  sn_code: '',
  bom_model: '',
  bom_name: '',
  status: 0,
  inventory_stock: 0,
  repair: 0,
  create_time: '',
  description: ''
})

const inventoryTagType = (value) => {
  if (value === 1) return 'success'
  if (value === 2) return 'danger'
  return 'warning'
}

const statusTagType = (value) => {
  if (value === 2) return 'success'
  if (value === 3) return 'danger'
  if (value === 1) return 'primary'
  return 'warning'
}

const bomTypeTagType = (value) => {
  if (value === 1) return 'primary'
  if (value === 2) return 'info'
  return 'success'
}

const formatFinishProductLabel = (row) => {
  if (!row) return ''
  if (row.bom_name) return `${row.bom_model}(${row.bom_name})`
  return row.bom_model || String(row.id)
}

const getList = () => {
  loading.value = true
  getFinishProductList(buildListParams())
    .then((response) => {
      tableData.value = response?.list || []
      total.value = response?.total || 0
    })
    .catch(() => {
      ElMessage.error('获取成品列表失败')
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
  queryParams.bom_model = ''
  queryParams.bom_name = ''
  queryParams.bom_type = ''
  queryParams.status = ''
  queryParams.inventory_stock = ''
  queryParams.repair = ''
  queryParams.createDateRange = null
  queryParams.updateDateRange = null
  queryParams.pageNum = 1
  getList()
}

const handleSizeChange = () => getList()
const handleCurrentChange = () => getList()

const handleEdit = (row) => {
  formData.id = row.id
  formData.sn_code = row.sn_code
  formData.bom_model = row.bom_model || ''
  formData.bom_name = row.bom_name || ''
  formData.status = row.status
  formData.inventory_stock = row.inventory_stock
  formData.repair = row.repair
  formData.create_time = row.create_time || ''
  formData.description = row.description || ''
  dialogVisible.value = true
}

const handleSubmit = () => {
  formRef.value?.validate((valid) => {
    if (!valid) return
    submitting.value = true
    updateFinishProduct({
      id: formData.id,
      sn_code: formData.sn_code?.trim() || '',
      status: formData.status,
      inventory_stock: formData.inventory_stock,
      repair: formData.repair,
      description: formData.description
    })
      .then(() => {
        ElMessage.success('保存成功')
        dialogVisible.value = false
        getList()
      })
      .catch(() => {})
      .finally(() => {
        submitting.value = false
      })
  })
}

const handleRollback = (row) => {
  const snText = row.sn_code ? `SN: ${row.sn_code}` : '无 SN 码'
  ElMessageBox.confirm(
    `回退将把成品「${formatFinishProductLabel(row)}」（${snText}）重新拆回零部件，并恢复对应零件库存。\n\n此操作非常危险，将永久删除该条成品数据且无法恢复，是否继续？`,
    '危险操作确认',
    {
      confirmButtonText: '确认回退',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
      dangerouslyUseHTMLString: false
    }
  )
    .then(() => rollbackFinishProduct({ id: row.id }))
    .then(() => {
      ElMessage.success('回退成功，零件库存已恢复')
      getList()
    })
    .catch((err) => {
      if (err !== 'cancel' && err !== 'close') {
        // 接口错误由 request 拦截器提示
      }
    })
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
.text-muted {
  color: #909399;
  font-style: italic;
}
</style>
