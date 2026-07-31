import { defineStore } from 'pinia'
import { ref } from 'vue'
import { AuthAPI, type LoginResponse } from '@/api/auth'
import { AuthStorage } from '@/utils/auth'

export const useUserStore = defineStore('user', () => {
  const userInfo = ref<LoginResponse['user'] | null>(null)
  const accessToken = ref<string>('')

  async function login(data: { username: string; password: string }) {
    const res = await AuthAPI.login(data)
    userInfo.value = res.user
    accessToken.value = res.accessToken
    AuthStorage.setAccessToken(res.accessToken)
    AuthStorage.setRefreshToken(res.refreshToken)
    return res
  }

  async function logout() {
    try {
      await AuthAPI.logout()
    } finally {
      userInfo.value = null
      accessToken.value = ''
      AuthStorage.clear()
    }
  }

  function loadFromStorage() {
    const token = AuthStorage.getAccessToken()
    if (token) {
      accessToken.value = token
    }
  }

  return {
    userInfo,
    accessToken,
    login,
    logout,
    loadFromStorage,
  }
})
