<template>
  <el-dialog
    v-model="visible"
    title="组装产品"
    width="640px"
    destroy-on-close
    @closed="handleClosed"
  >
    <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
      <el-form-item label="选择 BOM" prop="bom_id">
        <el-select
          v-model="formData.bom_id"
          filterable
          placeholder="请选择 BOM"
          style="width: 100%"
          :disabled="bomLocked"
          @change="loadPreview"
        >
          <el-option
            v-for="item in bomOptions"
            :key="item.id"
            :label="formatBomLabel(item)"
            :value="item.id"
            :disabled="!item.recipe_count"
          >
            <span>{{ formatBomLabel(item) }}</span>
            <span v-if="!item.recipe_count" style="color: #f56c6c; margin-left: 8px">（无明细）</span>
          </el-option>
        </el-select>
      </el-form-item>
      <el-form-item label="组装数量" prop="quantity">
        <el-input-number
          v-model="formData.quantity"
          :min="1"
          :step="1"
          controls-position="right"
          style="width: 200px"
          @change="loadPreview"
        />
      </el-form-item>
    </el-form>

    <div v-if="previewLines.length" class="preview-block">
      <div class="preview-title">将消耗以下库存：</div>
      <el-table :data="previewLines" border stripe size="small" max-height="280">
        <el-table-column prop="product_name" label="产品名称" min-width="140" show-overflow-tooltip />
        <el-table-column label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.product_type === 'raw' ? 'success' : 'info'" size="small">
              {{ row.product_type === 'raw' ? '原材料' : '组件' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="per_unit" label="单套用量" width="90" align="right" />
        <el-table-column prop="required" label="合计消耗" width="90" align="right" />
        <el-table-column prop="stock" label="当前库存" width="90" align="right">
          <template #default="{ row }">
            <span :class="{ 'stock-warn': row.stock < row.required }">{{ row.stock }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button
          type="success"
          plain
          :disabled="!previewLines.length"
          @click="handleExportExcel"
        >
          导出 Excel
        </el-button>
        <div class="dialog-footer-actions">
          <el-button @click="visible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">确定组装</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ExcelJS from 'exceljs'
import { getBomList, getBomDetail, assembleBom } from '@/api/bom'
import { getProductList } from '@/api/product'

const emit = defineEmits(['success'])

const formRef = ref(null)
const visible = ref(false)
const submitting = ref(false)
const bomLocked = ref(false)
const bomOptions = ref([])
const productStockMap = ref({})
const previewLines = ref([])
const currentRecipes = ref([])

const formData = reactive({
  bom_id: null,
  quantity: 1
})

const formRules = {
  bom_id: [{ required: true, message: '请选择 BOM', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入组装数量', trigger: 'blur' }]
}

const formatBomLabel = (item) => {
  if (!item) return ''
  const namePart = item.bom_name ? ` / ${item.bom_name}` : ''
  return `${item.id} - ${item.bom_model || ''}${namePart}`
}

const formatBomShortLabel = (item) => {
  if (!item) return ''
  if (item.bom_name) return `${item.bom_model}(${item.bom_name})`
  return item.bom_model || String(item.id)
}

const getSelectedBom = () => bomOptions.value.find((b) => b.id === formData.bom_id)

const formatNow = () => {
  const now = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
}

const saveXlsx = (buffer, fileName) => {
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=utf-8'
  })
  const downloadUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(downloadUrl)
}

const handleExportExcel = async () => {
  if (!formData.bom_id) {
    ElMessage.warning('请先选择 BOM')
    return
  }
  if (!previewLines.value.length) {
    ElMessage.warning('暂无库存消耗明细可导出')
    return
  }

  const bom = getSelectedBom()
  const bomLabel = bom ? `${bom.id}-${bom.bom_model}` : String(formData.bom_id)
  const qty = formData.quantity || 1

  try {
    const workbook = new ExcelJS.Workbook()
    const worksheet = workbook.addWorksheet('组装预览')

    worksheet.addRow(['组装产品预览'])
    worksheet.addRow(['BOM', bom ? formatBomLabel(bom) : formData.bom_id])
    if (bom?.bom_model) {
      worksheet.addRow(['BOM型号', bom.bom_model])
    }
    if (bom?.bom_name) {
      worksheet.addRow(['BOM名称', bom.bom_name])
    }
    if (bom?.material_code) {
      worksheet.addRow(['物料编码', bom.material_code])
    }
    if (bom?.type_name) {
      worksheet.addRow(['BOM类型', bom.type_name])
    }
    worksheet.addRow(['组装数量', qty])
    worksheet.addRow(['导出时间', formatNow()])
    worksheet.addRow([])

    const headerRow = worksheet.addRow([
      '产品名称',
      '类型',
      '单套用量',
      '合计消耗',
      '当前库存',
      '库存状态'
    ])
    headerRow.font = { bold: true }
    headerRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFF5F7FA' }
    }

    previewLines.value.forEach((row) => {
      worksheet.addRow([
        row.product_name,
        row.product_type === 'raw' ? '原材料' : '组件',
        row.per_unit,
        row.required,
        row.stock,
        row.stock < row.required ? '库存不足' : '充足'
      ])
    })

    worksheet.columns = [
      { width: 24 },
      { width: 12 },
      { width: 12 },
      { width: 12 },
      { width: 12 },
      { width: 12 }
    ]

    const buffer = await workbook.xlsx.writeBuffer()
    const safeName = bomLabel.replace(/[\\/:*?"<>|]/g, '_')
    saveXlsx(buffer, `BOM组装预览_${safeName}_${qty}套.xlsx`)
    ElMessage.success('导出成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('导出 Excel 失败')
  }
}

const loadBomOptions = () =>
  getBomList({ pageNum: 1, pageSize: 2000 }).then((res) => {
    bomOptions.value = res?.list || []
  })

const loadProductStock = () =>
  getProductList({ pageNum: 1, pageSize: 2000 }).then((res) => {
    const map = {}
    ;(res?.list || []).forEach((p) => {
      map[p.id] = p.quantity ?? 0
    })
    productStockMap.value = map
  })

const buildPreview = () => {
  const qty = formData.quantity || 1
  const agg = {}
  currentRecipes.value.forEach((r) => {
    const pid = r.part_product_id
    if (!pid) return
    const perUnit = r.part_quantity || 0
    const required = perUnit * qty
    if (agg[pid]) {
      agg[pid].required += required
    } else {
      agg[pid] = {
        product_id: pid,
        product_name: r.part_product_name,
        product_type: r.part_product_type,
        per_unit: perUnit,
        required,
        stock: productStockMap.value[pid] ?? 0
      }
    }
  })
  previewLines.value = Object.values(agg)
}

const loadPreview = async () => {
  previewLines.value = []
  currentRecipes.value = []
  if (!formData.bom_id) return
  try {
    const detail = await getBomDetail({ id: formData.bom_id })
    currentRecipes.value = detail?.recipes || []
    buildPreview()
  } catch {
    ElMessage.error('加载 BOM 明细失败')
  }
}

const open = async (row = null) => {
  formData.bom_id = row?.id || null
  formData.quantity = 1
  bomLocked.value = !!row?.id
  previewLines.value = []
  currentRecipes.value = []
  visible.value = true
  await Promise.all([loadBomOptions(), loadProductStock()])
  if (formData.bom_id) {
    await loadPreview()
  }
}

const handleClosed = () => {
  formRef.value?.resetFields()
  formData.bom_id = null
  formData.quantity = 1
  bomLocked.value = false
  previewLines.value = []
  currentRecipes.value = []
}

const handleSubmit = () => {
  formRef.value.validate((valid) => {
    if (!valid) return
    if (!previewLines.value.length) {
      ElMessage.warning('该 BOM 没有可组装的零件明细')
      return
    }
    const insufficient = previewLines.value.filter((l) => l.stock < l.required)
    if (insufficient.length) {
      ElMessage.warning(`「${insufficient[0].product_name}」库存不足，无法组装`)
      return
    }

    const bom = getSelectedBom()
    const bomLabel = bom ? formatBomShortLabel(bom) : formData.bom_id

    ElMessageBox.confirm(
      `确定按 BOM「${bomLabel}」组装 ${formData.quantity} 套？将扣减对应零件库存。`,
      '确认组装',
      { type: 'warning' }
    )
      .then(() => {
        submitting.value = true
        return assembleBom({
          bom_id: formData.bom_id,
          quantity: formData.quantity
        })
      })
      .then(() => {
        ElMessage.success('组装成功，已生成成品并扣减库存')
        emit('success')
        visible.value = false
      })
      .catch(() => {})
      .finally(() => {
        submitting.value = false
      })
  })
}

defineExpose({ open })
</script>

<style scoped>
.preview-block {
  margin-top: 8px;
}
.preview-title {
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #606266;
}
.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.dialog-footer-actions {
  display: flex;
  gap: 8px;
}
.stock-warn {
  color: #f56c6c;
  font-weight: 600;
}
</style>
