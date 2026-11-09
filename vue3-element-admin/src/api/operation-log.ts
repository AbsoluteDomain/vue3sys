import request from '@/utils/request'

export function getOperationLogList(params: any) {
  return request({
    url: '/api/v1/operation-logs/list/',
    method: 'get',
    params
  })
}

/** 审批记录（逐条动作） */
export interface ApprovalRecord {
  requestId: number
  /** 动作类型：submit-提交 approve-同意 reject-拒绝 execute-执行成功 execute_failed-执行失败 */
  type: "submit" | "approve" | "reject" | "execute" | "execute_failed"
  typeName: string
  /** 操作人 */
  actor: string
  /** 功能名称 */
  name: string
  targetName: string
  summary: string
  /** 审批意见或执行结果说明 */
  detail: string
  time: string
  /** 关联申请单当前状态：0-待审批 1-已通过 2-已驳回 3-执行失败 */
  status: number
  statusName: string
  executeError: string
}

export function getApprovalRecordList(params: any) {
  return request({
    url: '/api/v1/operation-logs/approval-records/',
    method: 'get',
    params
  })
}
