<template>
  <el-drawer
    v-model="visible"
    :title="dialogTitle"
    size="44%"
    destroy-on-close
    @close="handleClose"
  >
    <div v-loading="loading">
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="90px">
        <el-form-item label="BOM型号" prop="bom_model">
          <el-input v-model="formData.bom_model" placeholder="请输入BOM型号" style="max-width: 400px" />
        </el-form-item>
        <el-form-item label="BOM名称" prop="bom_name">
          <el-input v-model="formData.bom_name" placeholder="请输入BOM名称（可选）" style="max-width: 400px" />
        </el-form-item>
        <el-form-item label="物料编码" prop="material_code">
          <el-input v-model="formData.material_code" placeholder="请输入物料编码（可选）" style="max-width: 400px" />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-radio-group v-model="formData.type">
            <el-radio :value="0">关节</el-radio>
            <el-radio :value="1">机械臂</el-radio>
            <el-radio :value="2">其他</el-radio>
          </el-radio-group>
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
              remote
              reserve-keyword
              clearable
              :remote-method="(query) => searchProducts(query, row)"
              :loading="row.productLoading"
              placeholder="输入名称或ID搜索"
              style="width: 100%"
              @visible-change="(opened) => onSelectVisible(opened, row)"
              @change="(val) => onProductChange(row, val)"
            >
              <el-option
                v-for="p in row.productOptions"
                :key="p.id"
                :label="formatProductLabel(p)"
                :value="p.id"
              />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.product_type !== null && row.product_type !== undefined && row.product_type !== ''"
              :type="productTypeTagType(row.product_type)"
              size="small"
            >
              {{ row.product_type_name || formatProductTypeLabel(row.product_type) }}
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
    </div>

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
import { formatProductTypeLabel, productTypeTagType } from '../../productInfo/productType'

const emit = defineEmits(['success'])

const PRODUCT_SEARCH_PAGE_SIZE = 50

const formRef = ref(null)
const visible = ref(false)
const loading = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const recipeLines = ref([])
const productCache = new Map()

const formData = reactive({
  id: null,
  bom_model: '',
  bom_name: '',
  material_code: '',
  type: 0
})

const formRules = {
  bom_model: [{ required: true, message: '请输入BOM型号', trigger: 'blur' }],
  type: [{ required: true, message: '请选择 BOM 类型', trigger: 'change' }]
}

const dialogTitle = computed(() => (isEdit.value ? '编辑 BOM' : '新增 BOM'))

const selectedProductIds = computed(
  () => new Set(recipeLines.value.map((line) => line.product_id).filter(Boolean))
)

const formatProductLabel = (product) => `${product.id} - ${product.name}`

const upsertProductCache = (products) => {
  products.forEach((product) => {
    productCache.set(product.id, product)
  })
}

const emptyLine = () => ({
  product_id: null,
  product_name: '',
  product_type: null,
  product_type_name: '',
  unit: '',
  quantity: 1,
  productOptions: [],
  productLoading: false
})

const buildProductOption = (productId, name, type, typeName, unit) => ({
  id: productId,
  name: name || String(productId),
  type: type ?? null,
  type_name: typeName || '',
  unit: unit || ''
})

const ensureRowOption = (row) => {
  if (!row.product_id) return
  const cached = productCache.get(row.product_id)
  if (cached && !row.productOptions.some((item) => item.id === row.product_id)) {
    row.productOptions = [cached, ...row.productOptions]
  }
}

const searchProducts = async (query, row) => {
  row.productLoading = true
  try {
    const params = { pageNum: 1, pageSize: PRODUCT_SEARCH_PAGE_SIZE }
    const keyword = (query || '').trim()
    if (/^\d+$/.test(keyword)) {
      params.productId = keyword
    } else if (keyword) {
      params.productName = keyword
    }
    const res = await getProductList(params)
    const list = res?.list || []
    upsertProductCache(list)
    const selected = selectedProductIds.value
    row.productOptions = list.filter(
      (product) => !selected.has(product.id) || product.id === row.product_id
    )
    ensureRowOption(row)
  } catch (error) {
    console.error(error)
  } finally {
    row.productLoading = false
  }
}

const onSelectVisible = (opened, row) => {
  if (opened && !row.productOptions.length) {
    searchProducts('', row)
  }
}

const applyProductToRow = (row, product) => {
  if (!product) return
  row.product_name = product.name
  row.product_type = product.type
  row.product_type_name = product.type_name || formatProductTypeLabel(product.type)
  row.unit = product.unit || ''
  productCache.set(product.id, product)
  if (!row.productOptions.some((item) => item.id === product.id)) {
    row.productOptions = [product, ...row.productOptions]
  }
}

const onProductChange = (row, productId) => {
  if (!productId) {
    row.product_name = ''
    row.product_type = null
    row.product_type_name = ''
    row.unit = ''
    return
  }
  const product =
    row.productOptions.find((item) => item.id === productId) ||
    productCache.get(productId)
  applyProductToRow(row, product)
}

const addRecipeLine = () => {
  recipeLines.value.push(emptyLine())
}

const removeRecipeLine = (index) => {
  recipeLines.value.splice(index, 1)
}

const mapRecipeToLine = (recipe) => {
  const productId = recipe.part_product_id || recipe.product_id
  const line = {
    product_id: productId || null,
    product_name: recipe.part_product_name || '',
    product_type: recipe.part_product_type ?? null,
    product_type_name: recipe.part_product_type_name || '',
    unit: recipe.part_unit || '',
    quantity: recipe.part_quantity ?? 1,
    productOptions: [],
    productLoading: false
  }
  if (productId) {
    const option = buildProductOption(
      productId,
      line.product_name,
      line.product_type,
      line.product_type_name,
      line.unit
    )
    line.productOptions = [option]
    productCache.set(productId, option)
  }
  return line
}

const resetForm = (row = {}) => {
  formData.id = row.id || null
  formData.bom_model = row.bom_model || ''
  formData.bom_name = row.bom_name || ''
  formData.material_code = row.material_code || ''
  formData.type = row.type ?? 0
  recipeLines.value = []
  isEdit.value = !!row.id
}

const open = async (row = {}) => {
  resetForm(row)
  visible.value = true

  if (!row.id) return

  loading.value = true
  try {
    const detail = await getBomDetail({ id: row.id })
    formData.bom_model = detail.bom_model || formData.bom_model
    formData.bom_name = detail.bom_name || ''
    formData.material_code = detail.material_code || ''
    formData.type = detail.type ?? 0
    recipeLines.value = (detail.recipes || []).map((recipe) => mapRecipeToLine(recipe))
  } catch (error) {
    console.error(error)
    ElMessage.error('加载 BOM 详情失败')
    visible.value = false
  } finally {
    loading.value = false
  }
}

const handleClose = () => {
  formRef.value?.resetFields()
  recipeLines.value = []
  productCache.clear()
}

const handleSubmit = () => {
  formRef.value.validate((valid) => {
    if (!valid) return

    const lines = recipeLines.value.filter((line) => line.product_id)
    if (!lines.length) {
      ElMessage.warning('请至少绑定一个产品零件')
      return
    }

    const payload = {
      id: formData.id,
      bom_model: formData.bom_model,
      bom_name: formData.bom_name || undefined,
      material_code: formData.material_code || undefined,
      type: formData.type,
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
