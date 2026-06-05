<template>
  <div class="app-container">
    <product-nav />

    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="queryParams" class="search-form">
        <el-form-item label="BOM ID">
          <el-input
            v-model="queryParams.bomId"
            placeholder="ID"
            clearable
            style="width: 100px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="BOM名称">
          <el-input
            v-model="queryParams.bomName"
            placeholder="bom_name"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="resetQuery">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="toolbar">
        <el-button type="success" @click="handleAdd">
          <el-icon><Plus /></el-icon> 新增 BOM
        </el-button>
        <el-button type="warning" @click="handleAssemble">
          <el-icon><Box /></el-icon> 组装产品
        </el-button>
      </div>

      <el-table
        :data="tableData"
        border
        stripe
        style="width: 100%"
        height="500"
        v-loading="loading"
        highlight-current-row
        class="bom-main-table"
        @sort-change="handleSortChange"
        @row-click="handleRowClick"
      >
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="id" label="BOM ID" sortable="custom" width="90" />
        <el-table-column prop="bom_name" label="BOM名称" sortable="custom" min-width="200" show-overflow-tooltip />
        <el-table-column prop="recipe_count" label="明细条数" width="100" align="center" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="handleViewRecipes(row)">
              查看明细
            </el-button>
            <el-button link type="warning" size="small" @click.stop="handleAssembleRow(row)">
              组装
            </el-button>
            <el-button link type="primary" size="small" @click.stop="handleEdit(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button link type="danger" size="small" @click.stop="handleDelete(row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <bom-list-form ref="formRef" @success="getList" />
      <bom-recipe-dialog ref="recipeDialogRef" @edit="handleEdit" />
      <bom-assemble-dialog ref="assembleDialogRef" @success="getList" />

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="queryParams.pageNum"
          v-model:page-size="queryParams.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getBomList, deleteBom } from '@/api/bom'
import { Search, Refresh, Plus, Edit, Delete, Box } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ProductNav from '../components/ProductNav.vue'
import BomListForm from './bomInfo/BomListForm.vue'
import BomRecipeDialog from './bomInfo/BomRecipeDialog.vue'
import BomAssembleDialog from './bomInfo/BomAssembleDialog.vue'

const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  bomId: '',
  bomName: '',
  sortProp: '',
  sortOrder: ''
})

const formRef = ref(null)
const recipeDialogRef = ref(null)
const assembleDialogRef = ref(null)
const tableData = ref([])
const loading = ref(false)
const total = ref(0)

const getList = () => {
  loading.value = true
  const params = {
    pageNum: queryParams.pageNum,
    pageSize: queryParams.pageSize,
    bomName: queryParams.bomName,
    sortProp: queryParams.sortProp,
    sortOrder: queryParams.sortOrder,
    bomId: queryParams.bomId || undefined,
    id: queryParams.bomId || undefined
  }
  getBomList(params)
    .then((response) => {
      tableData.value = response?.list || []
      total.value = response?.total || 0
    })
    .catch(() => {
      ElMessage.error('获取 BOM 列表失败')
    })
    .finally(() => {
      loading.value = false
    })
}

const handleSearch = () => {
  queryParams.pageNum = 1
  getList()
}

const resetQuery = () => {
  queryParams.bomId = ''
  queryParams.bomName = ''
  queryParams.pageNum = 1
  getList()
}

const handleSizeChange = (val) => {
  queryParams.pageSize = val
  getList()
}

const handleCurrentChange = (val) => {
  queryParams.pageNum = val
  getList()
}

const handleSortChange = ({ prop, order }) => {
  queryParams.sortProp = prop || ''
  queryParams.sortOrder = order || ''
  queryParams.pageNum = 1
  getList()
}

const handleAdd = () => formRef.value?.open()
const handleEdit = (row) => formRef.value?.open(row)
const handleAssemble = () => assembleDialogRef.value?.open()
const handleAssembleRow = (row) => assembleDialogRef.value?.open(row)
const handleViewRecipes = (row) => recipeDialogRef.value?.open(row)
const handleRowClick = (row) => recipeDialogRef.value?.open(row)

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除 BOM「${row.bom_name}」吗？`, '警告', { type: 'warning' })
    .then(() => deleteBom({ id: row.id }))
    .then(() => {
      ElMessage.success('删除成功')
      getList()
    })
    .catch(() => {})
}

onMounted(() => getList())
</script>

<style scoped>
.app-container {
  padding: 20px;
}
.search-card {
  margin-bottom: 20px;
}
.search-form {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}
.table-card {
  margin-bottom: 20px;
}
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
}
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.bom-main-table :deep(.el-table__body tr) {
  cursor: pointer;
}
</style>
