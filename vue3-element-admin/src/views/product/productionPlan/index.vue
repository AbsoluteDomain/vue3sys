<template>
  <div class="app-container">
    <div class="toolbar">
      <span class="toolbar-label">预留库存倍率:</span>
      <el-input-number
        v-model="multiplier"
        :min="0.5"
        :max="5"
        :step="0.5"
        :precision="1"
        size="default"
        @change="onMultiplierChange"
      />
      <span class="toolbar-hint">采购周期 × 倍率 = 所需库存</span>
    </div>

    <el-card shadow="never" class="calendar-card">
      <el-calendar v-model="calendarDate" ref="calendarRef" :key="calendarKey">
        <template #date-cell="{ data }">
          <el-tooltip
            v-if="hasPlan(data) && getPlanStatus(data) !== '已计划' && getPlanStatus(data) !== '已过期'"
            :content="getShortageTooltip(data)"
            placement="top"
            effect="dark"
          >
            <div class="calendar-date-cell" :class="getDateCellClass(data)" @click.stop="onDateCellClick(data)">
              <span class="date-number">{{ data.day }}</span>
              <span v-if="hasPlan(data)" class="plan-tag" :class="getPlanTagClass(data)">
                {{ getPlanStatus(data) }}
              </span>
            </div>
          </el-tooltip>
          <div v-else class="calendar-date-cell" :class="getDateCellClass(data)" @click.stop="onDateCellClick(data)">
            <span class="date-number">{{ data.day }}</span>
            <span v-if="hasPlan(data)" class="plan-tag" :class="{ 'tag-expired': getPlanStatus(data) === '已过期' }">
              {{ getPlanStatus(data) }}
            </span>
          </div>
        </template>
      </el-calendar>
    </el-card>

    <el-card shadow="never" class="shortage-card" v-if="shortageSummary.length > 0">
      <template #header>
        <span class="card-title">缺料库存汇总</span>
      </template>
      <el-table :data="shortageSummary" border stripe style="width: 100%">
        <el-table-column prop="product_name" label="材料名称" min-width="150" />
        <el-table-column prop="material_code" label="物料编码" min-width="120" />
        <el-table-column prop="current_stock" label="当前库存" width="100" align="right">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.current_stock <= 0 }">{{ row.current_stock }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_required" label="需求数量" width="100" align="right" />
        <el-table-column label="计划缺料计算" width="200" align="center">
          <template #default="{ row }">
            <div v-if="row.required_stock > 0" class="plan-calc-info">
              <div>日均: {{ row.avg_daily?.toFixed(1) }}</div>
              <div>周期{{ row.procurement_cycle }}天×{{ multiplier }} = {{ row.required_stock?.toFixed(0) }}</div>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_shortage" label="缺口总量" width="100" align="right">
          <template #default="{ row }">
            <span :class="getShortageTypeClass(row.shortage_type)">{{ row.total_shortage }}</span>
          </template>
        </el-table-column>
        <el-table-column label="缺料类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getTagType(row.shortage_type)" size="small">
              {{ getShortageTypeLabel(row.shortage_type) }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="`${formatDateTitle(selectedDate)} 生产计划`" width="1100px" height="80vh" destroy-on-close>
      <el-form ref="formRef" :model="formData" class="plan-form">
        <el-form-item label="已选产品">
          <div class="bom-selection-list">
            <div v-if="selectedBoms.length === 0" class="empty-tip">
              请选择要生产的产品
            </div>
            <div v-for="(bom, idx) in selectedBoms" :key="bom.id" class="bom-item">
              <div class="bom-info">
                <span class="bom-model">{{ bom.bom_model }}</span>
                <span class="bom-name">{{ bom.bom_name }}</span>
                <span class="bom-type">{{ bom.type_name }}</span>
              </div>
              <el-input-number
                v-model="bom.quantity"
                :min="0"
                :max="9999"
                style="width: 120px"
                @change="calculateRequirements"
              />
              <el-button link type="danger" size="small" @click="removeBom(idx)">删除</el-button>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="添加产品">
          <el-select
            v-model="selectedBomId"
            placeholder="请选择BOM"
            style="width: 100%"
            filterable
            @change="addBom"
          >
            <el-option
              v-for="bom in availableBoms"
              :key="bom.id"
              :label="`${bom.bom_model} ${bom.bom_name || ''} (${bom.type_name})`"
              :value="bom.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="物料需求">
          <el-table
            :data="requirements"
            border
            stripe
            style="width: 100%"
            v-loading="loading"
            :max-height="350"
            :default-sort="{ prop: 'shortage', order: 'descending' }"
            @sort-change="handleSortChange"
          >
            <el-table-column prop="product_name" label="材料名称" min-width="180" sortable />
            <el-table-column prop="material_code" label="物料编码" min-width="140" sortable />
            <el-table-column prop="total_required" label="需求数量" width="120" align="right" sortable>
              <template #default="{ row }">
                <span :class="{ 'text-danger': row.shortage > 0 }">{{ row.total_required }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="stock_before" label="计划前库存" width="130" align="right" sortable>
              <template #default="{ row }">
                <span>{{ row.stock_before || row.current_stock }}</span>
              </template>
            </el-table-column>
            <el-table-column label="计划后库存" width="130" align="right">
              <template #default="{ row }">
                <span :class="{ 'text-danger': (row.stock_before || row.current_stock) - row.total_required < 0 }">
                  {{ Math.max(0, (row.stock_before || row.current_stock) - row.total_required) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="shortage" label="缺口" width="100" align="right" sortable>
              <template #default="{ row }">
                <span :class="getShortageTypeClass(row.shortage_type)" v-if="row.shortage > 0">
                  +{{ row.shortage }}
                </span>
                <span v-else>0</span>
              </template>
            </el-table-column>
            <el-table-column label="缺料类型" width="120" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.shortage_type" :type="getTagType(row.shortage_type)" size="small">
                  {{ getShortageTypeLabel(row.shortage_type) }}
                </el-tag>
                <el-tag v-else type="info" size="small">充足</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePlan">保存计划</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getBomList, calculateProductionRequirements, getProductionPlan, saveProductionPlan, listProductionPlan } from '@/api/product'

const calendarRef = ref(null)
const selectedDate = ref(new Date())
const calendarDate = ref(new Date())
const dialogVisible = ref(false)
const selectedBomId = ref(null)
const availableBoms = ref([])
const selectedBoms = ref([])
const requirements = ref([])
const loading = ref(false)
const saving = ref(false)
const formRef = ref(null)
const planDates = ref({})
const currentPlanInfo = ref(null)
const isMounted = ref(false)
const calendarKey = ref(0)
const shortageSummary = ref([])
const multiplier = ref(1.5)

function onMultiplierChange() {
  loadPlanDates()
}

const today = new Date()
today.setHours(0, 0, 0, 0)

function formatDate(dateData) {
  if (!dateData) return ''
  
  let year, month, day
  
  if (dateData instanceof Date) {
    year = dateData.getFullYear()
    month = dateData.getMonth() + 1
    day = dateData.getDate()
  } else if (typeof dateData === 'string') {
    const d = new Date(dateData)
    year = d.getFullYear()
    month = d.getMonth() + 1
    day = d.getDate()
  } else if (dateData && typeof dateData.getTime === 'function') {
    const d = new Date(dateData.getTime())
    year = d.getFullYear()
    month = d.getMonth() + 1
    day = d.getDate()
  } else if (dateData.date && dateData.date instanceof Date) {
    year = dateData.date.getFullYear()
    month = dateData.date.getMonth() + 1
    day = dateData.date.getDate()
  } else if (dateData.day && typeof dateData.day === 'string' && dateData.day.includes('-')) {
    const d = new Date(dateData.day)
    year = d.getFullYear()
    month = d.getMonth() + 1
    day = d.getDate()
  } else if (dateData.year && dateData.month && dateData.day) {
    year = dateData.year
    month = dateData.month
    day = dateData.day
  } else {
    console.warn('formatDate: 无法处理的日期格式', dateData)
    return ''
  }
  
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

function formatDateTitle(dateData) {
  if (!dateData) return ''
  
  let d
  if (dateData instanceof Date) {
    d = dateData
  } else if (typeof dateData === 'string') {
    d = new Date(dateData)
  } else if (dateData && typeof dateData.getTime === 'function') {
    d = new Date(dateData.getTime())
  } else if (dateData.date && dateData.date instanceof Date) {
    d = dateData.date
  } else if (dateData.year && dateData.month && dateData.day) {
    d = new Date(dateData.year, dateData.month - 1, dateData.day)
  } else {
    return ''
  }
  
  const year = d.getFullYear()
  const month = d.getMonth() + 1
  const day = d.getDate()
  const hours = String(d.getHours()).padStart(2, '0')
  const minutes = String(d.getMinutes()).padStart(2, '0')
  const seconds = String(d.getSeconds()).padStart(2, '0')
  
  return `${year}年${month}月${day}日${hours}:${minutes}:${seconds}`
}

function getDateCellClass(dateData) {
  if (!dateData) return []
  
  const dateStr = formatDate(dateData)
  if (!dateStr) return []
  
  const dateObj = new Date(dateStr)
  dateObj.setHours(0, 0, 0, 0)
  
  const classes = []
  
  if (dateObj < today) {
    classes.push('past')
  }
  
  const planInfo = planDates.value[dateStr]
  if (planInfo) {
    if (dateObj < today) {
      classes.push('expired-plan')
    } else if (planInfo.has_shortage) {
      const worstType = getWorstShortageType(planInfo.shortage_details)
      if (worstType === 'actual') {
        classes.push('has-shortage-actual')
      } else if (worstType === 'plan') {
        classes.push('has-shortage-plan')
      } else if (worstType === 'alert') {
        classes.push('has-shortage-alert')
      } else {
        classes.push('has-shortage')
      }
    } else {
      classes.push('has-plan')
    }
  }
  
  return classes
}

function getWorstShortageType(shortageDetails) {
  if (!shortageDetails || shortageDetails.length === 0) return ''
  const typePriority = { actual: 3, plan: 2, alert: 1 }
  let worst = ''
  let maxPriority = 0
  for (const d of shortageDetails) {
    if (d.shortage && d.shortage > 0 && d.shortage_type) {
      const p = typePriority[d.shortage_type] || 0
      if (p > maxPriority) {
        maxPriority = p
        worst = d.shortage_type
      }
    }
  }
  return worst
}

function getShortageTypeClass(type) {
  if (type === 'actual') return 'text-danger'
  if (type === 'plan') return 'text-warning'
  if (type === 'alert') return 'text-success'
  return 'text-danger'
}

function getTagType(type) {
  if (type === 'actual') return 'danger'
  if (type === 'plan') return 'warning'
  if (type === 'alert') return 'success'
  return 'danger'
}

function getShortageTypeLabel(type) {
  if (type === 'actual') return '库存缺料'
  if (type === 'plan') return '计划缺料'
  if (type === 'alert') return '缺料警告'
  return '缺少库存'
}

function getPlanTagClass(dateData) {
  if (!dateData) return ''
  const dateStr = formatDate(dateData)
  const planInfo = planDates.value[dateStr]
  if (!planInfo || !planInfo.has_shortage) return ''
  const worstType = getWorstShortageType(planInfo.shortage_details)
  if (worstType === 'actual') return 'tag-actual'
  if (worstType === 'plan') return 'tag-plan'
  if (worstType === 'alert') return 'tag-alert'
  return ''
}

function hasPlan(date) {
  if (!date) return false
  const dateStr = formatDate(date)
  return !!planDates.value[dateStr]
}

function getPlanStatus(date) {
  if (!date) return ''
  const dateStr = formatDate(date)
  
  const planInfo = planDates.value[dateStr]
  
  // 后端标记为已过期 或 日期在今天之前
  if (planInfo && planInfo.is_expired) {
    return '已过期'
  }
  
  const dateObj = new Date(dateStr)
  dateObj.setHours(0, 0, 0, 0)
  if (dateObj < today) {
    return '已过期'
  }
  
  if (planInfo && planInfo.has_shortage) {
    const worstType = getWorstShortageType(planInfo.shortage_details)
    if (worstType === 'actual') {
      return '库存缺料'
    } else if (worstType === 'plan') {
      return '计划缺料'
    } else if (worstType === 'alert') {
      return '缺料警告'
    }
    return '缺少库存'
  }
  return '已计划'
}

function getShortageTooltip(date) {
  if (!date) return ''
  const dateStr = formatDate(date)
  const planInfo = planDates.value[dateStr]
  if (!planInfo || !planInfo.shortage_bom_names || planInfo.shortage_bom_names.length === 0) {
    return '缺少库存'
  }
  
  const bomNames = planInfo.shortage_bom_names.join('、')
  const worstType = getWorstShortageType(planInfo.shortage_details)
  const typeText = worstType === 'actual' ? '库存缺料' : worstType === 'plan' ? '计划缺料' : worstType === 'alert' ? '缺料警告' : '缺少库存'
  return `${typeText}：${bomNames}`
}

async function loadPlanDates() {
  try {
    const data = await listProductionPlan({ multiplier: multiplier.value })
    planDates.value = {}
    const shortageMap = {}
    
    if (data && Array.isArray(data)) {
      data.forEach(item => {
        if (item && item.date) {
          planDates.value[item.date] = {
            has_shortage: item.has_shortage || false,
            shortage_details: item.shortage_details || [],
            shortage_bom_names: item.shortage_bom_names || [],
            boms: item.boms || [],
            is_expired: item.is_expired || false,
          }
          
          // 只汇总非过期计划的缺料信息
          if (!item.is_expired && item.shortage_details && item.shortage_details.length > 0) {
            item.shortage_details.forEach(detail => {
              if (detail.shortage && detail.shortage > 0) {
                const key = String(detail.product_id)
                if (!shortageMap[key]) {
                  shortageMap[key] = {
                    product_name: detail.product_name,
                    material_code: detail.material_code,
                    current_stock: detail.stock_before ?? 0,
                    total_required: detail.required ?? 0,
                    total_shortage: 0,
                    shortage_type: '',
                    alert_quantity: detail.alert_quantity ?? 0,
                    procurement_cycle: detail.procurement_cycle ?? 0,
                    required_stock: detail.required_stock ?? 0,
                    avg_daily: detail.avg_daily ?? 0,
                    distinct_days: detail.distinct_days ?? 0,
                  }
                } else {
                  shortageMap[key].total_required += (detail.required ?? 0)
                }
                // Accumulate shortage
                shortageMap[key].total_shortage += detail.shortage
                // Take the most severe type
                const typePriority = { actual: 3, plan: 2, alert: 1 }
                if (detail.shortage_type) {
                  const currentPriority = typePriority[shortageMap[key].shortage_type] || 0
                  const newPriority = typePriority[detail.shortage_type] || 0
                  if (newPriority > currentPriority) {
                    shortageMap[key].shortage_type = detail.shortage_type
                    shortageMap[key].current_stock = detail.stock_before ?? 0
                    shortageMap[key].required_stock = detail.required_stock ?? 0
                    shortageMap[key].avg_daily = detail.avg_daily ?? 0
                  }
                }
              }
            })
          }
        }
      })
    }
    
    shortageSummary.value = Object.values(shortageMap)
    calendarKey.value++
  } catch (error) {
    console.error('加载计划日期失败', error)
  }
}

function onDateCellClick(data) {
  if (!data) return
  
  const dateStr = formatDate(data)
  if (!dateStr) return
  
  selectedDate.value = new Date(dateStr + 'T00:00:00')
  
  loadPlanData(dateStr)
  dialogVisible.value = true
}

async function loadPlanData(dateStr) {
  loading.value = true
  try {
    const [bomList, planData] = await Promise.all([
      getBomList({ pageNum: 1, pageSize: 999 }),
      getProductionPlan(dateStr),
    ])
    availableBoms.value = bomList.list || []
    if (planData && planData.boms) {
      selectedBoms.value = planData.boms.map(bom => ({
        ...bom,
        quantity: bom.quantity || 1,
      }))
    } else {
      selectedBoms.value = []
    }
    currentPlanInfo.value = planDates.value[dateStr] || null
    await calculateRequirements()
  } catch (error) {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

function addBom(bomId) {
  if (!bomId) return
  const bom = availableBoms.value.find(b => b.id === bomId)
  if (!bom) return
  if (selectedBoms.value.some(b => b.id === bomId)) {
    ElMessage.warning('该产品已添加')
    return
  }
  selectedBoms.value.push({
    ...bom,
    quantity: 1,
  })
  selectedBomId.value = null
  calculateRequirements()
}

function removeBom(index) {
  selectedBoms.value.splice(index, 1)
  calculateRequirements()
}

async function calculateRequirements() {
  const validBoms = selectedBoms.value.filter(b => b.quantity > 0)
  
  if (validBoms.length === 0) {
    requirements.value = []
    return
  }

  loading.value = true
  try {
    const data = await calculateProductionRequirements({
      date: formatDate(selectedDate.value),
      boms: validBoms.map(b => ({
        bom_id: b.id,
        quantity: b.quantity,
      })),
    })
    requirements.value = data || []
  } catch (error) {
    ElMessage.error('计算物料需求失败')
  } finally {
    loading.value = false
  }
}

function handleSortChange({ prop, order }) {
  if (!prop || !order) return
  
  requirements.value.sort((a, b) => {
    const aVal = a[prop] ?? 0
    const bVal = b[prop] ?? 0
    
    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return order === 'ascending' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
    }
    
    return order === 'ascending' ? aVal - bVal : bVal - aVal
  })
}

async function savePlan() {
  const validBoms = selectedBoms.value.filter(b => b.quantity > 0)
  
  if (validBoms.length === 0) {
    await saveProductionPlan({
      date: formatDate(selectedDate.value),
      boms: [],
      multiplier: multiplier.value,
    })
    ElMessage.success('已清空该日期的生产计划')
    dialogVisible.value = false
    await loadPlanDates()
    return
  }

  saving.value = true
  try {
    const res = await saveProductionPlan({
      date: formatDate(selectedDate.value),
      boms: validBoms.map(b => ({
        bom_id: b.id,
        quantity: b.quantity,
      })),
      multiplier: multiplier.value,
    })
    if (res && res.has_shortage) {
      const shortageNames = (res.shortage_bom_names || []).join('、')
      ElMessage.warning(`保存成功，但库存不足！${shortageNames ? '缺料产品：' + shortageNames : ''}`)
    } else {
      ElMessage.success('保存成功')
    }
    dialogVisible.value = false
    await loadPlanDates()
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  isMounted.value = true
  getBomList({ pageNum: 1, pageSize: 999 }).then(res => {
    availableBoms.value = res.list || []
  })
  loadPlanDates()
})
</script>

<style scoped>
.app-container {
  padding: 20px;
}

.toolbar {
  max-width: 900px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--el-bg-color);
  border-radius: 4px;
  box-shadow: var(--el-box-shadow-light);
  border: 1px solid var(--el-border-color-lighter);
}

.toolbar-label {
  font-weight: 500;
  color: var(--el-text-color-primary);
  font-size: 14px;
}

.toolbar-hint {
  color: var(--el-text-color-regular);
  font-size: 12px;
  margin-left: auto;
}

.calendar-card {
  max-width: 900px;
  margin: 0 auto;
}

:deep(.el-calendar-table__row .el-calendar-table__cell) {
  height: 80px;
}

:deep(.el-calendar-table__row .el-calendar-table__cell .el-calendar-day) {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 80px;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 8px;
}

:deep(.el-calendar-table__row .el-calendar-table__cell .el-calendar-day:hover) {
  background-color: var(--el-fill-color-light, #f5f7fa);
}

:deep(.el-calendar-table__row .el-calendar-table__cell .el-calendar-day.past) {
  opacity: 0.4;
  cursor: not-allowed;
}

:deep(.el-calendar-table__row .el-calendar-table__cell .el-calendar-day.has-plan) {
  background-color: var(--el-color-success-light-9, #f0f9eb);
}

:deep(.el-calendar-table__row .el-calendar-table__cell .el-calendar-day.has-plan .date-number) {
  color: var(--el-color-success, #67c23a);
  font-weight: bold;
}

.calendar-date-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 80px;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 8px;
}

.calendar-date-cell:hover {
  background-color: var(--el-fill-color-light, #f5f7fa);
}

.calendar-date-cell.past {
  opacity: 0.4;
  cursor: not-allowed;
}

.calendar-date-cell.has-plan {
  background-color: var(--el-color-success-light-9, #f0f9eb);
}

.calendar-date-cell.has-plan .date-number {
  color: var(--el-color-success, #67c23a);
  font-weight: bold;
}

.calendar-date-cell.has-shortage {
  background-color: var(--el-color-danger-light-9, #fef0f0);
}

.calendar-date-cell.has-shortage .date-number {
  color: var(--el-color-danger, #f56c6c);
  font-weight: bold;
}

/* 库存缺料 - 红色 */
.calendar-date-cell.has-shortage-actual {
  background-color: var(--el-color-danger-light-9, #fef0f0);
}
.calendar-date-cell.has-shortage-actual .date-number {
  color: var(--el-color-danger, #f56c6c);
  font-weight: bold;
}
.calendar-date-cell.has-shortage-actual .plan-tag {
  color: var(--el-color-danger, #f56c6c);
  background-color: var(--el-color-danger-light-8, #fde2e2);
}

/* 计划缺料 - 橙色 */
.calendar-date-cell.has-shortage-plan {
  background-color: var(--el-color-warning-light-9, #faecd8);
}
.calendar-date-cell.has-shortage-plan .date-number {
  color: var(--el-color-warning, #e6a23c);
  font-weight: bold;
}
.calendar-date-cell.has-shortage-plan .plan-tag {
  color: var(--el-color-warning, #e6a23c);
  background-color: var(--el-color-warning-light-8, #faecd8);
}

/* 缺料警告 - 黄色 */
.calendar-date-cell.has-shortage-alert {
  background-color: var(--el-color-success-light-9, #f0f9eb);
}
.calendar-date-cell.has-shortage-alert .date-number {
  color: var(--el-color-success, #67c23a);
  font-weight: bold;
}
.calendar-date-cell.has-shortage-alert .plan-tag {
  color: var(--el-color-success, #67c23a);
  background-color: var(--el-color-success-light-8, #e1f3d8);
}

/* 标签颜色 */
.plan-tag.tag-actual {
  color: var(--el-color-danger, #f56c6c);
  background-color: var(--el-color-danger-light-8, #fde2e2);
}
.plan-tag.tag-plan {
  color: var(--el-color-warning, #e6a23c);
  background-color: var(--el-color-warning-light-8, #faecd8);
}
.plan-tag.tag-alert {
  color: var(--el-color-success, #67c23a);
  background-color: var(--el-color-success-light-8, #e1f3d8);
}

.date-number {
  font-size: 16px;
}

.plan-tag {
  font-size: 10px;
  color: var(--el-color-success, #67c23a);
  background-color: var(--el-color-success-light-8, #e8f5e9);
  padding: 2px 6px;
  border-radius: 4px;
  margin-top: 4px;
}

.has-shortage .plan-tag {
  color: var(--el-color-danger, #f56c6c);
  background-color: var(--el-color-danger-light-8, #fde2e2);
}

.calendar-date-cell.expired-plan {
  background-color: var(--el-color-gray-light-9, #f5f5f5);
  cursor: pointer !important;
}

.calendar-date-cell.expired-plan .date-number {
  color: var(--el-color-gray, #909399);
  font-weight: bold;
}

.expired-plan .plan-tag {
  color: var(--el-color-gray, #909399);
  background-color: var(--el-color-gray-light-8, #ebeef5);
}

/* 已过期标签 */
.plan-tag.tag-expired {
  color: var(--el-color-gray, #909399);
  background-color: var(--el-color-gray-light-8, #ebeef5);
}

/* 计划缺料计算信息 */
.plan-calc-info {
  font-size: 12px;
  line-height: 1.4;
  color: var(--el-color-text-regular, #606266);
}

.text-muted {
  color: var(--el-color-gray, #909399);
}

.plan-form :deep(.el-form-item__label) {
  font-weight: bold;
}

.bom-selection-list {
  max-height: 300px;
  overflow-y: auto;
}

.bom-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px;
  background-color: var(--el-bg-color-page, #f5f7fa);
  border-radius: 8px;
  margin-bottom: 10px;
}

.bom-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
}

.bom-model {
  font-weight: bold;
}

.bom-name {
  color: var(--el-text-color-secondary, #606266);
}

.bom-type {
  font-size: 12px;
  color: var(--el-text-color-placeholder, #909399);
}

.empty-tip {
  text-align: center;
  color: var(--el-text-color-placeholder, #909399);
  padding: 20px;
  background-color: var(--el-bg-color-page, #f5f7fa);
  border-radius: 8px;
}

.text-danger {
  color: var(--el-color-danger, #f56c6c) !important;
}

:deep(.el-dialog) {
  display: flex;
  flex-direction: column;
}

:deep(.el-dialog__body) {
  flex: 1;
  overflow: hidden;
  padding: 20px;
}

.plan-form {
  height: 100%;
  overflow-y: auto;
}

:deep(.el-table) {
  max-height: 400px;
  overflow-y: auto;
}

.text-danger {
  color: var(--el-color-danger, #f56c6c);
  font-weight: bold;
}

.text-warning {
  color: var(--el-color-warning, #e6a23c);
  font-weight: bold;
}

.text-success {
  color: var(--el-color-success, #67c23a);
  font-weight: bold;
}
</style>
