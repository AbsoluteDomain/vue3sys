<template>
  <!-- 
    v-model 控制显示/隐藏
    title 动态显示 "新增" 或 "编辑"
    destroy-on-close 关闭时销毁内容（重置表单状态）
  -->
  <el-drawer
    v-model="visible"
    :title="dialogTitle"
    size="500px"
    destroy-on-close
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="80px"
    >
      <el-form-item label="产品名称" prop="name">
        <el-input v-model="formData.name" placeholder="请输入产品名称" />
      </el-form-item>

      <el-form-item label="图号" prop="draw_code">
        <el-input v-model="formData.draw_code" placeholder="请输入图号（可选）" />
      </el-form-item>

      <el-form-item label="物料编码" prop="material_code">
        <el-input v-model="formData.material_code" placeholder="请输入物料编码（可选）" />
      </el-form-item>

      <el-form-item label="类型" prop="type">
        <el-select v-model="formData.type" placeholder="请选择类型" style="width: 100%">
          <el-option
            v-for="item in PRODUCT_TYPE_OPTIONS"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="数量" prop="quantity">
        <el-input-number v-model="formData.quantity" :min="0" style="width: 100%" />
      </el-form-item>

      <el-form-item label="单位" prop="unit">
        <el-input v-model="formData.unit" placeholder="如：个、台、kg" />
      </el-form-item>

      <el-form-item label="库位" prop="location">
        <el-input v-model="formData.location" placeholder="请输入库位" />
      </el-form-item>
      
      <el-form-item label="预警库存" prop="alert_quantity">
        <el-input-number v-model="formData.alert_quantity" :min="0" />
      </el-form-item>

      <el-form-item label="备注" prop="description">
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="3"
          placeholder="请输入备注"
        />
      </el-form-item>
    </el-form>

    <!-- 底部按钮 -->
    <template #footer>
      <div style="flex: auto">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { createProduct, editProduct } from '@/api/product'
import { PRODUCT_TYPE_OPTIONS } from './productType'
const emit = defineEmits(['success']) // 用于通知父组件刷新列表
const formRef = ref(null)
const visible = ref(false) // 控制抽屉显示
const isEdit = ref(false)  // 标记是新增还是编辑

// 表单数据
const formData = reactive({
  id: null,
  name: '',
  draw_code: '',
  material_code: '',
  type: 0,
  quantity: 0,
  unit: '',
  location: '',
  alert_quantity: 0,
  description: ''
})

// 表单校验规则
const formRules = {
  name: [{ required: true, message: '请输入产品名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  quantity: [{ required: true, message: '请输入数量', trigger: 'blur' }],
  unit: [{ required: true, message: '请输入单位', trigger: 'blur' }]
}

// 动态标题
const dialogTitle = computed(() => (isEdit.value ? '编辑产品' : '新增产品'))

// 打开抽屉
const open = (row = {}) => {
  // 重置表单
  Object.assign(formData, {
    id: null,
    name: '',
    draw_code: '',
    material_code: '',
    type: 0,
    quantity: 0,
    unit: '',
    location: '',
    alert_quantity: 0,
    description: ''
  })
  
  if (row.id) {
    isEdit.value = true
    Object.assign(formData, row)
    formData.type = Number(row.type ?? 0)
  } else {
    // 新增
    isEdit.value = false
  }
  visible.value = true
}

// 关闭回调
const handleClose = () => {
  formRef.value?.resetFields()
}

// 提交
const handleSubmit = () => {
  formRef.value.validate((valid) => {
    if (valid) {
      // 根据 isEdit 状态选择 API
      const apiMethod = isEdit.value ? editProduct : createProduct
      const actionName = isEdit.value ? '修改' : '新增'

      // 调用接口
      apiMethod(formData)
        .then(() => {
          // request.ts 在 code=00000 时会直接 resolve data
          ElMessage.success(`${actionName}成功`)
          emit('success') // 通知父组件刷新列表
          visible.value = false // 关闭抽屉
        })
        .catch((error) => {
          console.error(error)
          ElMessage.error(`${actionName}失败，请联系管理员`)
        })
    }
  })
}

// 暴露 open 方法给父组件
defineExpose({ open })
</script>