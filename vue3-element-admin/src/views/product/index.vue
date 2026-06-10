<template>
  <div class="app-container">
    <!-- <product-nav /> -->
    <!-- 搜索区域 -->
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="queryParams" class="search-form">
        <el-form-item label="产品ID">
          <el-input
            v-model="queryParams.productId"
            placeholder="产品ID"
            clearable
            style="width: 140px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="产品名称">
          <el-input
            v-model="queryParams.productName"
            placeholder="产品名称"
            clearable
            style="width: 200px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="是否报警">
          <el-select
            v-model="queryParams.isAlert"
            placeholder="全部"
            clearable
            style="width: 120px"
            @change="handleSearch"
            @clear="handleSearch"
          >
            <el-option label="是" value="1" />
            <el-option label="否" value="0" />
          </el-select>
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

    <!-- 表格区域 -->
    <el-card shadow="never" class="table-card">
      <div class="toolbar">
        <el-button type="success" @click="handleAdd">
          <el-icon><Plus /></el-icon> 新增
        </el-button>
      </div>

      <!-- 表格 -->
      <el-table
        :data="tableData"
        border
        stripe
        style="width: 100%"
        height="500"
        v-loading="loading"
        :row-class-name="getRowClassName"
        @sort-change="handleSortChange"
      >
        <el-table-column type="index" label="序号" width="60" align="center" />
        
        <!-- ⚠️ 这里对应后端的字段名 -->
        <el-table-column prop="id" label="产品ID" sortable="custom" width="100" />
        <el-table-column prop="name" label="产品名称" sortable="custom" min-width="150" show-overflow-tooltip />
        <el-table-column
          prop="type"
          class-name="col-product-type"
          label="类型"
          sortable="custom"
          width="100"
        >
          <template #default="{ row }">
            <el-tag :type="row.type === 'raw' ? 'success' : 'info'" size="small">
              {{ row.type === 'raw' ? '原材料' : '组件' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <!-- 数量 -->
        <el-table-column prop="quantity" label="数量" sortable="custom" width="100" align="right">
           <template #default="{ row }">
             {{ row.quantity }} {{ row.unit }}
           </template>
        </el-table-column>

        <el-table-column prop="alert_quantity" label="报警数量" sortable="custom" width="120" />
        
        <!-- 状态 (假设后端有 status 字段，如果没有可删除) -->
        <!-- <el-table-column prop="status" label="状态" sortable width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column> -->

        <!-- 更新时间 -->
        <el-table-column prop="updated_at" label="更新时间" sortable="custom" width="180" />

        <el-table-column
          class-name="col-product-actions"
          label="操作"
          width="300"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button link type="success" size="small" @click="handleStockIn(row)">入库</el-button>
            <el-button link type="warning" size="small" @click="handleStockOut(row)">出库</el-button>
            <el-button link type="primary" size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <productForm ref="formRef" @success="getList" />
      <stock-adjust-dialog ref="stockDialogRef" @success="getList" />
      <!-- 分页器 -->
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
// import { getProductList } from '@/api/product' // 引入接口
import { getProductList, deleteProduct } from '@/api/product' // 引入 deleteProduct
import { Search, Refresh, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
// 1. 引入 Drawer 组件
import productForm from './productInfo/ProductForm.vue'
import StockAdjustDialog from './productInfo/StockAdjustDialog.vue'
// import ProductNav from './components/ProductNav.vue'

// 1. 定义响应式数据
const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  productId: '',
  productName: '',
  isAlert: '',
  sortProp: '',
  sortOrder: ''
})
const formRef = ref(null) // 用于操作子组件的 ref
const stockDialogRef = ref(null)
const tableData = ref([]) // 表格数据
const loading = ref(false) // 加载状态
const total = ref(0) // 总条数
// 2. 获取数据的方法

const getList = () => {
  loading.value = true
  getProductList(queryParams)
    .then(response => {
      // request.ts 在 code=00000 时返回的是后端 data 字段
      tableData.value = response?.list || []
      total.value = response?.total || 0
    })
    .catch(error => {
      console.error('获取数据失败', error)
      ElMessage.error('获取数据失败')
    })
    .finally(() => {
      loading.value = false
    })
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确定删除产品 "${row.name}" 吗？`, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    // 调用删除接口
    // 注意：你的 deleteProduct 接收 data 对象，所以传 { id: row.id }
    deleteProduct({ id: row.id })
      .then(() => {
        ElMessage.success('删除成功')
        getList() // 刷新列表
      })
      .catch(() => {
        ElMessage.error('删除操作发生错误')
      })
  }).catch(() => {})
}

// 3. 搜索
const handleSearch = () => {
  queryParams.pageNum = 1
  getList()
}

// 4. 重置
const resetQuery = () => {
  queryParams.productId = ''
  queryParams.productName = ''
  queryParams.isAlert = ''
  queryParams.pageNum = 1
  getList()
}

// 5. 分页处理
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

/** 报警数量 >= 数量时整行标红 */
const getRowClassName = ({ row }) => {
  const q = row.quantity
  const a = row.alert_quantity
  if (a == null || a === '') return ''
  if (q == null || q === '') return ''
  if (Number(a) >= Number(q)) {
    return 'row-quantity-alert'
  }
  return ''
}

// 3. 修改按钮点击事件
const handleAdd = () => {
  // 打开抽屉，不传参数表示新增
  formRef.value.open()
}
const handleEdit = (row) => {
  // 打开抽屉，传入 row 数据表示编辑
  formRef.value.open(row)
}
const handleStockIn = (row) => stockDialogRef.value?.open(row, 'in')
const handleStockOut = (row) => stockDialogRef.value?.open(row, 'out')



// 初始化
onMounted(() => {
  getList()
})
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
}
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* 报警数量 ≥ 数量时：除「类型」「操作」外列文字为红色 */
:deep(
  .el-table__body
    tr.row-quantity-alert
    > td:not(.col-product-type):not(.col-product-actions)
) {
  color: #ff0000;
}
:deep(
  .el-table__body
    tr.row-quantity-alert:hover
    > td:not(.col-product-type):not(.col-product-actions)
) {
  color: #ff0000;
}
</style>