<template>
  <el-drawer
    v-model="visible"
    :title="dialogTitle"
    size="44%"
    destroy-on-close
    @close="handleClose"
  >
    <el-form ref="formRef" :model="formData" :rules="formRules" label-width="90px">
      <el-form-item label="BOM名称" prop="bom_name">
        <el-input v-model="formData.bom_name" placeholder="请输入 BOM 名称" style="max-width: 400px" />
      </el-form-item>
    </el-form>

    <div class="recipe-toolbar">
      <span class="recipe-title">绑定产品零件</span>
      <el-button type="primary" plain size="small" @click="addRecipeLine">
        <el-icon><Plus /></el-icon> 添加零件
      </el-button>
    </div>

    <el-table :data="recipeLines" border stripe max-height="660" empty-text="请添加产品零件">
      <el-table-column type="index" label="序号" width="60" align="center" />
      <el-table-column label="产品零件" min-width="280">
        <template #default="{ row }">
          <el-select
            v-model="row.product_id"
            filterable
            placeholder="从库存产品中选择"
            style="width: 100%"
            @change="(val) => onProductChange(row, val)"
          >
            <el-option
              v-for="p in availableProducts(row.product_id)"
              :key="p.id"
              :label="`${p.id} - ${p.name}`"
              :value="p.id"
            >
              <span>{{ p.id }} - {{ p.name }}</span>
              <el-tag :type="p.type === 'raw' ? 'success' : 'info'" size="small" style="margin-left: 8px">
                {{ p.type === 'raw' ? '原材料' : '组件' }}
              </el-tag>
            </el-option>
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="90" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.product_type" :type="row.product_type === 'raw' ? 'success' : 'info'" size="small">
            {{ row.product_type === 'raw' ? '原材料' : '组件' }}
          </el-tag>
          <span v-else class="text-muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="用量" width="140">
        <template #default="{ row }">
          <el-input-number
            v-model="row.quantity"
            :min="1"
            :step="1"
            controls-position="right"
            style="width: 100%"
          />
        </template>
      </el-table-column>
      <el-table-column label="单位" width="80">
        <template #default="{ row }">
          {{ row.unit || '—' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" align="center" fixed="right">
        <template #default="{ $index }">
          <el-button link type="danger" size="small" @click="removeRecipeLine($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <template #footer>
      <div style="flex: auto">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getProductList } from '@/api/product'
import { getBomDetail, createBom, updateBom } from '@/api/bom'

const emit = defineEmits(['success'])

const formRef = ref(null)
const visible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const productOptions = ref([])
const recipeLines = ref([])

const formData = reactive({
  id: null,
  bom_name: ''
})

const formRules = {
  bom_name: [{ required: true, message: '请输入 BOM 名称', trigger: 'blur' }]
}

const dialogTitle = computed(() => (isEdit.value ? '编辑 BOM' : '新增 BOM'))

const emptyLine = () => ({
  product_id: null,
  product_name: '',
  product_type: '',
  unit: '',
  quantity: 1
})

const loadProducts = () =>
  getProductList({ pageNum: 1, pageSize: 2000 }).then((res) => {
    productOptions.value = res?.list || []
  })

const availableProducts = (currentId) => {
  const selected = new Set(
    recipeLines.value.map((l) => l.product_id).filter((id) => id && id !== currentId)
  )
  return productOptions.value.filter((p) => !selected.has(p.id) || p.id === currentId)
}

const onProductChange = (row, productId) => {
  const product = productOptions.value.find((p) => p.id === productId)
  if (product) {
    row.product_name = product.name
    row.product_type = product.type
    row.unit = product.unit || ''
  }
}

const addRecipeLine = () => {
  recipeLines.value.push(emptyLine())
}

const removeRecipeLine = (index) => {
  recipeLines.value.splice(index, 1)
}

const mapRecipeToLine = (recipe) => ({
  product_id: recipe.part_product_id || recipe.product_id,
  product_name: recipe.part_product_name || '',
  product_type: recipe.part_product_type || '',
  unit: '',
  quantity: recipe.part_quantity ?? 1
})

const open = async (row = {}) => {
  formData.id = row.id || null
  formData.bom_name = row.bom_name || ''
  recipeLines.value = []
  isEdit.value = !!row.id

  await loadProducts()

  if (row.id) {
    try {
      const detail = await getBomDetail({ id: row.id })
      formData.bom_name = detail.bom_name || formData.bom_name
      recipeLines.value = (detail.recipes || []).map((r) => {
        const line = mapRecipeToLine(r)
        const p = productOptions.value.find((x) => x.id === line.product_id)
        if (p) line.unit = p.unit || ''
        return line
      })
    } catch {
      ElMessage.error('加载 BOM 详情失败')
      return
    }
  }

  visible.value = true
}

const handleClose = () => {
  formRef.value?.resetFields()
  recipeLines.value = []
}

const handleSubmit = () => {
  formRef.value.validate((valid) => {
    if (!valid) return

    const lines = recipeLines.value.filter((l) => l.product_id)
    if (!lines.length) {
      ElMessage.warning('请至少绑定一个产品零件')
      return
    }

    const payload = {
      id: formData.id,
      bom_name: formData.bom_name,
      recipes: lines.map((line) => ({
        product_id: line.product_id,
        quantity: line.quantity
      }))
    }

    submitting.value = true
    const apiMethod = isEdit.value ? updateBom : createBom
    const actionName = isEdit.value ? '保存' : '新增'

    apiMethod(payload)
      .then(() => {
        ElMessage.success(`${actionName}成功`)
        emit('success')
        visible.value = false
      })
      .catch(() => {
        ElMessage.error(`${actionName}失败`)
      })
      .finally(() => {
        submitting.value = false
      })
  })
}

defineExpose({ open })
</script>

<style scoped>
.recipe-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 8px 0 12px;
}
.recipe-title {
  font-weight: 600;
  font-size: 15px;
}
.text-muted {
  color: #909399;
}
</style>
