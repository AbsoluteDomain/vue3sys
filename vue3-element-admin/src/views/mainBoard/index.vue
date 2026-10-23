<template>
  <div v-loading="loading" class="app-container">
    <el-card shadow="never" class="mb-3 board-type-card">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div class="flex items-center gap-3">
          <span class="font-semibold text-base">库存看板</span>
          <el-radio-group v-model="boardType" @change="handleBoardTypeChange">
            <el-radio-button value="finish">成品</el-radio-button>
            <el-radio-button value="material">物料</el-radio-button>
          </el-radio-group>
        </div>
        <el-button type="primary" @click="openJointReportDialog">
          <el-icon><DataAnalysis /></el-icon> 关节测试每日报表
        </el-button>
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
        <div class="flex items-center justify-start flex-wrap gap-3">
          <div class="flex items-center gap-3 flex-wrap">
            <span class="text-sm text-[--el-text-color-regular]">统计周期：</span>
            <el-select v-model="periodType" placeholder="快捷选择" style="width: 140px" @change="onPeriodChange" clearable>
              <el-option label="今日" value="today" />
              <el-option label="本周" value="week" />
              <el-option label="本月" value="month" />
              <el-option label="本年" value="year" />
              <el-option label="近7天" value="7d" />
              <el-option label="近30天" value="30d" />
            </el-select>
            <span class="text-sm text-[--el-text-color-secondary]">或</span>
            <el-date-picker
              v-model="finishDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :shortcuts="dateRangeShortcuts"
              @change="onCustomDateChange"
            />
          </div>
          <div class="flex items-center gap-3">
            <span class="text-sm text-[--el-text-color-regular]">BOM类型：</span>
            <el-select v-model="bomType" placeholder="全部" style="width: 120px" @change="fetchFinishData">
              <el-option label="全部" value="" />
              <el-option label="机械臂" value="arm" />
              <el-option label="关节" value="joint" />
            </el-select>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-sm text-[--el-text-color-regular]" style="width: 90px">产品型号：</span>
            <el-select
              v-model="bomModelIds"
              multiple
              collapse-tags
              collapse-tags-tooltip
              filterable
              clearable
              placeholder="请选择产品型号（默认全部）"
              style="min-width: 280px"
              @change="fetchFinishData"
            >
              <el-option
                v-for="bom in boardBomList"
                :key="bom.id"
                :label="bom.bom_model || bom.bom_name"
                :value="bom.id"
              >
                <span>{{ bom.bom_model }}</span>
                <span style="float: right; color: #8492a6; font-size: 13px">{{ bom.bom_name }}</span>
              </el-option>
            </el-select>
          </div>
          <div class="flex items-center gap-4 flex-wrap">
            <div class="flex items-center gap-2">
              <span class="text-sm text-[--el-text-color-regular]">创建人：</span>
              <el-input
                v-model="creatorName"
                clearable
                placeholder="全部"
                style="width: 140px"
                @clear="fetchFinishData"
                @keyup.enter="fetchFinishData"
              />
            </div>
            <div class="flex items-center gap-2">
              <span class="text-sm text-[--el-text-color-regular]">最后修改人：</span>
              <el-input
                v-model="editorName"
                clearable
                placeholder="全部"
                style="width: 140px"
                @clear="fetchFinishData"
                @keyup.enter="fetchFinishData"
              />
            </div>
            <div class="flex items-center gap-2">
              <span class="text-sm text-[--el-text-color-regular]">SN码绑定人：</span>
              <el-input
                v-model="snCodeBinder"
                clearable
                placeholder="全部"
                style="width: 140px"
                @clear="fetchFinishData"
                @keyup.enter="fetchFinishData"
              />
            </div>
            <el-button type="primary" :icon="Refresh" @click="fetchFinishData">刷新</el-button>
          </div>
        </div>
      </el-card>

      <el-collapse v-model="activeBoardPanels" class="board-collapse mt-2" @change="handleBoardPanelChange">
        <el-collapse-item name="newRepair">
          <template #title>
            <span class="font-semibold">新品返修相关</span>
          </template>
      <el-row :gutter="10" class="mt-2">
        <el-col :xs="24" :lg="13" class="mb-3">
          <el-card shadow="never" class="h-full">
            <template #header>
              <div class="flex items-center gap-2">
                <span class="font-semibold">新品相关</span>
              </div>
            </template>
            <div class="compact-stat-grid grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-1.5">
              <div>
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.newCount > 0 }"
                  @click="openBoardDetail('newCount', finishSummary.newCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">新增成品</span>
                      <el-tooltip content="仅有SN码的算成品；有SN码录入时间的按录入时间统计，旧数据（无录入时间）按更新时间统计" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-blue-600">{{ finishSummary.newCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </div>
              <div>
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.pendingNewCount > 0 }"
                  @click="openBoardDetail('pendingNewCount', finishSummary.pendingNewCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">待测试新品</span>
                      <el-tooltip content="状态为未测试的新品（仅有SN码）；有SN码录入时间的按录入时间统计，旧数据（无录入时间）按测试状态修改时间统计" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-purple-600">{{ finishSummary.pendingNewCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </div>
              <div>
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.testingCount > 0 }"
                  @click="openBoardDetail('testingCount', finishSummary.testingCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">新品正在测试</span>
                      <el-tooltip content="按测试状态修改时间统计，状态为测试中且为新品的数量" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-sky-600">{{ finishSummary.testingCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </div>
              <div>
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.passCount > 0 }"
                  @click="openBoardDetail('passCount', finishSummary.passCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">新品测试合格</span>
                      <el-tooltip content="按测试状态修改时间统计，新品测试状态为合格的数量" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-green-600">{{ finishSummary.passCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </div>
              <div>
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.failCount > 0 }"
                  @click="openBoardDetail('failCount', finishSummary.failCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">新品测试不良</span>
                      <el-tooltip content="按测试状态修改时间统计，新品测试状态为不良的数量" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-red-600">{{ finishSummary.failCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </div>
              <div>
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': currentUnassembledCount > 0 }"
                  @click="openBoardDetail('unassembledCount', currentUnassembledCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">未组装</span>
                      <el-tooltip content="SN码为空的成品，按创建时间筛选" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-gray-600">{{ currentUnassembledCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </div>
            </div>
            <ECharts :options="newProductPassRateOptions" height="260px" class="mt-2" />
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="11" class="mb-3">
          <el-card shadow="never" class="h-full">
            <template #header>
              <div class="flex items-center gap-2">
                <span class="font-semibold">返修品相关</span>
              </div>
            </template>
            <div class="compact-stat-grid grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-1.5">
              <div>
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.repairCount > 0 }"
                  @click="openBoardDetail('repairCount', finishSummary.repairCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">新增返修</span>
                      <el-tooltip content="按产品更新时间统计，标记为返修品的产品数量" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-orange-600">{{ finishSummary.repairCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </div>
              <div>
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.pendingRepairCount > 0 }"
                  @click="openBoardDetail('pendingRepairCount', finishSummary.pendingRepairCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">待测试返修</span>
                      <el-tooltip content="按测试状态修改时间统计，状态为未测试且为返修品的数量" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-amber-600">{{ finishSummary.pendingRepairCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </div>
              <div>
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.repairTestingCount > 0 }"
                  @click="openBoardDetail('repairTestingCount', finishSummary.repairTestingCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">返修正在测试</span>
                      <el-tooltip content="按测试状态修改时间统计，状态为测试中且为返修品的数量" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-cyan-600">{{ finishSummary.repairTestingCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </div>
              <div>
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.repairPassCount > 0 }"
                  @click="openBoardDetail('repairPassCount', finishSummary.repairPassCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">返修测试合格</span>
                      <el-tooltip content="按测试状态修改时间统计，返修品测试状态为合格的数量" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-teal-600">{{ finishSummary.repairPassCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </div>
              <div>
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.repairFailCount > 0 }"
                  @click="openBoardDetail('repairFailCount', finishSummary.repairFailCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">返修测试不良</span>
                      <el-tooltip content="按测试状态修改时间统计，返修品测试状态为不良的数量" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-red-600">{{ finishSummary.repairFailCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </div>
            </div>
            <ECharts :options="repairProductPassRateOptions" height="260px" class="mt-2" />
          </el-card>
        </el-col>
      </el-row>

        </el-collapse-item>
        <el-collapse-item name="stockFlow">
          <template #title>
            <span class="font-semibold">库存与出入库相关</span>
          </template>
      <el-row :gutter="10" class="mt-2">
        <el-col :xs="24" class="mb-3">
          <el-card shadow="never">
            <template #header>
              <div class="flex items-center gap-2">
                <span class="font-semibold">库存与出入库</span>
              </div>
            </template>
            <el-row :gutter="10">
              <el-col :xs="12" :sm="6" :md="6" :lg="3" class="mb-3">
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': currentStockInCount > 0 }"
                  @click="openBoardDetail('currentStockInCount', currentStockInCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">成品库存</span>
                      <el-tooltip content="当前所有状态为入库的成品总数，不受日期筛选影响" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-indigo-600">{{ currentStockInCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </el-col>
              <el-col :xs="12" :sm="6" :md="6" :lg="3" class="mb-3">
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.stockInCount > 0 }"
                  @click="openBoardDetail('stockInCount', finishSummary.stockInCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">入库数量</span>
                      <el-tooltip content="按入库时间统计指定周期内入库的成品数量" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-violet-600">{{ finishSummary.stockInCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </el-col>
              <el-col :xs="12" :sm="6" :md="6" :lg="3" class="mb-3">
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.stockOutCount > 0 }"
                  @click="openBoardDetail('stockOutCount', finishSummary.stockOutCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">出库数量</span>
                      <el-tooltip content="按出库时间统计指定周期内出库的成品总数（含外销和研发）" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-slate-600">{{ finishSummary.stockOutCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </el-col>
              <el-col :xs="12" :sm="6" :md="6" :lg="3" class="mb-3">
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.stockOutSaleCount > 0 }"
                  @click="openBoardDetail('stockOutSaleCount', finishSummary.stockOutSaleCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">出库(外销)数量</span>
                      <el-tooltip content="按出库时间统计指定周期内出库类型为外销的成品数量" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-blue-600">{{ finishSummary.stockOutSaleCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </el-col>
              <el-col :xs="12" :sm="6" :md="6" :lg="3" class="mb-3">
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': finishSummary.stockOutDevCount > 0 }"
                  @click="openBoardDetail('stockOutDevCount', finishSummary.stockOutDevCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">出库(研发)数量</span>
                      <el-tooltip content="按出库时间统计指定周期内出库类型为研发的成品数量" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-orange-600">{{ finishSummary.stockOutDevCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </el-col>
              <el-col :xs="12" :sm="6" :md="6" :lg="3" class="mb-3">
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                  :class="{ 'stat-card--clickable': currentConsumeCount > 0 }"
                  @click="openBoardDetail('currentConsumeCount', currentConsumeCount)"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">组件消耗</span>
                      <el-tooltip content="绑定关节后被消耗的成品总数，属成品的一种流出方式，不受日期筛选影响" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-amber-600">{{ currentConsumeCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </el-col>
              <el-col :xs="12" :sm="6" :md="6" :lg="3" class="mb-3">
                <el-card
                  shadow="never"
                  class="h-full transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                >
                  <template #header>
                    <div class="flex items-center gap-2">
                      <span class="text-xs font-medium text-[--el-text-color-secondary]">流出合计</span>
                      <el-tooltip content="本周期出库数量 + 当前组件消耗数量；成品库存 = 入库数量 − 流出合计" placement="top">
                        <el-icon class="cursor-pointer text-gray-400"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </template>
                  <div class="mt-2 flex items-baseline gap-1.5">
                    <span class="text-2xl font-semibold text-rose-600">{{ totalOutflowCount }}</span>
                    <span class="text-xs text-[--el-text-color-secondary]">件</span>
                  </div>
                </el-card>
              </el-col>
            </el-row>
            <div class="mt-4 flex items-center justify-end gap-4">
              <div class="flex items-center gap-2">
                <span class="text-xs text-[--el-text-color-secondary]">饼图</span>
                <el-switch v-model="showStockPies" size="small" />
              </div>
              <div class="flex items-center gap-2">
                <span class="text-xs text-[--el-text-color-secondary]">表格</span>
                <el-switch v-model="showStockTable" size="small" />
              </div>
            </div>
            <el-row v-if="showStockPies" :gutter="20" class="mt-2">
              <el-col :xs="24" :md="8" class="mb-4">
                <div class="text-xs font-medium text-[--el-text-color-secondary] mb-2">入库 BOM 型号占比</div>
                <ECharts :options="bomStockInPieOptions" height="330px" />
              </el-col>
              <el-col :xs="24" :md="8" class="mb-4">
                <div class="text-xs font-medium text-[--el-text-color-secondary] mb-2">出库 BOM 型号占比</div>
                <ECharts :options="bomStockOutPieOptions" height="330px" />
              </el-col>
              <el-col :xs="24" :md="8" class="mb-4">
                <div class="text-xs font-medium text-[--el-text-color-secondary] mb-2">出库类型占比</div>
                <ECharts :options="outboundRatioOptions" height="330px" />
              </el-col>
            </el-row>
            <div v-if="showStockTable" class="mt-4 mb-2 flex items-center justify-end">
              <el-button size="small" @click="openBomColumnDialog">
                <el-icon><Setting /></el-icon> 列展示
              </el-button>
            </div>
            <el-table
              v-if="showStockTable"
              ref="bomStockTableRef"
              :data="bomStockTableRows"
              size="default"
              border
              :show-summary="bomStockTableRows.length > 0"
              :summary-method="bomStockSummaryMethod"
              empty-text="当前筛选条件下暂无出入库数据"
            >
              <el-table-column
                v-if="isBomColumnVisible('bom_model')"
                prop="bom_model"
                sortable
                label="BOM型号"
                min-width="140"
                show-overflow-tooltip
              />
              <el-table-column
                v-if="isBomColumnVisible('bom_name')"
                prop="bom_name"
                sortable
                label="名称"
                min-width="140"
                show-overflow-tooltip
              />
              <el-table-column
                v-if="isBomColumnVisible('stockCount')"
                prop="stockCount"
                sortable
                label="当前剩余库存"
                width="150"
                align="right"
              >
                <template #default="{ row }">
                  <span class="bom-stock-value">{{ row.stockCount }}</span>
                </template>
              </el-table-column>
              <el-table-column
                v-if="isBomColumnVisible('inCount')"
                prop="inCount"
                sortable
                label="入库数"
                width="100"
                align="right"
              />
              <el-table-column
                v-if="isBomColumnVisible('inPercent')"
                prop="inPercent"
                sortable
                label="入库占比"
                width="110"
                align="right"
              >
                <template #default="{ row }">{{ row.inPercent.toFixed(1) }}%</template>
              </el-table-column>
              <el-table-column
                v-if="isBomColumnVisible('outCount')"
                prop="outCount"
                sortable
                label="出库数"
                width="100"
                align="right"
              />
              <el-table-column
                v-if="isBomColumnVisible('outPercent')"
                prop="outPercent"
                sortable
                label="出库占比"
                width="110"
                align="right"
              >
                <template #default="{ row }">{{ row.outPercent.toFixed(1) }}%</template>
              </el-table-column>
              <el-table-column
                v-if="isBomColumnVisible('outSaleCount')"
                prop="outSaleCount"
                sortable
                label="出库(外销)"
                width="120"
                align="right"
              />
              <el-table-column
                v-if="isBomColumnVisible('outDevCount')"
                prop="outDevCount"
                sortable
                label="出库(研发)"
                width="120"
                align="right"
              />
              
            </el-table>
          </el-card>
        </el-col>
      </el-row>

        </el-collapse-item>
        <el-collapse-item name="dailyTrend">
          <template #title>
            <span class="font-semibold">每日成品趋势</span>
          </template>
      <el-row :gutter="10" class="mt-2">
        <el-col :xs="24" class="mb-3">
          <el-card>
            <template #header>
              <div class="flex items-center gap-2">
                <span class="font-semibold">每日成品趋势</span>
                <el-tooltip
                  :content="finishTrendTooltipHint"
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

        </el-collapse-item>
        <el-collapse-item name="dailyCompare">
          <template #title>
            <span class="font-semibold">每日统计对比</span>
          </template>
      <el-row :gutter="10" class="mt-2">
        <el-col :xs="24" class="mb-3">
          <el-card>
            <template #header>
              <div class="flex items-center gap-2">
                <span class="font-semibold">每日统计对比</span>
                <el-tooltip :content="finishTrendTooltipHint" placement="top">
                  <el-icon class="text-gray-400 cursor-pointer"><InfoFilled /></el-icon>
                </el-tooltip>
              </div>
            </template>
            <ECharts :options="dailyBarChartOptions" height="420px" />
          </el-card>
        </el-col>
      </el-row>

        </el-collapse-item>
        <el-collapse-item name="dailyDetail">
          <template #title>
            <span class="font-semibold">每日统计明细</span>
          </template>
      <el-row :gutter="10" class="mt-2">
        <el-col :xs="24" class="mb-3">
          <el-card>
            <template #header>
              <span class="font-semibold">每日统计明细</span>
            </template>
            <el-table ref="dailyStatsTableRef" :data="dailyStatsDisplay" border stripe style="width: 100%" max-height="420px">
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
              <el-table-column prop="stockOutSaleCount" label="出库(外销)" width="110" align="center">
                <template #default="{ row }">
                  <span
                    v-if="row.stockOutSaleCount > 0"
                    class="stat-cell-link text-blue-600"
                    @click.stop="openBoardDetail('stockOutSaleCount', row.stockOutSaleCount, row.date)"
                  >{{ row.stockOutSaleCount }}</span>
                  <span v-else class="text-blue-600">{{ row.stockOutSaleCount }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="stockOutDevCount" label="出库(研发)" width="110" align="center">
                <template #default="{ row }">
                  <span
                    v-if="row.stockOutDevCount > 0"
                    class="stat-cell-link text-orange-600"
                    @click.stop="openBoardDetail('stockOutDevCount', row.stockOutDevCount, row.date)"
                  >{{ row.stockOutDevCount }}</span>
                  <span v-else class="text-orange-600">{{ row.stockOutDevCount }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
        </el-collapse-item>
      </el-collapse>
    </template>

    <el-dialog
      v-model="detailDialogVisible"
      :title="detailDialogTitle"
      width="1280px"
      destroy-on-close
      class="finish-detail-dialog"
    >
      <div class="detail-table-toolbar">
        <el-button @click="openColumnDialog">
          <el-icon><Setting /></el-icon> 列展示
        </el-button>
      </div>
      <el-table
        ref="detailTableRef"
        :data="detailList"
        border
        stripe
        style="width: 100%"
        max-height="480px"
        v-loading="detailLoading"
        @sort-change="handleDetailSortChange"
      >
        <el-table-column type="index" label="序号" width="60" align="center" fixed="left" />
        <el-table-column
          v-if="isColumnVisible('sn_code')"
          prop="sn_code"
          sortable="custom"
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
          v-if="isColumnVisible('sn_code_time')"
          prop="sn_code_time"
          sortable="custom"
          label="SN码录入时间"
          width="170"
        />
        <el-table-column
          v-if="isColumnVisible('bom_type')"
          prop="bom_type_name"
          sortable="custom"
          label="BOM类型"
          width="110"
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
          sortable="custom"
          label="BOM型号"
          min-width="120"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('bom_name')"
          prop="bom_name"
          sortable="custom"
          label="BOM名称"
          min-width="120"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('material_code')"
          prop="material_code"
          sortable="custom"
          label="物料编码"
          min-width="110"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('parent_sn_code')"
          prop="parent_sn_code"
          sortable="custom"
          label="父级SN码"
          min-width="160"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('status')"
          prop="status"
          sortable="custom"
          label="测试状态"
          width="110"
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
          sortable="custom"
          label="库存状态"
          width="120"
          align="center"
        >
          <template #default="{ row }">
            <DictTag :code="'storage_status'" :model-value="row.inventory_stock" size="small" />
          </template>
        </el-table-column>
        <el-table-column
          v-if="isColumnVisible('repair')"
          prop="repair"
          sortable="custom"
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
          sortable="custom"
          label="创建时间"
          width="170"
        />
        <el-table-column
          v-if="isColumnVisible('test_time')"
          prop="test_time"
          sortable="custom"
          label="测试状态修改时间"
          width="170"
        />
        <el-table-column
          v-if="isColumnVisible('stock_in_time')"
          prop="stock_in_time"
          sortable="custom"
          label="入库时间"
          width="170"
        />
        <el-table-column
          v-if="isColumnVisible('stock_out_time')"
          prop="stock_out_time"
          sortable="custom"
          label="出库时间"
          width="170"
        />
        <el-table-column
          v-if="isColumnVisible('update_time')"
          prop="update_time"
          sortable="custom"
          label="更新时间"
          width="170"
        />
        <el-table-column
          v-if="isColumnVisible('description')"
          prop="description"
          sortable="custom"
          label="描述"
          min-width="140"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('creator_name')"
          prop="creator_name"
          label="创建人"
          width="120"
          align="center"
          show-overflow-tooltip
        />
        <el-table-column
          v-if="isColumnVisible('editor_name')"
          prop="editor_name"
          label="最后操作人"
          width="120"
          align="center"
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

    <el-dialog v-model="bomColumnDialogVisible" title="列展示设置" width="480px" destroy-on-close>
      <div class="column-setting-tip">勾选需要在 BOM 型号出入库明细表中展示的字段</div>
      <el-checkbox-group v-model="bomColumnDraftKeys" class="column-checkbox-group">
        <el-checkbox v-for="col in bomStockColumnOptions" :key="col.key" :label="col.key">
          {{ col.label }}
        </el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="resetBomColumnDraft">恢复默认</el-button>
        <el-button @click="bomColumnDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveBomColumnSettings">确定</el-button>
      </template>
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

    <!-- 关节测试每日报表对话框 -->
    <el-dialog
      v-model="jointReportVisible"
      title="关节测试每日报表"
      width="90%"
      top="5vh"
      destroy-on-close
      class="joint-report-dialog"
    >
      <!-- 筛选条件 -->
      <div class="joint-report-filter">
        <el-form :inline="true">
          <el-form-item label="日期范围">
            <el-date-picker
              v-model="jointReportDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              :shortcuts="jointReportDateShortcuts"
            />
          </el-form-item>
          <el-form-item label="BOM选择">
            <el-select
              v-model="jointReportBomIds"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="请选择BOM（默认全部）"
              style="min-width: 300px"
            >
              <el-option
                v-for="bom in jointReportBomList"
                :key="bom.id"
                :label="bom.bom_model || bom.bom_name"
                :value="bom.id"
              >
                <span>{{ bom.bom_model }}</span>
                <span style="float: right; color: #8492a6; font-size: 13px">{{ bom.bom_name }}</span>
              </el-option>
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="fetchJointReport">查询</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 报表内容 -->
      <div v-loading="jointReportLoading" class="joint-report-content">
        <div v-if="jointReportData.dates?.length" class="joint-report-table-wrapper">
          <el-table
            :data="jointReportTableData"
            border
            style="width: 100%"
            class="joint-report-table"
            size="small"
            max-height="calc(100vh - 280px)"
          >
            <!-- 左侧固定列：日期/不良项 -->
            <el-table-column
              label="日期/不良项"
              width="150"
              fixed="left"
              align="center"
              class-name="corner-header-col"
            >
              <template #header>
                <div class="corner-header">
                  <span class="corner-header__col">日期</span>
                  <span class="corner-header__row">不良项</span>
                </div>
              </template>
              <template #default="{ row }">
                <template v-if="row._isSummary">
                  <div class="summary-label">
                    <div>测试数量</div>
                    <div>不良数</div>
                    <div>合格率</div>
                  </div>
                </template>
                <template v-else>
                  <div class="unqualified-label">
                    <div class="label-title" :class="{ 'text-danger': row._isFirst }">{{ row._unqualifiedLabel }}</div>
                  </div>
                </template>
              </template>
            </el-table-column>

            <!-- 动态列：日期 × BOM -->
            <el-table-column
              v-for="date in jointReportData.dates"
              :key="date"
              :label="date.split('-')[2]"
              align="center"
            >
              <!-- 每个BOM作为子列 -->
              <el-table-column
                v-for="bom in jointReportData.boms"
                :key="bom.id"
                :label="bom.bom_model || bom.bom_name || ''"
                width="120"
                align="center"
              >
                <template #header>
                  <div class="bom-header" :title="bom.bom_name">
                    {{ (bom.bom_model || bom.bom_name || '').substring(0, 10) }}
                  </div>
                </template>
                <template #default="{ row }">
                  <!-- 汇总行 -->
                  <template v-if="row._isSummary">
                    <div class="report-cell">
                      <div class="report-sub-cell test-count">
                        {{ getSummaryCell(date, bom.id, 'test_count') }}
                      </div>
                      <div class="report-sub-cell fail-count">
                        {{ getSummaryCell(date, bom.id, 'fail_count') }}
                      </div>
                      <div class="report-sub-cell pass-rate">
                        {{ getSummaryCell(date, bom.id, 'pass_rate') }}
                      </div>
                    </div>
                  </template>
                  <!-- 不合格项行 -->
                  <template v-else>
                    <div class="report-cell">
                      {{ getUnqualifiedCell(date, bom.id, row._unqualifiedValue) }}
                    </div>
                  </template>
                </template>
              </el-table-column>
            </el-table-column>

            <!-- 合计列 -->
            <el-table-column
              label="合计"
              width="120"
              align="center"
              fixed="right"
            >
              <template #header>
                <div class="header-cell" style="height: 60px;">合计</div>
              </template>
              <template #default="{ row }">
                <template v-if="row._isSummary">
                  <div class="report-cell summary-cell">
                    <div class="report-sub-cell">{{ getTotalSummaryCell(row, 'test_count') }}</div>
                    <div class="report-sub-cell">{{ getTotalSummaryCell(row, 'fail_count') }}</div>
                    <div class="report-sub-cell">{{ getTotalSummaryCell(row, 'pass_rate') }}</div>
                  </div>
                </template>
                <template v-else>
                  <div class="report-cell">
                    {{ getTotalUnqualifiedCell(row) }}
                  </div>
                </template>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-else-if="!jointReportLoading" description="暂无数据，请选择日期范围后点击查询" />
      </div>

      <template #footer>
        <el-button @click="jointReportVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "MainBoard",
});

import { ref, computed, onMounted, watch, nextTick } from "vue";
import { getProductList, getBomList as getBomListApi } from "@/api/product";
import { getFinishProductDailyStats, getFinishProductBoardDetail, getJointTestReport } from "@/api/finish-product";
import ECharts from "@/components/ECharts/index.vue";
import DictTag from "@/components/DictTag/index.vue";
import { InfoFilled, Setting, Refresh, DataAnalysis } from "@element-plus/icons-vue";
import {
  useFinishProductTableColumns,
  FINISH_PRODUCT_BOARD_DETAIL_COLUMN_STORAGE_KEY,
  BOM_STOCK_COLUMN_STORAGE_KEY,
  bomStockColumnOptions,
} from "@/composables/useFinishProductTableColumns";
import { useDictStore } from "@/store";

const dictStore = useDictStore();

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

// BOM 型号出入库明细表列展示
const {
  columnDialogVisible: bomColumnDialogVisible,
  columnDraftKeys: bomColumnDraftKeys,
  visibleColumns: bomVisibleColumns,
  isColumnVisible: isBomColumnVisible,
  loadColumnSettings: loadBomColumnSettings,
  openColumnDialog: openBomColumnDialog,
  resetColumnDraft: resetBomColumnDraft,
  saveColumnSettings: saveBomColumnSettings,
} = useFinishProductTableColumns(BOM_STOCK_COLUMN_STORAGE_KEY, bomStockColumnOptions);

type BoardType = "material" | "finish";

/** 成品看板折叠面板展开项：前两组默认展开，其余默认收起 */
const activeBoardPanels = ref<string[]>(["newRepair", "stockFlow"]);

/** 折叠面板展开后重新计算表格列宽（隐藏状态下表格宽度会被算作 0） */
const dailyStatsTableRef = ref();
const handleBoardPanelChange = () => {
  nextTick(() => {
    bomStockTableRef.value?.doLayout();
    dailyStatsTableRef.value?.doLayout();
  });
};

/** 库存与出入库：三个占比饼图的显示/隐藏开关 */
const showStockPies = ref(true);

/** 库存与出入库：BOM 型号明细表格的显示/隐藏开关 */
const showStockTable = ref(false);

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
  repairFailCount: number;
  pendingRepairCount: number;
  stockInCount: number;
  stockOutCount: number;
  stockOutSaleCount: number;
  stockOutDevCount: number;
}

interface BomStockStat {
  bom_id: number;
  bom_model: string;
  bom_name: string;
  inCount: number;
  outCount: number;
  outSaleCount: number;
  outDevCount: number;
}

const finishChartSeries = [
  { name: "新增成品", key: "newCount", color: "#409EFF", timeField: "创建时间" },
  { name: "待测试新品", key: "pendingNewCount", color: "#9333EA", timeField: "测试状态修改时间" },
  { name: "新品正在测试", key: "testingCount", color: "#0EA5E9", timeField: "测试状态修改时间" },
  { name: "测试合格", key: "passCount", color: "#67C23A", timeField: "测试状态修改时间" },
  { name: "测试不良", key: "failCount", color: "#F56C6C", timeField: "测试状态修改时间" },
  { name: "新增返修", key: "repairCount", color: "#E6A23C", timeField: "更新时间" },
  { name: "返修正在测试", key: "repairTestingCount", color: "#06B6D4", timeField: "测试状态修改时间" },
  { name: "待测试返修", key: "pendingRepairCount", color: "#F59E0B", timeField: "测试状态修改时间" },
  { name: "返修合格", key: "repairPassCount", color: "#13C2C2", timeField: "测试状态修改时间" },
  { name: "返修不良", key: "repairFailCount", color: "#F56C6C", timeField: "测试状态修改时间" },
  { name: "入库数量", key: "stockInCount", color: "#8B5CF6", timeField: "入库时间" },
  { name: "出库数量", key: "stockOutCount", color: "#64748B", timeField: "出库时间" },
  { name: "出库(外销)", key: "stockOutSaleCount", color: "#3B82F6", timeField: "出库时间" },
  { name: "出库(研发)", key: "stockOutDevCount", color: "#F97316", timeField: "出库时间" },
] as const;

const finishChartTimeFieldMap = Object.fromEntries(
  finishChartSeries.map((item) => [item.name, item.timeField])
) as Record<string, string>;

const finishTrendTooltipHint =
  "新增成品按创建时间；测试相关按测试状态修改时间；新增返修按更新时间；入库/出库按各自时间。时间为空的不计入统计。成品库存为当前在库总数，不受日期筛选影响。";

const buildFinishChartTooltipFormatter = () => {
  return (params: any) => {
    const items = Array.isArray(params) ? params : [params];
    if (!items.length) {
      return "";
    }
    const lines = [`${items[0].axisValue ?? ""}`];
    items.forEach((item) => {
      const timeField = finishChartTimeFieldMap[item.seriesName] || "";
      const suffix = timeField ? `（${timeField}）` : "";
      lines.push(`${item.marker}${item.seriesName}${suffix}：${item.value ?? 0}`);
    });
    return lines.join("<br/>");
  };
};

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
  repairFailCount: "返修不良",
  stockInCount: "入库数量",
  stockOutCount: "出库数量",
  stockOutSaleCount: "出库(外销)数量",
  stockOutDevCount: "出库(研发)数量",
  currentStockInCount: "成品库存",
  unassembledCount: "未组装",
  currentConsumeCount: "组件消耗",
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
  repairFailCount: 0,
  pendingRepairCount: 0,
  stockInCount: 0,
  stockOutCount: 0,
  stockOutSaleCount: 0,
  stockOutDevCount: 0,
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
const currentUnassembledCount = ref(0);
const currentConsumeCount = ref(0);

/** 流出合计 = 本周期出库数量 + 当前组件消耗数量 */
const totalOutflowCount = computed(
  () => (finishSummary.value.stockOutCount || 0) + (currentConsumeCount.value || 0)
);
const dailyStats = ref<FinishDailyStat[]>([]);
const bomStockBreakdown = ref<BomStockStat[]>([]);
const bomStockTotal = ref({ inCount: 0, outCount: 0 });
const finishDataLoaded = ref(false);

const periodType = ref("30d");
const bomType = ref("");
const bomModelIds = ref<number[]>([]);
const boardBomList = ref<any[]>([]);
const creatorName = ref("");
const editorName = ref("");
const snCodeBinder = ref("");
const NEW_BOARD_DATE_RANGE_STORAGE_KEY = "new-board-date-range";

/** el-date-picker 自定义日期范围的快捷选项 */
const dateRangeShortcuts = [
  {
    text: "最近3天",
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 2);
      return [start, end];
    },
  },
  {
    text: "最近7天",
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 6);
      return [start, end];
    },
  },
  {
    text: "最近30天",
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 29);
      return [start, end];
    },
  },
  {
    text: "上周",
    value: () => {
      const now = new Date();
      const day = now.getDay() || 7;
      const thisMon = new Date(now);
      thisMon.setDate(now.getDate() - day + 1);
      const lastMon = new Date(thisMon);
      lastMon.setDate(thisMon.getDate() - 7);
      const lastSun = new Date(thisMon);
      lastSun.setDate(thisMon.getDate() - 1);
      return [lastMon, lastSun];
    },
  },
  {
    text: "本月",
    value: () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      return [start, new Date()];
    },
  },
  {
    text: "上月",
    value: () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const end = new Date(now.getFullYear(), now.getMonth(), 0);
      return [start, end];
    },
  },
  {
    text: "本季度",
    value: () => {
      const now = new Date();
      const q = Math.floor(now.getMonth() / 3);
      const start = new Date(now.getFullYear(), q * 3, 1);
      return [start, new Date()];
    },
  },
  {
    text: "本年至今",
    value: () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), 0, 1);
      return [start, new Date()];
    },
  },
];

function computeDateRangeByPeriod(period: string): [string, string] {
  const now = new Date();
  let start: Date;
  let end = new Date(now);

  switch (period) {
    case "today":
      start = new Date(now);
      break;
    case "week": {
      const day = now.getDay() || 7;
      start = new Date(now);
      start.setDate(now.getDate() - day + 1);
      break;
    }
    case "month":
      start = new Date(now.getFullYear(), now.getMonth(), 1);
      break;
    case "year":
      start = new Date(now.getFullYear(), 0, 1);
      break;
    case "7d":
      start = new Date(now);
      start.setDate(now.getDate() - 6);
      break;
    case "30d":
    default:
      start = new Date(now);
      start.setDate(now.getDate() - 29);
      break;
  }

  return [formatDate(start), formatDate(end)];
}

function onPeriodChange() {
  finishDateRange.value = computeDateRangeByPeriod(periodType.value);
  fetchFinishData();
}

/** 用户通过 el-date-picker 选择自定义日期范围时触发 */
function onCustomDateChange(_val: unknown) {
  // 选了自定义日期后清空快捷周期下拉，避免两个选择器显示不一致
  if (periodType.value !== "") {
    periodType.value = "";
  }
  fetchFinishData();
}

const detailDialogVisible = ref(false);
const detailDialogTitle = ref("");
const detailLoading = ref(false);
const detailList = ref<any[]>([]);
const detailTotal = ref(0);
const detailPageNum = ref(1);
const detailPageSize = ref(10);
const detailCategory = ref<BoardCategoryKey>("newCount");
const detailSingleDate = ref<string | null>(null);
const detailTableRef = ref<any>(null);
const detailSortProp = ref("");
const detailSortOrder = ref("");

const statusTagType = (value: number) => {
  if (value === 2) return "success";
  if (value === 3) return "danger";
  if (value === 1) return "primary";
  if (value === 4) return "info";
  return "warning";
};

const bomTypeTagType = (value: number | null | undefined) => {
  if (value === 1) return "primary";
  if (value === 2) return "info";
  return "success";
};

const buildDetailTitle = (category: BoardCategoryKey, singleDate?: string | null) => {
  const label = boardCategoryLabels[category] || category;
  const bomLabel = bomType.value === "arm" ? "（机械臂）" : bomType.value === "joint" ? "（关节）" : "";
  if (category === "currentStockInCount") {
    return `${label} - 明细（当前已入库）${bomLabel}`;
  }
  if (category === "currentConsumeCount") {
    return `${label} - 明细（当前组件消耗）${bomLabel}`;
  }
  if (category === "unassembledCount") {
    return `${label} - 明细（SN码为空）${bomLabel}`;
  }
  if (singleDate) {
    return `${label} - 明细（${singleDate}）${bomLabel}`;
  }
  const [start, end] = finishDateRange.value || [];
  if (start && end) {
    return start === end ? `${label} - 明细（${start}）${bomLabel}` : `${label} - 明细（${start} 至 ${end}）${bomLabel}`;
  }
  return `${label} - 明细${bomLabel}`;
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
      bom_type?: string;
      bom_ids?: string;
      creator_name?: string;
      editor_name?: string;
      sn_code_binder?: string;
      sort_prop?: string;
      sort_order?: string;
    } = {
      category: detailCategory.value,
      pageNum: detailPageNum.value,
      pageSize: detailPageSize.value,
      bom_type: bomType.value,
      bom_ids: bomModelIds.value.length > 0 ? bomModelIds.value.join(",") : undefined,
      creator_name: creatorName.value || undefined,
      editor_name: editorName.value || undefined,
      sn_code_binder: snCodeBinder.value || undefined,
      sort_prop: detailSortProp.value || undefined,
      sort_order: detailSortOrder.value || undefined,
    };
    if (detailCategory.value !== "currentStockInCount" && detailCategory.value !== "currentConsumeCount") {
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

const handleDetailSortChange = ({ prop, order }: { prop: string | null; order: string | null }) => {
  detailSortProp.value = prop || "";
  detailSortOrder.value = order === "ascending" ? "asc" : order === "descending" ? "desc" : "";
  detailPageNum.value = 1;
  fetchBoardDetail();
};

const openBoardDetail = (category: BoardCategoryKey, count: number, singleDate?: string) => {
  if (!count || count <= 0) {
    return;
  }
  detailCategory.value = category;
  detailSingleDate.value = singleDate || null;
  detailPageNum.value = 1;
  // 切换统计项时重置排序，使用各统计项默认排序
  detailSortProp.value = "";
  detailSortOrder.value = "";
  nextTick(() => detailTableRef.value?.clearSort());
  detailDialogTitle.value = buildDetailTitle(category, singleDate);
  detailDialogVisible.value = true;
  fetchBoardDetail();
  void bomType.value; // reactive dependency for title
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

const newProductPassRateOptions = computed(() => {
  const pass = finishSummary.value.passCount || 0;
  const fail = finishSummary.value.failCount || 0;

  return {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: { bottom: 0 },
    series: [{
      name: "新品合格率",
      type: "pie",
      radius: ["40%", "70%"],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 4, borderColor: "var(--el-bg-color)", borderWidth: 2 },
      label: { show: true, formatter: "{b}\n{d}%" },
      data: [
        { value: pass, name: "合格", itemStyle: { color: "#67C23A" } },
        { value: fail, name: "不良", itemStyle: { color: "#F56C6C" } },
      ],
    }],
  };
});

const repairProductPassRateOptions = computed(() => {
  const pass = finishSummary.value.repairPassCount || 0;
  const fail = finishSummary.value.repairFailCount || 0;

  return {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: { bottom: 0 },
    series: [{
      name: "返修品合格率",
      type: "pie",
      radius: ["40%", "70%"],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 4, borderColor: "var(--el-bg-color)", borderWidth: 2 },
      label: { show: true, formatter: "{b}\n{d}%" },
      data: [
        { value: pass, name: "合格", itemStyle: { color: "#13C2C2" } },
        { value: fail, name: "不良", itemStyle: { color: "#F56C6C" } },
      ],
    }],
  };
});

/** 同排三个饼图共用的几何参数：保证圆环大小、图例位置、标签样式完全一致 */
const PIE_COMMON = {
  legend: {
    bottom: 6,
    type: "scroll",
    itemGap: 12,
    itemWidth: 14,
    itemHeight: 10,
    // 下方图例文字大小：调这个数值即可放大/缩小
    textStyle: { fontSize: 15 },
  },
  // 圆饼上移并收小半径，与下方标签/图例之间留出空隙，避免标签被遮挡
  center: ["50%", "40%"],
  radius: ["30%", "52%"],
  itemStyle: { borderRadius: 4, borderColor: "var(--el-bg-color)", borderWidth: 2 },
  labelLine: { length: 12, length2: 14, smooth: true },
  labelLayout: { hideOverlap: true },
};

const outboundRatioOptions = computed(() => {
  const sale = finishSummary.value.stockOutSaleCount || 0;
  const dev = finishSummary.value.stockOutDevCount || 0;
  const total = sale + dev;

  return {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: PIE_COMMON.legend,
    series: [{
      name: "出库类型占比",
      type: "pie",
      center: PIE_COMMON.center,
      radius: PIE_COMMON.radius,
      avoidLabelOverlap: true,
      itemStyle: PIE_COMMON.itemStyle,
      label: {
        show: true,
        fontSize: 12,
        formatter: total > 0 ? "{b}\n{d}%" : "{b}\n0%",
      },
      labelLine: PIE_COMMON.labelLine,
      labelLayout: PIE_COMMON.labelLayout,
      data: [
        { value: sale, name: "外销", itemStyle: { color: "#3B82F6" } },
        { value: dev, name: "研发", itemStyle: { color: "#F97316" } },
      ],
    }],
  };
});

/** BOM 型号饼图配色（与入库/出库两张饼图保持一致，同一型号同色） */
const BOM_CHART_COLORS = [
  "#3B82F6", "#F97316", "#10B981", "#8B5CF6", "#EF4444",
  "#06B6D4", "#F59E0B", "#64748B", "#EC4899", "#84CC16",
];

const bomColorMap = computed(() => {
  const map: Record<number, string> = {};
  bomStockBreakdown.value.forEach((row, index) => {
    map[row.bom_id] = BOM_CHART_COLORS[index % BOM_CHART_COLORS.length];
  });
  return map;
});

const buildBomStockPieOptions = (countKey: "inCount" | "outCount", seriesName: string) => {
  const total = bomStockBreakdown.value.reduce((sum, row) => sum + (row[countKey] || 0), 0);
  const data = bomStockBreakdown.value
    .filter((row) => (row[countKey] || 0) > 0)
    .map((row) => ({
      value: row[countKey],
      name: row.bom_model || `BOM#${row.bom_id}`,
      itemStyle: { color: bomColorMap.value[row.bom_id] },
    }));

  return {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: PIE_COMMON.legend,
    series: [{
      name: seriesName,
      type: "pie",
      center: PIE_COMMON.center,
      radius: PIE_COMMON.radius,
      avoidLabelOverlap: true,
      itemStyle: PIE_COMMON.itemStyle,
      label: {
        show: true,
        fontSize: 12,
        formatter: total > 0 ? "{b}\n{d}%" : "{b}\n0%",
      },
      labelLine: PIE_COMMON.labelLine,
      labelLayout: PIE_COMMON.labelLayout,
      data,
    }],
  };
};

const bomStockInPieOptions = computed(() => buildBomStockPieOptions("inCount", "入库BOM型号占比"));
const bomStockOutPieOptions = computed(() => buildBomStockPieOptions("outCount", "出库BOM型号占比"));

const bomStockTableRows = computed(() => {
  const totalIn = bomStockTotal.value.inCount || 0;
  const totalOut = bomStockTotal.value.outCount || 0;
  return bomStockBreakdown.value.map((row) => ({
    ...row,
    inPercent: totalIn > 0 ? (row.inCount / totalIn) * 100 : 0,
    outPercent: totalOut > 0 ? (row.outCount / totalOut) * 100 : 0,
  }));
});

const bomStockTableRef = ref();

/** BOM 型号明细表合计行数据（按当前行集合汇总，不受列显隐影响） */
const bomStockTableTotals = computed(() => {
  const rows = bomStockTableRows.value;
  const pick = (key: string) => rows.reduce((sum, row) => sum + (row[key] || 0), 0);
  return {
    inCount: pick("inCount"),
    outCount: pick("outCount"),
    outSaleCount: pick("outSaleCount"),
    outDevCount: pick("outDevCount"),
    stockCount: pick("stockCount"),
  };
});

/** 合计行：首列显示「合计」，占比列在合计行按 100% 展示 */
const bomStockSummaryMethod = ({ columns }: { columns: any[] }) => {
  const totals = bomStockTableTotals.value;
  return columns.map((column: any, index: number) => {
    if (index === 0) return "合计";
    switch (column.property) {
      case "inCount":
        return String(totals.inCount);
      case "inPercent":
        return totals.inCount > 0 ? "100%" : "0.0%";
      case "outCount":
        return String(totals.outCount);
      case "outPercent":
        return totals.outCount > 0 ? "100%" : "0.0%";
      case "outSaleCount":
        return String(totals.outSaleCount);
      case "outDevCount":
        return String(totals.outDevCount);
      case "stockCount":
        return String(totals.stockCount);
      default:
        return "";
    }
  });
};

/** 列显隐变化后重新计算列宽，避免表头、表体与合计行错位 */
watch(
  () => JSON.stringify(bomVisibleColumns.value),
  () => nextTick(() => bomStockTableRef.value?.doLayout())
);

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

const fetchBoardBomList = async () => {
  if (boardBomList.value.length > 0) return;
  try {
    const res = await getBomListApi({ pageNum: 1, pageSize: 1000 });
    boardBomList.value = res?.list || [];
  } catch (e) {
    console.error("获取BOM列表失败", e);
  }
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
      bom_type: bomType.value,
      bom_ids: bomModelIds.value.length > 0 ? bomModelIds.value.join(",") : undefined,
      creator_name: creatorName.value || undefined,
      editor_name: editorName.value || undefined,
      sn_code_binder: snCodeBinder.value || undefined,
    });
    finishSummary.value = {
      ...emptyFinishSummary(),
      ...(res?.summary || {}),
    };
    currentStockInCount.value = res?.currentStockInCount ?? 0;
    currentUnassembledCount.value = res?.currentUnassembledCount ?? 0;
    currentConsumeCount.value = res?.currentConsumeCount ?? 0;
    dailyStats.value = res?.daily || [];
    bomStockBreakdown.value = res?.bomStockBreakdown || [];
    bomStockTotal.value = {
      inCount: res?.bomStockTotal?.inCount ?? 0,
      outCount: res?.bomStockTotal?.outCount ?? 0,
    };
    finishDataLoaded.value = true;
    updateFinishDailyCharts();
  } catch (error) {
    console.error("获取成品统计数据失败", error);
  } finally {
    loading.value = false;
  }
};

const resetFinishDateRange = () => {
  periodType.value = "30d";
  finishDateRange.value = computeDateRangeByPeriod("30d");
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
    tooltip: {
      trigger: "axis",
      formatter: buildFinishChartTooltipFormatter(),
    },
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
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: buildFinishChartTooltipFormatter(),
    },
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

// ==================== 关节测试每日报表 ====================

const jointReportVisible = ref(false);
const jointReportLoading = ref(false);
// 从localStorage恢复筛选状态，切换页面不重置
const jointReportDateRange = ref<[string, string] | null>(
  (() => {
    try {
      const saved = localStorage.getItem('jointReportDateRange');
      return saved ? JSON.parse(saved) : null;
    } catch { return null; }
  })()
);
const jointReportBomIds = ref<number[]>(
  (() => {
    try {
      const saved = localStorage.getItem('jointReportBomIds');
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  })()
);
const jointReportBomList = ref<any[]>([]);

// 监听筛选状态变化并持久化
watch(jointReportDateRange, (val) => {
  try {
    if (val) localStorage.setItem('jointReportDateRange', JSON.stringify(val));
    else localStorage.removeItem('jointReportDateRange');
  } catch {}
});
watch(jointReportBomIds, (val) => {
  try {
    localStorage.setItem('jointReportBomIds', JSON.stringify(val));
  } catch {}
});
const jointReportData = ref<any>({
  dates: [],
  boms: [],
  unqualified_items: [],
  summary: [],
  total_summary: {},
});

// 日期快捷选项
const jointReportDateShortcuts = [
  {
    text: '最近7天',
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 6);
      return [formatDate(start), formatDate(end)];
    },
  },
  {
    text: '最近30天',
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 29);
      return [formatDate(start), formatDate(end)];
    },
  },
  {
    text: '本月',
    value: () => {
      const end = new Date();
      const start = new Date(end.getFullYear(), end.getMonth(), 1);
      return [formatDate(start), formatDate(end)];
    },
  },
];

// 计算表格数据
const jointReportTableData = computed(() => {
  const rows: any[] = [];
  const unqualifiedItems = jointReportData.value.unqualified_items || [];
  
  // 添加汇总行（测试数量、不良数、合格率）
  rows.push({
    _isSummary: true,
    _rowType: 'summary',
  });
  
  // 添加不合格项行
  for (const item of unqualifiedItems) {
    rows.push({
      _isSummary: false,
      _unqualifiedValue: item.value,
      _unqualifiedLabel: item.label,
    });
  }
  
  return rows;
});

// 获取汇总单元格内容
const getSummaryCell = (date: string, bomId: number, field: string) => {
  const summary = jointReportData.value.summary?.find((s: any) => s.date === date);
  if (!summary || !summary.bom_summaries?.[bomId]) return '';
  
  const bomSummary = summary.bom_summaries[bomId];
  const value = bomSummary[field];
  
  if (value === null || value === undefined || value === 0) return '';
  
  if (field === 'pass_rate') return `${value}%`;
  return value;
};

// 获取不合格项单元格内容
const getUnqualifiedCell = (date: string, bomId: number, unqualifiedValue: number) => {
  const summary = jointReportData.value.summary?.find((s: any) => s.date === date);
  if (!summary || !summary.bom_summaries?.[bomId]) return '';
  
  const bomSummary = summary.bom_summaries[bomId];
  const count = bomSummary.unqualified_counts?.[unqualifiedValue];
  
  if (!count) return '';
  return count;
};

// 获取合计单元格内容（汇总行）
const getTotalSummaryCell = (row: any, field: string) => {
  const totalSummary = jointReportData.value.total_summary || {};
  const boms = jointReportData.value.boms || [];
  
  if (boms.length === 0) return '';
  
  let totalValue = 0;
  let hasValue = false;
  
  for (const bom of boms) {
    const bomSummary = totalSummary[bom.id];
    if (bomSummary) {
      const value = bomSummary[field];
      if (value !== null && value !== undefined && value !== 0) {
        hasValue = true;
        if (field === 'pass_rate') {
          // 合格率需要重新计算
          const testCount = bomSummary.test_count || 0;
          const failCount = bomSummary.fail_count || 0;
          const passCount = testCount - failCount;
          if (testCount > 0) {
            totalValue += passCount;
          }
        } else {
          totalValue += value;
        }
      }
    }
  }
  
  if (!hasValue && totalValue === 0) return '';
  
  if (field === 'pass_rate') {
    // 计算总合格率
    let totalTest = 0;
    for (const bom of boms) {
      const bomSummary = totalSummary[bom.id];
      if (bomSummary) {
        totalTest += bomSummary.test_count || 0;
      }
    }
    const totalPass = totalValue;
    if (totalTest === 0) return '';
    return `${((totalPass / totalTest) * 100).toFixed(1)}%`;
  }
  
  return totalValue;
};

// 获取合计单元格内容（不合格项行）
const getTotalUnqualifiedCell = (row: any) => {
  const totalSummary = jointReportData.value.total_summary || {};
  const boms = jointReportData.value.boms || [];
  const unqualifiedValue = row._unqualifiedValue;
  
  if (boms.length === 0) return '';
  
  let totalCount = 0;
  let hasValue = false;
  
  for (const bom of boms) {
    const bomSummary = totalSummary[bom.id];
    if (bomSummary?.unqualified_counts?.[unqualifiedValue]) {
      hasValue = true;
      totalCount += bomSummary.unqualified_counts[unqualifiedValue];
    }
  }
  
  if (!hasValue) return '';
  return totalCount;
};

// 打开报表对话框
const openJointReportDialog = async () => {
  jointReportVisible.value = true;
  
  // 加载所有BOM列表
  if (jointReportBomList.value.length === 0) {
    try {
      const res = await getBomListApi({ pageNum: 1, pageSize: 1000 });
      jointReportBomList.value = res?.list || [];
    } catch (e) {
      console.error('获取BOM列表失败', e);
    }
  }
  
  // 默认日期范围（仅首次未设置时）
  if (!jointReportDateRange.value) {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 6);
    jointReportDateRange.value = [formatDate(start), formatDate(end)];
  }
  
  // 自动加载数据
  await fetchJointReport();
};

// 获取报表数据
const fetchJointReport = async () => {
  if (!jointReportDateRange.value) return;
  
  jointReportLoading.value = true;
  try {
    const params: any = {
      start_date: jointReportDateRange.value[0],
      end_date: jointReportDateRange.value[1],
    };
    
    if (jointReportBomIds.value.length > 0) {
      params.bom_ids = jointReportBomIds.value.join(',');
    }
    
    // 注意：响应拦截器在成功时直接返回data，所以res就是数据本身
    const res = await getJointTestReport(params);
    jointReportData.value = res || {
      dates: [],
      boms: [],
      unqualified_items: [],
      summary: [],
      total_summary: {},
    };
  } catch (e) {
    console.error('获取关节测试报表失败', e);
  } finally {
    jointReportLoading.value = false;
  }
};

onMounted(() => {
  loadColumnSettings();
  loadBomColumnSettings();
  dictStore.loadDictItems('storage_status', true);
  periodType.value = "30d";
  finishDateRange.value = computeDateRangeByPeriod("30d");
  fetchBoardBomList();
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

/* 成品看板折叠面板：标题行高与字号
   EP 标题行由 min-height/line-height 取 var(--el-collapse-header-height) 控制，
   直接写 height 不生效，需覆盖变量 */
.board-collapse {
  --el-collapse-header-height: 25px;
  --el-collapse-header-font-size: 15px;
  
  :deep(.el-collapse-item__content) {
    padding-bottom: 0;
  }
}

.text-muted {
  color: #909399;
  font-style: italic;
}

.stat-card--clickable {
  cursor: pointer;
}

/* 紧凑统计卡片：缩小内边距，标题不换行（空间不足时省略号截断） */
.compact-stat-grid {
  :deep(.el-card__header) {
    padding: 8px 10px;

    > div {
      min-width: 0;
    }

    span {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      min-width: 0;
    }

    .el-icon {
      flex-shrink: 0;
    }
  }

  :deep(.el-card__body) {
    padding: 10px 12px;
  }
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

/* ==================== BOM 型号出入库明细表 ==================== */

/* 当前剩余库存：绿色标注（时点口径，与上方日期筛选无关） */
.bom-stock-value {
  font-weight: 600;
  color: var(--el-color-success);
}

/* 合计行：橙红标注 */
:deep(.el-table__footer-wrapper .el-table__footer .cell) {
  font-weight: 600;
  color: var(--el-color-danger);
}

// ==================== 关节测试每日报表样式 ====================

.joint-report-filter {
  margin-bottom: 16px;
  padding: 12px 16px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.joint-report-content {
  min-height: 300px;
}

.joint-report-table-wrapper {
  overflow-x: auto;
}

// 表格主题样式
.joint-report-table {
  :deep(.el-table__header-wrapper th) {
    background-color: var(--el-fill-color-light) !important;
    color: var(--el-text-color-primary) !important;
    font-weight: bold;
    text-align: center;
  }
  
  :deep(.el-table__body td) {
    text-align: center;
  }
  
  :deep(.el-table__body tr:hover > td) {
    background-color: var(--el-fill-color-blank) !important;
  }
  
  :deep(.el-table__fixed-header-wrapper),
  :deep(.el-table__fixed-right-header-wrapper) {
    th {
      background-color: var(--el-fill-color-light) !important;
    }
  }
  
  // 对角线表头样式
  :deep(.corner-header-col .cell) {
    padding: 0 !important;
    height: 100%;
  }
}

// 对角线表头
.corner-header {
  position: relative;
  width: 100%;
  height: 60px;
  overflow: hidden;
  
  // 对角线
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    // 使用渐变画对角线：右上→左下
    background: linear-gradient(
      to left bottom,
      transparent 49.3%,
      var(--el-border-color) 49.3%,
      var(--el-border-color) 50.7%,
      transparent 50.7%
    );
    pointer-events: none;
  }
  
  &__col {
    position: absolute;
    right: 6px;
    top: 4px;
    font-size: 13px;
    font-weight: 500;
    color: var(--el-text-color-primary);
  }
  
  &__row {
    position: absolute;
    left: 6px;
    bottom: 4px;
    font-size: 13px;
    font-weight: 500;
    color: var(--el-text-color-primary);
  }
}

.report-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 50px;
  font-size: 13px;
}

.report-sub-cell {
  padding: 2px 8px;
  line-height: 1.4;
  min-height: 18px;
}

.summary-cell {
  background-color: var(--el-color-success-light-9);
  font-weight: 600;
}

.summary-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 50px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  
  > div {
    padding: 4px 0;
    line-height: 1.4;
  }
}

.unqualified-label {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  
  .label-title {
    font-size: 13px;
    color: var(--el-text-color-regular);
  }
}

.bom-header {
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-regular);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
}

.test-count {
  color: var(--el-color-primary);
  font-weight: 500;
}

.fail-count {
  color: var(--el-color-danger);
  font-weight: 500;
}

.pass-rate {
  color: var(--el-color-success);
  font-weight: 500;
}

// 报表对话框
.joint-report-dialog {
  :deep(.el-dialog__body) {
    padding: 16px 20px;
  }
  
  :deep(.el-table__cell) {
    padding: 0;
  }
  
  :deep(.el-table__cell .cell) {
    padding: 4px 8px;
  }
}

.text-danger {
  color: var(--el-color-danger);
}
</style>
