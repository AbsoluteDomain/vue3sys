import request from '@/utils/request'

export function getFinishProductList(params: any) {
  return request({
    url: '/api/v1/finish-product/list/',
    method: 'get',
    params
  })
}

export function getFinishProductDailyStats(params: {
  start_date: string
  end_date: string
}) {
  return request({
    url: '/api/v1/finish-product/daily-stats/',
    method: 'get',
    params
  })
}

export function getFinishProductBoardDetail(params: {
  category: string
  start_date?: string
  end_date?: string
  date?: string
  pageNum?: number
  pageSize?: number
}) {
  return request({
    url: '/api/v1/finish-product/board-detail/',
    method: 'get',
    params
  })
}

export function updateFinishProduct(data: {
  id: number
  sn_code?: string
  status?: number
  inventory_stock?: number
  repair?: number
  description?: string
  create_time?: string | null
  test_time?: string | null
  stock_in_time?: string | null
  stock_out_time?: string | null
}) {
  return request({
    url: '/api/v1/finish-product/update/',
    method: 'post',
    data
  })
}

export function rollbackFinishProduct(data: { id: number }) {
  return request({
    url: '/api/v1/finish-product/rollback/',
    method: 'post',
    data
  })
}
