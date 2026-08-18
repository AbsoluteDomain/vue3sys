// src/api/order.ts
import axios from 'axios'
import request from '@/utils/request'

// 外部订单系统接口基地址
// 开发环境：通过 vite 代理到 http://172.20.45.143:35203
// 生产环境：通过 Nginx 代理到 http://172.20.45.143:35203
const EXTERNAL_ORDER_BASE_URL = '/ext-order'

// 外部接口专用 axios 实例（不带认证 header，不经过本系统响应拦截器）
const externalHttp = axios.create({
  baseURL: EXTERNAL_ORDER_BASE_URL,
  timeout: 60000
})

// 外部接口错误拦截：提取可读的错误信息
externalHttp.interceptors.response.use(
  (response) => response,
  (error) => {
    let msg = '请求外部接口失败'
    if (error.code === 'ECONNABORTED') {
      msg = `请求外部接口超时（${60000 / 1000}秒）`
    } else if (error.response) {
      const status = error.response.status
      const errData = error.response.data
      const detail = typeof errData === 'string'
        ? errData
        : (errData?.message || errData?.error || errData?.msg || JSON.stringify(errData))
      msg = `外部接口返回错误（${status}）：${detail}`
    } else if (error.message) {
      msg = error.message
    }
    return Promise.reject(new Error(msg))
  }
)

// 将外部接口返回的数据统一为列表格式
function normalizeOrderList(data: any): any[] {
  if (Array.isArray(data)) return data
  if (data && typeof data === 'object') {
    // 尝试常见的列表字段名
    for (const key of ['data', 'list', 'orders', 'results', 'items']) {
      const val = data[key]
      if (Array.isArray(val)) return val
      if (val && typeof val === 'object') return [val]
    }
    // 单个订单对象
    if (data.order_no || data.orderNo || data.contract_no || data.product_name) {
      return [data]
    }
  }
  return []
}

// ==================== 数据库查询（走本系统后端） ====================

// 获取订单列表（数据库）
export function getOrderList(params: any) {
  return request({
    url: '/api/v1/order/list/',
    method: 'get',
    params
  })
}

// ==================== 外部接口（直接调用 172.20.45.143:35203） ====================

// 健康检查
// GET http://172.20.45.143:35203/api/health
export function orderHealthCheck() {
  return externalHttp.get('/api/health').then((res) => res.data)
}

// 全量查询（支持可选时间段）
// GET http://172.20.45.143:35203/api/orders
// GET http://172.20.45.143:35203/api/orders?start_date=2026-08-01&end_date=2026-08-06
export function orderSyncAll(params?: { start_date?: string; end_date?: string }) {
  return externalHttp
    .get('/api/orders', { params })
    .then((res) => {
      const list = normalizeOrderList(res.data)
      return { list, total: list.length }
    })
}

// 查询当天
// GET http://172.20.45.143:35203/api/orders/today
export function orderSyncToday() {
  return externalHttp.get('/api/orders/today').then((res) => {
    const list = normalizeOrderList(res.data)
    return { list, total: list.length }
  })
}

// 增量查询（日期拼接到URL）
// GET http://172.20.45.143:35203/api/orders/since/2026-08-01
export function orderSyncSince(sinceDate: string) {
  return externalHttp.get(`/api/orders/since/${sinceDate}`).then((res) => {
    const list = normalizeOrderList(res.data)
    return { list, total: list.length }
  })
}

// 按订单号查询（订单号拼接到URL最后）
// GET http://172.20.45.143:35203/api/orders/SO20260801001
export function orderByNo(orderNo: string) {
  return externalHttp.get(`/api/orders/${orderNo}`).then((res) => {
    const list = normalizeOrderList(res.data)
    return { list, total: list.length }
  })
}
