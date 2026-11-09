<template>
  <div class="app-container">
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="queryParams" class="search-form">
        <el-form-item label="操作类型">
          <el-select
            v-model="queryParams.eventType"
            placeholder="全部"
            clearable
            style="width: 130px"
            @change="handleSearch"
            @clear="handleSearch"
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
            v-model="queryParams.userName"
            placeholder="申请人或审核人"
            clearable
            style="width: 150px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="queryParams.keyword"
            placeholder="功能/对象/申请内容"
            clearable
            style="width: 180px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="操作时间">
          <el-date-picker
            v-model="queryParams.dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            unlink-panels
            style="width: 240px"
            @change="handleSearch"
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
            <div class="record-target">{{ row.targetName || '—' }}</div>
            <div v-if="row.summary" class="record-summary">{{ row.summary }}</div>
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
import { getApprovalRecordList } from '@/api/operation-log'
import { Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  eventType: '',
  userName: '',
  keyword: '',
  dateRange: []
})
const tableData = ref([])
const loading = ref(false)
const total = ref(0)

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

const getList = () => {
  loading.value = true
  const params = {
    pageNum: queryParams.pageNum,
    pageSize: queryParams.pageSize,
    eventType: queryParams.eventType,
    userName: queryParams.userName,
    keyword: queryParams.keyword
  }
  if (queryParams.dateRange?.length === 2) {
    params.startTime = queryParams.dateRange[0]
    params.endTime = queryParams.dateRange[1]
  }
  getApprovalRecordList(params)
    .then(response => {
      tableData.value = response?.list || []
      total.value = response?.total || 0
    })
    .catch(error => {
      console.error('获取审批记录失败', error)
      ElMessage.error('获取审批记录失败')
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
  queryParams.eventType = ''
  queryParams.userName = ''
  queryParams.keyword = ''
  queryParams.dateRange = []
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
.record-target {
  font-weight: 500;
  color: var(--el-text-color-primary);
}
.record-summary {
  margin-top: 2px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
