<template>
  <div class="app-container">
    <div class="filter-section">
      <el-form ref="queryFormRef" :model="queryParams" :inline="true" label-suffix=":">
        <el-form-item label="版本号" prop="version">
          <el-input
            v-model="queryParams.version"
            placeholder="版本号"
            clearable
            @keyup.enter="handleQuery()"
          />
        </el-form-item>
        <el-form-item label="标题" prop="title">
          <el-input
            v-model="queryParams.title"
            placeholder="标题"
            clearable
            @keyup.enter="handleQuery()"
          />
        </el-form-item>
        <el-form-item label="发布状态" prop="publishStatus">
          <el-select
            v-model="queryParams.publishStatus"
            clearable
            placeholder="全部"
            style="width: 110px"
          >
            <el-option :value="0" label="未发布" />
            <el-option :value="1" label="已发布" />
            <el-option :value="-1" label="已撤回" />
          </el-select>
        </el-form-item>
        <el-form-item class="search-buttons">
          <el-button type="primary" icon="search" @click="handleQuery()">搜索</el-button>
          <el-button icon="refresh" @click="handleResetQuery()">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-card shadow="hover" class="table-section">
      <div class="table-section__toolbar">
        <div class="table-section__toolbar--actions">
          <el-button
            v-hasPerm="['sys:release:create']"
            type="success"
            icon="plus"
            @click="openDialog()"
          >
            新增版本
          </el-button>
          <el-button
            v-hasPerm="['sys:release:delete']"
            type="danger"
            :disabled="selectIds.length === 0"
            icon="delete"
            @click="handleDelete()"
          >
            删除
          </el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="pageData"
        highlight-current-row
        class="table-section__content"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column type="index" label="序号" width="60" />
        <el-table-column label="版本号" prop="version" width="120" />
        <el-table-column label="标题" prop="title" min-width="180" show-overflow-tooltip />
        <el-table-column label="类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.releaseType === 3" type="danger" size="small">紧急</el-tag>
            <el-tag v-else-if="row.releaseType === 2" type="warning" size="small">重要</el-tag>
            <el-tag v-else type="info" size="small">常规</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="登录弹窗" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.forceNotify === 1" type="success" size="small">是</el-tag>
            <el-tag v-else type="info" size="small">否</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发布状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.publishStatus === 0" type="info" size="small">未发布</el-tag>
            <el-tag v-else-if="row.publishStatus === 1" type="success" size="small">已发布</el-tag>
            <el-tag v-else type="warning" size="small">已撤回</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发布时间" prop="publishTime" width="170" />
        <el-table-column label="创建时间" prop="createTime" width="170" />
        <el-table-column fixed="right" label="操作" width="220" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="openDetailDialog(row.id)">
              查看
            </el-button>
            <el-button
              v-if="row.publishStatus !== 1"
              v-hasPerm="['sys:release:publish']"
              type="primary"
              size="small"
              link
              @click="handlePublish(row.id)"
            >
              发布
            </el-button>
            <el-button
              v-if="row.publishStatus === 1"
              v-hasPerm="['sys:release:revoke']"
              type="primary"
              size="small"
              link
              @click="handleRevoke(row.id)"
            >
              撤回
            </el-button>
            <el-button
              v-if="row.publishStatus !== 1"
              v-hasPerm="['sys:release:update']"
              type="primary"
              size="small"
              link
              @click="openDialog(row.id)"
            >
              编辑
            </el-button>
            <el-button
              v-if="row.publishStatus !== 1"
              v-hasPerm="['sys:release:delete']"
              type="danger"
              size="small"
              link
              @click="handleDelete(row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <pagination
        v-if="total > 0"
        v-model:total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="fetchData()"
      />
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="720px"
      destroy-on-close
      @closed="resetForm"
    >
      <el-form ref="dataFormRef" :model="formData" :rules="rules" label-width="100px">
        <el-form-item label="版本号" prop="version">
          <el-input v-model="formData.version" placeholder="如 v1.2.0" clearable />
        </el-form-item>
        <el-form-item label="标题" prop="title">
          <el-input v-model="formData.title" placeholder="版本更新标题" clearable />
        </el-form-item>
        <el-form-item label="摘要" prop="summary">
          <el-input
            v-model="formData.summary"
            type="textarea"
            :rows="2"
            placeholder="简要说明本次更新（可选）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="发布类型" prop="releaseType">
          <el-radio-group v-model="formData.releaseType">
            <el-radio :value="1">常规</el-radio>
            <el-radio :value="2">重要</el-radio>
            <el-radio :value="3">紧急</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="登录弹窗" prop="forceNotify">
          <el-switch v-model="formData.forceNotify" active-text="发布后登录弹窗提醒" />
        </el-form-item>

        <el-form-item label="更新条目" required>
          <div class="release-items">
            <div v-for="(item, index) in formData.items" :key="index" class="release-items__row">
              <el-select v-model="item.itemType" style="width: 110px">
                <el-option :value="1" label="新功能" />
                <el-option :value="2" label="优化" />
                <el-option :value="3" label="修复" />
                <el-option :value="4" label="其他" />
              </el-select>
              <el-input
                v-model="item.content"
                placeholder="请输入更新内容"
                maxlength="500"
                clearable
              />
              <el-button type="danger" link icon="delete" @click="removeItem(index)" />
            </div>
            <el-button type="primary" link icon="plus" @click="addItem">添加条目</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <ReleaseDetailDialog v-model="detailVisible" :detail="detailData" confirm-text="关闭" />
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "Release",
  inheritAttrs: false,
});

import type { FormInstance, FormRules } from "element-plus";
import ReleaseAPI, {
  type ReleaseBrief,
  type ReleaseDetail,
  type ReleaseForm,
  type ReleaseQueryParams,
} from "@/api/system/release";
import ReleaseDetailDialog from "@/components/ReleaseDropdown/ReleaseDetailDialog.vue";

const queryFormRef = ref<FormInstance>();
const dataFormRef = ref<FormInstance>();

const queryParams = reactive<ReleaseQueryParams>({
  pageNum: 1,
  pageSize: 10,
});

const pageData = ref<ReleaseBrief[]>([]);
const total = ref(0);
const loading = ref(false);
const submitLoading = ref(false);
const selectIds = ref<number[]>([]);

const dialogVisible = ref(false);
const dialogTitle = ref("新增版本");
const editingId = ref<number | null>(null);

const detailVisible = ref(false);
const detailData = ref<ReleaseDetail | null>(null);

const defaultForm = (): ReleaseForm => ({
  version: "",
  title: "",
  summary: "",
  releaseType: 1,
  forceNotify: true,
  items: [{ itemType: 1, content: "" }],
});

const formData = reactive<ReleaseForm>(defaultForm());

const rules: FormRules = {
  version: [{ required: true, message: "请输入版本号", trigger: "blur" }],
  title: [{ required: true, message: "请输入标题", trigger: "blur" }],
};

function handleQuery() {
  queryParams.pageNum = 1;
  fetchData();
}

function fetchData() {
  loading.value = true;
  ReleaseAPI.getAdminPage(queryParams)
    .then((data) => {
      pageData.value = data.list || [];
      total.value = data.total ?? 0;
    })
    .finally(() => {
      loading.value = false;
    });
}

function handleResetQuery() {
  queryFormRef.value?.resetFields();
  queryParams.pageNum = 1;
  fetchData();
}

function handleSelectionChange(selection: ReleaseBrief[]) {
  selectIds.value = selection.map((item) => item.id);
}

function resetForm() {
  Object.assign(formData, defaultForm());
  editingId.value = null;
  dataFormRef.value?.clearValidate();
}

function addItem() {
  formData.items.push({ itemType: 1, content: "" });
}

function removeItem(index: number) {
  if (formData.items.length <= 1) {
    formData.items[0].content = "";
    return;
  }
  formData.items.splice(index, 1);
}

function openDialog(id?: number) {
  resetForm();
  if (id) {
    dialogTitle.value = "编辑版本";
    editingId.value = id;
    ReleaseAPI.getAdminDetail(id).then((data) => {
      Object.assign(formData, {
        version: data.version,
        title: data.title,
        summary: data.summary || "",
        releaseType: data.releaseType,
        forceNotify: data.forceNotify === 1,
        items: data.items?.length
          ? data.items.map((item) => ({ itemType: item.itemType, content: item.content }))
          : [{ itemType: 1, content: "" }],
      });
    });
  } else {
    dialogTitle.value = "新增版本";
  }
  dialogVisible.value = true;
}

function openDetailDialog(id: number) {
  ReleaseAPI.getAdminDetail(id).then((data) => {
    detailData.value = data;
    detailVisible.value = true;
  });
}

function handlePublish(id: number) {
  ElMessageBox.confirm("发布后将对启用登录弹窗的用户进行提醒，是否继续？", "提示", {
    type: "warning",
  }).then(() => {
    ReleaseAPI.publish(id).then(() => {
      ElMessage.success("发布成功");
      fetchData();
    });
  });
}

function handleRevoke(id: number) {
  ElMessageBox.confirm("撤回后用户将无法在导航栏看到该版本，是否继续？", "提示", {
    type: "warning",
  }).then(() => {
    ReleaseAPI.revoke(id).then(() => {
      ElMessage.success("撤回成功");
      fetchData();
    });
  });
}

function handleDelete(id?: number) {
  const ids = id ? [id] : selectIds.value;
  if (!ids.length) return;
  ElMessageBox.confirm("确认删除所选版本公告？", "提示", { type: "warning" }).then(() => {
    ReleaseAPI.deleteByIds(ids.join(",")).then(() => {
      ElMessage.success("删除成功");
      fetchData();
    });
  });
}

function handleSubmit() {
  dataFormRef.value?.validate((valid) => {
    if (!valid) return;
    const items = formData.items.filter((item) => item.content.trim());
    if (!items.length) {
      ElMessage.warning("请至少填写一条更新条目");
      return;
    }
    submitLoading.value = true;
    const payload: ReleaseForm = {
      ...formData,
      items: items.map((item, index) => ({ ...item, sort: index })),
    };
    const req = editingId.value
      ? ReleaseAPI.update(editingId.value, payload)
      : ReleaseAPI.create(payload);
    req
      .then(() => {
        ElMessage.success(editingId.value ? "更新成功" : "创建成功");
        dialogVisible.value = false;
        fetchData();
      })
      .finally(() => {
        submitLoading.value = false;
      });
  });
}

onMounted(() => {
  fetchData();
});
</script>

<style lang="scss" scoped>
.release-items {
  width: 100%;

  &__row {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-bottom: 8px;

    .el-input {
      flex: 1;
    }
  }
}
</style>
