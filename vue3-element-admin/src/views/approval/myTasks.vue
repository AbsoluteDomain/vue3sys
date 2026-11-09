<template>
  <div class="approval-tasks">
    <el-card class="approval-card" shadow="never">
      <div class="approval-header">
        <span class="approval-title">我的审批</span>
        <span class="approval-desc">处理待我审批的业务申请，或查看我发起的审批进度</span>
      </div>

      <el-tabs v-model="activeScope" class="approval-tabs" @tab-change="handleScopeChange">
        <el-tab-pane label="待我审批" name="pending" />
        <el-tab-pane label="我发起的" name="mine" />
        <el-tab-pane label="我已处理的" name="processed" />
      </el-tabs>

      <el-table v-loading="loading" :data="tasks" row-key="id" class="approval-table">
        <el-table-column label="功能" width="100" prop="name" />
        <el-table-column label="申请内容" min-width="220">
          <template #default="{ row }">
            <div class="task-target">{{ row.target_name }}</div>
            <div class="task-summary">{{ row.summary }}</div>
          </template>
        </el-table-column>
        <el-table-column label="申请人" width="110">
          <template #default="{ row }">{{ row.applicant_name || "—" }}</template>
        </el-table-column>
        <el-table-column label="审批模式" width="120">
          <template #default="{ row }">
            <el-tag :type="row.approval_mode === 'multi' ? 'warning' : 'primary'" size="small" effect="plain">
              {{ row.approval_mode_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="审核人" min-width="200">
          <template #default="{ row }">
            <div class="task-approvers">
              <el-tooltip
                v-for="approver in row.approvers"
                :key="approver.approver_id"
                :content="approver.comment || approver.decision_name"
                placement="top"
              >
                <el-tag
                  :type="approver.decision === 1 ? 'success' : approver.decision === 2 ? 'danger' : 'info'"
                  size="small"
                  effect="plain"
                >
                  {{ approver.approver_name }} · {{ approver.decision_name }}
                </el-tag>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="审核状态" width="110">
          <template #default="{ row }">
            <el-tooltip :content="row.execute_error" :disabled="!row.execute_error" placement="top">
              <el-tag :type="statusTagType(row.status)" size="small" effect="plain">
                {{ row.status_name }}
              </el-tag>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="170">
          <template #default="{ row }">{{ row.created_at || "—" }}</template>
        </el-table-column>
        <el-table-column label="操作" width="190" align="center">
          <template #default="{ row }">
            <template v-if="row.can_decide">
              <el-button type="success" link @click="openDecide(row, 'approve')">同意</el-button>
              <el-button type="danger" link @click="openDecide(row, 'reject')">拒绝</el-button>
            </template>
            <el-button type="primary" link @click="openHistory(row)">审批历史</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <div class="approval-empty">暂无审批数据</div>
        </template>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pageNum"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="decideMode === 'approve' ? '同意审批' : '拒绝审批'"
      width="520px"
      @closed="resetDialog"
    >
      <div v-if="currentTask" class="decide-info">
        <span class="decide-info__label">申请内容：</span>
        <span>{{ currentTask.summary }}</span>
      </div>
      <el-form label-width="80px">
        <el-form-item label="审批意见">
          <el-input
            v-model="comment"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            :placeholder="decideMode === 'approve' ? '请输入审批意见（选填）' : '请输入拒绝原因（选填）'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          :type="decideMode === 'approve' ? 'success' : 'danger'"
          :loading="submitting"
          @click="handleDecide"
        >
          确定
        </el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="historyVisible"
      title="审批历史"
      size="480px"
      @closed="resetHistory"
    >
      <div v-loading="historyLoading" class="history-body">
        <template v-if="historyData">
          <div class="history-head">
            <div class="history-title">
              {{ historyData.name }}
              <el-tag :type="statusTagType(historyData.status)" size="small" effect="plain">
                {{ historyData.status_name }}
              </el-tag>
            </div>
            <div class="history-target">{{ historyData.target_name || "—" }}</div>
            <div v-if="historyData.summary" class="history-summary">{{ historyData.summary }}</div>
          </div>
          <el-timeline>
            <el-timeline-item
              v-for="(event, index) in historyData.events"
              :key="index"
              :timestamp="event.time"
              :type="eventTagType(event.type)"
            >
              <div class="history-event">
                <span class="history-action">{{ event.type_name }}</span>
                <span class="history-actor">{{ event.actor }}</span>
              </div>
              <div v-if="event.detail" class="history-detail">{{ event.detail }}</div>
            </el-timeline-item>
          </el-timeline>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";

import ApprovalAPI, { type ApprovalHistory, type ApprovalTask } from "@/api/approval";

const loading = ref(false);
const submitting = ref(false);
const tasks = ref<ApprovalTask[]>([]);
const activeScope = ref<"pending" | "mine" | "processed">("pending");
const pageNum = ref(1);
const pageSize = ref(10);
const total = ref(0);

const dialogVisible = ref(false);
const decideMode = ref<"approve" | "reject">("approve");
const currentTask = ref<ApprovalTask | null>(null);
const comment = ref("");

const historyVisible = ref(false);
const historyLoading = ref(false);
const historyData = ref<ApprovalHistory | null>(null);

function statusTagType(status: number) {
  if (status === 1) return "success";
  if (status === 2) return "danger";
  if (status === 3) return "warning";
  return "info";
}

function eventTagType(type: string) {
  if (type === "approve" || type === "execute") return "success";
  if (type === "reject" || type === "execute_failed") return "danger";
  return "primary";
}

async function fetchTasks() {
  loading.value = true;
  try {
    const result = await ApprovalAPI.getMyTasks({
      scope: activeScope.value,
      pageNum: pageNum.value,
      pageSize: pageSize.value,
    });
    tasks.value = result?.list || [];
    total.value = result?.total || 0;
  } catch {
    tasks.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

function handleScopeChange() {
  pageNum.value = 1;
  fetchTasks();
}

function handleSizeChange(size: number) {
  pageSize.value = size;
  pageNum.value = 1;
  fetchTasks();
}

function handleCurrentChange(page: number) {
  pageNum.value = page;
  fetchTasks();
}

function openDecide(row: ApprovalTask, mode: "approve" | "reject") {
  currentTask.value = row;
  decideMode.value = mode;
  comment.value = "";
  dialogVisible.value = true;
}

function resetDialog() {
  currentTask.value = null;
  comment.value = "";
}

async function handleDecide() {
  if (!currentTask.value) return;
  submitting.value = true;
  try {
    const action =
      decideMode.value === "approve"
        ? ApprovalAPI.approveRequest(currentTask.value.id, comment.value.trim())
        : ApprovalAPI.rejectRequest(currentTask.value.id, comment.value.trim());
    const result = await action;
    ElMessage.success(result ? result.status_name : "操作成功");
    dialogVisible.value = false;
    fetchTasks();
  } catch {
    // 请求层已统一提示错误
  } finally {
    submitting.value = false;
  }
}

async function openHistory(row: ApprovalTask) {
  historyVisible.value = true;
  historyData.value = null;
  historyLoading.value = true;
  try {
    historyData.value = await ApprovalAPI.getRequestHistory(row.id);
  } catch {
    // 请求层已统一提示错误
  } finally {
    historyLoading.value = false;
  }
}

function resetHistory() {
  historyData.value = null;
  historyLoading.value = false;
}

onMounted(fetchTasks);
</script>

<style lang="scss" scoped>
.approval-tasks {
  min-height: calc(100vh - 84px);
  padding: 16px;
  background: var(--el-fill-color-blank);
}

.approval-card {
  :deep(.el-card__body) {
    padding: 20px;
  }
}

.approval-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-light);

  .approval-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  .approval-desc {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }
}

.approval-tabs {
  margin-top: 8px;
}

.approval-table {
  margin-top: 4px;
}

.task-target {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.task-summary {
  margin-top: 2px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.task-approvers {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.approval-empty {
  color: var(--el-text-color-secondary);
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.history-body {
  min-height: 200px;
  padding: 0 4px;
}

.history-head {
  padding-bottom: 16px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--el-border-color-light);
}

.history-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.history-target {
  margin-top: 6px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.history-summary {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.history-event {
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-action {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.history-actor {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.history-detail {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

.decide-info {
  padding: 10px 12px;
  margin-bottom: 16px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-light);
  border-radius: 4px;

  &__label {
    color: var(--el-text-color-secondary);
  }
}
</style>
