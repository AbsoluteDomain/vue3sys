<template>
  <div class="app-container">
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="queryParams" class="search-form">
        <el-form-item label="模块">
          <el-select
            v-model="queryParams.module"
            placeholder="全部"
            clearable
            style="width: 120px"
            @change="handleSearch"
            @clear="handleSearch"
          >
            <el-option label="库存" value="product" />
            <el-option label="BOM" value="bom" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select
            v-model="queryParams.operationType"
            placeholder="全部"
            clearable
            style="width: 120px"
            @change="handleSearch"
            @clear="handleSearch"
          >
            <el-option label="创建" value="create" />
            <el-option label="更新" value="update" />
            <el-option label="删除" value="delete" />
            <el-option label="入库" value="stock_in" />
            <el-option label="出库" value="stock_out" />
            <el-option label="组装" value="assemble" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作人">
          <el-input
            v-model="queryParams.userName"
            placeholder="操作人"
            clearable
            style="width: 150px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
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
      <el-table
        :data="tableData"
        border
        stripe
        style="width: 100%"
        height="500"
        v-loading="loading"
      >
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="moduleName" label="模块" width="100" />
        <el-table-column prop="operationTypeName" label="操作类型" width="100" />
        <el-table-column prop="targetName" label="操作对象" min-width="150" show-overflow-tooltip />
        <el-table-column prop="userName" label="操作人" width="120" />
        <el-table-column prop="ip" label="IP地址" width="140" />
        <el-table-column prop="description" label="操作详情" min-width="200" show-overflow-tooltip />
        <el-table-column prop="createTime" label="操作时间" width="180" />
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
import { getOperationLogList } from '@/api/operation-log'
import { Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  module: '',
  operationType: '',
  userName: ''
})

const tableData = ref([])
const loading = ref(false)
const total = ref(0)

const getList = () => {
  loading.value = true
  getOperationLogList(queryParams)
    .then(response => {
      tableData.value = response?.list || []
      total.value = response?.total || 0
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
  queryParams.module = ''
  queryParams.operationType = ''
  queryParams.userName = ''
  queryParams.pageNum = 1
  getList()
}

const handleSizeChange = (val) => {
  queryParams.pageSize = val
  getList()
}

const handleCurrentChange = (val) => {
  queryParams.pageNum = val
  getList()
}

onMounted(() => {
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
