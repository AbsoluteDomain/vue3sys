<template>
  <div class="file-manager">
    <el-card class="file-card" shadow="never">
      <!-- 服务器标题栏 -->
      <div class="server-header">
        <span class="server-title">共享文件服务器</span>
        <div class="server-user">
          <el-avatar :size="28" :src="userStore.userInfo.avatar || undefined" class="server-avatar">
            {{ userInitial }}
          </el-avatar>
          <span class="server-user__name">
            {{ userStore.userInfo.nickname || userStore.userInfo.username }}（{{
              userStore.userInfo.username
            }}）
          </span>
          <el-button size="small" @click="handleExit">退出</el-button>
        </div>
      </div>

      <!-- 全部文件 / 回收站 -->
      <div class="view-tabs">
        <el-button
          :type="viewMode === 'normal' ? 'primary' : 'default'"
          size="small"
          @click="switchView('normal')"
        >
          全部文件
        </el-button>
        <el-button
          :type="viewMode === 'recycle' ? 'primary' : 'default'"
          size="small"
          @click="switchView('recycle')"
        >
          回收站
        </el-button>
      </div>

      <!-- 面包屑 -->
      <el-breadcrumb v-if="viewMode === 'normal'" class="file-breadcrumb" separator="/">
        <el-breadcrumb-item v-for="(node, index) in breadcrumbs" :key="node.id">
          <span
            class="breadcrumb-link"
            :class="{ 'is-current': index === breadcrumbs.length - 1 }"
            @click="handleBreadcrumb(node)"
          >
            {{ node.name }}
          </span>
        </el-breadcrumb-item>
      </el-breadcrumb>

      <!-- 工具栏 -->
      <div class="file-toolbar">
        <div class="file-toolbar__left">
          <el-input
            v-model="query.keyword"
            class="file-toolbar__search"
            placeholder="搜索文件名"
            clearable
            @keyup.enter="handleSearch"
            @clear="handleSearch"
          />
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-select v-model="query.sort_field" class="file-toolbar__select" @change="handleSearch">
            <el-option label="按名称" value="name" />
            <el-option label="按大小" value="size" />
            <el-option label="按上传时间" value="time" />
          </el-select>
          <el-select v-model="query.sort_order" class="file-toolbar__select" @change="handleSearch">
            <el-option label="升序" value="asc" />
            <el-option label="降序" value="desc" />
          </el-select>
        </div>
        <div v-if="viewMode === 'normal'" class="file-toolbar__right">
          <el-button type="warning" plain @click="handleCreateFolder">新建文件夹</el-button>
          <el-button type="success" :loading="uploading" @click="triggerUpload">
            上传到当前目录
          </el-button>
          <el-tooltip content="刷新" placement="top">
            <el-button circle :icon="Refresh" @click="refresh" />
          </el-tooltip>
          <input
            ref="uploadInput"
            type="file"
            multiple
            style="display: none"
            @change="handleUploadChange"
          />
        </div>
      </div>

      <!-- 文件表格 -->
      <el-table
        v-loading="loading"
        :data="list"
        row-key="id"
        class="file-table"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="48" />
        <el-table-column label="序号" width="64" align="center" :index="indexMethod" type="index" />
        <el-table-column label="名称" min-width="320">
          <template #default="{ row }">
            <span
              v-if="row.is_dir"
              class="file-name file-name--dir"
              @click="handleEnterFolder(row)"
            >
              <el-icon class="file-name__icon"><Folder /></el-icon>
              {{ row.name }}
            </span>
            <span v-else class="file-name" @click="handlePreview(row)">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="大小" width="120" align="center">
          <template #default="{ row }">
            {{ row.is_dir ? "—" : row.size_text }}
          </template>
        </el-table-column>
        <el-table-column label="类型" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="typeTagType(row)" size="small" effect="plain">
              {{ typeLabel(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="180" align="center">
          <template #default="{ row }">
            {{ viewMode === "recycle" ? row.deleted_at : row.created_at }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="{ row }">
            <template v-if="viewMode === 'normal'">
              <el-button v-if="!row.is_dir" type="primary" link @click="handlePreview(row)">
                预览
              </el-button>
              <el-button v-if="!row.is_dir" type="primary" link @click="handleDownload(row)">
                下载
              </el-button>
              <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
            </template>
            <template v-else>
              <el-button type="primary" link @click="handleRestore(row)">还原</el-button>
              <el-button type="danger" link @click="handlePurge(row)">彻底删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          background
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新建文件夹 -->
    <el-dialog v-model="folderDialogVisible" title="新建文件夹" width="420">
      <el-form label-width="90" @submit.prevent>
        <el-form-item label="文件夹名称">
          <el-input
            v-model="folderName"
            maxlength="100"
            placeholder="请输入文件夹名称"
            @keyup.enter="handleSubmitFolder"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="folderDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="folderSubmitting" @click="handleSubmitFolder">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { Folder, Refresh } from "@element-plus/icons-vue";

import FileManagerAPI, { type FileBreadcrumb, type FileItem } from "@/api/file-manager";
import { useUserStoreHook } from "@/store";

type ViewMode = "normal" | "recycle";

const userStore = useUserStoreHook();
const router = useRouter();

const MAX_UPLOAD_SIZE = 200 * 1024 * 1024;
const PREVIEW_TYPES = ["pdf", "png", "jpg", "jpeg", "gif", "webp", "bmp", "txt"];

const loading = ref(false);
const uploading = ref(false);
const folderSubmitting = ref(false);
const folderDialogVisible = ref(false);
const folderName = ref("");
const viewMode = ref<ViewMode>("normal");
const list = ref<FileItem[]>([]);
const total = ref(0);
const selectedIds = ref<number[]>([]);
const breadcrumbs = ref<FileBreadcrumb[]>([{ id: 0, name: "全部文件" }]);
const uploadInput = ref<HTMLInputElement | null>(null);

const query = reactive({
  parent_id: 0,
  keyword: "",
  sort_field: "name",
  sort_order: "asc",
  page: 1,
  size: 10,
});

const userInitial = computed(() => {
  const name = userStore.userInfo.nickname || userStore.userInfo.username || "";
  return name.charAt(0).toUpperCase();
});

/** 名称列序号：跟随分页 */
const indexMethod = (index: number) => (query.page - 1) * query.size + index + 1;

const TYPE_MAP: Record<string, { label: string; type: "primary" | "success" | "info" | "warning" | "danger" }> = {
  folder: { label: "文件夹", type: "info" },
  pdf: { label: "PDF", type: "danger" },
  doc: { label: "DOC", type: "info" },
  docx: { label: "DOC", type: "info" },
  ppt: { label: "PPT", type: "warning" },
  pptx: { label: "PPT", type: "warning" },
  xls: { label: "XLS", type: "success" },
  xlsx: { label: "XLS", type: "success" },
  csv: { label: "CSV", type: "success" },
  zip: { label: "ZIP", type: "primary" },
  rar: { label: "RAR", type: "primary" },
  urdf: { label: "URDF", type: "primary" },
  png: { label: "图片", type: "success" },
  jpg: { label: "图片", type: "success" },
  jpeg: { label: "图片", type: "success" },
  gif: { label: "图片", type: "success" },
  webp: { label: "图片", type: "success" },
  txt: { label: "TXT", type: "info" },
};

function typeLabel(row: FileItem) {
  if (row.is_dir) return "文件夹";
  return TYPE_MAP[row.file_type]?.label || (row.file_type ? row.file_type.toUpperCase() : "未知");
}

function typeTagType(row: FileItem) {
  if (row.is_dir) return "info" as const;
  return TYPE_MAP[row.file_type]?.type || ("info" as const);
}

async function fetchList() {
  loading.value = true;
  try {
    const data = await FileManagerAPI.getList({
      parent_id: query.parent_id,
      keyword: query.keyword,
      sort_field: query.sort_field,
      sort_order: query.sort_order,
      page: query.page,
      size: query.size,
      status: viewMode.value,
    });
    list.value = data?.list || [];
    total.value = data?.total || 0;
  } finally {
    loading.value = false;
  }
}

async function fetchBreadcrumb() {
  if (viewMode.value === "recycle") {
    breadcrumbs.value = [];
    return;
  }
  breadcrumbs.value = await FileManagerAPI.getBreadcrumb(query.parent_id);
}

function refresh() {
  fetchList();
  fetchBreadcrumb();
}

function switchView(mode: ViewMode) {
  if (viewMode.value === mode) return;
  viewMode.value = mode;
  query.parent_id = 0;
  query.keyword = "";
  query.page = 1;
  selectedIds.value = [];
  refresh();
}

function handleSearch() {
  query.page = 1;
  fetchList();
}

function handleSizeChange(size: number) {
  query.size = size;
  query.page = 1;
  fetchList();
}

function handleCurrentChange(page: number) {
  query.page = page;
  fetchList();
}

function handleSelectionChange(rows: FileItem[]) {
  selectedIds.value = rows.map((row) => row.id);
}

function enterFolder(folderId: number) {
  query.parent_id = folderId;
  query.keyword = "";
  query.page = 1;
  selectedIds.value = [];
  refresh();
}

function handleEnterFolder(row: FileItem) {
  enterFolder(row.id);
}

function handleBreadcrumb(node: FileBreadcrumb) {
  if (node.id === query.parent_id) return;
  enterFolder(node.id);
}

function handleExit() {
  router.push("/dashboard");
}

function triggerUpload() {
  uploadInput.value?.click();
}

async function handleUploadChange(event: Event) {
  const target = event.target as HTMLInputElement;
  const files = target.files ? Array.from(target.files) : [];
  target.value = "";
  if (!files.length) return;

  const oversize = files.find((file) => file.size > MAX_UPLOAD_SIZE);
  if (oversize) {
    ElMessage.warning(`文件「${oversize.name}」超过 200MB 上限`);
    return;
  }

  uploading.value = true;
  let successCount = 0;
  try {
    for (const file of files) {
      try {
        await FileManagerAPI.uploadFile(file, query.parent_id);
        successCount += 1;
      } catch {
        // 请求层已统一提示错误，继续上传其余文件
      }
    }
  } finally {
    uploading.value = false;
    if (successCount) {
      ElMessage.success(`成功上传 ${successCount} 个文件`);
      query.page = 1;
      fetchList();
    }
  }
}

function handleCreateFolder() {
  folderName.value = "";
  folderDialogVisible.value = true;
}

async function handleSubmitFolder() {
  const name = folderName.value.trim();
  if (!name) {
    ElMessage.warning("请输入文件夹名称");
    return;
  }
  folderSubmitting.value = true;
  try {
    await FileManagerAPI.createFolder({ name, parent_id: query.parent_id });
    ElMessage.success("新建文件夹成功");
    folderDialogVisible.value = false;
    query.page = 1;
    fetchList();
  } catch {
    // 请求层已统一提示错误
  } finally {
    folderSubmitting.value = false;
  }
}

function collectIds(row?: FileItem) {
  if (row) return [row.id];
  return selectedIds.value;
}

async function handleDelete(row?: FileItem) {
  const ids = collectIds(row);
  if (!ids.length) {
    ElMessage.warning("请先选择要删除的文件");
    return;
  }
  try {
    await ElMessageBox.confirm(`确定将选中的 ${ids.length} 项移入回收站吗？`, "删除确认", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await FileManagerAPI.remove(ids);
    ElMessage.success("已移入回收站");
    fetchList();
  } catch {
    // 请求层已统一提示错误
  }
}

async function handleRestore(row?: FileItem) {
  const ids = collectIds(row);
  if (!ids.length) {
    ElMessage.warning("请先选择要还原的文件");
    return;
  }
  try {
    await FileManagerAPI.restore(ids);
    ElMessage.success("还原成功");
    fetchList();
  } catch {
    // 请求层已统一提示错误
  }
}

async function handlePurge(row?: FileItem) {
  const ids = collectIds(row);
  if (!ids.length) {
    ElMessage.warning("请先选择要彻底删除的文件");
    return;
  }
  try {
    await ElMessageBox.confirm("彻底删除后无法恢复，确定继续吗？", "彻底删除", {
      type: "error",
      confirmButtonText: "彻底删除",
      cancelButtonText: "取消",
    });
  } catch {
    return;
  }
  try {
    await FileManagerAPI.purge(ids);
    ElMessage.success("彻底删除成功");
    fetchList();
  } catch {
    // 请求层已统一提示错误
  }
}

function handlePreview(row: FileItem) {
  if (row.is_dir) return;
  if (!PREVIEW_TYPES.includes(row.file_type)) {
    ElMessage.info("该文件类型暂不支持在线预览，请下载查看");
    return;
  }
  window.open(row.file_url, "_blank");
}

function handleDownload(row: FileItem) {
  window.open(FileManagerAPI.downloadUrl(row.id), "_blank");
}

onMounted(() => {
  refresh();
});
</script>

<style lang="scss" scoped>
.file-manager {
  min-height: calc(100vh - 84px);
  padding: 16px;
  background: var(--el-fill-color-blank);
}

.file-card {
  :deep(.el-card__body) {
    padding: 20px;
  }
}

.server-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-light);

  .server-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  .server-user {
    display: flex;
    align-items: center;
    gap: 10px;

    .server-avatar {
      background: var(--el-color-primary);
      color: var(--el-color-white);
      font-size: 14px;
    }

    &__name {
      font-size: 14px;
      color: var(--el-text-color-regular);
    }
  }
}

.view-tabs {
  display: flex;
  gap: 10px;
  margin: 16px 0 12px;
}

.file-breadcrumb {
  margin-bottom: 14px;

  .breadcrumb-link {
    cursor: pointer;
    color: var(--el-text-color-regular);

    &:hover {
      color: var(--el-color-primary);
    }

    &.is-current {
      cursor: default;
      color: var(--el-text-color-primary);
      font-weight: 600;

      &:hover {
        color: var(--el-text-color-primary);
      }
    }
  }
}

.file-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;

  &__left,
  &__right {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
  }

  &__search {
    width: 220px;
  }

  &__select {
    width: 130px;
  }
}

.file-table {
  width: 100%;
}

.file-name {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  color: var(--el-color-primary);

  &:hover {
    text-decoration: underline;
  }

  &--dir {
    color: var(--el-color-primary);
  }

  &__icon {
    margin-right: 6px;
    color: var(--el-color-warning);
  }
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
