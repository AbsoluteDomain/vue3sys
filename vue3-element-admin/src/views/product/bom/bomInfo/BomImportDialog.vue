<template>
  <el-dialog
    v-model="visible"
    title="导入 BOM"
    width="760px"
    destroy-on-close
    @closed="handleClosed"
  >
    <div class="import-tip">
      支持在一个 Excel 中导入多个 BOM，每个 BOM 由「BOM基本信息」+「零件明细」组成，块与块之间空一行分隔。
      字段与「新增 BOM」一致；零件只需填写产品 ID 或物料编码；导入时逐条提交，成功的会入库。
    </div>

    <div class="import-actions">
      <el-button type="primary" plain @click="handleDownloadTemplate">下载导入模板</el-button>
      <div class="import-upload-row">
        <el-upload
          ref="uploadRef"
          class="import-upload"
          :auto-upload="false"
          :limit="1"
          accept=".xlsx"
          :show-file-list="true"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
        >
          <el-button type="success">选择 Excel 文件</el-button>
        </el-upload>
      </div>
    </div>

    <el-table
      v-if="previewItems.length"
      :data="previewItems"
      border
      stripe
      max-height="320"
      class="preview-table"
    >
      <el-table-column type="index" label="序号" width="60" align="center" />
      <el-table-column prop="bom_model" label="BOM型号" min-width="120" show-overflow-tooltip />
      <el-table-column prop="bom_name" label="BOM名称" min-width="120" show-overflow-tooltip />
      <el-table-column prop="material_code" label="物料编码" min-width="110" show-overflow-tooltip />
      <el-table-column label="类型" width="90" align="center">
        <template #default="{ row }">{{ bomTypeLabel(row.type) }}</template>
      </el-table-column>
      <el-table-column label="明细条数" width="90" align="center">
        <template #default="{ row }">{{ row.recipes?.length || 0 }}</template>
      </el-table-column>
    </el-table>

    <div v-if="importResult" class="import-result">
      <el-alert
        :title="importResult.msg"
        :type="importResult.fail_count ? 'warning' : 'success'"
        show-icon
        :closable="false"
      />
      <el-table
        v-if="importResult.fail_list?.length"
        :data="importResult.fail_list"
        border
        stripe
        max-height="180"
        class="fail-table"
      >
        <el-table-column prop="index" label="序号" width="70" align="center" />
        <el-table-column prop="bom_model" label="BOM型号" min-width="140" show-overflow-tooltip />
        <el-table-column prop="msg" label="失败原因" min-width="220" show-overflow-tooltip />
      </el-table>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button type="primary" :loading="submitting" :disabled="!previewItems.length" @click="handleImport">
        开始导入
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { importBomBatch } from '@/api/bom'
import {
  downloadBomImportTemplate,
  parseBomExcelFile
} from './bomExcel'

const emit = defineEmits(['success'])

const visible = ref(false)
const submitting = ref(false)
const uploadRef = ref(null)
const previewItems = ref([])
const importResult = ref(null)

const bomTypeLabel = (type) => {
  if (type === 1) return '机械臂'
  if (type === 2) return '其他'
  return '关节'
}

const open = () => {
  previewItems.value = []
  importResult.value = null
  visible.value = true
}

const handleClosed = () => {
  previewItems.value = []
  importResult.value = null
  uploadRef.value?.clearFiles()
}

const handleDownloadTemplate = async () => {
  try {
    await downloadBomImportTemplate()
    ElMessage.success('模板下载成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('模板下载失败')
  }
}

const handleFileChange = async (uploadFile) => {
  importResult.value = null
  if (!uploadFile?.raw) return
  try {
    previewItems.value = await parseBomExcelFile(uploadFile.raw)
    ElMessage.success(`已解析 ${previewItems.value.length} 条 BOM`)
  } catch (error) {
    previewItems.value = []
    uploadRef.value?.clearFiles()
    ElMessage.error(error?.message || 'Excel 解析失败')
  }
}

const handleFileRemove = () => {
  previewItems.value = []
  importResult.value = null
}

const handleImport = async () => {
  if (!previewItems.value.length) {
    ElMessage.warning('请先选择并解析 Excel 文件')
    return
  }

  submitting.value = true
  try {
    const result = await importBomBatch({ items: previewItems.value })
    const successCount = result?.success_count || 0
    const failCount = result?.fail_count || 0
    const msg = failCount
      ? `导入完成：成功 ${successCount} 条，失败 ${failCount} 条`
      : `导入成功，共 ${successCount} 条`
    importResult.value = {
      msg,
      fail_count: failCount,
      fail_list: result?.fail_list || []
    }
    if (successCount) {
      emit('success')
    }
    if (!failCount) {
      ElMessage.success(msg)
      visible.value = false
    } else if (successCount) {
      ElMessage.warning(msg)
    } else {
      ElMessage.error(msg)
    }
  } catch (error) {
    console.error(error)
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.import-tip {
  margin-bottom: 12px;
  color: #909399;
  font-size: 13px;
  line-height: 1.6;
}
.import-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.import-upload-row {
  display: flex;
  align-items: center;
  min-height: 32px;
}
.import-upload-row :deep(.import-upload) {
  display: inline-flex;
  align-items: center;
}
.import-upload-row :deep(.el-upload-list) {
  margin: 0 0 0 12px;
}
.import-upload-row :deep(.el-upload-list__item) {
  margin-top: 0;
}
.preview-table {
  margin-bottom: 12px;
}
.import-result {
  margin-top: 12px;
}
.fail-table {
  margin-top: 12px;
}
</style>
