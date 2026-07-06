import request from "@/utils/request";

const RELEASE_BASE_URL = "/api/v1/releases";

export interface ReleaseItemRow {
  id?: number;
  itemType: number;
  itemTypeName?: string;
  content: string;
  sort?: number;
}

export interface ReleaseBrief {
  id: number;
  version: string;
  title: string;
  summary?: string;
  releaseType: number;
  releaseTypeName?: string;
  publishStatus: number;
  publishStatusName?: string;
  publishTime?: string;
  forceNotify?: number;
  createTime?: string;
  isRead?: number;
}

export interface ReleaseDetail extends ReleaseBrief {
  revokeTime?: string;
  items: ReleaseItemRow[];
}

export interface ReleaseForm {
  id?: number;
  version: string;
  title: string;
  summary?: string;
  releaseType: number;
  forceNotify: boolean;
  items: ReleaseItemRow[];
}

export interface ReleaseQueryParams {
  pageNum?: number;
  pageSize?: number;
  version?: string;
  title?: string;
  publishStatus?: number | string;
}

const ReleaseAPI = {
  getAdminPage(queryParams?: ReleaseQueryParams) {
    return request<any, PageResult<ReleaseBrief>>({
      url: `${RELEASE_BASE_URL}/admin/list/`,
      method: "get",
      params: queryParams,
    });
  },

  getAdminDetail(id: number) {
    return request<any, ReleaseDetail>({
      url: `${RELEASE_BASE_URL}/admin/${id}/`,
      method: "get",
    });
  },

  create(data: ReleaseForm) {
    return request({
      url: `${RELEASE_BASE_URL}/admin/create/`,
      method: "post",
      data,
    });
  },

  update(id: number, data: ReleaseForm) {
    return request({
      url: `${RELEASE_BASE_URL}/admin/${id}/update/`,
      method: "put",
      data,
    });
  },

  deleteByIds(ids: string) {
    return request({
      url: `${RELEASE_BASE_URL}/admin/${ids}/delete/`,
      method: "delete",
    });
  },

  publish(id: number) {
    return request({
      url: `${RELEASE_BASE_URL}/admin/${id}/publish/`,
      method: "put",
    });
  },

  revoke(id: number) {
    return request({
      url: `${RELEASE_BASE_URL}/admin/${id}/revoke/`,
      method: "put",
    });
  },

  getPublishedList(limit = 20) {
    return request<any, ReleaseBrief[]>({
      url: `${RELEASE_BASE_URL}/published/`,
      method: "get",
      params: { limit },
    });
  },

  getDetail(id: number) {
    return request<any, ReleaseDetail>({
      url: `${RELEASE_BASE_URL}/${id}/detail/`,
      method: "get",
    });
  },

  getLatestUnread() {
    return request<any, ReleaseDetail | null>({
      url: `${RELEASE_BASE_URL}/latest-unread/`,
      method: "get",
    });
  },

  markRead(id: number) {
    return request({
      url: `${RELEASE_BASE_URL}/${id}/read/`,
      method: "put",
    });
  },
};

export default ReleaseAPI;
