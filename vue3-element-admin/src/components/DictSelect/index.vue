<template>
  <el-select
    v-if="type === 'select'"
    v-model="selectedValue"
    :placeholder="placeholder"
    :disabled="disabled"
    clearable
    :style="style"
    @change="handleChange"
  >
    <el-option
      v-for="option in currentOptions"
      :key="option.value"
      :label="option.label"
      :value="option.value"
    />
  </el-select>

  <el-radio-group
    v-else-if="type === 'radio'"
    v-model="selectedValue"
    :disabled="disabled"
    :style="style"
    @change="handleChange"
  >
    <el-radio v-for="option in currentOptions" :key="option.value" :value="option.value">
      {{ option.label }}
    </el-radio>
  </el-radio-group>

  <el-checkbox-group
    v-else-if="type === 'checkbox'"
    v-model="selectedValue"
    :disabled="disabled"
    :style="style"
    @change="handleChange"
  >
    <el-checkbox v-for="option in currentOptions" :key="option.value" :value="option.value">
      {{ option.label }}
    </el-checkbox>
  </el-checkbox-group>
</template>

<script setup lang="ts">
import { useDictStore } from "@/store";

const dictStore = useDictStore();

const props = defineProps({
  code: {
    type: String,
    required: true,
  },
  modelValue: {
    type: [String, Number, Array],
    required: false,
  },
  type: {
    type: String,
    default: "select",
    validator: (value: string) => ["select", "radio", "checkbox"].includes(value),
  },
  placeholder: {
    type: String,
    default: "请选择",
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  style: {
    type: Object,
    default: () => {
      return {
        width: "300px",
      };
    },
  },
});

const emit = defineEmits(["update:modelValue", "change"]);

const selectedValue = ref<any>(
  typeof props.modelValue === "string" || typeof props.modelValue === "number"
    ? props.modelValue
    : Array.isArray(props.modelValue)
      ? props.modelValue
      : undefined
);

// 响应式获取字典选项，当缓存更新时自动刷新
const currentOptions = computed(() => {
  return dictStore.getDictItems(props.code);
});

// 监听 modelValue 和 options 的变化
watch(
  [() => props.modelValue, () => currentOptions.value],
  ([newValue, newOptions]) => {
    if (newOptions.length > 0 && newValue !== undefined) {
      if (props.type === "checkbox") {
        selectedValue.value = Array.isArray(newValue) ? newValue : [];
      } else {
        const matchedOption = newOptions.find(
          (option) => String(option.value) === String(newValue)
        );
        selectedValue.value = matchedOption?.value;
      }
    } else {
      selectedValue.value = undefined;
    }
  },
  { immediate: true }
);

// 监听 selectedValue 的变化并触发 update:modelValue
function handleChange(val: any) {
  // 保持与原始 modelValue 相同的类型
  let emittedValue = val;
  if (typeof props.modelValue === "number" && typeof val === "string") {
    const numVal = Number(val);
    emittedValue = isNaN(numVal) ? val : numVal;
  }
  emit("update:modelValue", emittedValue);
  emit("change", emittedValue);
}

// 获取字典数据
onMounted(async () => {
  await dictStore.loadDictItems(props.code);
});
</script>
