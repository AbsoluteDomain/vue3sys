<template>
  <div class="approval-manage">
    <el-card class="approval-card" shadow="never">
      <div class="approval-header">
        <span class="approval-title">审核管理</span>
        <span class="approval-desc">按角色权限层级展示产品管理下全部审核项，点击权限行即可配置审批人、审批模式与启用状态</span>
      </div>

      <el-table
        v-loading="loading"
        :data="configs"
        row-key="row_key"
        :tree-props="{ children: 'children' }"
        default-expand-all
        class="approval-table"
        @row-click="handleRowClick"
      >
        <el-table-column label="功能" min-width="220" prop="name">
          <template #default="{ row }">
            <span :class="{ 'approval-parent-name': row.node_type !== 'button' }">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="权限标识" min-width="220">
          <template #default="{ row }">
            <span v-if="row.perm_code" class="approval-perm">{{ row.perm_code }}</span>
            <span v-else class="approval-empty">—</span>
          </template>
        </el-table-column>
        <el-table-column label="审核状态" width="130">
          <template #default="{ row }">
            <el-tag
              v-if="row.node_type === 'button'"
              :type="row.enabled ? 'success' : 'info'"
              size="small"
              effect="plain"
            >
              {{ row.enabled ? "已启用" : "未启用" }}
            </el-tag>
            <span v-else class="approval-summary">已启用 {{ row.enabled_count }}/{{ row.total }}</span>
          </template>
        </el-table-column>
        <el-table-column label="审核人" min-width="180">
          <template #default="{ row }">
            <template v-if="row.node_type === 'button'">
              <span v-if="row.approver_names">{{ row.approver_names }}</span>
              <span v-else class="approval-empty">未配置</span>
            </template>
            <span v-else class="approval-empty">—</span>
          </template>
        </el-table-column>
        <el-table-column label="审批模式" width="160">
          <template #default="{ row }">
            <el-tag
              v-if="row.node_type === 'button'"
              :type="row.approval_mode === 'multi' ? 'warning' : 'primary'"
              size="small"
              effect="plain"
            >
              {{ row.approval_mode === "multi" ? "多人审批（会签）" : "单人审批（或签）" }}
            </el-tag>
            <span v-else class="approval-empty">—</span>
          </template>
        </el-table-column>
        <el-table-column label="最近修改人" width="120">
          <template #default="{ row }">
            <span v-if="row.node_type === 'button' && row.editor_name">{{ row.editor_name }}</span>
            <span v-else class="approval-empty">—</span>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="170">
          <template #default="{ row }">
            <span v-if="row.node_type === 'button' && row.updated_at">{{ row.updated_at }}</span>
            <span v-else class="approval-empty">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.node_type === 'button' && row.perm_code"
              type="primary"
              link
              @click.stop="openDialog(row)"
            >
              配置
            </el-button>
            <span v-else class="approval-empty">—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="`配置审核 - ${currentConfig?.name || ''}`"
      width="560px"
      @closed="resetForm"
    >
      <el-form v-if="currentConfig" label-width="96px">
        <el-form-item label="审核状态">
          <el-switch
            v-model="form.enabled"
            :active-value="1"
            :inactive-value="0"
            active-text="已启用"
            inactive-text="未启用"
          />
        </el-form-item>
        <el-form-item label="审批模式">
          <el-radio-group v-model="form.approval_mode">
            <el-radio-button value="single">单人审批</el-radio-button>
            <el-radio-button value="multi">多人审批</el-radio-button>
          </el-radio-group>
          <div class="approval-mode-tip">
            {{ form.approval_mode === "multi"
              ? "多人审批（会签）：所有审核人都同意后才通过，任意一人拒绝即驳回"
              : "单人审批（或签）：任意一名审核人同意即通过" }}
          </div>
        </el-form-item>
        <el-form-item label="审核人">
          <el-select
            v-model="form.approver_ids"
            multiple
            filterable
            placeholder="请选择审核人"
            class="approval-approver-select"
          >
            <el-option
              v-for="option in userOptions"
              :key="option.value"
              :label="option.label"
              :value="Number(option.value)"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import ApprovalAPI, { type ApprovalConfig } from "@/api/approval";
import UserAPI from "@/api/system/user";
import type { OptionItem } from "@/types/api";

const loading = ref(false);
const submitting = ref(false);
const dialogVisible = ref(false);
const configs = ref<ApprovalConfig[]>([]);
const userOptions = ref<OptionItem[]>([]);
const currentConfig = ref<ApprovalConfig | null>(null);

const form = reactive<{ enabled: number; approval_mode: "single" | "multi"; approver_ids: number[] }>({
  enabled: 0,
  approval_mode: "single",
  approver_ids: [],
});

async function fetchConfigs() {
  loading.value = true;
  try {
    configs.value = (await ApprovalAPI.getConfigs()) || [];
  } finally {
    loading.value = false;
  }
}

async function fetchUserOptions() {
  try {
    userOptions.value = (await UserAPI.getOptions()) || [];
  } catch {
    userOptions.value = [];
  }
}

function openDialog(row: ApprovalConfig) {
  currentConfig.value = row;
  form.enabled = row.enabled;
  form.approval_mode = row.approval_mode;
  form.approver_ids = [...(row.approver_ids || [])];
  dialogVisible.value = true;
}

function handleRowClick(row: ApprovalConfig) {
  // 仅按钮权限行可配置，目录/模块行只展示汇总信息
  if (row.node_type !== "button" || !row.perm_code) return;
  openDialog(row);
}

function resetForm() {
  currentConfig.value = null;
  form.enabled = 0;
  form.approval_mode = "single";
  form.approver_ids = [];
}

async function handleSave() {
  if (!currentConfig.value) return;
  if (form.enabled === 1 && form.approver_ids.length === 0) {
    ElMessage.warning("启用审核时必须至少选择一名审核人");
    return;
  }
  submitting.value = true;
  try {
    const payload = {
      enabled: form.enabled,
      approval_mode: form.approval_mode,
      approver_ids: form.approver_ids,
    };
    if (currentConfig.value.id) {
      await ApprovalAPI.updateConfig(currentConfig.value.id, payload);
    } else {
      // 首次配置该按钮权限时后端还没有配置记录，走创建接口
      await ApprovalAPI.createConfig({
        perm_code: currentConfig.value.perm_code,
        menu_id: currentConfig.value.menu_id as number,
        name: currentConfig.value.name,
        ...payload,
      });
    }
    ElMessage.success("保存成功");
    dialogVisible.value = false;
    fetchConfigs();
  } catch {
    // 请求层已统一提示错误
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  fetchConfigs();
  fetchUserOptions();
});
</script>

<style lang="scss" scoped>
.approval-manage {
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
  margin-bottom: 16px;
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

.approval-table {
  :deep(.el-table__row) {
    cursor: pointer;
  }
}

.approval-parent-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.approval-perm {
  font-family: var(--el-font-family-mono, monospace);
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.approval-summary {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.approval-empty {
  color: var(--el-text-color-secondary);
}

.approval-mode-tip {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-secondary);
}

.approval-approver-select {
  width: 100%;
}
</style>
