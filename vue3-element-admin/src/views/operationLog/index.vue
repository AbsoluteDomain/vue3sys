<template>
  <div class="app-container">
    <el-tabs v-model="activeTab" class="log-tabs" @tab-change="handleTabChange">
      <el-tab-pane label="操作日志" name="operation">
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
                <el-option label="成品" value="finishProduct" />
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
                <el-option label="回退" value="rollback" />
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
      </el-tab-pane>

      <el-tab-pane label="审批记录" name="approval">
        <el-card shadow="never" class="search-card">
          <el-form :inline="true" :model="recordParams" class="search-form">
            <el-form-item label="操作类型">
              <el-select
                v-model="recordParams.eventType"
                placeholder="全部"
                clearable
                style="width: 130px"
                @change="handleRecordSearch"
                @clear="handleRecordSearch"
              >
                <el-option label="提交审批" value="submit" />
                <el-option label="同意" value="approve" />
                <el-option label="拒绝" value="reject" />
                <el-option label="执行成功" value="execute" />
                <el-option label="执行失败" value="execute_failed" />
              </el-select>
            </el-form-item>
            <el-form-item label="操作人">
              <el-input
                v-model="recordParams.userName"
                placeholder="申请人或审核人"
                clearable
                style="width: 150px"
                @clear="handleRecordSearch"
                @keyup.enter="handleRecordSearch"
              />
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="recordParams.keyword"
                placeholder="功能/对象/申请内容"
                clearable
                style="width: 180px"
                @clear="handleRecordSearch"
                @keyup.enter="handleRecordSearch"
              />
            </el-form-item>
            <el-form-item label="操作时间">
              <el-date-picker
                v-model="recordParams.dateRange"
                type="daterange"
                value-format="YYYY-MM-DD"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                unlink-panels
                style="width: 240px"
                @change="handleRecordSearch"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleRecordSearch">
                <el-icon><Search /></el-icon> 搜索
              </el-button>
              <el-button @click="resetRecordQuery">
                <el-icon><Refresh /></el-icon> 重置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never" class="table-card">
          <el-table
            :data="recordData"
            border
            stripe
            style="width: 100%"
            height="500"
            v-loading="recordLoading"
          >
            <el-table-column type="index" label="序号" width="60" align="center" />
            <el-table-column label="操作类型" width="110">
              <template #default="{ row }">
                <el-tag :type="eventTagType(row.type)" size="small" effect="plain">
                  {{ row.typeName }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="actor" label="操作人" width="120" />
            <el-table-column prop="name" label="功能" width="110" show-overflow-tooltip />
            <el-table-column label="业务对象/申请内容" min-width="220">
              <template #default="{ row }">
                <div class="log-target">{{ row.targetName || '—' }}</div>
                <div v-if="row.summary" class="log-summary">{{ row.summary }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="detail" label="审批意见/执行结果" min-width="200" show-overflow-tooltip />
            <el-table-column label="当前状态" width="110">
              <template #default="{ row }">
                <el-tooltip :content="row.executeError" :disabled="!row.executeError" placement="top">
                  <el-tag :type="statusTagType(row.status)" size="small" effect="plain">
                    {{ row.statusName }}
                  </el-tag>
                </el-tooltip>
              </template>
            </el-table-column>
            <el-table-column prop="time" label="操作时间" width="170" />
          </el-table>
          <div class="pagination-container">
            <el-pagination
              v-model:current-page="recordParams.pageNum"
              v-model:page-size="recordParams.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              :total="recordTotal"
              @size-change="handleRecordSizeChange"
              @current-change="handleRecordCurrentChange"
            />
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getOperationLogList, getApprovalRecordList } from '@/api/operation-log'
import { Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const activeTab = ref('operation')

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

const recordParams = reactive({
  pageNum: 1,
  pageSize: 10,
  eventType: '',
  userName: '',
  keyword: '',
  dateRange: []
})
const recordData = ref([])
const recordLoading = ref(false)
const recordTotal = ref(0)
const recordLoaded = ref(false)

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

const getRecordList = () => {
  recordLoading.value = true
  const params = {
    pageNum: recordParams.pageNum,
    pageSize: recordParams.pageSize,
    eventType: recordParams.eventType,
    userName: recordParams.userName,
    keyword: recordParams.keyword
  }
  if (recordParams.dateRange?.length === 2) {
    params.startTime = recordParams.dateRange[0]
    params.endTime = recordParams.dateRange[1]
  }
  getApprovalRecordList(params)
    .then(response => {
      recordData.value = response?.list || []
      recordTotal.value = response?.total || 0
    })
    .catch(error => {
      console.error('获取审批记录失败', error)
      ElMessage.error('获取审批记录失败')
    })
    .finally(() => {
      recordLoading.value = false
    })
}

const statusTagType = (status) => {
  if (status === 1) return 'success'
  if (status === 2) return 'danger'
  if (status === 3) return 'warning'
  return 'info'
}

const eventTagType = (type) => {
  if (type === 'approve' || type === 'execute') return 'success'
  if (type === 'reject' || type === 'execute_failed') return 'danger'
  return 'info'
}

const handleTabChange = (name) => {
  if (name === 'approval' && !recordLoaded.value) {
    recordLoaded.value = true
    getRecordList()
  }
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

const handleRecordSearch = () => {
  recordParams.pageNum = 1
  getRecordList()
}

const resetRecordQuery = () => {
  recordParams.eventType = ''
  recordParams.userName = ''
  recordParams.keyword = ''
  recordParams.dateRange = []
  recordParams.pageNum = 1
  getRecordList()
}

const handleRecordSizeChange = (val) => {
  recordParams.pageSize = val
  getRecordList()
}

const handleRecordCurrentChange = (val) => {
  recordParams.pageNum = val
  getRecordList()
}

onMounted(() => {
  getList()
})
</script>

<style scoped>
.app-container {
  padding: 20px;
}
.log-tabs {
  margin-top: -10px;
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
.log-target {
  font-weight: 500;
  color: var(--el-text-color-primary);
}
.log-summary {
  margin-top: 2px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
