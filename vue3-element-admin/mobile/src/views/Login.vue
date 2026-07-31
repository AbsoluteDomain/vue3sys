<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import { showToast } from 'vant'

const router = useRouter()
const userStore = useUserStore()

const username = ref('')
const password = ref('')
const loading = ref(false)

async function handleLogin() {
  if (!username.value.trim()) {
    showToast('请输入用户名')
    return
  }
  if (!password.value.trim()) {
    showToast('请输入密码')
    return
  }
  loading.value = true
  try {
    await userStore.login({
      username: username.value.trim(),
      password: password.value.trim(),
    })
    showToast('登录成功')
    await router.push({ name: 'Home' })
  } catch (error: any) {
    showToast(error.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-header">
      <div class="logo">
        <span class="logo-icon">📦</span>
        <h1 class="logo-text">产品管理系统</h1>
        <p class="logo-subtitle">移动端</p>
      </div>
    </div>
    <div class="login-form">
      <van-cell-group inset>
        <van-field
          v-model="username"
          placeholder="请输入用户名"
          left-icon="user-o"
          clearable
        />
        <van-field
          v-model="password"
          type="password"
          placeholder="请输入密码"
          left-icon="lock"
          clearable
          show-eye
        />
      </van-cell-group>
      <div class="login-btn-wrap">
        <van-button
          type="primary"
          block
          :loading="loading"
          @click="handleLogin"
        >
          登录
        </van-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
}

.logo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 64px;
}

.logo-text {
  font-size: 28px;
  font-weight: bold;
  color: #fff;
  margin: 0;
}

.logo-subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
}

.login-form {
  background: #fff;
  border-radius: 16px;
  padding: 30px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.login-btn-wrap {
  margin-top: 24px;
}
</style>
