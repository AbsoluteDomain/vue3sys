// src/api/product.ts
import request from '@/utils/request' // 引入框架封装的 axios 实例

// 1. 定义获取产品列表的接口
export function getProductList(params: any) {
  return request({
    url: '/api/v1/product/list/', // 对应后端的 /api/v1/product/list
    method: 'get',
    params // 如果后端需要分页参数（如 page, pageSize），在这里传递
  })
}

// 2. 定义新增产品的接口 (示例)
export function createProduct(data: any) {
  return request({
    url: '/api/v1/product/create/', // 对应后端的 /api/v1/product/create
    method: 'post',
    data
  })
}

export function editProduct(data: any) {
  return request({
    url: '/api/v1/product/update/', // 对应后端的 /api/v1/product/update
    method: 'post',
    data
  })
}

export function deleteProduct(data: any) {
  return request({
    url: '/api/v1/product/delete/', // 对应后端的 /api/v1/product/delete
    method: 'post',
    data
  })
}

export function adjustProductStock(data: { id: number; type: 'in' | 'out'; quantity: number }) {
  return request({
    url: '/api/v1/product/stock-adjust/',
    method: 'post',
    data
  })
}