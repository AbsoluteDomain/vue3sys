import request from "@/utils/request";

/** 审批配置 */
export interface ApprovalConfig {
  id: number;
  /** 业务类型编码 */
  biz_type: string;
  /** 权限标识 */
  perm_code: string;
  /** 按钮权限对应的菜单ID */
  menu_id: number | null;
  /** 表格行唯一键 */
  row_key: string;
  /** 节点类型：catalog-目录 menu-模块 button-按钮权限 */
  node_type: "catalog" | "menu" | "button";
  /** 功能名称 */
  name: string;
  /** 审核状态：1-已启用 0-未启用 */
  enabled: number;
  /** 审批模式：single-单人审批（或签） multi-多人审批（会签） */
  approval_mode: "single" | "multi";
  /** 审批模式名称 */
  approval_mode_name: string;
  /** 审核人ID */
  approver_ids: number[];
  /** 审核人名称（逗号分隔） */
  approver_names: string;
  /** 最近修改人 */
  editor_name: string;
  /** 更新时间 */
  updated_at: string;
  /** 子节点（模块/权限项） */
  children?: ApprovalConfig[];
  /** 已启用审核项数量（目录/模块节点） */
  enabled_count?: number;
  /** 审核项总数（目录/模块节点） */
  total?: number;
}

/** 审批配置更新参数 */
export interface ApprovalConfigForm {
  enabled: number;
  approval_mode: "single" | "multi";
  approver_ids: number[];
}

/** 审批配置首次保存参数（配置行尚未创建时使用） */
export interface ApprovalConfigCreateForm extends ApprovalConfigForm {
  perm_code: string;
  menu_id: number;
  name: string;
}

/** 审批申请单审核人 */
export interface ApprovalTaskApprover {
  approver_id: number;
  approver_name: string;
  /** 审批结果：0-待处理 1-同意 2-拒绝 */
  decision: number;
  decision_name: string;
  comment: string;
  decided_at: string;
}

/** 审批申请单 */
export interface ApprovalTask {
  id: number;
  biz_type: string;
  /** 功能名称（入库/出库） */
  name: string;
  target_id: number;
  target_name: string;
  /** 申请内容摘要 */
  summary: string;
  applicant_id: number;
  applicant_name: string;
  approval_mode: "single" | "multi";
  approval_mode_name: string;
  /** 审批状态：0-待审批 1-已通过 2-已驳回 3-执行失败 */
  status: number;
  status_name: string;
  execute_error: string;
  created_at: string;
  finished_at: string;
  approvers: ApprovalTaskApprover[];
  my_decision: number | null;
  can_decide: boolean;
}

/** 我的审批查询参数 */
export interface ApprovalTaskQuery {
  scope: "pending" | "mine" | "processed";
  pageNum: number;
  pageSize: number;
}

/** 审批历史事件 */
export interface ApprovalHistoryEvent {
  /** 事件类型：submit-提交 approve-同意 reject-拒绝 execute-执行成功 execute_failed-执行失败 */
  type: "submit" | "approve" | "reject" | "execute" | "execute_failed";
  type_name: string;
  /** 操作人 */
  actor: string;
  /** 意见或执行结果说明 */
  detail: string;
  time: string;
}

/** 审批申请单历史 */
export interface ApprovalHistory {
  id: number;
  name: string;
  target_name: string;
  summary: string;
  status: number;
  status_name: string;
  events: ApprovalHistoryEvent[];
}

export interface ApprovalTaskPage {
  list: ApprovalTask[];
  total: number;
  pageNum: number;
  pageSize: number;
}

/** 待审批数量与最新一条申请 */
export interface ApprovalTaskCount {
  count: number;
  latest: {
    id: number;
    name: string;
    summary: string;
    applicant_name: string;
    created_at: string;
  } | null;
}

const BASE_URL = "/api/v1/approvals";

const ApprovalAPI = {
  /** 查询审批配置列表 */
  getConfigs() {
    return request<any, ApprovalConfig[]>({
      url: `${BASE_URL}/configs`,
      method: "get",
    });
  },

  /** 首次保存审批配置（配置行尚不存在时创建） */
  createConfig(data: ApprovalConfigCreateForm) {
    return request<any, ApprovalConfig>({
      url: `${BASE_URL}/configs/create`,
      method: "post",
      data,
    });
  },

  /** 更新审批配置 */
  updateConfig(id: number, data: ApprovalConfigForm) {
    return request<any, ApprovalConfig>({
      url: `${BASE_URL}/configs/${id}`,
      method: "put",
      data,
    });
  },

  /** 当前用户待处理审批数量 */
  getMyTaskCount() {
    return request<any, { count: number }>({
      url: `${BASE_URL}/my-tasks/count`,
      method: "get",
    });
  },

  /** 我的审批列表 */
  getMyTasks(params: ApprovalTaskQuery) {
    return request<any, ApprovalTaskPage>({
      url: `${BASE_URL}/my-tasks`,
      method: "get",
      params,
    });
  },

  /** 审批申请完整历史 */
  getRequestHistory(id: number) {
    return request<any, ApprovalHistory>({
      url: `${BASE_URL}/requests/${id}/history`,
      method: "get",
    });
  },

  /** 同意审批 */
  approveRequest(id: number, comment = "") {
    return request<any, ApprovalTask>({
      url: `${BASE_URL}/requests/${id}/approve`,
      method: "post",
      data: { comment },
    });
  },

  /** 拒绝审批 */
  rejectRequest(id: number, comment = "") {
    return request<any, ApprovalTask>({
      url: `${BASE_URL}/requests/${id}/reject`,
      method: "post",
      data: { comment },
    });
  },
};

export default ApprovalAPI;
