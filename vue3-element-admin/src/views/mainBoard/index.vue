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
                    <el-option label="自制" :value="0" />
                    <el-option label="外协" :value="1" />
                    <el-option label="外购" :value="2" />
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

      <el-row :gutter="10" class="mt-2 finish-stat-row finish-stat-row--9">
        <el-col :xs="12" :sm="8" :md="6" :lg="3" class="mb-3">
          <el-card
            shadow="never"
            class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            :class="{ 'stat-card--clickable': finishSummary.newCount > 0 }"
            @click="openBoardDetail('newCount', finishSummary.newCount)"
          >
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
          <el-card
            shadow="never"
            class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            :class="{ 'stat-card--clickable': finishSummary.pendingNewCount > 0 }"
            @click="openBoardDetail('pendingNewCount', finishSummary.pendingNewCount)"
          >
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
          <el-card
            shadow="never"
            class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            :class="{ 'stat-card--clickable': finishSummary.testingCount > 0 }"
            @click="openBoardDetail('testingCount', finishSummary.testingCount)"
          >
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">新品正在测试</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-sky-600">{{ finishSummary.testingCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="6" :lg="3" class="mb-3">
          <el-card
            shadow="never"
            class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            :class="{ 'stat-card--clickable': finishSummary.passCount > 0 }"
            @click="openBoardDetail('passCount', finishSummary.passCount)"
          >
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
          <el-card
            shadow="never"
            class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            :class="{ 'stat-card--clickable': finishSummary.failCount > 0 }"
            @click="openBoardDetail('failCount', finishSummary.failCount)"
          >
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
          <el-card
            shadow="never"
            class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            :class="{ 'stat-card--clickable': finishSummary.repairCount > 0 }"
            @click="openBoardDetail('repairCount', finishSummary.repairCount)"
          >
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
          <el-card
            shadow="never"
            class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            :class="{ 'stat-card--clickable': finishSummary.repairTestingCount > 0 }"
            @click="openBoardDetail('repairTestingCount', finishSummary.repairTestingCount)"
          >
            <template #header>
              <span class="text-xs font-medium text-[--el-text-color-secondary]">返修正在测试</span>
            </template>
            <div class="mt-2 flex items-baseline gap-1.5">
              <span class="text-2xl font-semibold text-cyan-600">{{ finishSummary.repairTestingCount }}</span>
              <span class="text-xs text-[--el-text-color-secondary]">件</span>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="12" :sm="8" :md="6" :lg="3" class="mb-3">
          <el-card
            shadow="never"
            class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            :class="{ 'stat-card--clickable': finishSummary.pendingRepairCount > 0 }"
            @click="openBoardDetail('pendingRepairCount', finishSummary.pendingRepairCount)"
          >
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
          <el-card
            shadow="never"
            class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            :class="{ 'stat-card--clickable': finishSummary.repairPassCount > 0 }"
            @click="openBoardDetail('repairPassCount', finishSummary.repairPassCount)"
          >
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
          <el-card
            shadow="never"
            class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            :class="{ 'stat-card--clickable': currentStockInCount > 0 }"
            @click="openBoardDetail('currentStockInCount', currentStockInCount)"
          >
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
          <el-card
            shadow="never"
            class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            :class="{ 'stat-card--clickable': finishSummary.stockInCount > 0 }"
            @click="openBoardDetail('stockInCount', finishSummary.stockInCount)"
          >
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
          <el-card
            shadow="never"
            class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
            :class="{ 'stat-card--clickable': finishSummary.stockOutCount > 0 }"
            @click="openBoardDetail('stockOutCount', finishSummary.stockOutCount)"
          >
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
              <el-table-column prop="newCount" label="新增成品" width="100" align="center">
                <template #default="{ row }">
                  <span
                    v-if="row.newCount > 0"
                    class="stat-cell-link text-blue-600"
                    @click.stop="openBoardDetail('newCount', row.newCount, row.date)"
                  >{{ row.newCount }}</span>
                  <span v-else>{{ row.newCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="pendingNewCount" label="待测试新品" width="110" align="center">
                <template #default="{ row }">
                  <span
                    v-if="row.pendingNewCount > 0"
                    class="stat-cell-link text-purple-600"
                    @click.stop="openBoardDetail('pendingNewCount', row.pendingNewCount, row.date)"
                  >{{ row.pendingNewCount }}</span>
                  <span v-else class="text-purple-600">{{ row.pendingNewCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="testingCount" label="新品正在测试" width="120" align="center">
                <template #default="{ row }">
                  <span
                    v-if="row.testingCount > 0"
                    class="stat-cell-link text-sky-600"
                    @click.stop="openBoardDetail('testingCount', row.testingCount, row.date)"
                  >{{ row.testingCount }}</span>
                  <span v-else class="text-sky-600">{{ row.testingCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="passCount" label="测试合格" width="100" align="center">
                <template #default="{ row }">
                  <span
                    v-if="row.passCount > 0"
                    class="stat-cell-link text-green-600"
                    @click.stop="openBoardDetail('passCount', row.passCount, row.date)"
                  >{{ row.passCount }}</span>
                  <span v-else class="text-green-600">{{ row.passCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="failCount" label="测试不良" width="100" align="center">
                <template #default="{ row }">
                  <span
                    v-if="row.failCount > 0"
                    class="stat-cell-link text-red-600"
                    @click.stop="openBoardDetail('failCount', row.failCount, row.date)"
                  >{{ row.failCount }}</span>
                  <span v-else class="text-red-600">{{ row.failCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="repairCount" label="新增返修" width="100" align="center">
                <template #default="{ row }">
                  <span
                    v-if="row.repairCount > 0"
                    class="stat-cell-link"
                    @click.stop="openBoardDetail('repairCount', row.repairCount, row.date)"
                  >{{ row.repairCount }}</span>
                  <span v-else>{{ row.repairCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="repairTestingCount" label="返修正在测试" width="120" align="center">
                <template #default="{ row }">
                  <span
                    v-if="row.repairTestingCount > 0"
                    class="stat-cell-link text-cyan-600"
                    @click.stop="openBoardDetail('repairTestingCount', row.repairTestingCount, row.date)"
                  >{{ row.repairTestingCount }}</span>
                  <span v-else class="text-cyan-600">{{ row.repairTestingCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="pendingRepairCount" label="待测试返修" width="110" align="center">
                <template #default="{ row }">
                  <span
                    v-if="row.pendingRepairCount > 0"
                    class="stat-cell-link text-amber-600"
                    @click.stop="openBoardDetail('pendingRepairCount', row.pendingRepairCount, row.date)"
                  >{{ row.pendingRepairCount }}</span>
                  <span v-else class="text-amber-600">{{ row.pendingRepairCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="repairPassCount" label="返修合格" width="100" align="center">
                <template #default="{ row }">
                  <span
                    v-if="row.repairPassCount > 0"
                    class="stat-cell-link"
                    @click.stop="openBoardDetail('repairPassCount', row.repairPassCount, row.date)"
                  >{{ row.repairPassCount }}</span>
                  <span v-else>{{ row.repairPassCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="stockInCount" label="入库数量" width="100" align="center">
                <template #default="{ row }">
                  <span
                    v-if="row.stockInCount > 0"
                    class="stat-cell-link text-violet-600"
                    @click.stop="openBoardDetail('stockInCount', row.stockInCount, row.date)"
                  >{{ row.stockInCount }}</span>
                  <span v-else class="text-violet-600">{{ row.stockInCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="stockOutCount" label="出库数量" width="100" align="center">
                <template #default="{ row }">
                  <span
                    v-if="row.stockOutCount > 0"
                    class="stat-cell-link text-slate-600"
                    @click.stop="openBoardDetail('stockOutCount', row.stockOutCount, row.date)"
                  >{{ row.stockOutCount }}</span>
                  <span v-else class="text-slate-600">{{ row.stockOutCount }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-dialog
      v-model="detailDialogVisible"
      :title="detailDialogTitle"
      width="1080px"
      destroy-on-close
      class="finish-detail-dialog"
    >
      <div class="detail-table-toolbar">
        <el-button @click="openColumnDialog">
          <el-icon><Setting /></el-icon> 列展示
        </el-button>
      </div>
      <el-table
        :data="detailList"
        border
        stripe
        style="width: 100%"
        max-height="480px"
        v-loading="detailLoading"
      >
        <el-table-column type="index" label="序号" width="60" align="center" fixed="left" />
        <el-table-column
          v-if="isColumnVisible('sn_code')"
          prop="sn_code"
          label="SN码"
          min-width="180"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span v-if="row.sn_code">{{ row.sn_code }}</span>
            <span v-else class="text-muted">待填写</span>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('bom_type')"
          prop="bom_type_name"
          label="BOM类型"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <el-tag :type="bomTypeTagType(row.bom_type)" size="small">
              {{ row.bom_type_name || '—' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('bom_model')"
          prop="bom_model"
          label="BOM型号"
          min-width="120"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('bom_name')"
          prop="bom_name"
          label="BOM名称"
          min-width="120"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('material_code')"
          prop="material_code"
          label="物料编码"
          min-width="110"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('status')"
          prop="status"
          label="测试状态"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ row.status_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('inventory_stock')"
          prop="inventory_stock"
          label="库存状态"
          width="100"
          align="center"
        >
          <template #default="{ row }">
            <el-tag :type="inventoryTagType(row.inventory_stock)" size="small">
              {{ row.inventory_stock_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('repair')"
          prop="repair"
          label="返修"
          width="90"
          align="center"
        >
          <template #default="{ row }">
            <el-tag :type="row.repair === 1 ? 'warning' : 'info'" size="small">
              {{ row.repair_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('create_time')"
          prop="create_time"
          label="创建时间"
          width="170"
        />
        <el-table-column
          v-if="isColumnVisible('update_time')"
          prop="update_time"
          label="更新时间"
          width="170"
        />
        <el-table-column
          v-if="isColumnVisible('description')"
          prop="description"
          label="描述"
          min-width="140"
          show-overflow-tooltip
        />
      </el-table>
      <div class="detail-pagination">
        <el-pagination
          v-model:current-page="detailPageNum"
          v-model:page-size="detailPageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          :total="detailTotal"
          @size-change="fetchBoardDetail"
          @current-change="fetchBoardDetail"
        />
      </div>
    </el-dialog>

    <el-dialog v-model="columnDialogVisible" title="列展示设置" width="480px" destroy-on-close>
      <div class="column-setting-tip">勾选需要在表格中展示的字段（序号列始终显示）</div>
      <el-checkbox-group v-model="columnDraftKeys" class="column-checkbox-group">
        <el-checkbox v-for="col in columnOptions" :key="col.key" :label="col.key">
          {{ col.label }}
        </el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="resetColumnDraft">恢复默认</el-button>
        <el-button @click="columnDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveColumnSettings">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "MainBoard",
});

import { ref, computed, onMounted, watch } from "vue";
import { getProductList } from "@/api/product";
import { getFinishProductDailyStats, getFinishProductBoardDetail } from "@/api/finish-product";
import ECharts from "@/components/ECharts/index.vue";
import { InfoFilled, Setting } from "@element-plus/icons-vue";
import { useFinishProductTableColumns, FINISH_PRODUCT_BOARD_DETAIL_COLUMN_STORAGE_KEY } from "@/composables/useFinishProductTableColumns";

const {
  columnOptions,
  columnDialogVisible,
  columnDraftKeys,
  isColumnVisible,
  loadColumnSettings,
  openColumnDialog,
  resetColumnDraft,
  saveColumnSettings,
} = useFinishProductTableColumns(FINISH_PRODUCT_BOARD_DETAIL_COLUMN_STORAGE_KEY);

type BoardType = "material" | "finish";

interface FinishDailyStat {
  date: string;
  newCount: number;
  passCount: number;
  failCount: number;
  pendingNewCount: number;
  testingCount: number;
  repairCount: number;
  repairTestingCount: number;
  repairPassCount: number;
  pendingRepairCount: number;
  stockInCount: number;
  stockOutCount: number;
}

const finishChartSeries = [
  { name: "新增成品", key: "newCount", color: "#409EFF" },
  { name: "待测试新品", key: "pendingNewCount", color: "#9333EA" },
  { name: "新品正在测试", key: "testingCount", color: "#0EA5E9" },
  { name: "测试合格", key: "passCount", color: "#67C23A" },
  { name: "测试不良", key: "failCount", color: "#F56C6C" },
  { name: "新增返修", key: "repairCount", color: "#E6A23C" },
  { name: "返修正在测试", key: "repairTestingCount", color: "#06B6D4" },
  { name: "待测试返修", key: "pendingRepairCount", color: "#F59E0B" },
  { name: "返修合格", key: "repairPassCount", color: "#13C2C2" },
  { name: "入库数量", key: "stockInCount", color: "#8B5CF6" },
  { name: "出库数量", key: "stockOutCount", color: "#64748B" },
] as const;

const boardCategoryLabels: Record<string, string> = {
  newCount: "新增成品",
  pendingNewCount: "待测试新品",
  testingCount: "新品正在测试",
  passCount: "测试合格",
  failCount: "测试不良",
  repairCount: "新增返修",
  repairTestingCount: "返修正在测试",
  pendingRepairCount: "待测试返修",
  repairPassCount: "返修合格",
  stockInCount: "入库数量",
  stockOutCount: "出库数量",
  currentStockInCount: "成品库存",
};

type BoardCategoryKey = keyof typeof boardCategoryLabels;

const emptyFinishSummary = () => ({
  newCount: 0,
  passCount: 0,
  failCount: 0,
  pendingNewCount: 0,
  testingCount: 0,
  repairCount: 0,
  repairTestingCount: 0,
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

const FINISH_BOARD_DATE_RANGE_STORAGE_KEY = "finish-board-date-range";
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

const isValidDateRange = (value: unknown): value is [string, string] => {
  if (!Array.isArray(value) || value.length !== 2) {
    return false;
  }
  const [start, end] = value;
  return (
    typeof start === "string" &&
    typeof end === "string" &&
    DATE_PATTERN.test(start) &&
    DATE_PATTERN.test(end) &&
    start <= end
  );
};

const loadFinishDateRange = (): [string, string] => {
  const saved = localStorage.getItem(FINISH_BOARD_DATE_RANGE_STORAGE_KEY);
  if (!saved) {
    return createDefaultFinishDateRange();
  }
  try {
    const parsed = JSON.parse(saved);
    if (isValidDateRange(parsed)) {
      return parsed;
    }
  } catch {
    // ignore invalid saved value
  }
  return createDefaultFinishDateRange();
};

const saveFinishDateRange = (range: [string, string]) => {
  if (!isValidDateRange(range)) {
    return;
  }
  localStorage.setItem(FINISH_BOARD_DATE_RANGE_STORAGE_KEY, JSON.stringify(range));
};

const loading = ref(false);
const boardType = ref<BoardType>("finish");
const allProducts = ref<any[]>([]);
const chartProductType = ref("");
const finishDateRange = ref<[string, string]>(loadFinishDateRange());

watch(finishDateRange, (range) => {
  saveFinishDateRange(range);
});
const finishSummary = ref(emptyFinishSummary());
const currentStockInCount = ref(0);
const dailyStats = ref<FinishDailyStat[]>([]);
const finishDataLoaded = ref(false);

const detailDialogVisible = ref(false);
const detailDialogTitle = ref("");
const detailLoading = ref(false);
const detailList = ref<any[]>([]);
const detailTotal = ref(0);
const detailPageNum = ref(1);
const detailPageSize = ref(10);
const detailCategory = ref<BoardCategoryKey>("newCount");
const detailSingleDate = ref<string | null>(null);

const inventoryTagType = (value: number) => {
  if (value === 1) return "success";
  if (value === 2) return "danger";
  return "warning";
};

const statusTagType = (value: number) => {
  if (value === 2) return "success";
  if (value === 3) return "danger";
  if (value === 1) return "primary";
  return "warning";
};

const bomTypeTagType = (value: number | null | undefined) => {
  if (value === 1) return "primary";
  if (value === 2) return "info";
  return "success";
};

const buildDetailTitle = (category: BoardCategoryKey, singleDate?: string | null) => {
  const label = boardCategoryLabels[category] || category;
  if (category === "currentStockInCount") {
    return `${label} - 明细（当前已入库）`;
  }
  if (singleDate) {
    return `${label} - 明细（${singleDate}）`;
  }
  const [start, end] = finishDateRange.value || [];
  if (start && end) {
    return start === end ? `${label} - 明细（${start}）` : `${label} - 明细（${start} 至 ${end}）`;
  }
  return `${label} - 明细`;
};

const fetchBoardDetail = async () => {
  detailLoading.value = true;
  try {
    const params: {
      category: string;
      start_date?: string;
      end_date?: string;
      date?: string;
      pageNum?: number;
      pageSize?: number;
    } = {
      category: detailCategory.value,
      pageNum: detailPageNum.value,
      pageSize: detailPageSize.value,
    };
    if (detailCategory.value !== "currentStockInCount") {
      if (detailSingleDate.value) {
        params.date = detailSingleDate.value;
      } else if (finishDateRange.value?.[0] && finishDateRange.value?.[1]) {
        params.start_date = finishDateRange.value[0];
        params.end_date = finishDateRange.value[1];
      }
    }
    const res = await getFinishProductBoardDetail(params);
    detailList.value = res?.list || [];
    detailTotal.value = res?.total || 0;
  } catch (error) {
    console.error("获取成品明细失败", error);
    detailList.value = [];
    detailTotal.value = 0;
  } finally {
    detailLoading.value = false;
  }
};

const openBoardDetail = (category: BoardCategoryKey, count: number, singleDate?: string) => {
  if (!count || count <= 0) {
    return;
  }
  detailCategory.value = category;
  detailSingleDate.value = singleDate || null;
  detailPageNum.value = 1;
  detailDialogTitle.value = buildDetailTitle(category, singleDate);
  detailDialogVisible.value = true;
  fetchBoardDetail();
};

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
  if (chartProductType.value !== "" && chartProductType.value !== null) {
    filteredProducts = allProducts.value.filter(
      (p) => Number(p.type) === Number(chartProductType.value)
    );
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
  loadColumnSettings();
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

.stat-card--clickable {
  cursor: pointer;
}

.finish-stat-row--9 {
  @media (min-width: 1200px) {
    flex-wrap: nowrap;

    > .el-col {
      flex: 0 0 11.111111%;
      max-width: 11.111111%;
    }
  }

  :deep(.el-card__header) {
    padding: 10px 12px;
  }

  :deep(.el-card__body) {
    padding: 12px;
  }
}

.stat-cell-link {
  cursor: pointer;
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.stat-cell-link:hover {
  opacity: 0.85;
}

.detail-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-table-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.column-setting-tip {
  margin-bottom: 12px;
  color: #909399;
  font-size: 13px;
}

.column-checkbox-group {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px 12px;
}
</style>
