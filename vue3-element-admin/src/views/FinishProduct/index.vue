<template>
  <div class="app-container">
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="queryParams" class="search-form">
        <el-form-item label="SN码">
          <el-input
            v-model="queryParams.sn_code"
            placeholder="SN码"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="产品型号">
          <el-input
            v-model="queryParams.bom_model"
            placeholder="产品型号"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="BOM名称">
          <el-input
            v-model="queryParams.bom_name"
            placeholder="BOM名称"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="BOM类型">
          <el-select
            v-model="queryParams.bom_type"
            placeholder="全部"
            clearable
            style="width: 120px"
            @change="handleSearch"
            @clear="handleSearch"
          >
            <el-option label="关节" value="0" />
            <el-option label="机械臂" value="1" />
            <el-option label="其他" value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="测试状态">
          <el-select
            v-model="queryParams.status"
            placeholder="全部"
            clearable
            style="width: 120px"
            @change="handleSearch"
            @clear="handleSearch"
          >
            <el-option label="未测试" value="0" />
            <el-option label="测试中" value="1" />
            <el-option label="测试合格" value="2" />
            <el-option label="测试不良" value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="库存状态">
          <DictSelect
            v-model="queryParams.inventory_stock"
            code="storage_status"
            placeholder="全部"
            style="width: 130px"
            @change="handleSearch"
          />
        </el-form-item>
        <el-form-item label="返修">
          <el-select
            v-model="queryParams.repair"
            placeholder="全部"
            clearable
            style="width: 100px"
            @change="handleSearch"
            @clear="handleSearch"
          >
            <el-option label="新品" value="0" />
            <el-option label="返修品" value="1" />
          </el-select>
        </el-form-item>
        <el-form-item label="创建时间">
          <el-date-picker
            v-model="queryParams.createDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 260px"
            @change="handleSearch"
            @clear="handleSearch"
          />
        </el-form-item>
        <el-form-item label="更新时间">
          <el-date-picker
            v-model="queryParams.updateDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 260px"
            @change="handleSearch"
            @clear="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="resetQuery">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <div v-if="showJointWarning" class="joint-warning">
      <el-icon class="warning-icon"><WarningFilled /></el-icon>
      <span>库存关节数量与成品关节数量不符，请添加关节父级物料关系</span>
    </div>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <el-checkbox v-model="collapseMode">折叠模式</el-checkbox>
        <div class="toolbar-actions">
          <el-button type="warning" @click="handleAssemble">
            <el-icon><Box /></el-icon> 组装产品
          </el-button>
          <el-button @click="openColumnDialog">
            <el-icon><Setting /></el-icon> 列展示
          </el-button>
        </div>
      </div>

      <el-table
        :data="filteredTableData"
        border
        stripe
        style="width: 100%"
        height="500"
        v-loading="loading"
        :row-class-name="getRowClassName"
        @row-click="handleRowClick"
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
          label="产品型号"
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
          v-if="isColumnVisible('parent_sn_code')"
          prop="parent_sn_code"
          label="父级SN码"
          min-width="130"
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
          v-if="isColumnVisible('test_time')"
          prop="test_time"
          label="测试状态修改时间"
          width="170"
        />
        <el-table-column
          v-if="isColumnVisible('stock_in_time')"
          prop="stock_in_time"
          label="入库时间"
          width="170"
        />
        <el-table-column
          v-if="isColumnVisible('stock_out_time')"
          prop="stock_out_time"
          label="出库时间"
          width="170"
        />
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
        <el-table-column label="操作" width="190" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="handleEdit(row)">编辑</el-button>
            <el-button
              v-if="String(row.bom_type) === '1' && row.sn_code"
              link type="success" size="small" @click.stop="handleBindJoints(row)"
            >关节绑定</el-button>
            <el-button link type="danger" size="small" @click.stop="handleRollback(row)">回退</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="queryParams.pageNum"
          v-model:page-size="queryParams.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="dialogVisible" title="编辑成品" width="720px" destroy-on-close>
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="132px"
        class="finish-edit-form"
      >
        <el-form-item label="SN码" prop="sn_code">
          <el-input
            v-model="formData.sn_code"
            maxlength="255"
            clearable
            placeholder="请填写产品 SN 码"
          />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="产品型号">
              <el-input v-model="formData.bom_model" disabled />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="BOM名称">
              <el-input v-model="formData.bom_name" disabled />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="创建时间" prop="create_time">
              <el-date-picker
                v-model="formData.create_time"
                type="datetime"
                placeholder="选择创建时间"
                value-format="YYYY-MM-DD HH:mm:ss"
                format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="测试状态修改时间">
              <el-date-picker
                v-model="formData.test_time"
                type="datetime"
                placeholder="选择测试状态修改时间"
                value-format="YYYY-MM-DD HH:mm:ss"
                format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
                clearable
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="返修" class="finish-edit-form__radio-row">
          <el-radio-group v-model="formData.repair">
            <el-radio :value="0">新品</el-radio>
            <el-radio :value="1">返修品</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="测试状态" class="finish-edit-form__radio-row">
          <el-radio-group v-model="formData.status">
            <el-radio :value="0" :disabled="requiresPassStatus">未测试</el-radio>
            <el-radio :value="1" :disabled="requiresPassStatus">测试中</el-radio>
            <el-radio :value="2">测试合格</el-radio>
            <el-radio :value="3" :disabled="requiresPassStatus">测试不良</el-radio>
          </el-radio-group>
          <div v-if="requiresPassStatus" class="finish-edit-form__hint">
            选择入库/出库时，测试状态必须为「测试合格」
          </div>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="入库时间">
              <el-date-picker
                v-model="formData.stock_in_time"
                type="datetime"
                placeholder="选择入库时间"
                value-format="YYYY-MM-DD HH:mm:ss"
                format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="出库时间">
              <el-date-picker
                v-model="formData.stock_out_time"
                type="datetime"
                placeholder="选择出库时间"
                value-format="YYYY-MM-DD HH:mm:ss"
                format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
                clearable
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="库存状态">
          <el-select
            v-model="formData.inventory_stock"
            placeholder="请选择库存状态"
            style="width: 100%"
            :disabled="isJointWithParent"
          >
            <el-option
              v-for="item in availableStockOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
              :disabled="isStockOptionDisabled(item.value)"
            />
          </el-select>
          <div v-if="isJointWithParent" class="finish-edit-form__hint">
            关节有关联父级，库存状态固定为「组件消耗」
          </div>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            maxlength="255"
            show-word-limit
            placeholder="请输入描述"
          />
        </el-form-item>
        <el-form-item label="父级SN码">
          <el-input
            v-model="formData.parent_sn_code"
            placeholder="请输入父级产品SN码"
            maxlength="255"
            clearable
            :disabled="isArmProduct"
          />
          <div v-if="isArmProduct" class="finish-edit-form__hint">
            机械臂类型不可填写父级SN码
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="columnDialogVisible" title="列展示设置" width="480px" destroy-on-close>
      <div class="column-setting-tip">勾选需要在表格中展示的字段（序号、操作列始终显示）</div>
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

    <bom-assemble-dialog ref="assembleDialogRef" @success="getList" />

    <el-dialog
      v-model="repairConfirmVisible"
      title="生成返修单"
      width="420px"
      :close-on-click-modal="false"
      @close="handleRepairConfirmCancel"
    >
      <div class="repair-confirm-tip">
        <el-icon class="warning-icon"><WarningFilled /></el-icon>
        <span>当前产品已标记为「返修品」，是否同时生成返修单？</span>
      </div>
      <template #footer>
        <el-button @click="handleRepairConfirmCancel">取消</el-button>
        <el-button type="info" @click="handleRepairConfirmSkip">不生成</el-button>
        <el-button type="primary" @click="handleRepairConfirmGenerate">生成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="repairDialogVisible" title="生成返修单" width="480px" destroy-on-close>
      <el-form :model="repairFormData" label-width="80px">
        <el-form-item label="SN码">
          <span>{{ formData.sn_code || '—' }}</span>
        </el-form-item>
        <el-form-item label="返修内容">
          <el-input
            v-model="repairFormData.repair_info"
            type="textarea"
            :rows="4"
            maxlength="500"
            show-word-limit
            placeholder="请输入返修内容描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="repairDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="repairSubmitting" @click="handleRepairSubmit">
          保存并生成返修单
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="jointDetailVisible"
      title="关节详情"
      width="860px"
      destroy-on-close
    >
      <div v-if="jointDetailRow" class="joint-detail-header">
        <span>机械臂 SN码：{{ jointDetailRow.sn_code || '—' }}</span>
        <span>（共 {{ getJointChildren(jointDetailRow.sn_code).length }} 个关节子件）</span>
      </div>
      <el-table
        :data="jointDetailRow ? getJointChildren(jointDetailRow.sn_code) : []"
        border
        stripe
        style="width: 100%"
        max-height="400"
      >
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="sn_code" label="SN码" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.sn_code || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="bom_model" label="产品型号" min-width="120" show-overflow-tooltip />
        <el-table-column prop="bom_name" label="BOM名称" min-width="120" show-overflow-tooltip />
        <el-table-column prop="material_code" label="物料编码" min-width="110" show-overflow-tooltip />
        <el-table-column prop="status" label="测试状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ row.status_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="inventory_stock" label="库存状态" width="120" align="center">
          <template #default="{ row }">
            <DictTag :code="'storage_status'" :model-value="row.inventory_stock" size="small" />
          </template>
        </el-table-column>
        <el-table-column prop="repair" label="返修" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.repair === 1 ? 'warning' : 'info'" size="small">
              {{ row.repair_name }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="jointDetailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="bindJointVisible"
      title="关节绑定"
      width="720px"
      destroy-on-close
    >
      <div v-if="bindJointRow" class="bind-joint-header">
        <span>机械臂：{{ bindJointRow.bom_model }} ({{ bindJointRow.bom_name }})</span>
        <span>SN码：{{ bindJointRow.sn_code }}</span>
      </div>
      <div class="bind-joint-tip">
        选择要绑定到此机械臂的关节（仅显示有SN码、测试合格且已入库的未绑定关节）
      </div>
      <div v-loading="bindJointLoading" element-loading-text="加载可绑定关节...">
        <div class="bind-joint-select-wrapper">
          <el-select
            v-model="selectedJointIds"
            multiple
            filterable
            placeholder="请选择关节（可输入筛选）"
            style="flex: 1; min-width: 0"
          >
            <el-option
              v-for="joint in availableJoints"
              :key="joint.id"
              :label="`${joint.sn_code || '无SN码'} - ${joint.bom_model}${joint.bom_name ? ' (' + joint.bom_name + ')' : ''}`"
              :value="joint.id"
            >
              <div class="joint-option">
                <span class="joint-option__sn">{{ joint.sn_code || '无SN码' }}</span>
                <span class="joint-option__model">{{ joint.bom_model }}</span>
                <span v-if="joint.bom_name" class="joint-option__name">({{ joint.bom_name }})</span>
                <el-tag
                  v-if="joint.status != null"
                  :type="statusTagType(joint.status)"
                  size="small"
                  class="joint-option__tag"
                >
                  {{ joint.status_name }}
                </el-tag>
              </div>
            </el-option>
            <template #empty>
              <div class="select-empty">
                <template v-if="bindJointLoading">加载中...</template>
                <template v-else>暂无符合条件的关节（需有SN码、测试合格、已入库且未绑定）</template>
              </div>
            </template>
          </el-select>
          <el-button type="primary" @click="openAddJointDialog">
            <el-icon><Plus /></el-icon> 添加关节
          </el-button>
        </div>
      </div>
      <div v-if="selectedJointIds.length > 0" class="bind-joint-selected">
        <span class="selected-label">已选关节：</span>
        <div class="selected-tags">
          <el-tag
            v-for="joint in selectedJoints"
            :key="joint.id"
            closable
            @close="selectedJointIds = selectedJointIds.filter(id => id !== joint.id)"
          >
            {{ joint.sn_code || '无SN码' }} - {{ joint.bom_model }}
          </el-tag>
        </div>
      </div>
      <div class="bind-joint-footer">
        已选择 <b>{{ selectedJointIds.length }}</b> 个关节
      </div>
      <template #footer>
        <el-button @click="bindJointVisible = false">取消</el-button>
        <el-button type="primary" :loading="bindSubmitting" @click="handleBindSubmit">
          确认绑定
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="addJointVisible"
      title="添加关节"
      width="480px"
      destroy-on-close
    >
      <el-form :model="{ addJointBomId, addJointSnCode }" label-width="100px">
        <el-form-item label="关节BOM">
          <el-select
            v-model="addJointBomId"
            filterable
            placeholder="请选择关节BOM"
            style="width: 100%"
          >
            <el-option
              v-for="bom in jointBomList"
              :key="bom.id"
              :label="`${bom.bom_model} ${bom.bom_name || ''} (${bom.type_name || ''})`"
              :value="bom.id"
            />
            <template #empty>
              <div class="select-empty">暂无关节类型的BOM</div>
            </template>
          </el-select>
        </el-form-item>
        <el-form-item label="SN码">
          <el-input
            v-model="addJointSnCode"
            placeholder="请输入SN码（选填）"
            clearable
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addJointVisible = false">取消</el-button>
        <el-button type="primary" :loading="addJointSubmitting" @click="handleAddJoint">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { Search, Refresh, Setting, Box, WarningFilled, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getFinishProductList, createFinishProduct, updateFinishProduct, rollbackFinishProduct, checkJointStockConsistency, bindJointsToArm } from '@/api/finish-product'
import { createRepair, getBomList } from '@/api/product'
import { useFinishProductTableColumns } from '@/composables/useFinishProductTableColumns'
import BomAssembleDialog from '../product/bom/bomInfo/BomAssembleDialog.vue'
import DictSelect from '@/components/DictSelect/index.vue'
import DictTag from '@/components/DictTag/index.vue'
import { useDictStore } from '@/store'

const dictStore = useDictStore()

const {
  columnOptions,
  columnDialogVisible,
  columnDraftKeys,
  isColumnVisible,
  loadColumnSettings,
  openColumnDialog,
  resetColumnDraft,
  saveColumnSettings,
} = useFinishProductTableColumns()

const queryParams = reactive({
  pageNum: 1,
  pageSize: 10,
  sn_code: '',
  bom_model: '',
  bom_name: '',
  bom_type: '',
  status: '',
  inventory_stock: '',
  repair: '',
  createDateRange: null,
  updateDateRange: null
})

const appendDateRangeParams = (params, range, startKey, endKey) => {
  if (range?.[0] && range?.[1]) {
    params[startKey] = range[0]
    params[endKey] = range[1]
  }
}

const buildListParams = () => {
  const params = {
    pageNum: queryParams.pageNum,
    pageSize: queryParams.pageSize,
    sn_code: queryParams.sn_code,
    bom_model: queryParams.bom_model,
    bom_name: queryParams.bom_name,
    bom_type: queryParams.bom_type,
    status: queryParams.status,
    inventory_stock: queryParams.inventory_stock,
    repair: queryParams.repair
  }
  appendDateRangeParams(params, queryParams.createDateRange, 'create_start_date', 'create_end_date')
  appendDateRangeParams(params, queryParams.updateDateRange, 'update_start_date', 'update_end_date')
  return params
}

const tableData = ref([])
const loading = ref(false)
const backendTotal = ref(0)
const dialogVisible = ref(false)
const originalInventoryStock = ref(0)
const submitting = ref(false)
const formRef = ref(null)
const assembleDialogRef = ref(null)

const repairDialogVisible = ref(false)
const repairSubmitting = ref(false)
const repairFormData = reactive({
  repair_info: ''
})

const repairConfirmVisible = ref(false)

const collapseMode = ref(true)

const jointDetailVisible = ref(false)
const jointDetailRow = ref(null)

const bindJointVisible = ref(false)
const bindJointRow = ref(null)
const bindSubmitting = ref(false)
const bindJointLoading = ref(false)
const selectedJointIds = ref([])

// 绑定对话框专用的全量关节数据
const bindJointData = ref([])

// 可用于绑定的关节：使用专用的全量数据（bindJointData），确保不受当前页限制
const availableJoints = computed(() => {
  return bindJointData.value.filter(
    item =>
      String(item.bom_type) === '0' &&
      !item.parent_sn_code &&
      item.sn_code &&
      Number(item.status) === STATUS_PASS &&
      Number(item.inventory_stock) === INVENTORY_IN
  )
})

// 已选中的关节对象列表（用于提交）
const selectedJoints = computed(() => {
  return availableJoints.value.filter(j => selectedJointIds.value.includes(j.id))
})

// 添加关节对话框
const addJointVisible = ref(false)
const addJointSubmitting = ref(false)
const addJointBomId = ref(null)
const addJointSnCode = ref('')
const addJointBomList = ref([])

// 过滤仅显示关节类型的BOM
const jointBomList = computed(() => {
  return addJointBomList.value.filter(b => String(b.type) === '0' || String(b.bom_type) === '0')
})

// 折叠后可见的数据（仅过滤掉被折叠的行，未分页）
const visibleData = computed(() => {
  if (!collapseMode.value) return tableData.value
  return tableData.value.filter(row => {
    // 只折叠那些有parent_sn_code 且 对应父级存在并拥有sn_code的关节
    if (String(row.bom_type) !== '0' || !row.parent_sn_code) return true
    const parentExists = tableData.value.some(
      item => String(item.bom_type) === '1' && item.sn_code === row.parent_sn_code
    )
    return !parentExists
  })
})

// 最终显示的数据：折叠模式下前端分页，确保每页显示 pageSize 条可见数据
const filteredTableData = computed(() => {
  if (!collapseMode.value) return tableData.value
  const start = (queryParams.pageNum - 1) * queryParams.pageSize
  const end = start + queryParams.pageSize
  return visibleData.value.slice(start, end)
})

// 总条数：折叠模式下为可见数据条数，否则为后端返回的总数
const total = computed(() => {
  if (collapseMode.value) return visibleData.value.length
  return backendTotal.value
})

const formRules = {
  sn_code: [{ max: 255, message: 'SN码不能超过255个字符', trigger: 'blur' }]
}

const formData = reactive({
  id: null,
  sn_code: '',
  bom_id: null,
  bom_type: null,
  bom_model: '',
  bom_name: '',
  status: 0,
  inventory_stock: 0,
  repair: 0,
  create_time: '',
  test_time: '',
  stock_in_time: '',
  stock_out_time: '',
  description: '',
  parent_sn_code: ''
})

const showJointWarning = ref(false)

const STATUS_PASS = 2

const INVENTORY_IN = 1

const INVENTORY_CONSUME = 4

// 记录关节变为组件消耗前的库存状态
const stockBeforeConsume = ref(null)

const storageStatusOptions = computed(() => {
  return dictStore.getDictItems('storage_status').map(item => ({
    ...item,
    value: Number(item.value)
  }))
})

// 是否为机械臂产品（bom_type=1）
const isArmProduct = computed(() => {
  return String(formData.bom_type) === '1'
})

// 是否为有关联父级的关节（bom_type=0且有parent_sn_code）
const isJointWithParent = computed(() => {
  return String(formData.bom_type) === '0' && !!formData.parent_sn_code
})

// 可用的库存状态选项
const availableStockOptions = computed(() => {
  if (isJointWithParent.value) {
    // 有关联父级的关节，只能选择组件消耗
    return storageStatusOptions.value.filter(item => item.value === INVENTORY_CONSUME)
  }
  return storageStatusOptions.value
})

const isStockOptionDisabled = (value) => {
  const numValue = Number(value)
  // 有关联父级的关节，只能选择组件消耗
  if (isJointWithParent.value && numValue !== INVENTORY_CONSUME) {
    return true
  }
  // 未入库的成品(0)不能直接出库(2或3)
  if (Number(originalInventoryStock.value) === 0 && (numValue === 2 || numValue === 3)) {
    return true
  }
  return false
}

// 组件消耗状态(4)不需要强制测试合格
const requiresPassStatus = computed(
  () => formData.inventory_stock === 1 || formData.inventory_stock === 2 || formData.inventory_stock === 3
)

watch(
  () => formData.inventory_stock,
  (val) => {
    if (val === 1 || val === 2 || val === 3) {
      formData.status = STATUS_PASS
    }
  }
)

// 监听parent_sn_code变化，关节有父级时自动设置库存状态为组件消耗
watch(
  () => formData.parent_sn_code,
  (val, oldVal) => {
    // 机械臂类型：忽略父级SN码变化
    if (String(formData.bom_type) === '1') return
    if (String(formData.bom_type) === '0' && val) {
      // 关节有父级SN码：强制设置库存状态为组件消耗
      if (formData.inventory_stock !== INVENTORY_CONSUME) {
        stockBeforeConsume.value = formData.inventory_stock
        formData.inventory_stock = INVENTORY_CONSUME
      }
    }
    // 清除父级SN码时，不允许库存状态为组件消耗
    if (String(formData.bom_type) === '0' && !val && formData.inventory_stock === INVENTORY_CONSUME) {
      const revertVal = stockBeforeConsume.value !== null ? stockBeforeConsume.value : (originalInventoryStock.value === INVENTORY_CONSUME ? 0 : originalInventoryStock.value)
      formData.inventory_stock = revertVal
      originalInventoryStock.value = revertVal
      stockBeforeConsume.value = null
    }
  }
)

const statusTagType = (value) => {
  if (value === 2) return 'success'
  if (value === 3) return 'danger'
  if (value === 1) return 'primary'
  return 'warning'
}

const bomTypeTagType = (value) => {
  if (value === 1) return 'primary'
  if (value === 2) return 'info'
  return 'success'
}

const formatFinishProductLabel = (row) => {
  if (!row) return ''
  if (row.bom_name) return `${row.bom_model}(${row.bom_name})`
  return row.bom_model || String(row.id)
}

const getList = () => {
  loading.value = true
  const params = buildListParams()
  // 折叠模式：一次性加载所有数据，由前端分页，确保每页显示 pageSize 条可见数据
  if (collapseMode.value) {
    params.pageNum = 1
    params.pageSize = 9999
  }
  getFinishProductList(params)
    .then((response) => {
      tableData.value = response?.list || []
      backendTotal.value = response?.total || 0
      // 折叠模式下防止当前页越界
      if (collapseMode.value) {
        const maxPage = Math.max(1, Math.ceil(visibleData.value.length / queryParams.pageSize))
        if (queryParams.pageNum > maxPage) {
          queryParams.pageNum = 1
        }
      }
    })
    .catch(() => {
      ElMessage.error('获取成品列表失败')
    })
    .finally(() => {
      loading.value = false
    })
}

const handleSearch = () => {
  queryParams.pageNum = 1
  getList()
}

const resetQuery = () => {
  queryParams.sn_code = ''
  queryParams.bom_model = ''
  queryParams.bom_name = ''
  queryParams.bom_type = ''
  queryParams.status = ''
  queryParams.inventory_stock = ''
  queryParams.repair = ''
  queryParams.createDateRange = null
  queryParams.updateDateRange = null
  queryParams.pageNum = 1
  getList()
}

const handleSizeChange = () => {
  queryParams.pageNum = 1
  // 折叠模式下数据已全部加载，前端分页无需重新请求
  if (!collapseMode.value) {
    getList()
  }
}
const handleCurrentChange = () => {
  if (!collapseMode.value) {
    getList()
  }
}

const handleAssemble = () => assembleDialogRef.value?.open()

// 切换折叠模式时重新加载数据（折叠模式需一次性加载，非折叠模式恢复后端分页）
watch(collapseMode, () => {
  queryParams.pageNum = 1
  getList()
})

const handleRowClick = (row) => {
  if (!collapseMode.value) return
  if (String(row.bom_type) === '1' && row.sn_code) {
    jointDetailRow.value = row
    jointDetailVisible.value = true
  }
}

const getJointChildren = (parentSnCode) => {
  if (!parentSnCode) return []
  return tableData.value.filter(
    item => String(item.bom_type) === '0' && item.parent_sn_code === parentSnCode
  )
}

const getRowClassName = ({ row }) => {
  if (collapseMode.value && String(row.bom_type) === '1' && row.sn_code) {
    return 'row-clickable'
  }
  return ''
}

const handleEdit = (row) => {
  formData.id = row.id
  formData.sn_code = row.sn_code
  formData.bom_id = row.bom_id
  formData.bom_type = row.bom_type
  formData.bom_model = row.bom_model || ''
  formData.bom_name = row.bom_name || ''
  formData.inventory_stock = row.inventory_stock
  originalInventoryStock.value = row.inventory_stock
  stockBeforeConsume.value = null
  formData.repair = row.repair
  formData.create_time = row.create_time || ''
  formData.test_time = row.test_time || ''
  formData.stock_in_time = row.stock_in_time || ''
  formData.stock_out_time = row.stock_out_time || ''
  formData.description = row.description || ''
  // 机械臂类型：清空父级SN码（不可设置）
  if (String(row.bom_type) === '1') {
    formData.parent_sn_code = ''
  } else {
    formData.parent_sn_code = row.parent_sn_code || ''
  }
  // 立即同步：如果是有关联父级的关节，强制设置为组件消耗状态
  if (String(row.bom_type) === '0' && row.parent_sn_code) {
    if (formData.inventory_stock !== INVENTORY_CONSUME) {
      stockBeforeConsume.value = formData.inventory_stock
      formData.inventory_stock = INVENTORY_CONSUME
    }
  } else if (String(row.bom_type) === '0' && !row.parent_sn_code && formData.inventory_stock === INVENTORY_CONSUME) {
    // 清除父级SN码后的状态
    const revertVal = stockBeforeConsume.value !== null ? stockBeforeConsume.value : 0
    formData.inventory_stock = revertVal
    originalInventoryStock.value = revertVal
    stockBeforeConsume.value = null
  }
  // 同步测试状态
  formData.status =
    formData.inventory_stock === 1 || formData.inventory_stock === 2 || formData.inventory_stock === 3 ? STATUS_PASS : row.status
  dialogVisible.value = true
}

const saveProduct = () => {
  submitting.value = true
  return updateFinishProduct({
    id: formData.id,
    sn_code: formData.sn_code?.trim() || '',
    status: formData.status,
    inventory_stock: formData.inventory_stock,
    repair: formData.repair,
    description: formData.description,
    parent_sn_code: formData.parent_sn_code?.trim() || '',
    create_time: formData.create_time || null,
    test_time: formData.test_time || null,
    stock_in_time: formData.stock_in_time || null,
    stock_out_time: formData.stock_out_time || null
  })
}

const handleSubmit = () => {
  if (requiresPassStatus.value && formData.status !== STATUS_PASS) {
    ElMessage.warning('入库或出库时，测试状态必须为「测试合格」')
    return
  }
  // 组件消耗状态需要SN码
  if (formData.inventory_stock === INVENTORY_CONSUME && !formData.sn_code?.trim()) {
    ElMessage.warning('组件消耗状态必须填写SN码')
    return
  }
  formRef.value?.validate((valid) => {
    if (!valid) return

    if (formData.repair === 1) {
      repairConfirmVisible.value = true
    } else {
      doSaveProduct()
    }
  })
}

const doSaveProduct = () => {
  saveProduct()
    .then(() => {
      ElMessage.success('保存成功')
      dialogVisible.value = false
      getList()
      checkJointConsistency()
    })
    .catch(() => {})
    .finally(() => {
      submitting.value = false
    })
}

const handleRepairConfirmGenerate = () => {
  repairConfirmVisible.value = false
  repairFormData.repair_info = ''
  repairDialogVisible.value = true
}

const handleRepairConfirmSkip = () => {
  repairConfirmVisible.value = false
  doSaveProduct()
}

const handleRepairConfirmCancel = () => {
  repairConfirmVisible.value = false
}

const handleRepairSubmit = () => {
  if (!repairFormData.repair_info?.trim()) {
    ElMessage.warning('请填写返修内容')
    return
  }
  repairSubmitting.value = true
  saveProduct()
    .then(() => {
      return createRepair({
        product_id: formData.id,
        repair_info: repairFormData.repair_info.trim()
      })
    })
    .then(() => {
      ElMessage.success('保存成功，返修单已生成')
      repairDialogVisible.value = false
      dialogVisible.value = false
      getList()
      checkJointConsistency()
    })
    .catch(() => {})
    .finally(() => {
      repairSubmitting.value = false
      submitting.value = false
    })
}

const handleRollback = (row) => {
  const snText = row.sn_code ? `SN: ${row.sn_code}` : '无 SN 码'
  ElMessageBox.confirm(
    `回退将把成品「${formatFinishProductLabel(row)}」（${snText}）重新拆回零部件，并恢复对应零件库存。\n\n此操作非常危险，将永久删除该条成品数据且无法恢复，是否继续？`,
    '危险操作确认',
    {
      confirmButtonText: '确认回退',
      cancelButtonText: '取消',
      type: 'warning',
      confirmButtonClass: 'el-button--danger',
      dangerouslyUseHTMLString: false
    }
  )
    .then(() => rollbackFinishProduct({ id: row.id }))
    .then(() => {
      ElMessage.success('回退成功，零件库存已恢复')
      getList()
    })
    .catch((err) => {
      if (err !== 'cancel' && err !== 'close') {
        // 接口错误由 request 拦截器提示
      }
    })
}

const handleBindJoints = async (row) => {
  bindJointRow.value = row
  selectedJointIds.value = []
  bindJointVisible.value = true
  bindJointLoading.value = true
  loadJointBomList()

  // 加载全量数据，确保可绑定的关节列表不受当前页限制
  try {
    const res = await getFinishProductList({
      pageNum: 1,
      pageSize: 9999,
      bom_type: '0',
      status: STATUS_PASS,
      inventory_stock: INVENTORY_IN
    })
    // 用后端返回的数据过滤出未绑定的关节
    const allData = res?.list || []
    bindJointData.value = allData.filter(
      item => !item.parent_sn_code && item.sn_code
    )
  } catch (e) {
    console.error('加载全量关节数据失败', e)
    bindJointData.value = []
  } finally {
    bindJointLoading.value = false
  }
}

const loadJointBomList = async () => {
  try {
    const res = await getBomList({ pageNum: 1, pageSize: 999 })
    addJointBomList.value = res?.list || []
  } catch (e) {
    console.error('加载BOM列表失败', e)
  }
}

const openAddJointDialog = () => {
  addJointBomId.value = null
  addJointSnCode.value = ''
  addJointVisible.value = true
}

const handleAddJoint = async () => {
  if (!addJointBomId.value) {
    ElMessage.warning('请选择关节BOM')
    return
  }
  addJointSubmitting.value = true
  try {
    await createFinishProduct({
      bom_id: addJointBomId.value,
      sn_code: addJointSnCode.value?.trim() || ''
    })
    ElMessage.success('关节创建成功')
    addJointVisible.value = false
    addJointBomId.value = null
    addJointSnCode.value = ''
    await getList()
  } catch (e) {
    // 错误由request拦截器提示
  } finally {
    addJointSubmitting.value = false
  }
}

const handleBindSubmit = () => {
  if (!bindJointRow.value?.sn_code) {
    ElMessage.warning('机械臂缺少SN码')
    return
  }
  if (selectedJoints.value.length === 0) {
    ElMessage.warning('请至少选择一个关节')
    return
  }
  bindSubmitting.value = true
  bindJointsToArm({
    arm_id: bindJointRow.value.id,
    arm_sn_code: bindJointRow.value.sn_code,
    joint_ids: selectedJoints.value.map(j => j.id)
  })
    .then(() => {
      ElMessage.success(`已绑定 ${selectedJoints.value.length} 个关节到机械臂`)
      bindJointVisible.value = false
      getList()
      checkJointConsistency()
    })
    .catch(() => {})
    .finally(() => {
      bindSubmitting.value = false
    })
}

const checkJointConsistency = async () => {
  try {
    const data = await checkJointStockConsistency()
    showJointWarning.value = !data.is_consistent
  } catch (error) {
    console.error('检查关节库存一致性失败', error)
  }
}

onMounted(() => {
  loadColumnSettings()
  dictStore.loadDictItems('storage_status', true)
  getList()
  checkJointConsistency()
})
</script>

<style scoped>
.app-container {
  padding: 20px;
}
.search-card {
  margin-bottom: 20px;
}
.search-form {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}
.table-card {
  margin-bottom: 20px;
}
.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.table-toolbar .toolbar-actions {
  display: flex;
  gap: 8px;
}

:deep(.el-table .row-clickable) {
  cursor: pointer;
}

:deep(.el-table .row-clickable:hover > td) {
  background-color: var(--el-color-primary-light-9) !important;
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
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.text-muted {
  color: #909399;
  font-style: italic;
}
.finish-edit-form :deep(.el-form-item__label) {
  white-space: nowrap;
}
.finish-edit-form__radio-row :deep(.el-radio-group) {
  flex-wrap: nowrap;
}
.joint-warning {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  margin-bottom: 20px;
  background-color: #fef0f0;
  border: 1px solid #fecaca;
  border-radius: 4px;
  color: #dc3545;
  font-size: 14px;
}

.joint-warning .warning-icon {
  font-size: 16px;
}

.repair-confirm-tip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  background-color: var(--el-color-warning-light-9);
  border: 1px solid var(--el-color-warning-light-7);
  border-radius: 6px;
  color: var(--el-color-warning);
  font-size: 14px;
  line-height: 1.5;
}

.repair-confirm-tip .warning-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.joint-detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 10px 14px;
  background-color: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: 6px;
  color: var(--el-color-primary);
  font-size: 14px;
}

.bind-joint-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  background: var(--el-color-primary-light-9);
  border-radius: 4px;
  margin-bottom: 12px;
  font-size: 14px;
}

.bind-joint-tip {
  margin-bottom: 12px;
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.bind-joint-footer {
  margin-top: 12px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.bind-joint-footer b {
  color: var(--el-color-primary);
}

.bind-joint-select-wrapper {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.joint-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.joint-option__sn {
  font-weight: 500;
}

.joint-option__model {
  color: var(--el-text-color-regular);
}

.joint-option__name {
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}

.joint-option__tag {
  margin-left: auto;
}

.bind-joint-selected {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;
  padding: 10px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
}

.selected-label {
  font-size: 13px;
  color: var(--el-text-color-regular);
  white-space: nowrap;
  line-height: 1.6;
}

.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.select-empty {
  text-align: center;
  color: var(--el-text-color-placeholder);
  padding: 10px;
  font-size: 13px;
}

.finish-edit-form__radio-row :deep(.el-radio) {
  margin-right: 16px;
}
.finish-edit-form__radio-row :deep(.el-radio:last-child) {
  margin-right: 0;
}
.finish-edit-form__hint {
  width: 100%;
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.4;
  color: var(--el-color-warning);
}
</style>
