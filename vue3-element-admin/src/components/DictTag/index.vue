<template>
  <template v-if="resolvedTagType">
    <el-tag :type="resolvedTagType" :size="tagSize">{{ resolvedLabel }}</el-tag>
  </template>
  <template v-else>
    <span>{{ resolvedLabel }}</span>
  </template>
</template>

<script setup lang="ts">
import { useDictStore } from "@/store";

const props = defineProps({
  code: String, // 字典编码
  modelValue: [String, Number], // 字典项的值
  size: {
    type: String,
    default: "default", // 标签大小
  },
});

const tagSize = ref<"default" | "large" | "small">(props.size as "default" | "large" | "small");
const dictStore = useDictStore();

// 响应式获取 label 和 tagType
const resolvedLabel = computed(() => {
  if (!props.code || props.modelValue === undefined) return "";
  const dictItems = dictStore.getDictItems(props.code);
  const dictItem = dictItems.find((item) => String(item.value) === String(props.modelValue));
  return dictItem?.label || "";
});

const resolvedTagType = computed(() => {
  if (!props.code || props.modelValue === undefined) return undefined;
  const dictItems = dictStore.getDictItems(props.code);
  const dictItem = dictItems.find((item) => String(item.value) === String(props.modelValue));
  return dictItem?.tagType as typeof resolvedTagType.value;
});

// 初始化加载字典数据
onMounted(async () => {
  if (props.code) {
    await dictStore.loadDictItems(props.code);
  }
});

// code 变化时重新加载字典
watch(() => props.code, async (newCode) => {
  if (newCode) {
    await dictStore.loadDictItems(newCode);
  }
});
</script>
