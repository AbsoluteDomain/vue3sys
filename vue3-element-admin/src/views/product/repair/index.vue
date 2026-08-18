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
          <el-form-item label="BOM名称">
            <el-input
              v-model="queryParams.bom_name"
              placeholder="BOM名称"
              clearable
              style="width: 160px"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="resetSearch">重置</el-button>
          </el-form-item>
        </el-form>
        <el-button type="primary" @click="showCreateDialog">新增返修计划</el-button>
      </div>
    </el-card>

    <el-card shadow="never" class="data-card">
      <el-table 
        :data="tableData" 
        border 
        stripe 
        style="width: 100%" 
        v-loading="loading"
        @row-click="handleViewDetail"
        highlight-current-row
      >
        <el-table-column prop="sn_code" label="SN码" min-width="150" />
        <el-table-column prop="bom_name" label="BOM名称" min-width="180" />
        <el-table-column prop="repair_cnt" label="返修次数" width="100" align="center" />
        <el-table-column prop="last_repair_time" label="最后返修时间" min-width="170" />
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button size="small" @click.stop="handleViewDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="tableData.length === 0 && !loading" description="暂无返修数据" />
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增返修计划" width="500px" destroy-on-close>
      <el-form :model="formData" label-width="100px">
        <el-form-item label="选择成品" required>
          <el-select
            v-model="formData.product_id"
            placeholder="请选择拥有SN码的成品"
            style="width: 100%"
            filterable
            @change="handleProductChange"
          >
            <el-option
              v-for="item in productOptions"
              :key="item.id"
              :label="`${item.sn_code} - ${item.bom_name}`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="不良项">
          <el-select
            v-model="formData.unqualified_values"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择不良项"
            style="width: 100%"
          >
            <el-option
              v-for="item in repairUnqualifiedOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="返修内容" required>
          <el-input
            v-model="formData.repair_info"
            type="textarea"
            placeholder="请输入返修内容"
            :rows="4"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="saving">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="historyDialogVisible" title="返修历史记录" width="1000px">
      <div v-if="currentRow">
        <p><strong>SN码：</strong>{{ currentRow.sn_code }}</p>
        <p><strong>BOM名称：</strong>{{ currentRow.bom_name }}</p>
        <p><strong>返修次数：</strong>{{ currentRow.repair_cnt }}</p>
      </div>
      <el-table :data="historyData" border stripe style="width: 100%; margin-top: 15px" v-loading="historyLoading">
        <el-table-column prop="repair_cnt" label="第几次返修" width="120" align="center" />
        <el-table-column prop="repair_info" label="返修内容" min-width="300" />
        <el-table-column prop="create_time" label="返修时间" min-width="170" />
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listRepairProducts, createRepair, getProductsWithSn, getProductRepairHistory, deleteRepair } from '@/api/product'
import { getUnqualifiedItems } from '@/api/finish-product'
import { useDictStore } from '@/store'

const dictStore = useDictStore()

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const historyDialogVisible = ref(false)
const historyLoading = ref(false)
const tableData = ref([])
const historyData = ref([])
const productOptions = ref([])
const currentRow = ref(null)
const repairUnqualifiedOptions = ref([])

const queryParams = reactive({
  sn_code: '',
  bom_name: '',
})

const formData = reactive({
  product_id: '',
  repair_info: '',
  unqualified_values: []
})

onMounted(() => {
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const res = await listRepairProducts()
    tableData.value = res || []
  } catch (error) {
    ElMessage.error('加载失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

async function handleSearch() {
  await loadData()
}

function resetSearch() {
  queryParams.sn_code = ''
  queryParams.bom_name = ''
  handleSearch()
}

async function showCreateDialog() {
  formData.product_id = ''
  formData.repair_info = ''
  formData.unqualified_values = []
  repairUnqualifiedOptions.value = []
  
  try {
      const res = await getProductsWithSn()
      productOptions.value = res || []
    } catch (error) {
    ElMessage.error('加载成品列表失败: ' + error.message)
  }
  
  dialogVisible.value = true
}

// 当选择成品时，加载该产品的不良项
async function handleProductChange(productId) {
  formData.unqualified_values = []
  
  // 加载字典项
  await dictStore.loadDictItems('unqualified_status')
  const allOptions = dictStore.getDictItems('unqualified_status').map(item => ({
    value: item.value,
    label: item.label
  }))

  // 加载产品已绑定的不良项
  if (productId) {
    try {
      const res = await getUnqualifiedItems({ finish_product_id: productId })
      const boundItems = res || []
      if (boundItems.length > 0) {
        // 如果有绑定的不良项，显示绑定的几项
        repairUnqualifiedOptions.value = boundItems.map(item => ({
          value: item.unqualified_value,
          label: item.unqualified_label
        }))
        formData.unqualified_values = boundItems.map(item => item.unqualified_value)
      } else {
        // 如果没有绑定，显示全部
        repairUnqualifiedOptions.value = allOptions
      }
    } catch {
      // 如果加载失败，显示全部
      repairUnqualifiedOptions.value = allOptions
    }
  } else {
    repairUnqualifiedOptions.value = []
  }
}

async function handleSubmit() {
  if (!formData.product_id) {
    ElMessage.warning('请选择成品')
    return
  }

  // 构建返修内容：将选中的不良项标签拼接到返修内容中
  const selectedLabels = repairUnqualifiedOptions.value
    .filter(opt => formData.unqualified_values.includes(opt.value))
    .map(opt => opt.label)
  let finalRepairInfo = formData.repair_info.trim()
  if (selectedLabels.length > 0) {
    const prefix = `不良项：${selectedLabels.join('、')}`
    finalRepairInfo = finalRepairInfo ? `${prefix}\n${finalRepairInfo}` : prefix
  }

  // === 调试日志 ===
  console.log('===== 返修计划提交日志 =====')
  console.log('选中的不良项值:', formData.unqualified_values)
  console.log('选中的不良项标签:', selectedLabels)
  console.log('原返修内容:', formData.repair_info)
  console.log('最终拼接的返修内容:', finalRepairInfo)
  console.log('==============================')
  // === 调试日志结束 ===

  if (!finalRepairInfo) {
    ElMessage.warning('请填写返修内容或选择不良项')
    return
  }
  
  saving.value = true
  try {
    await createRepair({
      product_id: formData.product_id,
      repair_info: finalRepairInfo,
    })
    ElMessage.success('创建成功')
    dialogVisible.value = false
    await loadData()
  } catch (error) {
    ElMessage.error('创建失败: ' + error.message)
  } finally {
    saving.value = false
  }
}

async function handleViewDetail(row) {
  currentRow.value = row
  historyDialogVisible.value = true
  historyLoading.value = true
  try {
    const res = await getProductRepairHistory({ product_id: row.product_id })
    historyData.value = res || []
  } catch (error) {
    ElMessage.error('加载返修历史失败: ' + error.message)
  } finally {
    historyLoading.value = false
  }
}

async function handleDelete(row) {
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
    await loadData()
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
</style>