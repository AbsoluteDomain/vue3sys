import request from '@/utils/request'

export interface Product {
  id: number
  name: string
  code: string
  type: string
  unit: string
  stock: number
  price: number
  createTime: string
}

export const ProductAPI = {
  getList(params: { page?: number; pageSize?: number; keyword?: string }) {
    return request<any, { list: Product[]; total: number }>({
      url: '/api/v1/product/list/',
      method: 'get',
      params,
    })
  },
  create(data: any) {
    return request({
      url: '/api/v1/product/create/',
      method: 'post',
      data,
    })
  },
  update(data: any) {
    return request({
      url: '/api/v1/product/update/',
      method: 'post',
      data,
    })
  },
  delete(data: { id: number }) {
    return request({
      url: '/api/v1/product/delete/',
      method: 'post',
      data,
    })
  },
}
