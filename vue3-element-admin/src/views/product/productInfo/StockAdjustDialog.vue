<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="420px"
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
import { adjustProductStock } from '@/api/product'

const emit = defineEmits(['success'])

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const stockType = ref('in')
const productId = ref(null)
const productName = ref('')
const currentStock = ref(null)
const unit = ref('')

const formData = reactive({
  quantity: 1
})

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
  stockType.value = type
  productId.value = row.id
  productName.value = row.name
  currentStock.value = row.quantity ?? 0
  unit.value = row.unit || ''
  formData.quantity = 1
  visible.value = true
}

const handleClosed = () => {
  formRef.value?.resetFields()
  formData.quantity = 1
}

const handleSubmit = () => {
  formRef.value.validate((valid) => {
    if (!valid) return
    if (stockType.value === 'out' && formData.quantity > (currentStock.value ?? 0)) {
      ElMessage.warning('出库数量不能大于当前库存')
      return
    }
    submitting.value = true
    adjustProductStock({
      id: productId.value,
      type: stockType.value,
      quantity: formData.quantity
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
  color: #909399;
  font-size: 13px;
}
</style>
