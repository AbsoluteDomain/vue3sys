import axios, { type InternalAxiosRequestConfig } from 'axios'
import { showToast } from 'vant'
import { AuthStorage, redirectToLogin } from './auth'

const retriedConfigs = new WeakSet<InternalAxiosRequestConfig>()

const http = axios.create({
  timeout: 30000,
  headers: { 'Content-Type': 'application/json;charset=utf-8' },
})

http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = AuthStorage.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

http.interceptors.response.use(
  (response) => {
    const { code, data, msg } = response.data
    if (code === 200) {
      return data
    }
    showToast(msg || '系统出错')
    return Promise.reject(new Error(msg || '系统出错'))
  },
  async (error) => {
    const { config, response } = error
    if (!response) {
      showToast('网络连接失败')
      return Promise.reject(error)
    }
    const { code, msg } = response.data
    if (code === 401) {
      if (retriedConfigs.has(config)) {
        await redirectToLogin()
        return Promise.reject(new Error('Token Invalid'))
      }
      retriedConfigs.add(config)
      try {
        const refreshToken = AuthStorage.getRefreshToken()
        if (refreshToken) {
          const res = await http.post('/api/v1/auth/refresh-token', null, {
            params: { refreshToken },
          })
          AuthStorage.setAccessToken(res.data.accessToken)
          AuthStorage.setRefreshToken(res.data.refreshToken)
          config.headers.Authorization = `Bearer ${res.data.accessToken}`
          return http(config)
        }
      } catch {
        await redirectToLogin()
        return Promise.reject(new Error('Token refresh failed'))
      }
    }
    showToast(msg || '请求失败')
    return Promise.reject(new Error(msg || '请求失败'))
  }
)

export default http
