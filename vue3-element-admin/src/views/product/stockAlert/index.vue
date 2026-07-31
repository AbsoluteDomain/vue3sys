<template>
  <div class="stock-alert-page">
    <div class="page-header">
      <h2>库存预警</h2>
      <div class="header-actions">
        <span class="toolbar-label">预留库存倍率:</span>
        <el-input-number
          v-model="multiplier"
          :min="0.5"
          :max="5"
          :step="0.5"
          :precision="1"
          size="default"
          @change="getList"
        />
        <el-button type="primary" :icon="Refresh" @click="getList">刷新</el-button>
      </div>
    </div>

    <el-descriptions :column="5" border class="summary-card">
      <el-descriptions-item label="监控零件数">
        <span class="count">{{ data.total }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="库存缺料">
        <span class="count type-actual">{{ data.actual_count }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="计划缺料">
        <span class="count type-plan">{{ data.plan_count }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="缺料警告">
        <span class="count type-alert">{{ data.alert_count_by_type }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="正常">
        <span class="count normal">{{ Math.max(0, data.total - data.alert_count) }}</span>
      </el-descriptions-item>
    </el-descriptions>

    <el-table :data="tableData" border stripe v-loading="loading" style="width: 100%">
      <el-table-column type="index" label="序号" width="60" align="center" :index="indexMethod" />
      <el-table-column prop="product_name" label="零件名称" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <span :class="{ 'alert-text': row.is_alert }">{{ row.product_name }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="material_code" label="物料编码" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">
          <span>{{ row.material_code || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="current_stock" label="当前库存" width="100" align="center">
        <template #default="{ row }">
          <span :class="getStockClass(row)">{{ row.current_stock }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="alert_quantity" label="预警库存" width="100" align="center">
        <template #default="{ row }">
          <span>{{ row.alert_quantity || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="procurement_cycle" label="采购周期(天)" width="110" align="center">
        <template #default="{ row }">
          <span>{{ row.procurement_cycle || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="alert_days" label="预警周期(天)" width="110" align="center">
        <template #default="{ row }">
          <span>{{ row.alert_days || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="cycle_demand" label="周期内需求量" width="120" align="center">
        <template #default="{ row }">
          <span>{{ row.cycle_demand || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="total_demand" label="总需求量" width="100" align="center">
        <template #default="{ row }">
          <span :class="{ 'alert-text': row.actual_shortage > 0 }">{{ row.total_demand || '—' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="缺料类型" width="120" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.shortage_type" :type="getTagType(row.shortage_type)" size="small">
            {{ getShortageTypeLabel(row.shortage_type) }}
          </el-tag>
          <el-tag v-else type="success" size="small">正常</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="缺口数量" width="100" align="center">
        <template #default="{ row }">
          <span v-if="row.shortage > 0" :class="getShortageTypeClass(row.shortage_type)">
            {{ row.shortage }}
          </span>
          <span v-else class="text-muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="suggested_order" label="建议补货量" width="110" align="center">
        <template #default="{ row }">
          <span v-if="row.is_alert" :class="getShortageTypeClass(row.shortage_type)">{{ row.suggested_order }}</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-container">
      <el-pagination
        v-model:current-page="pageNum"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="totalCount"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>

    <el-empty v-if="!loading && tableData.length === 0" description="暂无预警数据，请先在生产计划中添加计划，并为零件设置采购周期" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { listStockAlert } from '@/api/product'

const loading = ref(false)
const tableData = ref<any[]>([])
const multiplier = ref(1.5)
const pageNum = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const summary = ref({
  alert_count: 0,
  actual_count: 0,
  plan_count: 0,
  alert_count_by_type: 0,
})

const data = computed(() => ({
  total: totalCount.value,
  alert_count: summary.value.alert_count,
  actual_count: summary.value.actual_count,
  plan_count: summary.value.plan_count,
  alert_count_by_type: summary.value.alert_count_by_type,
}))

function getTagType(type: string) {
  if (type === 'actual') return 'danger'
  if (type === 'plan') return 'warning'
  if (type === 'alert') return 'success'
  return 'info'
}

function getShortageTypeLabel(type: string) {
  if (type === 'actual') return '库存缺料'
  if (type === 'plan') return '计划缺料'
  if (type === 'alert') return '缺料警告'
  return '未知'
}

function getShortageTypeClass(type: string) {
  if (type === 'actual') return 'alert-text'
  if (type === 'plan') return 'warning-text'
  if (type === 'alert') return 'alert-warning-text'
  return ''
}

function getStockClass(row: any) {
  if (row.shortage_type === 'actual') return 'alert-text'
  if (row.shortage_type === 'plan') return 'warning-text'
  if (row.shortage_type === 'alert') return 'alert-warning-text'
  return ''
}

const getList = async () => {
  loading.value = true
  try {
    const res = await listStockAlert({
      multiplier: multiplier.value,
      pageNum: pageNum.value,
      pageSize: pageSize.value,
    })
    tableData.value = res?.list || []
    totalCount.value = res?.total || 0
    summary.value = {
      alert_count: res?.alert_count || 0,
      actual_count: res?.actual_count || 0,
      plan_count: res?.plan_count || 0,
      alert_count_by_type: res?.alert_count_by_type || 0,
    }
  } catch (error) {
    ElMessage.error('获取预警列表失败')
  } finally {
    loading.value = false
  }
}

function indexMethod(index: number) {
  return (pageNum.value - 1) * pageSize.value + index + 1
}

function handleSizeChange(val: number) {
  pageSize.value = val
  pageNum.value = 1
  getList()
}

function handleCurrentChange(val: number) {
  pageNum.value = val
  getList()
}

onMounted(() => {
  getList()
})
</script>

<style scoped lang="scss">
.stock-alert-page {
  padding: 20px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h2 {
      margin: 0;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .toolbar-label {
      font-weight: 500;
      color: var(--el-text-color-primary);
      font-size: 14px;
    }
  }

  .summary-card {
    margin-bottom: 16px;
  }

  .count {
    font-size: 20px;
    font-weight: bold;

    &.type-actual {
      color: var(--el-color-danger, #f56c6c);
    }

    &.type-plan {
      color: var(--el-color-warning, #e6a23c);
    }

    &.type-alert {
      color: var(--el-color-success, #67c23a);
    }

    &.normal {
      color: var(--el-color-info, #909399);
    }
  }

  .alert-text {
    color: var(--el-color-danger, #f56c6c);
    font-weight: bold;
  }

  .warning-text {
    color: var(--el-color-warning, #e6a23c);
    font-weight: bold;
  }

  .alert-warning-text {
    color: var(--el-color-success, #67c23a);
    font-weight: bold;
  }

  .text-muted {
    color: var(--el-color-info, #909399);
  }

  .pagination-container {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }
}
</style>
