<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import { showToast } from 'vant'

const router = useRouter()
const userStore = useUserStore()

const menuItems = [
  { icon: 'goods-o', label: '产品管理', path: '/products', color: '#1989fa' },
  { icon: 'list-o', label: 'BOM管理', path: '/boms', color: '#07c160' },
]

async function handleLogout() {
  try {
    await userStore.logout()
    showToast('已退出登录')
    await router.push({ name: 'Login' })
  } catch (error) {
    showToast('退出失败')
  }
}

onMounted(() => {
  userStore.loadFromStorage()
})
</script>

<template>
  <div class="home-container">
    <van-nav-bar title="首页" fixed />
    <div class="content">
      <div class="user-card">
        <div class="avatar-wrap">
          <van-icon name="user-o" size="48" color="#fff" />
        </div>
        <div class="user-info">
          <p class="username">{{ userStore.userInfo?.nickname || userStore.userInfo?.username || '用户' }}</p>
          <p class="user-id">ID: {{ userStore.userInfo?.id }}</p>
        </div>
      </div>
      <div class="menu-grid">
        <van-grid :column-num="2" :border="false">
          <van-grid-item
            v-for="item in menuItems"
            :key="item.path"
            :icon="item.icon"
            :text="item.label"
            :icon-color="item.color"
            @click="router.push(item.path)"
          />
        </van-grid>
      </div>
      <div class="logout-btn-wrap">
        <van-button type="default" block @click="handleLogout">
          退出登录
        </van-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-container {
  min-height: 100vh;
  background: #f5f5f5;
}

.content {
  padding: 80px 20px 20px;
}

.user-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.avatar-wrap {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-info {
  flex: 1;
}

.username {
  font-size: 20px;
  font-weight: bold;
  color: #fff;
  margin: 0 0 8px;
}

.user-id {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
}

.menu-grid {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 20px;
}

.logout-btn-wrap {
  padding-top: 20px;
}
</style>
