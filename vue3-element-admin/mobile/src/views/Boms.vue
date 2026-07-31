<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { BomAPI, type Bom } from '@/api/bom'
import { showToast, showConfirmDialog } from 'vant'

const list = ref<Bom[]>([])
const loading = ref(false)
const finished = ref(false)
const page = ref(1)
const pageSize = ref(10)

async function loadData() {
  if (loading.value) return
  loading.value = true
  try {
    const res = await BomAPI.getList({
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
      message: '确定要删除这个BOM吗？',
    })
    await BomAPI.delete({ id })
    list.value = list.value.filter((item: Bom) => item.id !== id)
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
  <div class="boms-container">
    <van-nav-bar title="BOM管理" />
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
            :title="item.productName"
            :value="item.productCode"
            is-link
            @click="showToast(`BOM ID: ${item.id}`)"
          >
            <template #icon>
              <van-icon name="list-o" size="24" color="#07c160" />
            </template>
            <template #right-icon>
              <van-button size="mini" type="danger" plain @click.stop="handleDelete(item.id)">
                删除
              </van-button>
            </template>
            <template #label>
              <div class="bom-info">
                <span class="bom-quantity">数量: {{ item.quantity }}</span>
              </div>
            </template>
          </van-cell>
        </van-cell-group>
      </van-list>
    </van-pull-refresh>
    <div class="fab-btn">
      <van-button type="primary" round size="large" icon="plus" @click="showToast('添加BOM')">
        添加
      </van-button>
    </div>
  </div>
</template>

<style scoped>
.boms-container {
  min-height: 100vh;
  background: #f5f5f5;
}

.bom-info {
  margin-top: 8px;
}

.bom-quantity {
  font-size: 12px;
  color: #07c160;
}

.fab-btn {
  position: fixed;
  bottom: 30px;
  right: 20px;
}
</style>
