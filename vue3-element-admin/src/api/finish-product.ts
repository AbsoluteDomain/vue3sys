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
  bom_type?: string
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
  bom_type?: string
}) {
  return request({
    url: '/api/v1/finish-product/board-detail/',
    method: 'get',
    params
  })
}

export function createFinishProduct(data: {
  bom_id: number
  sn_code?: string
  status?: number
  inventory_stock?: number
  repair?: number
  description?: string
  parent_sn_code?: string
  create_time?: string | null
  test_time?: string | null
  stock_in_time?: string | null
  stock_out_time?: string | null
}) {
  return request({
    url: '/api/v1/finish-product/create/',
    method: 'post',
    data
  })
}

export function updateFinishProduct(data: {
  id: number
  sn_code?: string
  status?: number
  inventory_stock?: number
  repair?: number
  description?: string
  warehouse_log_description?: string
  parent_sn_code?: string
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

export function checkJointStockConsistency() {
  return request({
    url: '/api/v1/finish-product/check-joint-consistency/',
    method: 'get'
  })
}

export function bindJointsToArm(data: {
  arm_id: number
  arm_sn_code: string
  joint_ids: number[]
}) {
  return request({
    url: '/api/v1/finish-product/bind-joints/',
    method: 'post',
    data
  })
}

export function getWarehouseLogList(params: {
  pageNum?: number
  pageSize?: number
  sn_code?: string
  material_code?: string
  storage_status?: number | string
  start_date?: string
  end_date?: string
}) {
  return request({
    url: '/api/v1/finish-product/warehouse-log/list/',
    method: 'get',
    params
  })
}

// ==================== 不合格项 API ====================

export function getUnqualifiedItems(params: {
  finish_product_id?: number | string
  sn_code?: string
}) {
  return request({
    url: '/api/v1/finish-product/unqualified/list/',
    method: 'get',
    params
  })
}

export function saveUnqualifiedItems(data: {
  finish_product_id: number
  sn_code?: string
  unqualified_values: number[]
}) {
  return request({
    url: '/api/v1/finish-product/unqualified/save/',
    method: 'post',
    data
  })
}

export function deleteUnqualifiedItem(id: number) {
  return request({
    url: '/api/v1/finish-product/unqualified/delete/',
    method: 'post',
    data: { id }
  })
}

export function addUnqualifiedItem(data: {
  finish_product_id: number
  sn_code?: string
  unqualified_value: number
}) {
  return request({
    url: '/api/v1/finish-product/unqualified/add/',
    method: 'post',
    data
  })
}

// ==================== 关节测试报表 API ====================

export function getJointTestReport(params: {
  start_date: string
  end_date: string
  bom_ids?: string
}) {
  return request({
    url: '/api/v1/finish-product/joint-test-report/',
    method: 'get',
    params
  })
}
