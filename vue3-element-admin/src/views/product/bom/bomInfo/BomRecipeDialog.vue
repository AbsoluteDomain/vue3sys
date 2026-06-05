<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="920px"
    destroy-on-close
    @closed="handleClosed"
  >
    <el-table
      v-loading="loading"
      :data="recipes"
      border
      stripe
      max-height="480"
      empty-text="暂无装配明细，请点击编辑绑定产品零件"
    >
      <el-table-column type="index" label="序号" width="60" align="center" />
      <el-table-column prop="id" label="明细ID" width="80" />
      <el-table-column prop="product_name" label="成品名称" min-width="120" show-overflow-tooltip />
      <el-table-column label="零件类型" width="90" align="center">
        <template #default="{ row }">
          <el-tag
            v-if="row.part_product_type"
            :type="row.part_product_type === 'raw' ? 'success' : 'info'"
            size="small"
          >
            {{ row.part_product_type === 'raw' ? '原材料' : '组件' }}
          </el-tag>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column prop="part_product_id" label="产品ID" width="85" />
      <el-table-column prop="part_product_name" label="产品名称" min-width="120" show-overflow-tooltip />
      <el-table-column prop="part_quantity" label="用量" width="80" align="right" />
      <el-table-column prop="updated_at" label="更新时间" width="165" />
    </el-table>
    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button type="primary" @click="handleEdit">编辑 BOM</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { getBomDetail } from '@/api/bom'

const emit = defineEmits(['edit'])

const visible = ref(false)
const loading = ref(false)
const bomHeader = ref(null)
const recipes = ref([])

const dialogTitle = computed(() => {
  if (!bomHeader.value) return 'BOM 装配明细'
  return `BOM 装配明细 — ${bomHeader.value.bom_name}（共 ${recipes.value.length} 条）`
})

const open = (row) => {
  if (!row?.id) return
  bomHeader.value = { id: row.id, bom_name: row.bom_name }
  recipes.value = []
  visible.value = true
  loading.value = true
  getBomDetail({ id: row.id })
    .then((data) => {
      bomHeader.value = data
      recipes.value = data?.recipes || []
    })
    .catch(() => {
      ElMessage.error('加载装配明细失败')
      visible.value = false
    })
    .finally(() => {
      loading.value = false
    })
}

const handleEdit = () => {
  if (bomHeader.value) {
    emit('edit', bomHeader.value)
    visible.value = false
  }
}

const handleClosed = () => {
  bomHeader.value = null
  recipes.value = []
}

defineExpose({ open })
</script>
