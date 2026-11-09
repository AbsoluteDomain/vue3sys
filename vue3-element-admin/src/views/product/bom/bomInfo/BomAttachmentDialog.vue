<template>
  <el-dialog
    v-model="visible"
    :title="`BOM 附件 - ${bomLabel}`"
    width="960px"
    destroy-on-close
    @closed="handleClosed"
  >
    <div class="attachment-toolbar">
      <el-upload
        :show-file-list="false"
        accept=".xls,.xlsx"
        :before-upload="(file) => beforeUpload('excel', file)"
        :http-request="(options) => handleUpload('excel', options)"
      >
        <el-button
          v-hasPerm="'product:bom:create'"
          type="primary"
          size="small"
          :loading="uploadingType === 'excel'"
        >
          <el-icon><Upload /></el-icon> 上传 Excel
        </el-button>
      </el-upload>

      <el-upload
        :show-file-list="false"
        accept=".pdf"
        :before-upload="(file) => beforeUpload('pdf', file)"
        :http-request="(options) => handleUpload('pdf', options)"
      >
        <el-button
          v-hasPerm="'product:bom:create'"
          type="warning"
          size="small"
          :loading="uploadingType === 'pdf'"
        >
          <el-icon><Upload /></el-icon> 上传 PDF
        </el-button>
      </el-upload>

      <el-upload
        :show-file-list="false"
        accept=".urdf,.zip"
        :before-upload="(file) => beforeUpload('urdf', file)"
        :http-request="(options) => handleUpload('urdf', options)"
      >
        <el-button
          v-hasPerm="'product:bom:create'"
          type="success"
          size="small"
          :loading="uploadingType === 'urdf'"
        >
          <el-icon><Upload /></el-icon> 上传 URDF
        </el-button>
      </el-upload>

      <span class="attachment-tip">URDF 支持 .urdf 或包含 urdf+meshes 的 .zip 包</span>
    </div>

    <el-table
      :data="attachments"
      border
      stripe
      style="width: 100%"
      v-loading="loading"
      max-height="420"
    >
      <el-table-column label="类型" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="typeTag(row.file_type)" size="small">
            {{ typeLabel(row.file_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="file_name" label="文件名" min-width="240" show-overflow-tooltip />
      <el-table-column label="大小" width="100" align="right">
        <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column prop="uploader_name" label="上传人" width="110" />
      <el-table-column prop="created_at" label="上传时间" width="170" />
      <el-table-column label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.file_type === 'pdf'"
            link
            type="primary"
            size="small"
            @click="handlePreview(row)"
          >
            查看
          </el-button>
          <el-button
            v-if="row.file_type === 'urdf'"
            link
            type="primary"
            size="small"
            @click="handleViewUrdf(row)"
          >
            查看
          </el-button>
          <el-button link type="success" size="small" @click="handleDownload(row)">
            下载
          </el-button>
          <el-button
            v-hasPerm="'product:bom:delete'"
            link
            type="danger"
            size="small"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>

  <urdf-viewer-dialog ref="urdfViewerRef" />
</template>

<script setup>
import { ref, computed } from 'vue'
import { Upload } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getBomAttachments,
  uploadBomAttachment,
  deleteBomAttachment,
} from '@/api/bom'
import UrdfViewerDialog from './UrdfViewerDialog.vue'

const MAX_SIZE_MB = { excel: 20, pdf: 20, urdf: 50 }
const TYPE_LABELS = { excel: 'Excel', pdf: 'PDF', urdf: 'URDF' }
const TYPE_TAGS = { excel: 'success', pdf: 'warning', urdf: 'primary' }

const visible = ref(false)
const loading = ref(false)
const uploadingType = ref('')
const attachments = ref([])
const bom = ref(null)
const urdfViewerRef = ref(null)

const bomLabel = computed(() => {
  if (!bom.value) return ''
  return bom.value.bom_name
    ? `${bom.value.bom_model}(${bom.value.bom_name})`
    : bom.value.bom_model || String(bom.value.id)
})

const typeLabel = (fileType) => TYPE_LABELS[fileType] || fileType
const typeTag = (fileType) => TYPE_TAGS[fileType] || 'info'

const formatSize = (bytes) => {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const open = (row) => {
  bom.value = row
  visible.value = true
  loadAttachments()
}

const loadAttachments = () => {
  if (!bom.value?.id) return
  loading.value = true
  getBomAttachments({ bom_id: bom.value.id })
    .then((data) => {
      attachments.value = data?.list || []
    })
    .catch(() => {})
    .finally(() => {
      loading.value = false
    })
}

const beforeUpload = (fileType, file) => {
  const limitMb = MAX_SIZE_MB[fileType] || 20
  if (file.size > limitMb * 1024 * 1024) {
    ElMessage.warning(`文件大小不能超过 ${limitMb}MB`)
    return false
  }
  return true
}

const handleUpload = (fileType, options) => {
  const formData = new FormData()
  formData.append('bom_id', bom.value.id)
  formData.append('file_type', fileType)
  formData.append('file', options.file)

  uploadingType.value = fileType
  return uploadBomAttachment(formData)
    .then(() => {
      ElMessage.success('上传成功')
      loadAttachments()
    })
    .catch(() => {})
    .finally(() => {
      uploadingType.value = ''
    })
}

const handlePreview = (row) => {
  window.open(row.file_url, '_blank')
}

const handleViewUrdf = (row) => {
  urdfViewerRef.value?.openUrl(row.file_url, row.file_name)
}

const handleDownload = (row) => {
  const link = document.createElement('a')
  link.href = row.file_url
  link.target = '_blank'
  link.download = row.file_name
  link.click()
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除附件「${row.file_name}」吗？`, '警告', { type: 'warning' })
    .then(() => deleteBomAttachment({ id: row.id }))
    .then(() => {
      ElMessage.success('删除成功')
      loadAttachments()
    })
    .catch(() => {})
}

const handleClosed = () => {
  attachments.value = []
  bom.value = null
}

defineExpose({ open })
</script>

<style lang="scss" scoped>
.attachment-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;

  :deep(.el-upload) {
    display: inline-flex;
  }
}

.attachment-tip {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
