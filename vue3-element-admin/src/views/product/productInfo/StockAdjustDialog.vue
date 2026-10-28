<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="480px"
    destroy-on-close
    @closed="handleClosed"
  >
    <el-form ref="formRef" :model="formData" :rules="formRules" label-width="90px">
      <el-form-item label="产品">
        <span>{{ productName }}</span>
        <span v-if="currentStock !== null" class="stock-hint">
          （当前库存：{{ currentStock }}{{ unit ? ` ${unit}` : '' }}）
        </span>
      </el-form-item>
      <el-form-item :label="quantityLabel" prop="quantity">
        <el-input-number
          v-model="formData.quantity"
          :min="1"
          :max="stockType === 'out' ? maxOutbound : undefined"
          :step="1"
          controls-position="right"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item v-if="stockType === 'out'" label="出库类型" prop="stockOutType">
        <el-radio-group v-model="formData.stockOutType">
          <el-radio
            v-for="option in outboundTypeOptions"
            :key="option.value"
            :value="option.value"
          >
            {{ option.label }}
          </el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="描述" prop="description">
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="3"
          maxlength="500"
          show-word-limit
          placeholder="请输入出入库描述（选填）"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button :type="stockType === 'in' ? 'success' : 'warning'" :loading="submitting" @click="handleSubmit">
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { adjustProductStock, createWarehouseLog } from '@/api/product'
import { useDictStore } from '@/store'

const emit = defineEmits(['success'])
const dictStore = useDictStore()

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const stockType = ref('in')
const productId = ref(null)
const productName = ref('')
const currentStock = ref(null)
const unit = ref('')
const materialCode = ref('')

const formData = reactive({
  quantity: 1,
  description: '',
  stockOutType: '2' // 默认外销
})

// 出库类型读字典（排除入库、组件消耗及系统专用类型）
const OUTBOUND_EXCLUDED_VALUES = new Set([1, 4, 5, 6, 7])
const outboundTypeOptions = computed(() =>
  dictStore
    .getDictItems('warehouse_log_type')
    .map(item => ({ label: item.label, value: String(item.value) }))
    .filter(item => !OUTBOUND_EXCLUDED_VALUES.has(Number(item.value)))
)
const defaultOutboundType = computed(() => outboundTypeOptions.value[0]?.value || '2')

const formRules = {
  quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }]
}

const dialogTitle = computed(() => (stockType.value === 'in' ? '产品入库' : '产品出库'))
const quantityLabel = computed(() => (stockType.value === 'in' ? '入库数量' : '出库数量'))
const maxOutbound = computed(() => {
  if (currentStock.value === null || currentStock.value < 1) return 1
  return currentStock.value
})

const open = (row, type) => {
  dictStore.loadDictItems('warehouse_log_type')
  stockType.value = type
  productId.value = row.id
  productName.value = row.name
  currentStock.value = row.quantity ?? 0
  unit.value = row.unit || ''
  materialCode.value = row.material_code || ''
  formData.quantity = 1
  formData.description = ''
  formData.stockOutType = defaultOutboundType.value
  visible.value = true
}

const handleClosed = () => {
  formRef.value?.resetFields()
  formData.quantity = 1
  formData.description = ''
  formData.stockOutType = defaultOutboundType.value
}

const handleSubmit = () => {
  formRef.value.validate((valid) => {
    if (!valid) return
    if (stockType.value === 'out' && formData.quantity > (currentStock.value ?? 0)) {
      ElMessage.warning('出库数量不能大于当前库存')
      return
    }
    submitting.value = true
    // 入库=1，出库(外销)=2，出库(研发)=3
    const storageStatus = stockType.value === 'in' ? 1 : parseInt(formData.stockOutType, 10)
    const desc = formData.description.trim()
    const warehouseLogData = {
      name: productName.value,
      material_code: materialCode.value?.trim() || undefined,
      storage_status: storageStatus,
      count: formData.quantity,
      user_description: desc || undefined
    }
    adjustProductStock({
      id: productId.value,
      type: stockType.value,
      quantity: formData.quantity
    })
      .then(() => {
        return createWarehouseLog(warehouseLogData)
      })
      .then(() => {
        ElMessage.success(stockType.value === 'in' ? '入库成功' : '出库成功')
        emit('success')
        visible.value = false
      })
      .catch(() => {
        ElMessage.error(stockType.value === 'in' ? '入库失败' : '出库失败')
      })
      .finally(() => {
        submitting.value = false
      })
  })
}

defineExpose({ open })
</script>

<style scoped>
.stock-hint {
  margin-left: 8px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
