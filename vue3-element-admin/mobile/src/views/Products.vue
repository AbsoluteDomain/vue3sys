<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ProductAPI, type Product } from '@/api/product'
import { showToast, showConfirmDialog } from 'vant'

const list = ref<Product[]>([])
const loading = ref(false)
const finished = ref(false)
const page = ref(1)
const pageSize = ref(10)

async function loadData() {
  if (loading.value) return
  loading.value = true
  try {
    const res = await ProductAPI.getList({
      page: page.value,
      pageSize: pageSize.value,
    })
    if (res.list.length === 0) {
      finished.value = true
    } else {
      list.value = [...list.value, ...res.list]
      page.value++
    }
  } catch (error: any) {
    showToast(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await showConfirmDialog({
      title: '确认删除',
      message: '确定要删除这个产品吗？',
    })
    await ProductAPI.delete({ id })
    list.value = list.value.filter((item: Product) => item.id !== id)
    showToast('删除成功')
  } catch {
    showToast('已取消')
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="products-container">
    <van-nav-bar title="产品管理" />
    <van-pull-refresh @refresh="loadData">
      <van-list
        v-model:loading="loading"
        v-model:finished="finished"
        :finished-text="list.length ? '没有更多了' : '暂无数据'"
        @load="loadData"
      >
        <van-cell-group v-if="list.length">
          <van-cell
            v-for="item in list"
            :key="item.id"
            :title="item.name"
            :value="item.code"
            is-link
            @click="showToast(`产品ID: ${item.id}`)"
          >
            <template #icon>
              <van-icon name="goods-o" size="24" color="#1989fa" />
            </template>
            <template #right-icon>
              <van-button size="mini" type="danger" plain @click.stop="handleDelete(item.id)">
                删除
              </van-button>
            </template>
            <template #label>
              <div class="product-info">
                <span class="product-type">{{ item.type }}</span>
                <span class="product-stock">库存: {{ item.stock }}</span>
              </div>
            </template>
          </van-cell>
        </van-cell-group>
      </van-list>
    </van-pull-refresh>
    <div class="fab-btn">
      <van-button type="primary" round size="large" icon="plus" @click="showToast('添加产品')">
        添加
      </van-button>
    </div>
  </div>
</template>

<style scoped>
.products-container {
  min-height: 100vh;
  background: #f5f5f5;
}

.product-info {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.product-type {
  font-size: 12px;
  color: #999;
}

.product-stock {
  font-size: 12px;
  color: #1989fa;
}

.fab-btn {
  position: fixed;
  bottom: 30px;
  right: 20px;
}
</style>
