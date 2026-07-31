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
import { Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
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
  queryParams.storage_status = ''
  dateRange.value = null
  queryParams.pageNum = 1
  getList()
}

const handleSizeChange = () => getList()
const handleCurrentChange = () => getList()

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
</style>
