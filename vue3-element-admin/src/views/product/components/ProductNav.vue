<template>
  <el-card shadow="never" class="product-nav-card">
    <el-radio-group :model-value="activePath" @change="onNavChange">
      <el-radio-button value="/product/index">库存管理</el-radio-button>
      <el-radio-button value="/product/productBom">产品BOM管理</el-radio-button>
    </el-radio-group>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const activePath = computed(() => {
  if (route.path.includes('productBom') || route.path.includes('/bom')) {
    return '/product/productBom'
  }
  return '/product/index'
})

const onNavChange = (path) => {
  if (path && path !== route.path) {
    router.push(path)
  }
}
</script>

<style scoped>
.product-nav-card {
  margin-bottom: 16px;
}
.product-nav-card :deep(.el-card__body) {
  padding: 12px 16px;
}
</style>
