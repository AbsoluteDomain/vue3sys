<template>
  <el-dropdown class="release__dropdown" trigger="click" @visible-change="handleVisibleChange">
    <div class="release__trigger" title="版本更新">
      <el-badge v-if="unreadCount > 0" :value="unreadCount" :max="99">
        <el-icon :size="18"><Tickets /></el-icon>
      </el-badge>
      <el-icon v-else :size="18"><Tickets /></el-icon>
    </div>

    <template #dropdown>
      <div class="release__panel">
        <div class="release__panel-title">版本更新历史</div>
        <template v-if="list.length > 0">
          <div
            v-for="item in list"
            :key="item.id"
            class="release__item"
            @click="openDetail(item.id)"
          >
            <div class="release__item-head">
              <span class="release__version">{{ item.version }}</span>
              <el-tag v-if="item.isRead !== 1" size="small" type="danger" effect="plain">未读</el-tag>
            </div>
            <div class="release__item-title">{{ item.title }}</div>
            <div class="release__item-time">{{ item.publishTime }}</div>
          </div>
        </template>
        <el-empty v-else description="暂无版本记录" :image-size="50" />
      </div>
    </template>
  </el-dropdown>

  <ReleaseDetailDialog
    v-model="detailVisible"
    :detail="detail"
    confirm-text="关闭"
    @confirm="handleDetailClose"
    @closed="handleDetailClose"
  />
</template>

<script setup lang="ts">
import { Tickets } from "@element-plus/icons-vue";
import ReleaseAPI, { type ReleaseBrief, type ReleaseDetail } from "@/api/system/release";
import ReleaseDetailDialog from "./ReleaseDetailDialog.vue";

const list = ref<ReleaseBrief[]>([]);
const detail = ref<ReleaseDetail | null>(null);
const detailVisible = ref(false);
const viewingId = ref<number | null>(null);

const unreadCount = computed(() => list.value.filter((item) => item.isRead !== 1).length);

async function markViewedAsRead(id: number) {
  const item = list.value.find((x) => x.id === id);
  if (item && item.isRead === 1) return;
  try {
    await ReleaseAPI.markRead(id);
    if (item) {
      item.isRead = 1;
    } else {
      await fetchList();
    }
  } catch {
    // 标记失败时不阻断关闭
  }
}

async function fetchList() {
  try {
    list.value = (await ReleaseAPI.getPublishedList()) || [];
  } catch {
    list.value = [];
  }
}

async function openDetail(id: number) {
  try {
    viewingId.value = id;
    detail.value = await ReleaseAPI.getDetail(id);
    detailVisible.value = true;
  } catch {
    viewingId.value = null;
    ElMessage.error("加载版本详情失败");
  }
}

async function handleDetailClose() {
  const id = viewingId.value ?? detail.value?.id ?? null;
  viewingId.value = null;
  detail.value = null;
  if (id) {
    await markViewedAsRead(id);
  }
}

function handleVisibleChange(visible: boolean) {
  if (visible) {
    fetchList();
  }
}

onMounted(() => {
  fetchList();
});

defineExpose({ refresh: fetchList });
</script>

<style lang="scss" scoped>
.release {
  &__dropdown {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
  }

  &__trigger {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    color: inherit;
    cursor: pointer;
  }

  &__panel {
    width: 360px;
    max-height: 420px;
    padding: 12px 0;
    overflow-y: auto;
  }

  &__panel-title {
    padding: 0 16px 8px;
    font-size: 13px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  &__item {
    padding: 10px 16px;
    cursor: pointer;
    transition: background 0.2s;

    &:hover {
      background: var(--el-fill-color-light);
    }
  }

  &__item-head {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  &__version {
    font-size: 13px;
    font-weight: 600;
    color: var(--el-color-primary);
  }

  &__item-title {
    margin-top: 4px;
    overflow: hidden;
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__item-time {
    margin-top: 2px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}
</style>
