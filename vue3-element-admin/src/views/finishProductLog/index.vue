<template>
  <div class="app-container">
    <el-card shadow="never" class="welcome-card">
      <div class="welcome">
        <el-icon class="welcome-icon"><Tickets /></el-icon>
        <div class="welcome-text">
          <h2 class="welcome-title">成品操作记录</h2>
          <p class="welcome-desc">页面已创建，后续具体功能将在此基础上开发。</p>
        </div>
        <el-tag type="success" effect="light" size="large" round>
          页面已接入导航
        </el-tag>
      </div>
    </el-card>

    <el-card shadow="never" class="placeholder-card">
      <el-empty description="功能开发中，敬请期待">
        <template #image>
          <el-icon :size="80" color="var(--el-color-primary-light-5)">
            <Document />
          </el-icon>
        </template>
        <el-button type="primary" @click="goDashboard">
          <el-icon><HomeFilled /></el-icon>
          返回首页
        </el-button>
      </el-empty>
    </el-card>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Tickets, Document, HomeFilled } from '@element-plus/icons-vue'

defineOptions({
  name: 'FinishProductLog'
})

const router = useRouter()

const goDashboard = () => {
  router.push('/dashboard')
}
</script>

<style scoped>
.app-container {
  padding: 20px;
}
.welcome-card {
  margin-bottom: 20px;
}
.welcome {
  display: flex;
  align-items: center;
  gap: 16px;
}
.welcome-icon {
  font-size: 48px;
  color: var(--el-color-primary);
}
.welcome-text {
  flex: 1;
}
.welcome-title {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.welcome-desc {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}
.placeholder-card {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
