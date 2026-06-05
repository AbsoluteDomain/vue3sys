import request from '@/utils/request'

export function getOperationLogList(params: any) {
  return request({
    url: '/api/v1/operation-logs/list/',
    method: 'get',
    params
  })
}
