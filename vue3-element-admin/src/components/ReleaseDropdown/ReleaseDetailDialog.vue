<template>
  <el-dialog
    v-model="visible"
    :title="detail ? `${detail.version} ${detail.title}` : '版本更新'"
    width="640px"
    destroy-on-close
    append-to-body
    @closed="handleClosed"
  >
    <div v-if="detail" class="release-detail">
      <div class="release-detail__meta">
        <el-tag v-if="detail.releaseTypeName" size="small" :type="releaseTagType">
          {{ detail.releaseTypeName }}
        </el-tag>
        <span v-if="detail.publishTime" class="release-detail__time">
          {{ detail.publishTime }}
        </span>
      </div>

      <p v-if="detail.summary" class="release-detail__summary">
        {{ detail.summary }}
      </p>

      <div v-if="groupedItems.length" class="release-detail__groups">
        <div v-for="group in groupedItems" :key="group.type" class="release-detail__group">
          <div class="release-detail__group-title">{{ group.label }}</div>
          <ul class="release-detail__list">
            <li v-for="(item, idx) in group.items" :key="idx">{{ item.content }}</li>
          </ul>
        </div>
      </div>
      <el-empty v-else description="暂无更新条目" :image-size="60" />
    </div>

    <template #footer>
      <el-button type="primary" @click="handleConfirm">
        {{ confirmText }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import type { ReleaseDetail } from "@/api/system/release";

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    detail: ReleaseDetail | null;
    confirmText?: string;
  }>(),
  {
    confirmText: "我知道了",
  }
);

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
  confirm: [];
  closed: [];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

const releaseTagType = computed(() => {
  const type = props.detail?.releaseType;
  if (type === 3) return "danger";
  if (type === 2) return "warning";
  return "info";
});

const ITEM_TYPE_ORDER = [
  { type: 1, label: "新功能" },
  { type: 2, label: "优化" },
  { type: 3, label: "修复" },
  { type: 4, label: "其他" },
];

const groupedItems = computed(() => {
  if (!props.detail?.items?.length) return [];
  const map = new Map<number, { type: number; label: string; items: typeof props.detail.items }>();
  for (const row of props.detail.items) {
    const type = row.itemType || 4;
    if (!map.has(type)) {
      const label = row.itemTypeName || ITEM_TYPE_ORDER.find((x) => x.type === type)?.label || "其他";
      map.set(type, { type, label, items: [] });
    }
    map.get(type)!.items.push(row);
  }
  return ITEM_TYPE_ORDER.filter((x) => map.has(x.type)).map((x) => map.get(x.type)!);
});

function handleConfirm() {
  emit("confirm");
  visible.value = false;
}

function handleClosed() {
  emit("closed");
}
</script>

<style lang="scss" scoped>
.release-detail {
  &__meta {
    display: flex;
    gap: 12px;
    align-items: center;
    margin-bottom: 12px;
  }

  &__time {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }

  &__summary {
    margin: 0 0 16px;
    font-size: 14px;
    line-height: 1.6;
    color: var(--el-text-color-regular);
  }

  &__group {
    & + & {
      margin-top: 16px;
    }
  }

  &__group-title {
    margin-bottom: 8px;
    font-size: 14px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  &__list {
    margin: 0;
    padding-left: 20px;
    font-size: 14px;
    line-height: 1.8;
    color: var(--el-text-color-regular);
  }
}
</style>
