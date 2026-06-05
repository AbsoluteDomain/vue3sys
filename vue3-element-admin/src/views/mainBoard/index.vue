<template>
  <div class="app-container">
    <el-row :gutter="10" class="mt-2">
      <!-- 统计卡片 -->
      <el-col :xs="24" :sm="12" :md="6" class="mb-3">
        <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
          <template #header>
            <div class="flex-x-between">
              <span class="text-xs font-medium text-[--el-text-color-secondary]">物料总数</span>
            </div>
          </template>
          <div class="mt-2">
            <div class="flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-blue-600">{{ stats.totalCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">种</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6" class="mb-3">
        <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
          <template #header>
            <div class="flex-x-between">
              <span class="text-xs font-medium text-[--el-text-color-secondary]">报警物料</span>
            </div>
          </template>
          <div class="mt-2">
            <div class="flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-red-600">{{ stats.alertCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">种</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6" class="mb-3">
        <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
          <template #header>
            <div class="flex-x-between">
              <span class="text-xs font-medium text-[--el-text-color-secondary]">库存健康度</span>
            </div>
          </template>
          <div class="mt-2">
            <div class="flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-green-600">{{ healthPercent }}%</span>
              <span class="text-xs text-[--el-text-color-secondary]">健康</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6" class="mb-3">
        <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
          <template #header>
            <div class="flex-x-between">
              <span class="text-xs font-medium text-[--el-text-color-secondary]">总库存量</span>
            </div>
          </template>
          <div class="mt-2">
            <div class="flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-orange-600">{{ stats.totalQuantity }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="10" class="mt-2">
      <!-- 饼图：报警物料占比 -->
      <el-col :xs="24" :lg="12" class="mb-3">
        <el-card>
          <template #header>
            <div class="flex-x-between">
              <div class="flex items-center gap-2">
                <span class="font-semibold">报警物料占比</span>
                <el-tooltip content="展示安全物料与报警物料的比例，红色代表报警，绿色代表安全" placement="top">
                  <el-icon class="text-gray-400 cursor-pointer"><InfoFilled /></el-icon>
                </el-tooltip>
              </div>
            </div>
          </template>
          <ECharts :options="pieChartOptions" height="350px" />
        </el-card>
      </el-col>
      <!-- 柱状图：库存安全对比 -->
      <el-col :xs="24" :lg="12" class="mb-3">
        <el-card>
          <template #header>
            <div class="flex-x-between flex-wrap gap-2">
              <div class="flex items-center gap-2">
                <span class="font-semibold">库存安全分析</span>
                <el-tooltip content="展示各物料的当前库存状态，用颜色标识库存紧张程度" placement="top">
                  <el-icon class="text-gray-400 cursor-pointer"><InfoFilled /></el-icon>
                </el-tooltip>
              </div>
              <div class="flex items-center gap-4">
                <div class="flex items-center gap-1">
                  <span class="w-3 h-3 rounded-full bg-red-500 inline-block"></span>
                  <span class="text-xs">缺料</span>
                </div>
                <div class="flex items-center gap-1">
                  <span class="w-3 h-3 rounded-full bg-orange-500 inline-block"></span>
                  <span class="text-xs">预警</span>
                </div>
                <div class="flex items-center gap-1">
                  <span class="w-3 h-3 rounded-full bg-green-500 inline-block"></span>
                  <span class="text-xs">安全</span>
                </div>
                <el-select v-model="chartProductType" size="small" style="width: 120px" @change="handleTypeChange">
                  <el-option label="全部" value="" />
                  <el-option label="原材料" value="raw" />
                  <el-option label="组件" value="component" />
                </el-select>
              </div>
            </div>
          </template>
          <ECharts :options="barChartOptions" height="450px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="10" class="mt-2">
      <!-- 横向柱状图：报警物料TOP榜 -->
      <el-col :xs="24" :lg="12" class="mb-3">
        <el-card>
          <template #header>
            <div class="flex-x-between">
              <span class="font-semibold">报警物料TOP榜</span>
            </div>
          </template>
          <ECharts :options="horizontalBarOptions" height="350px" />
        </el-card>
      </el-col>
      <!-- 报警物料详情表格 -->
      <el-col :xs="24" :lg="12" class="mb-3">
        <el-card>
          <template #header>
            <div class="flex-x-between">
              <span class="font-semibold">报警物料详情</span>
            </div>
          </template>
          <el-table :data="alertProducts" border stripe style="width: 100%" height="350px">
            <el-table-column type="index" label="序号" width="60" align="center" />
            <el-table-column prop="name" label="产品名称" min-width="120" show-overflow-tooltip />
            <el-table-column prop="quantity" label="当前库存" width="100" align="center">
              <template #default="{ row }">
                <span class="text-red-600 font-semibold">{{ row.quantity }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="alert_quantity" label="报警线" width="100" align="center" />
            <el-table-column label="缺件数" width="100" align="center">
              <template #default="{ row }">
                <span class="font-semibold" :class="
                  row.shortage > 50 ? 'text-red-600' :
                  row.shortage > 20 ? 'text-orange-600' :
                  'text-yellow-600'
                ">{{ row.shortage }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="unit" label="单位" width="80" align="center" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "MainBoard",
});

import { ref, computed, onMounted } from "vue";
import { getProductList } from "@/api/product";
import ECharts from "@/components/ECharts/index.vue";
import { InfoFilled } from "@element-plus/icons-vue";

const loading = ref(false);
const allProducts = ref<any[]>([]);
const chartProductType = ref("");

// 统计数据
const stats = ref({
  totalCount: 0,
  alertCount: 0,
  totalQuantity: 0,
});

// 健康度计算
const healthPercent = computed(() => {
  if (stats.value.totalCount === 0) return 0;
  const safeCount = stats.value.totalCount - stats.value.alertCount;
  return Math.round((safeCount / stats.value.totalCount) * 100);
});

// 报警物料列表 - 按缺料数量从大到小排序
const alertProducts = computed(() => {
  return allProducts.value
    .filter((p) => {
      const qty = Number(p.quantity) || 0;
      const alertQty = Number(p.alert_quantity) || 0;
      return alertQty > 0 && qty <= alertQty;
    })
    .map((p) => ({
      ...p,
      shortage: Math.max(0, (Number(p.alert_quantity) || 0) - (Number(p.quantity) || 0)),
    }))
    .sort((a, b) => b.shortage - a.shortage);
});

// 饼图配置
const pieChartOptions = ref<any>({});
// 柱状图配置
const barChartOptions = ref<any>({});
// 横向柱状图配置
const horizontalBarOptions = ref<any>({});

// 获取数据
const fetchData = async () => {
  loading.value = true;
  try {
    const res = await getProductList({ pageNum: 1, pageSize: 1000 });
    allProducts.value = res?.list || [];

    // 计算统计数据
    let totalQty = 0;
    let alertCount = 0;
    allProducts.value.forEach((p) => {
      const qty = Number(p.quantity) || 0;
      const alertQty = Number(p.alert_quantity) || 0;
      totalQty += qty;
      if (alertQty > 0 && qty <= alertQty) {
        alertCount++;
      }
    });

    stats.value = {
      totalCount: allProducts.value.length,
      alertCount,
      totalQuantity: totalQty,
    };

    // 更新图表
    updateCharts();
  } catch (error) {
    console.error("获取数据失败", error);
  } finally {
    loading.value = false;
  }
};

// 更新图表
const updateCharts = () => {
  // 过滤数据
  let filteredProducts = allProducts.value;
  if (chartProductType.value) {
    filteredProducts = allProducts.value.filter(
      (p) => p.type === chartProductType.value
    );
  }

  // 饼图数据
  const alertCount = filteredProducts.filter((p) => {
    const qty = Number(p.quantity) || 0;
    const alertQty = Number(p.alert_quantity) || 0;
    return alertQty > 0 && qty <= alertQty;
  }).length;
  const safeCount = filteredProducts.length - alertCount;

  pieChartOptions.value = {
    tooltip: {
      trigger: "item",
      formatter: "{a} <br/>{b}: {c} ({d}%)",
    },
    legend: {
      orient: "vertical",
      left: "left",
    },
    series: [
      {
        name: "库存状态",
        type: "pie",
        radius: ["30%", "60%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: "#fff",
          borderWidth: 2,
        },
        label: {
          show: true,
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: "bold",
          },
        },
        data: [
          { value: safeCount, name: "安全", itemStyle: { color: "#67C23A" } },
          { value: alertCount, name: "报警", itemStyle: { color: "#F56C6C" } },
        ],
      },
    ],
  };

  // 重新设计的库存安全分析 - 用颜色标识库存状态
  const sortedProducts = [...filteredProducts]
    .map((p) => ({
      ...p,
      quantity: Number(p.quantity) || 0,
      alertQty: Number(p.alert_quantity) || 0,
    }))
    .sort((a, b) => {
      const scoreA = (a.alertQty > 0 && a.quantity <= a.alertQty) ? 0 : 
                   (a.alertQty > 0 && a.quantity <= 2 * a.alertQty) ? 1 : 2;
      const scoreB = (b.alertQty > 0 && b.quantity <= b.alertQty) ? 0 : 
                   (b.alertQty > 0 && b.quantity <= 2 * b.alertQty) ? 1 : 2;
      if (scoreA !== scoreB) return scoreA - scoreB;
      const shortageA = Math.max(0, a.alertQty - a.quantity);
      const shortageB = Math.max(0, b.alertQty - b.quantity);
      return shortageB - shortageA;
    })
    .slice(0, 15);

  barChartOptions.value = {
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "shadow",
      },
      formatter: (params: any) => {
        const name = params[0].name;
        const product = sortedProducts.find((p) => p.name === name);
        if (!product) return name;
        let status = '';
        if (product.alertQty > 0 && product.quantity <= product.alertQty) {
          status = '🔴 缺料';
        } else if (product.alertQty > 0 && product.quantity <= 2 * product.alertQty) {
          status = '🟡 预警';
        } else {
          status = '🟢 安全';
        }
        return `${name}<br/>当前库存: ${product.quantity}<br/>报警线: ${product.alertQty}<br/>状态: ${status}`;
      }
    },
    grid: {
      left: "3%",
      right: "15%",
      bottom: "3%",
      top: "3%",
      containLabel: true,
    },
    xAxis: {
      type: "value",
      axisLabel: {
        formatter: (value: number) => value,
      },
    },
    yAxis: {
      type: "category",
      data: sortedProducts.map((p) => p.name).reverse(),
    },
    series: [
      {
        type: "bar",
        data: sortedProducts.map((p) => ({
          value: p.quantity,
          itemStyle: {
            color: p.alertQty > 0 && p.quantity <= p.alertQty ? "#F56C6C" :
                   p.alertQty > 0 && p.quantity <= 2 * p.alertQty ? "#E6A23C" :
                   "#67C23A",
          },
        })).reverse(),
        label: {
          show: true,
          position: "right",
          formatter: (params: any) => {
            const name = params.name;
            const product = sortedProducts.find((p) => p.name === name);
            if (!product) return params.value;
            // if (product.alertQty > 0 && product.quantity <= product.alertQty) {
            //   return `⚠️ 缺料`;
            // } else if (product.alertQty > 0 && product.quantity <= 2 * product.alertQty) {
            //   return `⚡ 预警`;
            // } else {
            //   return `✓ 安全`;
            // }
          },
        },
      },
    ],
  };

  // 横向柱状图 - 报警物料TOP10（已经按严重程度排序）
  const topAlertProducts = alertProducts.value.slice(0, 10);
  horizontalBarOptions.value = {
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "shadow",
      },
    },
    grid: {
      left: "3%",
      right: "10%",
      bottom: "3%",
      top: "3%",
      containLabel: true,
    },
    xAxis: {
      type: "value",
    },
    yAxis: {
      type: "category",
      data: topAlertProducts.map((p) => p.name).reverse(),
    },
    series: [
      {
        name: "缺件数量",
        type: "bar",
        data: topAlertProducts
          .map((p) => {
            const qty = Number(p.quantity) || 0;
            const alertQty = Number(p.alert_quantity) || 0;
            return alertQty - qty;
          })
          .reverse(),
        itemStyle: {
          color: function (params: any) {
            const val = params.value;
            if (val > 50) return "#F56C6C";
            if (val > 20) return "#E6A23C";
            return "#F7BA2A";
          },
        },
      },
    ],
  };
};

// 切换物料类型
const handleTypeChange = () => {
  updateCharts();
};

onMounted(() => {
  fetchData();
});
</script>

<style lang="scss" scoped>
.app-container {
  padding: 20px;
}
</style>
