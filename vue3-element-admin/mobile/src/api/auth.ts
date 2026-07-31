import request from '@/utils/request'

const AUTH_BASE_URL = '/api/v1/auth'

export interface LoginRequest {
  username: string
  password: string
  captchaId?: string
  captchaCode?: string
  tenantId?: number
}

export interface LoginResponse {
  accessToken: string
  refreshToken: string
  expires: number
  user: {
    id: number
    username: string
    nickname: string
    avatar: string
  }
}

export const AuthAPI = {
  login(data: LoginRequest) {
    const payload: Record<string, any> = {
      username: data.username,
      password: data.password,
    }
    if (data.captchaId) payload.captchaId = data.captchaId
    if (data.captchaCode) payload.captchaCode = data.captchaCode
    if (data.tenantId !== undefined) payload.tenantId = data.tenantId
    return request<any, LoginResponse>({
      url: `${AUTH_BASE_URL}/login`,
      method: 'post',
      data: payload,
    })
  },
  refreshToken(refreshToken: string) {
    return request<any, LoginResponse>({
      url: `${AUTH_BASE_URL}/refresh-token`,
      method: 'post',
      params: { refreshToken },
    })
  },
  logout() {
    return request({
      url: `${AUTH_BASE_URL}/logout`,
      method: 'delete',
    })
  },
}
