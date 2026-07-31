import request from '@/utils/request'

export interface Bom {
  id: number
  productCode: string
  productName: string
  quantity: number
  createTime: string
}

export const BomAPI = {
  getList(params: { page?: number; pageSize?: number; keyword?: string }) {
    return request<any, { list: Bom[]; total: number }>({
      url: '/api/v1/bom/list/',
      method: 'get',
      params,
    })
  },
  getDetail(params: { id: number }) {
    return request<any, Bom>({
      url: '/api/v1/bom/detail/',
      method: 'get',
      params,
    })
  },
  create(data: any) {
    return request({
      url: '/api/v1/bom/create/',
      method: 'post',
      data,
    })
  },
  update(data: any) {
    return request({
      url: '/api/v1/bom/update/',
      method: 'post',
      data,
    })
  },
  delete(data: { id: number }) {
    return request({
      url: '/api/v1/bom/delete/',
      method: 'post',
      data,
    })
  },
}
