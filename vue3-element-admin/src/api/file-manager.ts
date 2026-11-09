import request from "@/utils/request";

/** 文件管理条目 */
export interface FileItem {
  id: number;
  parent_id: number;
  /** 名称 */
  name: string;
  /** 是否文件夹 */
  is_dir: boolean;
  /** 文件类型（小写扩展名，文件夹为 folder） */
  file_type: string;
  /** 文件大小（字节） */
  file_size: number;
  /** 格式化后的大小 */
  size_text: string;
  /** 访问地址 */
  file_url: string;
  /** 上传人 */
  uploader_name: string;
  download_count: number;
  created_at: string;
  deleted_at: string;
}

/** 文件列表结果 */
export interface FileListResult {
  list: FileItem[];
  total: number;
  page: number;
  size: number;
}

/** 文件列表查询参数 */
export interface FileListParams {
  parent_id?: number;
  keyword?: string;
  /** 排序字段：name/size/time */
  sort_field?: string;
  /** 排序方向：asc/desc */
  sort_order?: string;
  page?: number;
  size?: number;
  /** normal-正常目录 recycle-回收站 */
  status?: "normal" | "recycle";
}

/** 面包屑节点 */
export interface FileBreadcrumb {
  id: number;
  name: string;
}

const BASE_URL = "/api/v1/files/manager";

const FileManagerAPI = {
  /** 分页查询文件列表 */
  getList(params: FileListParams) {
    return request<any, FileListResult>({
      url: `${BASE_URL}/list`,
      method: "get",
      params,
    });
  },

  /** 查询目录面包屑 */
  getBreadcrumb(parentId: number) {
    return request<any, FileBreadcrumb[]>({
      url: `${BASE_URL}/breadcrumb`,
      method: "get",
      params: { parent_id: parentId },
    });
  },

  /** 上传文件到指定目录 */
  uploadFile(file: File, parentId: number) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("parent_id", String(parentId));
    return request<any, FileItem>({
      url: `${BASE_URL}/upload`,
      method: "post",
      data: formData,
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  /** 新建文件夹 */
  createFolder(data: { name: string; parent_id: number }) {
    return request<any, FileItem>({
      url: `${BASE_URL}/folder`,
      method: "post",
      data,
    });
  },

  /** 移入回收站 */
  remove(ids: number[]) {
    return request<any, { count: number }>({
      url: `${BASE_URL}/delete`,
      method: "post",
      data: { ids },
    });
  },

  /** 从回收站还原 */
  restore(ids: number[]) {
    return request<any, { count: number }>({
      url: `${BASE_URL}/restore`,
      method: "post",
      data: { ids },
    });
  },

  /** 彻底删除 */
  purge(ids: number[]) {
    return request<any, { count: number }>({
      url: `${BASE_URL}/purge`,
      method: "post",
      data: { ids },
    });
  },

  /** 下载地址 */
  downloadUrl(id: number) {
    return `${BASE_URL}/download?id=${id}`;
  },
};

export default FileManagerAPI;
