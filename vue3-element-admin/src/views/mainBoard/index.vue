<template>
  <div v-loading="loading" class="app-container">
    <el-card shadow="never" class="mb-3 board-type-card">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <span class="font-semibold text-base">库存看板</span>
        <el-radio-group v-model="boardType" @change="handleBoardTypeChange">
          <el-radio-button value="finish">成品</el-radio-button>
          <el-radio-button value="material">物料</el-radio-button>
        </el-radio-group>
      </div>
    </el-card>

    <!-- 物料看板 -->
    <template v-if="boardType === 'material'">
      <el-row :gutter="10" class="mt-2">
        <el-col :xs="24" :sm="12" :md="6" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">物料总数</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-blue-600">{{ materialStats.totalCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">种</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">报警物料</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-red-600">{{ materialStats.alertCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">种</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">库存健康度</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-green-600">{{ materialHealthPercent }}%</span>
              <span class="text-xs text-[--el-text-color-secondary]">健康</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">总库存量</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-orange-600">{{ materialStats.totalQuantity }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="10" class="mt-2">
        <el-col :xs="24" :lg="12" class="mb-3">
          <el-card>
            <template #header>
              <div class="flex items-center gap-2">
                <span class="font-semibold">报警物料占比</span>
                <el-tooltip content="展示安全物料与报警物料的比例，红色代表报警，绿色代表安全" placement="top">
                  <el-icon class="text-gray-400 cursor-pointer"><InfoFilled /></el-icon>
                </el-tooltip>
              </div>
            </template>
            <ECharts :options="pieChartOptions" height="350px" />
          </el-card>
        </el-col>
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
                  <el-select v-model="chartProductType" size="small" style="width: 120px" @change="updateMaterialCharts">
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
        <el-col :xs="24" :lg="12" class="mb-3">
          <el-card>
            <template #header>
              <span class="font-semibold">报警物料TOP榜</span>
            </template>
            <ECharts :options="horizontalBarOptions" height="350px" />
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="12" class="mb-3">
          <el-card>
            <template #header>
              <span class="font-semibold">报警物料详情</span>
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
                  <span
                    class="font-semibold"
                    :class="
                      row.shortage > 50 ? 'text-red-600' :
                      row.shortage > 20 ? 'text-orange-600' :
                      'text-yellow-600'
                    "
                  >{{ row.shortage }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="unit" label="单位" width="80" align="center" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <!-- 成品看板 -->
    <template v-else>
      <el-card shadow="never" class="mb-3">
        <el-form :inline="true" class="search-form">
          <el-form-item label="统计日期">
            <el-date-picker
              v-model="finishDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              :clearable="false"
              style="width: 260px"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchFinishData">查询</el-button>
            <el-button @click="resetFinishDateRange">近30天</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-row :gutter="10" class="mt-2">
        <el-col :xs="12" :sm="8" :md="6" :lg="3" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">新增成品</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-blue-600">{{ finishSummary.newCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="6" :lg="3" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">待测试新品</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-purple-600">{{ finishSummary.pendingNewCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="6" :lg="3" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">测试合格</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-green-600">{{ finishSummary.passCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="6" :lg="3" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">测试不良</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-red-600">{{ finishSummary.failCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="6" :lg="3" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">新增返修</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-orange-600">{{ finishSummary.repairCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="6" :lg="3" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">待测试返修</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-amber-600">{{ finishSummary.pendingRepairCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="6" :lg="3" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">返修合格</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-teal-600">{{ finishSummary.repairPassCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="10" class="mt-2">
        <el-col :xs="12" :sm="8" :md="6" :lg="3" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">成品库存</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-indigo-600">{{ currentStockInCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="6" :lg="3" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">入库数量</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-violet-600">{{ finishSummary.stockInCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="6" :lg="3" class="mb-3">
          <el-card shadow="never" class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg">
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">出库数量</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-slate-600">{{ finishSummary.stockOutCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="10" class="mt-2">
        <el-col :xs="24" class="mb-3">
          <el-card>
            <template #header>
              <div class="flex items-center gap-2">
                <span class="font-semibold">每日成品趋势</span>
                <el-tooltip
                  content="新品/测试按创建时间统计；返修、入库/出库按更新时间统计。成品库存为当前已入库总数，不受日期筛选影响"
                  placement="top"
                >
                  <el-icon class="text-gray-400 cursor-pointer"><InfoFilled /></el-icon>
                </el-tooltip>
              </div>
            </template>
            <ECharts :options="dailyLineChartOptions" height="400px" />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="10" class="mt-2">
        <el-col :xs="24" class="mb-3">
          <el-card>
            <template #header>
              <span class="font-semibold">每日统计对比</span>
            </template>
            <ECharts :options="dailyBarChartOptions" height="420px" />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="10" class="mt-2">
        <el-col :xs="24" class="mb-3">
          <el-card>
            <template #header>
              <span class="font-semibold">每日统计明细</span>
            </template>
            <el-table :data="dailyStatsDisplay" border stripe style="width: 100%" max-height="420px">
              <el-table-column prop="date" label="日期" width="120" align="center" fixed />
              <el-table-column prop="newCount" label="新增成品" width="100" align="center" />
              <el-table-column prop="pendingNewCount" label="待测试新品" width="110" align="center">
                <template #default="{ row }">
                  <span class="text-purple-600">{{ row.pendingNewCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="passCount" label="测试合格" width="100" align="center">
                <template #default="{ row }">
                  <span class="text-green-600">{{ row.passCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="failCount" label="测试不良" width="100" align="center">
                <template #default="{ row }">
                  <span class="text-red-600">{{ row.failCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="repairCount" label="新增返修" width="100" align="center" />
              <el-table-column prop="pendingRepairCount" label="待测试返修" width="110" align="center">
                <template #default="{ row }">
                  <span class="text-amber-600">{{ row.pendingRepairCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="repairPassCount" label="返修合格" width="100" align="center" />
              <el-table-column prop="stockInCount" label="入库数量" width="100" align="center">
                <template #default="{ row }">
                  <span class="text-violet-600">{{ row.stockInCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="stockOutCount" label="出库数量" width="100" align="center">
                <template #default="{ row }">
                  <span class="text-slate-600">{{ row.stockOutCount }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "MainBoard",
});

import { ref, computed, onMounted } from "vue";
import { getProductList } from "@/api/product";
import { getFinishProductDailyStats } from "@/api/finish-product";
import ECharts from "@/components/ECharts/index.vue";
import { InfoFilled } from "@element-plus/icons-vue";

type BoardType = "material" | "finish";

interface FinishDailyStat {
  date: string;
  newCount: number;
  passCount: number;
  failCount: number;
  pendingNewCount: number;
  repairCount: number;
  repairPassCount: number;
  pendingRepairCount: number;
  stockInCount: number;
  stockOutCount: number;
}

const finishChartSeries = [
  { name: "新增成品", key: "newCount", color: "#409EFF" },
  { name: "待测试新品", key: "pendingNewCount", color: "#9333EA" },
  { name: "测试合格", key: "passCount", color: "#67C23A" },
  { name: "测试不良", key: "failCount", color: "#F56C6C" },
  { name: "新增返修", key: "repairCount", color: "#E6A23C" },
  { name: "待测试返修", key: "pendingRepairCount", color: "#F59E0B" },
  { name: "返修合格", key: "repairPassCount", color: "#13C2C2" },
  { name: "入库数量", key: "stockInCount", color: "#8B5CF6" },
  { name: "出库数量", key: "stockOutCount", color: "#64748B" },
] as const;

const emptyFinishSummary = () => ({
  newCount: 0,
  passCount: 0,
  failCount: 0,
  pendingNewCount: 0,
  repairCount: 0,
  repairPassCount: 0,
  pendingRepairCount: 0,
  stockInCount: 0,
  stockOutCount: 0,
});

const formatDate = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const createDefaultFinishDateRange = () => {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 29);
  return [formatDate(start), formatDate(end)] as [string, string];
};

const loading = ref(false);
const boardType = ref<BoardType>("finish");
const allProducts = ref<any[]>([]);
const chartProductType = ref("");
const finishDateRange = ref<[string, string]>(createDefaultFinishDateRange());
const finishSummary = ref(emptyFinishSummary());
const currentStockInCount = ref(0);
const dailyStats = ref<FinishDailyStat[]>([]);
const finishDataLoaded = ref(false);

const materialStats = ref({
  totalCount: 0,
  alertCount: 0,
  totalQuantity: 0,
});

const pieChartOptions = ref<any>({});
const barChartOptions = ref<any>({});
const horizontalBarOptions = ref<any>({});
const dailyLineChartOptions = ref<any>({});
const dailyBarChartOptions = ref<any>({});

const materialHealthPercent = computed(() => {
  if (materialStats.value.totalCount === 0) return 0;
  const safeCount = materialStats.value.totalCount - materialStats.value.alertCount;
  return Math.round((safeCount / materialStats.value.totalCount) * 100);
});

const dailyStatsDisplay = computed(() => {
  return [...dailyStats.value].reverse();
});

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


const isMaterialAlert = (product: any) => {
  const qty = Number(product.quantity) || 0;
  const alertQty = Number(product.alert_quantity) || 0;
  return alertQty > 0 && qty <= alertQty;
};

const fetchFinishData = async () => {
  if (!finishDateRange.value?.[0] || !finishDateRange.value?.[1]) {
    return;
  }

  loading.value = true;
  try {
    const res = await getFinishProductDailyStats({
      start_date: finishDateRange.value[0],
      end_date: finishDateRange.value[1],
    });
    finishSummary.value = {
      ...emptyFinishSummary(),
      ...(res?.summary || {}),
    };
    currentStockInCount.value = res?.currentStockInCount ?? 0;
    dailyStats.value = res?.daily || [];
    finishDataLoaded.value = true;
    updateFinishDailyCharts();
  } catch (error) {
    console.error("获取成品统计数据失败", error);
  } finally {
    loading.value = false;
  }
};

const resetFinishDateRange = () => {
  finishDateRange.value = createDefaultFinishDateRange();
  fetchFinishData();
};

const updateFinishDailyCharts = () => {
  const dates = dailyStats.value.map((item) => item.date.slice(5));
  const legendData = finishChartSeries.map((item) => item.name);

  const buildSeriesData = (type: "line" | "bar") =>
    finishChartSeries.map((item) => ({
      name: item.name,
      type,
      smooth: type === "line",
      data: dailyStats.value.map((row) => row[item.key as keyof FinishDailyStat] as number),
      itemStyle: { color: item.color },
      ...(type === "line" ? {} : {}),
    }));

  dailyLineChartOptions.value = {
    tooltip: { trigger: "axis" },
    legend: {
      data: legendData,
      top: 0,
      type: "scroll",
    },
    grid: { left: "3%", right: "3%", bottom: "3%", top: "18%", containLabel: true },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: dates,
    },
    yAxis: {
      type: "value",
      minInterval: 1,
    },
    series: buildSeriesData("line"),
  };

  dailyBarChartOptions.value = {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: {
      data: legendData,
      top: 0,
      type: "scroll",
    },
    grid: { left: "3%", right: "3%", bottom: "3%", top: "18%", containLabel: true },
    xAxis: {
      type: "category",
      data: dates,
      axisLabel: {
        rotate: dates.length > 10 ? 45 : 0,
      },
    },
    yAxis: {
      type: "value",
      minInterval: 1,
    },
    series: buildSeriesData("bar"),
  };
};

const fetchMaterialData = async () => {
  loading.value = true;
  try {
    const res = await getProductList({ pageNum: 1, pageSize: 1000 });
    allProducts.value = res?.list || [];

    let totalQty = 0;
    let alertCount = 0;
    allProducts.value.forEach((p) => {
      const qty = Number(p.quantity) || 0;
      totalQty += qty;
      if (isMaterialAlert(p)) {
        alertCount++;
      }
    });

    materialStats.value = {
      totalCount: allProducts.value.length,
      alertCount,
      totalQuantity: totalQty,
    };

    updateMaterialCharts();
  } catch (error) {
    console.error("获取物料数据失败", error);
  } finally {
    loading.value = false;
  }
};

const updateMaterialCharts = () => {
  let filteredProducts = allProducts.value;
  if (chartProductType.value) {
    filteredProducts = allProducts.value.filter((p) => {
      if (chartProductType.value === "component") {
        return p.type === "component" || p.type === "finished";
      }
      return p.type === chartProductType.value;
    });
  }

  const alertCount = filteredProducts.filter(isMaterialAlert).length;
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
        label: { show: true },
        emphasis: {
          label: { show: true, fontSize: 20, fontWeight: "bold" },
        },
        data: [
          { value: safeCount, name: "安全", itemStyle: { color: "#67C23A" } },
          { value: alertCount, name: "报警", itemStyle: { color: "#F56C6C" } },
        ],
      },
    ],
  };

  const sortedProducts = [...filteredProducts]
    .map((p) => ({
      ...p,
      quantity: Number(p.quantity) || 0,
      alertQty: Number(p.alert_quantity) || 0,
    }))
    .sort((a, b) => {
      const scoreA =
        a.alertQty > 0 && a.quantity <= a.alertQty ? 0 :
        a.alertQty > 0 && a.quantity <= 2 * a.alertQty ? 1 : 2;
      const scoreB =
        b.alertQty > 0 && b.quantity <= b.alertQty ? 0 :
        b.alertQty > 0 && b.quantity <= 2 * b.alertQty ? 1 : 2;
      if (scoreA !== scoreB) return scoreA - scoreB;
      return Math.max(0, b.alertQty - b.quantity) - Math.max(0, a.alertQty - a.quantity);
    })
    .slice(0, 15);

  barChartOptions.value = {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params: any) => {
        const name = params[0].name;
        const product = sortedProducts.find((p) => p.name === name);
        if (!product) return name;
        let status = "";
        if (product.alertQty > 0 && product.quantity <= product.alertQty) {
          status = "缺料";
        } else if (product.alertQty > 0 && product.quantity <= 2 * product.alertQty) {
          status = "预警";
        } else {
          status = "安全";
        }
        return `${name}<br/>当前库存: ${product.quantity}<br/>报警线: ${product.alertQty}<br/>状态: ${status}`;
      },
    },
    grid: { left: "3%", right: "15%", bottom: "3%", top: "3%", containLabel: true },
    xAxis: { type: "value" },
    yAxis: {
      type: "category",
      data: sortedProducts.map((p) => p.name).reverse(),
    },
    series: [
      {
        type: "bar",
        data: sortedProducts
          .map((p) => ({
            value: p.quantity,
            itemStyle: {
              color:
                p.alertQty > 0 && p.quantity <= p.alertQty ? "#F56C6C" :
                p.alertQty > 0 && p.quantity <= 2 * p.alertQty ? "#E6A23C" :
                "#67C23A",
            },
          }))
          .reverse(),
        label: { show: true, position: "right" },
      },
    ],
  };

  const topAlertProducts = alertProducts.value.slice(0, 10);
  horizontalBarOptions.value = {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    grid: { left: "3%", right: "10%", bottom: "3%", top: "3%", containLabel: true },
    xAxis: { type: "value" },
    yAxis: {
      type: "category",
      data: topAlertProducts.map((p) => p.name).reverse(),
    },
    series: [
      {
        name: "缺件数量",
        type: "bar",
        data: topAlertProducts
          .map((p) => Math.max(0, (Number(p.alert_quantity) || 0) - (Number(p.quantity) || 0)))
          .reverse(),
        itemStyle: {
          color: (params: any) => {
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

const handleBoardTypeChange = () => {
  if (boardType.value === "material") {
    if (allProducts.value.length === 0) {
      fetchMaterialData();
    } else {
      updateMaterialCharts();
    }
    return;
  }

  if (!finishDataLoaded.value) {
    fetchFinishData();
  } else {
    updateFinishDailyCharts();
  }
};

onMounted(() => {
  fetchFinishData();
});
</script>

<style lang="scss" scoped>
.app-container {
  padding: 20px;
}

.board-type-card {
  :deep(.el-card__body) {
    padding: 16px 20px;
  }
}

.text-muted {
  color: #909399;
  font-style: italic;
}
</style>
