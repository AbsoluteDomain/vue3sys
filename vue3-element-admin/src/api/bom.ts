import request from '@/utils/request'

export function getBomList(params: any) {
  return request({
    url: '/api/v1/bom/list/',
    method: 'get',
    params
  })
}

export function getBomDetail(params: { id: number }) {
  return request({
    url: '/api/v1/bom/detail/',
    method: 'get',
    params
  })
}

export function getBomExport(params: any) {
  return request({
    url: '/api/v1/bom/export/',
    method: 'get',
    params
  })
}

export function importBomBatch(data: { items: any[] }) {
  return request({
    url: '/api/v1/bom/import/',
    method: 'post',
    data
  })
}

/** 单条导入（兼容） */
export function importBom(data: { item: any }) {
  return importBomBatch({ items: [data.item] })
}

export function createBom(data: any) {
  return request({
    url: '/api/v1/bom/create/',
    method: 'post',
    data
  })
}

export function updateBom(data: any) {
  return request({
    url: '/api/v1/bom/update/',
    method: 'post',
    data
  })
}

export function deleteBom(data: { id: number }) {
  return request({
    url: '/api/v1/bom/delete/',
    method: 'post',
    data
  })
}

export function assembleBom(data: { bom_id: number; quantity: number }) {
  return request({
    url: '/api/v1/bom/assemble/',
    method: 'post',
    data
  })
}
