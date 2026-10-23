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
          <DictSelect
            v-model="queryParams.status"
            code="test_status"
            placeholder="全部"
            style="width: 130px"
            @change="handleSearch"
          />
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
        <el-form-item label="描述">
          <el-input
            v-model="queryParams.description"
            placeholder="描述"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="创建人">
          <el-input
            v-model="queryParams.creator_name"
            placeholder="创建人"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="最后操作人">
          <el-input
            v-model="queryParams.editor_name"
            placeholder="最后操作人"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
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
        <el-form-item label="SN码录入时间">
          <el-date-picker
            v-model="queryParams.snDateRange"
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
      <span>库存关节/机械臂数量与成品入库数量不符，请检查产品库存是否正确</span>
    </div>

    <el-card shadow="never" class="table-card">
      <div class="table-toolbar">
        <el-checkbox v-model="collapseMode">折叠模式</el-checkbox>
        <div class="toolbar-actions">
          <el-button type="success" @click="openQuickActionDialog">
            <el-icon><Operation /></el-icon> 快捷操作
          </el-button>
          <el-button type="warning" @click="handleAssemble">
            <el-icon><Box /></el-icon> 组装产品
          </el-button>
          <el-button type="info" :loading="exportLoading" @click="handleExportExcel">
            <el-icon><Download /></el-icon> 导出Excel
          </el-button>
          <el-button @click="openColumnDialog">
            <el-icon><Setting /></el-icon> 列展示
          </el-button>
        </div>      </div>

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
          v-if="isColumnVisible('sn_code_time')"
          prop="sn_code_time"
          label="SN码录入时间"
          width="170"
        />
        <el-table-column
          v-if="isColumnVisible('sn_code_binder')"
          prop="sn_code_binder"
          label="SN码绑定人"
          width="120"
          show-overflow-tooltip
        />
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
        <el-table-column label="操作" width="240" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click.stop="handleEdit(row)">编辑</el-button>
            <el-button
              v-if="String(row.status) === '3' || String(row.repair) === '1'"
              link type="warning" size="small" @click.stop="handleViewUnqualified(row)"
            >不良详情</el-button>
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
          <div v-if="lockNonSnFields" class="finish-edit-form__hint">
            未组装产品仅可填写SN码，保存后测试状态将自动变为「未测试」
          </div>
        </el-form-item>
        <el-form-item label="SN码绑定人">
          <el-input
            v-model="formData.sn_code_binder"
            disabled
            placeholder="SN码录入时自动写入"
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
                placeholder="数据生成时自动写入"
                value-format="YYYY-MM-DD HH:mm:ss"
                format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
                disabled
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="测试状态修改时间">
              <el-date-picker
                v-model="formData.test_time"
                type="datetime"
                placeholder="测试状态变更时自动写入"
                value-format="YYYY-MM-DD HH:mm:ss"
                format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
                disabled
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="SN码录入时间">
              <el-date-picker
                v-model="formData.sn_code_time"
                type="datetime"
                placeholder="SN码修改时自动写入"
                value-format="YYYY-MM-DD HH:mm:ss"
                format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
                disabled
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="上次更改时间">
              <el-date-picker
                v-model="formData.update_time"
                type="datetime"
                placeholder="保存时自动写入"
                value-format="YYYY-MM-DD HH:mm:ss"
                format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
                disabled
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="返修" class="finish-edit-form__radio-row">
          <el-radio-group v-model="formData.repair" :disabled="lockNonSnFields">
            <el-radio :value="0">新品</el-radio>
            <el-radio :value="1">返修品</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="测试状态" class="finish-edit-form__radio-row">
          <el-radio-group v-model="formData.status" :disabled="lockNonSnFields">
            <el-radio :value="4" :disabled="requiresPassStatus">未组装</el-radio>
            <el-radio :value="0" :disabled="requiresPassStatus">未测试</el-radio>
            <el-radio :value="1" :disabled="requiresPassStatus">测试中</el-radio>
            <el-radio :value="2">测试合格</el-radio>
            <el-radio :value="3" :disabled="requiresPassStatus">测试不良</el-radio>
          </el-radio-group>
          <div v-if="requiresPassStatus" class="finish-edit-form__hint">
            选择入库/出库时，测试状态必须为「测试合格」
          </div>
          <div v-if="formData.status === 3" class="finish-edit-form__hint" style="color: #E6A23C;">
            ⚠️ 选择「测试不良」后，保存时需要选择不合格项
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
                :disabled="lockNonSnFields"
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
                :disabled="lockNonSnFields"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="库存状态">
          <el-select
            v-model="formData.inventory_stock"
            placeholder="请选择库存状态"
            style="width: 100%"
            :disabled="isJointWithParent || lockNonSnFields"
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
            :disabled="lockNonSnFields"
          />
        </el-form-item>
        <el-form-item label="父级SN码">
          <el-input
            v-model="formData.parent_sn_code"
            placeholder="请输入父级产品SN码"
            maxlength="255"
            clearable
            :disabled="isArmProduct || lockNonSnFields"
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
    >
      <div class="repair-confirm-tip">
        <el-icon class="warning-icon"><WarningFilled /></el-icon>
        <span>{{ repairConfirmTip }}</span>
      </div>
      <template #footer>
        <el-button @click="handleRepairConfirmCancel">取消</el-button>
        <el-button type="info" @click="handleRepairConfirmSkip">不生成</el-button>
        <el-button type="primary" @click="handleRepairConfirmGenerate">生成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="repairDialogVisible" title="生成返修单" width="520px" destroy-on-close>
      <el-form :model="repairFormData" label-width="80px">
        <el-form-item label="SN码">
          <span>{{ formData.sn_code || '—' }}</span>
        </el-form-item>
        <el-form-item label="不良项">
          <el-select
            v-model="repairFormData.unqualified_values"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择不良项"
            style="width: 100%"
          >
            <el-option
              v-for="item in repairUnqualifiedOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
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
        <span>（共 {{ jointDetailChildren.length }} 个关节子件）</span>
      </div>
      <el-table
        v-loading="jointDetailLoading"
        :data="jointDetailChildren"
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
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="danger"
              size="small"
              :loading="row._unbinding"
              @click.stop="handleUnbindJoint(row)"
            >
              解除绑定
            </el-button>
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
        <el-form-item label="SN码" required>
          <el-input
            v-model="addJointSnCode"
            placeholder="请输入SN码"
            clearable
          />
        </el-form-item>
        <el-form-item label="创建时间">
          <el-date-picker
            v-model="addJointCreateTime"
            type="datetime"
            placeholder="默认为当前时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="SN码录入时间">
          <el-date-picker
            v-model="addJointSnCodeTime"
            type="datetime"
            placeholder="默认为当前时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="入库时间">
          <el-date-picker
            v-model="addJointStockInTime"
            type="datetime"
            placeholder="默认为当前时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
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

    <!-- 不合格项选择对话框（编辑保存时使用） -->
    <el-dialog
      v-model="unqualifiedSelectVisible"
      title="测试不良处理"
      width="520px"
      :close-on-click-modal="false"
    >
      <div class="unqualified-tip">
        请选择该成品的不合格项（可多选）
      </div>
      <el-form :model="{ values: selectedUnqualifiedValues }" label-width="0">
        <el-form-item>
          <el-select
            v-model="selectedUnqualifiedValues"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择不合格项"
            style="width: 100%"
          >
            <el-option
              v-for="item in dictStore.getDictItems('unqualified_status')"
              :key="item.value"
              :label="item.label"
              :value="Number(item.value)"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <div class="generate-repair-row">
            <span>同时生成返修单</span>
            <el-switch v-model="unqualifiedGenerateRepair" />
          </div>
        </el-form-item>
        <el-form-item v-if="unqualifiedGenerateRepair">
          <el-input
            v-model="unqualifiedRepairInfo"
            type="textarea"
            :rows="3"
            placeholder="选填，默认使用已选不良项作为返修内容"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="unqualifiedSelectVisible = false">取消</el-button>
        <el-button type="primary" :loading="unqualifiedSelectSubmitting" @click="handleUnqualifiedSelectConfirm">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 不合格项详情对话框（列表中查看使用） -->
    <el-dialog
      v-model="unqualifiedDetailVisible"
      title="不良详情"
      width="520px"
      destroy-on-close
    >
      <div v-if="unqualifiedDetailRow" class="unqualified-detail-header">
        <span>SN码：{{ unqualifiedDetailRow.sn_code || '—' }}</span>
        <span>BOM：{{ unqualifiedDetailRow.bom_model }} ({{ unqualifiedDetailRow.bom_name }})</span>
      </div>
      <div v-loading="unqualifiedDetailLoading">
        <el-table :data="unqualifiedDetailItems" border stripe style="width: 100%" max-height="300">
          <el-table-column prop="unqualified_label" label="不合格项" />
          <el-table-column prop="create_time" label="添加时间" width="170" />
          <el-table-column label="操作" width="80" align="center">
            <template #default="{ row }">
              <el-button
                link
                type="danger"
                size="small"
                @click="handleDeleteUnqualified(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
          <template #empty>
            <div style="padding: 20px; color: #999;">暂无不合格项</div>
          </template>
        </el-table>
      </div>
      <el-form :model="{ value: newUnqualifiedValue }" label-width="80px" style="margin-top: 10px;">
        <el-form-item label="添加不良">
          <el-select
            v-model="newUnqualifiedValue"
            placeholder="选择不合格项"
            style="width: 100%"
            clearable
          >
            <el-option
              v-for="item in dictStore.getDictItems('unqualified_status')"
              :key="item.value"
              :label="item.label"
              :value="Number(item.value)"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="unqualifiedDetailVisible = false">关闭</el-button>
        <el-button type="primary" :loading="unqualifiedDetailSubmitting" @click="handleAddUnqualified">
          添加
        </el-button>
      </template>
    </el-dialog>

    <!-- 快捷操作主对话框 -->
    <el-dialog
      v-model="quickActionVisible"
      title="快捷操作"
      width="520px"
      destroy-on-close
    >
      <div class="quick-action-buttons">
        <el-button
          type="success"
          size="large"
          @click="handleQuickActionSelect('pass')"
          :loading="quickActionSubmitting"
        >
          测试合格
        </el-button>
        <el-button
          type="danger"
          size="large"
          @click="handleQuickActionSelect('fail')"
          :loading="quickActionSubmitting"
        >
          测试不良
        </el-button>
        <el-button
          type="primary"
          size="large"
          @click="openBatchBindSnDialog"
        >
          批量绑定SN码
        </el-button>
        <el-button
          type="warning"
          size="large"
          @click="openBatchAddJointDialog"
        >
          添加关节
        </el-button>
      </div>
      <template #footer>
        <el-button @click="quickActionVisible = false">取消</el-button>
      </template>
    </el-dialog>

    <!-- 快捷操作SN码输入对话框（测试合格支持批量） -->
    <el-dialog
      v-model="quickActionSnVisible"
      :title="quickActionSnTitle"
      width="480px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form label-width="80px">
        <el-form-item label="SN码">
          <div v-if="quickActionType === 'pass'" class="quick-sn-list">
            <el-input
              v-for="(sn, index) in quickActionSnList"
              :key="index"
              :ref="(el) => setQuickSnRef(el, index)"
              v-model="quickActionSnList[index]"
              placeholder="请输入SN码，按回车填写下一个"
              clearable
              @keydown.enter.prevent="addQuickSnInput"
            />
            <el-button class="quick-sn-add" @click="addQuickSnInput">
              <el-icon><Plus /></el-icon> 填写下一个
            </el-button>
          </div>
          <el-input
            v-else
            v-model="quickActionSnCode"
            placeholder="请输入SN码"
            maxlength="255"
            clearable
            @keydown.enter.prevent="handleQuickActionSnConfirm"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="quickActionSnVisible = false">取消</el-button>
        <el-button type="primary" :loading="quickActionSnSubmitting" @click="handleQuickActionSnConfirm">
          {{ quickActionType === 'pass' ? '保存' : '确认' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 快捷操作：批量添加关节 -->
    <el-dialog
      v-model="batchAddJointVisible"
      title="批量添加关节"
      width="520px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form label-width="110px">
        <el-form-item label="关节BOM" required>
          <el-select
            v-model="batchAddJointBomId"
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
        <el-form-item label="SN码" required>
          <div class="quick-sn-list">
            <el-input
              v-for="(sn, index) in batchAddJointSnList"
              :key="index"
              :ref="(el) => setBatchAddJointSnRef(el, index)"
              v-model="batchAddJointSnList[index]"
              placeholder="请输入SN码，按回车填写下一个"
              clearable
              @keydown.enter.prevent="addBatchAddJointSnInput"
            />
            <el-button class="quick-sn-add" @click="addBatchAddJointSnInput">
              <el-icon><Plus /></el-icon> 填写下一个
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="创建时间">
          <el-date-picker
            v-model="batchAddJointCreateTime"
            type="datetime"
            placeholder="默认为当前时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="SN码录入时间">
          <el-date-picker
            v-model="batchAddJointSnCodeTime"
            type="datetime"
            placeholder="默认为当前时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="入库时间">
          <el-date-picker
            v-model="batchAddJointStockInTime"
            type="datetime"
            placeholder="默认为当前时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchAddJointVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchAddJointSubmitting" @click="handleBatchAddJoint">
          批量创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 批量绑定SN码弹窗 -->
    <el-dialog
      v-model="batchBindSnVisible"
      title="批量绑定SN码"
      width="1200px"
      :close-on-click-modal="false"
      destroy-on-close
      @closed="batchBindData = []"
    >
      <div class="batch-bind-wrapper">
        <div class="batch-bind-toolbar">
          <span class="batch-bind-count">共 {{ batchBindData.length }} 条待填写</span>
        </div>
        <el-table :data="batchBindData" border stripe height="500" style="width: 100%">
          <el-table-column type="index" label="序号" width="60" align="center" fixed="left" />
          <el-table-column prop="sn_code" label="SN码" min-width="200" fixed="left">
            <template #default="{ row, $index }">
              <el-input
                :ref="(el) => setBatchSnRef(el, $index)"
                v-model="row.sn_code"
                placeholder="请输入SN码"
                clearable
                :class="{ 'sn-duplicate': isSnDuplicate($index) }"
                @keydown.enter.prevent="handleBatchSnEnter($index)"
              />
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
            v-if="isColumnVisible('create_time')"
            prop="create_time"
            label="创建时间"
            width="170"
          />
          <el-table-column
            v-if="isColumnVisible('description')"
            prop="description"
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
      </div>
      <template #footer>
        <el-button @click="batchBindSnVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchBindSaving" @click="handleBatchBindSave">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch, nextTick } from 'vue'
import { Search, Refresh, Setting, Box, WarningFilled, Plus, Operation, Download } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ExcelJS from 'exceljs'
import { getFinishProductList, createFinishProduct, updateFinishProduct, rollbackFinishProduct, checkJointStockConsistency, bindJointsToArm, getBindableJoints, getUnqualifiedItems, saveUnqualifiedItems, deleteUnqualifiedItem, addUnqualifiedItem } from '@/api/finish-product'
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
  description: '',
  creator_name: '',
  editor_name: '',
  createDateRange: null,
  snDateRange: null,
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
    repair: queryParams.repair,
    description: queryParams.description,
    creator_name: queryParams.creator_name,
    editor_name: queryParams.editor_name
  }
  appendDateRangeParams(params, queryParams.createDateRange, 'create_start_date', 'create_end_date')
  appendDateRangeParams(params, queryParams.snDateRange, 'sn_start_date', 'sn_end_date')
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
  repair_info: '',
  unqualified_values: []
})
const repairUnqualifiedOptions = ref([])

const repairConfirmVisible = ref(false)
const repairConfirmTip = ref('当前产品已标记为「返修品」，是否同时生成返修单？')

const collapseMode = ref(true)

const jointDetailVisible = ref(false)
const jointDetailRow = ref(null)
const jointDetailChildren = ref([])
const jointDetailLoading = ref(false)

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
const addJointCreateTime = ref('')
const addJointSnCodeTime = ref('')
const addJointStockInTime = ref('')
const addJointBomList = ref([])

// 不合格项选择对话框（编辑时使用）
const unqualifiedSelectVisible = ref(false)
const unqualifiedSelectSubmitting = ref(false)
const selectedUnqualifiedValues = ref([])
// 测试不良弹窗内直接选择是否生成返修单
const unqualifiedGenerateRepair = ref(false)
const unqualifiedRepairInfo = ref('')

// 不合格项详情对话框（列表中查看使用）
const unqualifiedDetailVisible = ref(false)
const unqualifiedDetailRow = ref(null)
const unqualifiedDetailItems = ref([])
const unqualifiedDetailLoading = ref(false)
const newUnqualifiedValue = ref(null)
const unqualifiedDetailSubmitting = ref(false)

// 快捷操作相关状态
const quickActionVisible = ref(false)
const quickActionSubmitting = ref(false)
const quickActionSnVisible = ref(false)
const quickActionSnTitle = ref('')
const quickActionSnCode = ref('')
const quickActionSnSubmitting = ref(false)
const quickActionType = ref('')
// 测试合格批量：SN码输入框列表（每个元素对应一个输入框）
const quickActionSnList = ref([''])
const quickSnInputRefs = []

// 快捷操作：批量添加关节
const batchAddJointVisible = ref(false)
const batchAddJointSubmitting = ref(false)
const batchAddJointBomId = ref(null)
const batchAddJointSnList = ref([''])
const batchAddJointCreateTime = ref('')
const batchAddJointSnCodeTime = ref('')
const batchAddJointStockInTime = ref('')
const batchAddJointSnRefs = []

// 批量绑定SN码相关状态
const batchBindSnVisible = ref(false)
const batchBindSaving = ref(false)
const batchBindData = ref([])
const batchSnInputRefs = []
// 原始数据快照（打开时的 sn_code），用于保存时判断是否被修改
const batchBindOriginalSnapshot = ref({})

// 过滤仅显示关节类型的BOM
const jointBomList = computed(() => {
  return addJointBomList.value.filter(b => String(b.type) === '0' || String(b.bom_type) === '0')
})

// 折叠后可见的数据（仅过滤掉被折叠的行，未分页）
const visibleData = computed(() => {
  if (!collapseMode.value) return tableData.value
  // 折叠模式：已绑定父级（有 parent_sn_code）的关节一律隐藏。
  // 关节详情通过点击机械臂行后按 parent_sn_code 单独从后端加载，
  // 不依赖父级机械臂是否在当前结果集中（父级可能因筛选条件或已回退而不在列表内）。
  return tableData.value.filter(row => {
    return String(row.bom_type) !== '0' || !row.parent_sn_code
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
  sn_code_time: '',
  sn_code_binder: '',
  update_time: '',
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

// 当前编辑行的原始SN码（handleEdit 填充时记录）
const editingOriginalSnCode = ref('')

// 未组装产品（SN码为空）编辑锁定：仅允许填写SN码，保存后后端自动将测试状态改为未测试
const lockNonSnFields = computed(() => !editingOriginalSnCode.value)

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
  if (value === 4) return 'info'
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
  if (collapseMode.value) {
    // 折叠模式：循环分页加载全部数据（后端 MAX_PAGE_SIZE=100，不能一次全拿）
    loadAllPages(params)
      .then(({ allList, total }) => {
        tableData.value = allList
        backendTotal.value = total
        // 折叠模式下防止当前页越界
        const maxPage = Math.max(1, Math.ceil(visibleData.value.length / queryParams.pageSize))
        if (queryParams.pageNum > maxPage) {
          queryParams.pageNum = 1
        }
      })
      .catch(() => {
        ElMessage.error('获取成品列表失败')
      })
      .finally(() => {
        loading.value = false
      })
  } else {
    getFinishProductList(params)
      .then((response) => {
        tableData.value = response?.list || []
        backendTotal.value = response?.total || 0
      })
      .catch(() => {
        ElMessage.error('获取成品列表失败')
      })
      .finally(() => {
        loading.value = false
      })
  }
}

// 折叠模式专用：循环拉取所有页（后端单页上限 100）
const loadAllPages = async (baseParams) => {
  const pageSize = 100  // 匹配后端 MAX_PAGE_SIZE
  let pageNum = 1
  const allList = []
  let total = 0
  while (true) {
    const resp = await getFinishProductList({ ...baseParams, pageNum, pageSize })
    const list = resp?.list || []
    total = resp?.total || 0
    allList.push(...list)
    if (allList.length >= total || list.length < pageSize) break
    pageNum++
  }
  return { allList, total }
}

// ==================== 导出 Excel ====================
const exportLoading = ref(false)

const EXPORT_COLUMNS = [
  { header: 'SN码', key: 'sn_code' },
  { header: 'SN码录入时间', key: 'sn_code_time' },
  { header: 'SN码绑定人', key: 'sn_code_binder' },
  { header: 'BOM类型', key: 'bom_type' },
  { header: 'BOM型号', key: 'bom_model' },
  { header: 'BOM名称', key: 'bom_name' },
  { header: '物料编码', key: 'material_code' },
  { header: '父级SN码', key: 'parent_sn_code' },
  { header: '测试状态', key: 'status' },
  { header: '库存状态', key: 'inventory_stock' },
  { header: '返修', key: 'repair' },
  { header: '测试状态修改时间', key: 'test_time' },
  { header: '入库时间', key: 'stock_in_time' },
  { header: '出库时间', key: 'stock_out_time' },
  { header: '创建时间', key: 'create_time' },
  { header: '更新时间', key: 'update_time' },
  { header: '描述', key: 'description' },
]

// 库存状态从字典取标签
const resolveDictLabel = (code, value) => {
  if (value === null || value === undefined || value === '') return ''
  const items = dictStore.getDictItems(code)
  const item = items.find(i => String(i.value) === String(value))
  return item?.label || ''
}

// 按列 key 取行的显示值（格式化后的文本，非原始 code）
const getExportCellValue = (row, key) => {
  switch (key) {
    case 'bom_type': return row.bom_type_name || ''
    case 'status': return row.status_name || ''
    case 'inventory_stock': return resolveDictLabel('storage_status', row.inventory_stock)
    case 'repair': return row.repair_name || ''
    default: return row[key] ?? ''
  }
}

const handleExportExcel = async () => {
  exportLoading.value = true
  try {
    let exportData
    if (collapseMode.value) {
      exportData = visibleData.value
    } else {
      const params = buildListParams()
      const { allList } = await loadAllPages({ ...params, pageNum: 1, pageSize: 100 })
      exportData = allList
    }

    if (!exportData || exportData.length === 0) {
      ElMessage.warning('没有可导出的数据')
      return
    }

    const workbook = new ExcelJS.Workbook()
    const sheet = workbook.addWorksheet('成品列表')

    sheet.columns = EXPORT_COLUMNS.map(col => ({
      header: col.header,
      key: col.key,
      width: 22,
    }))

    // 表头样式
    const headerRow = sheet.getRow(1)
    headerRow.font = { bold: true }
    headerRow.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE0E0E0' } }
    headerRow.alignment = { vertical: 'middle', horizontal: 'center' }

    exportData.forEach(row => {
      const rowData = {}
      EXPORT_COLUMNS.forEach(col => {
        rowData[col.key] = getExportCellValue(row, col.key)
      })
      sheet.addRow(rowData)
    })

    // 自动筛选：覆盖表头到最后一行数据
    const lastCol = String.fromCharCode(64 + EXPORT_COLUMNS.length)
    const lastRow = exportData.length + 1
    sheet.autoFilter = `A1:${lastCol}${lastRow}`

    const buffer = await workbook.xlsx.writeBuffer()
    const blob = new Blob([buffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=utf-8',
    })
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    const now = new Date()
    const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
    link.href = downloadUrl
    link.download = `成品列表_${dateStr}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)

    ElMessage.success(`已导出 ${exportData.length} 条数据`)
  } catch (e) {
    console.error('导出失败', e)
    ElMessage.error('导出失败')
  } finally {
    exportLoading.value = false
  }
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
  queryParams.description = ''
  queryParams.creator_name = ''
  queryParams.editor_name = ''
  queryParams.createDateRange = null
  queryParams.snDateRange = null
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

const handleRowClick = async (row) => {
  if (!collapseMode.value) return
  if (String(row.bom_type) === '1' && row.sn_code) {
    jointDetailRow.value = row
    jointDetailVisible.value = true
    // 从后端加载关节数据，不依赖当前页表格数据
    jointDetailLoading.value = true
    jointDetailChildren.value = []
    try {
      const res = await getFinishProductList({
        parent_sn_code: row.sn_code,
        pageNum: 1,
        pageSize: 1000,
      })
      jointDetailChildren.value = res?.list || []
    } catch (e) {
      console.error('加载关节数据失败', e)
    } finally {
      jointDetailLoading.value = false
    }
  }
}

const handleUnbindJoint = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定解除关节 ${row.sn_code || '无SN码'} 与机械臂 ${jointDetailRow.value?.sn_code} 的绑定吗？`,
      '解除绑定',
      { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  row._unbinding = true
  try {
    await updateFinishProduct({
      id: row.id,
      sn_code: row.sn_code || '',
      parent_sn_code: '',
    })
    ElMessage.success('解除绑定成功')
    // 从列表中移除已解绑的关节
    jointDetailChildren.value = jointDetailChildren.value.filter(item => item.id !== row.id)
    // 更新主表格中对应的数据
    const tableRow = tableData.value.find(item => item.id === row.id)
    if (tableRow) {
      tableRow.parent_sn_code = ''
    }
  } catch (e) {
    ElMessage.error('解除绑定失败')
    console.error(e)
  } finally {
    row._unbinding = false
  }
}

// ==================== 不合格项相关方法 ====================

// 查看不合格项详情
const handleViewUnqualified = async (row) => {
  unqualifiedDetailRow.value = row
  unqualifiedDetailVisible.value = true
  unqualifiedDetailLoading.value = true
  unqualifiedDetailItems.value = []
  try {
    const res = await getUnqualifiedItems({ finish_product_id: row.id })
    unqualifiedDetailItems.value = res || []
  } catch (e) {
    console.error('加载不合格项失败', e)
    ElMessage.error('加载不合格项失败')
  } finally {
    unqualifiedDetailLoading.value = false
  }
}

// 编辑保存时，不合格项选择确认
const handleUnqualifiedSelectConfirm = async () => {
  unqualifiedSelectSubmitting.value = true
  try {
    // 1. 先保存成品
    await saveProduct()
    // 2. 再保存不合格项
    await saveUnqualifiedItems({
      finish_product_id: formData.id,
      sn_code: formData.sn_code?.trim() || '',
      unqualified_values: selectedUnqualifiedValues.value,
    })
    // 3. 勾选生成返修单时，同一次提交内创建返修单
    if (formData.status === 3 && unqualifiedGenerateRepair.value) {
      const options = dictStore.getDictItems('unqualified_status')
      const selectedLabels = selectedUnqualifiedValues.value.map((value) => {
        const matched = options.find(item => Number(item.value) === Number(value))
        return matched ? matched.label : String(value)
      })
      let repairInfo = unqualifiedRepairInfo.value.trim()
      if (selectedLabels.length > 0) {
        const prefix = `不良项：${selectedLabels.join('、')}`
        repairInfo = repairInfo ? `${prefix}\n${repairInfo}` : prefix
      }
      if (!repairInfo) {
        repairInfo = '测试不良返修'
      }
      try {
        await createRepair({
          product_id: formData.id,
          repair_info: repairInfo,
        })
        ElMessage.success('保存成功，返修单已生成')
      } catch (repairError) {
        // 成品与不良项已保存，返修单失败不回滚，仅提示
        ElMessage.error('成品与不良项已保存，返修单生成失败：' + (repairError.message || repairError))
      }
    } else {
      ElMessage.success('保存成功')
    }
    unqualifiedSelectVisible.value = false
    dialogVisible.value = false
    getList()
    checkJointConsistency()
  } catch (e) {
    console.error(e)
  } finally {
    unqualifiedSelectSubmitting.value = false
    submitting.value = false
  }
}

// 删除单个不合格项
const handleDeleteUnqualified = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除此不合格项吗？', '删除', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteUnqualifiedItem(row.id)
    ElMessage.success('删除成功')
    // 从列表中移除
    unqualifiedDetailItems.value = unqualifiedDetailItems.value.filter(item => item.id !== row.id)
  } catch (e) {
    ElMessage.error('删除失败')
    console.error(e)
  }
}

// 添加单个不合格项
const handleAddUnqualified = async () => {
  if (!newUnqualifiedValue.value) {
    ElMessage.warning('请选择不合格项')
    return
  }
  unqualifiedDetailSubmitting.value = true
  try {
    const res = await addUnqualifiedItem({
      finish_product_id: unqualifiedDetailRow.value.id,
      sn_code: unqualifiedDetailRow.value.sn_code,
      unqualified_value: newUnqualifiedValue.value,
    })
    if (res) {
      unqualifiedDetailItems.value.push(res)
      newUnqualifiedValue.value = null
      ElMessage.success('添加成功')
    }
  } catch (e) {
    console.error(e)
  } finally {
    unqualifiedDetailSubmitting.value = false
  }
}

const getRowClassName = ({ row }) => {
  if (collapseMode.value && String(row.bom_type) === '1' && row.sn_code) {
    return 'row-clickable'
  }
  return ''
}

const handleEdit = (row) => {
  formData.id = row.id
  editingOriginalSnCode.value = row.sn_code || ''
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
  formData.sn_code_time = row.sn_code_time || ''
  formData.sn_code_binder = row.sn_code_binder || ''
  formData.update_time = row.update_time || ''
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
  unqualifiedGenerateRepair.value = false
  unqualifiedRepairInfo.value = ''
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

    // 测试不良状态：弹出不合格项选择对话框（可在同一弹窗内勾选生成返修单）
    if (formData.status === 3) {
      unqualifiedGenerateRepair.value = false
      unqualifiedRepairInfo.value = ''
      // 加载已有的不合格项
      getUnqualifiedItems({ finish_product_id: formData.id })
        .then((items) => {
          selectedUnqualifiedValues.value = items.map(item => item.unqualified_value)
          unqualifiedSelectVisible.value = true
        })
        .catch(() => {
          selectedUnqualifiedValues.value = []
          unqualifiedSelectVisible.value = true
        })
      return
    }

    if (formData.repair === 1) {
      repairConfirmTip.value = '当前产品已标记为「返修品」，是否同时生成返修单？'
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

const handleRepairConfirmGenerate = async () => {
  repairConfirmVisible.value = false
  repairFormData.repair_info = ''
  repairFormData.unqualified_values = []

  // 加载字典项
  await dictStore.loadDictItems('unqualified_status')
  const allOptions = dictStore.getDictItems('unqualified_status').map(item => ({
    value: Number(item.value),
    label: item.label
  }))

  // 加载产品已绑定的不良项
  try {
    const res = await getUnqualifiedItems({ finish_product_id: formData.id })
    const boundItems = res || []
    if (boundItems.length > 0) {
      // 如果有绑定的不良项，显示绑定的几项
      repairUnqualifiedOptions.value = boundItems.map(item => ({
        value: item.unqualified_value,
        label: item.unqualified_label
      }))
      repairFormData.unqualified_values = boundItems.map(item => item.unqualified_value)
    } else {
      // 如果没有绑定，显示全部
      repairUnqualifiedOptions.value = allOptions
    }
  } catch {
    // 如果加载失败，显示全部
    repairUnqualifiedOptions.value = allOptions
  }

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
  // 构建返修内容：将选中的不良项标签拼接到返修内容中
  const selectedLabels = repairUnqualifiedOptions.value
    .filter(opt => repairFormData.unqualified_values.includes(opt.value))
    .map(opt => opt.label)
  let finalRepairInfo = repairFormData.repair_info.trim()
  if (selectedLabels.length > 0) {
    const prefix = `不良项：${selectedLabels.join('、')}`
    finalRepairInfo = finalRepairInfo ? `${prefix}\n${finalRepairInfo}` : prefix
  }

  if (!finalRepairInfo) {
    ElMessage.warning('请填写返修内容或选择不良项')
    return
  }
  repairSubmitting.value = true
  saveProduct()
    .then(() => {
      return createRepair({
        product_id: formData.id,
        repair_info: finalRepairInfo
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

const loadBindableJoints = async () => {
  bindJointLoading.value = true
  try {
    const res = await getBindableJoints()
    bindJointData.value = res?.list || []
  } catch (e) {
    console.error('加载全量关节数据失败', e)
    bindJointData.value = []
  } finally {
    bindJointLoading.value = false
  }
}

const handleBindJoints = async (row) => {
  bindJointRow.value = row
  selectedJointIds.value = []
  bindJointVisible.value = true
  loadJointBomList()

  // 加载全部可绑定关节（专用不分页接口，避免 max_page_size=100 截断）
  await loadBindableJoints()
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
  addJointCreateTime.value = nowStr()
  addJointSnCodeTime.value = nowStr()
  addJointStockInTime.value = nowStr()
  addJointVisible.value = true
}

const handleAddJoint = async () => {
  if (!addJointBomId.value) {
    ElMessage.warning('请选择关节BOM')
    return
  }
  if (!addJointSnCode.value?.trim()) {
    ElMessage.warning('请输入SN码')
    return
  }
  addJointSubmitting.value = true
  try {
    await createFinishProduct({
      bom_id: addJointBomId.value,
      sn_code: addJointSnCode.value.trim(),
      description: '非计划添加',
      status: STATUS_PASS,
      inventory_stock: INVENTORY_IN,
      create_time: addJointCreateTime.value || null,
      sn_code_time: addJointSnCodeTime.value || null,
      stock_in_time: addJointStockInTime.value || null
    })
    ElMessage.success('关节创建成功')
    addJointVisible.value = false
    addJointBomId.value = null
    addJointSnCode.value = ''
    addJointCreateTime.value = ''
    addJointSnCodeTime.value = ''
    addJointStockInTime.value = ''
    await getList()
    // 刷新"关节绑定"的可绑定下拉，使新关节可直接被搜索到
    await loadBindableJoints()
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

// ==================== 快捷操作相关方法 ====================

// 打开快捷操作主对话框
const openQuickActionDialog = () => {
  quickActionVisible.value = true
}

// 选择快捷操作类型（测试合格/测试不良）
const handleQuickActionSelect = (type) => {
  quickActionType.value = type
  quickActionSnTitle.value = type === 'pass' ? '测试合格' : '测试不良'
  quickActionSnCode.value = ''
  // 测试合格支持批量：初始化SN码输入框列表
  quickActionSnList.value = ['']
  quickSnInputRefs.length = 0
  quickActionSnVisible.value = true
}

// 获取当前时间字符串（YYYY-MM-DD HH:mm:ss）
const nowStr = () => {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// 记录SN码输入框引用，便于新增后自动聚焦
const setQuickSnRef = (el, index) => {
  if (el) quickSnInputRefs[index] = el
}

// 新增下一个SN码输入框并聚焦
const addQuickSnInput = async () => {
  quickActionSnList.value.push('')
  await nextTick()
  quickSnInputRefs[quickActionSnList.value.length - 1]?.focus()
}

// ==================== 快捷操作：批量添加关节 ====================

// 打开批量添加关节对话框
const openBatchAddJointDialog = async () => {
  batchAddJointBomId.value = null
  batchAddJointSnList.value = ['']
  batchAddJointSnRefs.length = 0
  batchAddJointCreateTime.value = nowStr()
  batchAddJointSnCodeTime.value = nowStr()
  batchAddJointStockInTime.value = nowStr()
  batchAddJointVisible.value = true
  await loadJointBomList()
}

// 记录批量添加关节的SN码输入框引用
const setBatchAddJointSnRef = (el, index) => {
  if (el) batchAddJointSnRefs[index] = el
}

// 新增下一个SN码输入框并聚焦
const addBatchAddJointSnInput = async () => {
  batchAddJointSnList.value.push('')
  await nextTick()
  batchAddJointSnRefs[batchAddJointSnList.value.length - 1]?.focus()
}

// 批量创建关节：逐个调用创建接口，等同于多次使用「添加关节」，日志逐条保存
const handleBatchAddJoint = async () => {
  if (!batchAddJointBomId.value) {
    ElMessage.warning('请选择关节BOM')
    return
  }
  const snCodes = batchAddJointSnList.value
    .map((s) => s.trim())
    .filter(Boolean)
    .filter((s, i, arr) => arr.indexOf(s) === i)
  if (!snCodes.length) {
    ElMessage.warning('请输入SN码')
    return
  }
  batchAddJointSubmitting.value = true
  const results = []
  try {
    for (const sn of snCodes) {
      try {
        await createFinishProduct({
          bom_id: batchAddJointBomId.value,
          sn_code: sn,
          description: '非计划添加',
          status: STATUS_PASS,
          inventory_stock: INVENTORY_IN,
          create_time: batchAddJointCreateTime.value || null,
          sn_code_time: batchAddJointSnCodeTime.value || null,
          stock_in_time: batchAddJointStockInTime.value || null
        })
        results.push({ sn, ok: true })
      } catch (e) {
        results.push({ sn, ok: false, reason: '创建失败（SN码可能已存在）' })
      }
    }
    batchAddJointVisible.value = false
    quickActionVisible.value = false
    getList()
    await loadBindableJoints()
    showBatchResult(results)
  } finally {
    batchAddJointSubmitting.value = false
  }
}

// 按SN码查找成品，找不到返回 null
const findProductBySn = async (snCode) => {
  const res = await getFinishProductList({ sn_code: snCode, pageNum: 1, pageSize: 1 })
  return res?.list?.[0] || null
}

// 复用 handleEdit 填充 formData，并覆盖为「测试合格入库」字段（保存由调用方执行）
const fillQuickPassForm = (product) => {
  handleEdit(product)
  dialogVisible.value = false
  const now = nowStr()
  formData.inventory_stock = INVENTORY_IN
  formData.status = STATUS_PASS
  formData.stock_in_time = now
  formData.test_time = now
  formData.description = '扫码入库'
}

// 复用 handleEdit 填充 formData，并覆盖为「测试不良」字段（保存由调用方执行）
const fillQuickFailForm = (product) => {
  handleEdit(product)
  dialogVisible.value = false
  const now = nowStr()
  formData.inventory_stock = 0
  formData.status = 3
  formData.test_time = now
  formData.description = '扫码不良'
}

// SN码确认：测试合格支持批量，测试不良保持单个SN流程
const handleQuickActionSnConfirm = async () => {
  // 测试不良：保持原有单个SN流程
  if (quickActionType.value !== 'pass') {
    const snCode = quickActionSnCode.value?.trim()
    if (!snCode) {
      ElMessage.warning('请输入SN码')
      return
    }
    quickActionSnSubmitting.value = true
    try {
      const product = await findProductBySn(snCode)
      if (!product) {
        ElMessage.error(`未找到SN码为「${snCode}」的成品`)
        return
      }
      await executeQuickActionFail(product)
      quickActionSnVisible.value = false
      quickActionVisible.value = false
    } catch (e) {
      console.error('快捷操作失败', e)
    } finally {
      quickActionSnSubmitting.value = false
    }
    return
  }

  // 测试合格：收集所有输入框中的SN码（去空、去重）
  const snCodes = quickActionSnList.value
    .map((s) => s.trim())
    .filter(Boolean)
    .filter((s, i, arr) => arr.indexOf(s) === i)
  if (!snCodes.length) {
    ElMessage.warning('请输入SN码')
    return
  }
  quickActionSnSubmitting.value = true
  try {
    // 单个SN：保持原流程
    if (snCodes.length === 1) {
      const product = await findProductBySn(snCodes[0])
      if (!product) {
        ElMessage.error(`未找到SN码为「${snCodes[0]}」的成品`)
        return
      }
      await executeQuickActionPass(product)
      quickActionSnVisible.value = false
      quickActionVisible.value = false
      return
    }
    // 批量：逐个查找并保存，最后汇总结果
    const results = []
    for (const sn of snCodes) {
      try {
        const product = await findProductBySn(sn)
        if (!product) {
          results.push({ sn, ok: false, reason: '未找到' })
          continue
        }
        fillQuickPassForm(product)
        await saveProduct()
        results.push({ sn, ok: true })
      } catch {
        results.push({ sn, ok: false, reason: '保存失败' })
      }
    }
    submitting.value = false
    quickActionSnVisible.value = false
    quickActionVisible.value = false
    getList()
    checkJointConsistency()
    showBatchResult(results)
  } finally {
    quickActionSnSubmitting.value = false
  }
}

// 转义HTML，防止SN码中的特殊字符破坏提示内容
const escapeHtml = (str) =>
  String(str).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ))

// 展示批量操作结果汇总
const showBatchResult = (results) => {
  const okCount = results.filter((r) => r.ok).length
  const failList = results.filter((r) => !r.ok)
  if (!failList.length) {
    ElMessage.success(`批量操作完成：成功 ${okCount} 个`)
    return
  }
  const lines = failList.map((f) => `${escapeHtml(f.sn)}（${f.reason}）`).join('<br/>')
  ElMessageBox.alert(
    `成功 ${okCount} 个，失败 ${failList.length} 个：<br/>${lines}`,
    '批量操作结果',
    { type: 'warning', dangerouslyUseHTMLString: true, confirmButtonText: '知道了' }
  )
}

// 执行测试合格快捷操作（复用 handleEdit 填充 formData，复用 doSaveProduct 保存）
const executeQuickActionPass = (product) => {
  fillQuickPassForm(product)
  // 复用现有的 doSaveProduct 保存
  return doSaveProduct()
}

// 执行测试不良快捷操作（复用 handleEdit 填充 formData，复用不合格项选择对话框）
const executeQuickActionFail = async (product) => {
  fillQuickFailForm(product)
  unqualifiedGenerateRepair.value = false
  unqualifiedRepairInfo.value = ''
  // 加载已有不合格项并弹出选择对话框（复用现有的 handleUnqualifiedSelectConfirm 流程）
  try {
    const items = await getUnqualifiedItems({ finish_product_id: formData.id })
    selectedUnqualifiedValues.value = (items || []).map(item => item.unqualified_value)
  } catch {
    selectedUnqualifiedValues.value = []
  }
  unqualifiedSelectVisible.value = true
}

// ==================== 批量绑定SN码相关方法 ====================

// 记录批量绑定弹窗中每行SN码输入框的引用
const setBatchSnRef = (el, index) => {
  if (el) batchSnInputRefs[index] = el
}

// 打开批量绑定SN码弹窗：使用外层当前分页数据，过滤 sn_code 为空的行
const openBatchBindSnDialog = () => {
  quickActionVisible.value = false
  batchBindSnVisible.value = true
  batchSnInputRefs.length = 0
  // 直接使用外层当前分页的数据（已受搜索条件筛选），从中过滤 sn_code 为空的行
  const emptySnList = (filteredTableData.value || []).filter(row => !row.sn_code)
  batchBindData.value = emptySnList
  // 记录原始快照（打开时均为空字符串）
  const snapshot = {}
  emptySnList.forEach(row => { snapshot[row.id] = '' })
  batchBindOriginalSnapshot.value = snapshot
  if (emptySnList.length === 0) {
    ElMessage.info('当前分页中没有待填写SN码的数据')
  }
  // 数据加载后自动聚焦第一行
  nextTick(() => {
    batchSnInputRefs[0]?.focus?.()
  })
}

// 回车键跳到下一行的SN码输入框；最后一行时停留
const handleBatchSnEnter = (index) => {
  const next = index + 1
  if (next < batchBindData.value.length) {
    batchSnInputRefs[next]?.focus?.()
  }
}

// 判断该行SN码是否与其他行重复（用于高亮提示）
const isSnDuplicate = (index) => {
  const current = (batchBindData.value[index]?.sn_code || '').trim()
  if (!current) return false
  return batchBindData.value.some((row, i) => i !== index && (row.sn_code || '').trim() === current)
}

// 保存：将填入的SN码批量提交到后端
const handleBatchBindSave = async () => {
  // 收集有填入SN码且与原始值不同的行
  const changedRows = batchBindData.value.filter(row => {
    const sn = (row.sn_code || '').trim()
    return sn && sn !== (batchBindOriginalSnapshot.value[row.id] || '')
  })
  if (changedRows.length === 0) {
    ElMessage.warning('没有需要保存的SN码')
    return
  }
  // 重复校验：弹窗内行间重复
  const snMap = {}
  for (const row of changedRows) {
    const sn = row.sn_code.trim()
    if (snMap[sn]) {
      ElMessage.warning(`SN码「${sn}」在表格中重复，请检查后再保存`)
      return
    }
    snMap[sn] = true
  }
  batchBindSaving.value = true
  try {
    const results = await Promise.allSettled(
      changedRows.map(row =>
        updateFinishProduct({ id: row.id, sn_code: row.sn_code.trim() })
      )
    )
    const failed = results.filter(r => r.status === 'rejected')
    if (failed.length === 0) {
      ElMessage.success(`成功保存 ${changedRows.length} 条SN码`)
      batchBindSnVisible.value = false
      getList()
    } else {
      ElMessage.warning(`保存完成：成功 ${changedRows.length - failed.length} 条，失败 ${failed.length} 条`)
      // 刷新已保存的行，保留失败的行继续编辑
      getList()
    }
  } catch {
    ElMessage.error('保存失败')
  } finally {
    batchBindSaving.value = false
  }
}

onMounted(() => {
  loadColumnSettings()
  dictStore.loadDictItems('storage_status', true)
  dictStore.loadDictItems('unqualified_status', true)
  dictStore.loadDictItems('test_status', true)
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

.unqualified-tip {
  margin-bottom: 16px;
  padding: 10px 12px;
  background-color: var(--el-color-warning-light-9);
  border: 1px solid var(--el-color-warning-light-7);
  border-radius: 4px;
  color: var(--el-text-color-regular);
  font-size: 13px;
}

.generate-repair-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  color: var(--el-text-color-regular);
}

.unqualified-detail-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
  padding: 10px 12px;
  background-color: var(--el-fill-color-light);
  border-radius: 4px;
  font-size: 13px;
}

.quick-action-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  padding: 20px 0;
}

.quick-action-buttons .el-button {
  width: 100%;
  height: 64px;
  font-size: 16px;
  font-weight: 500;
  margin-left: 0;
}

.quick-sn-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.quick-sn-add {
  width: 100%;
}

.batch-bind-wrapper {
  min-height: 200px;
}

.batch-bind-toolbar {
  margin-bottom: 12px;
}

.batch-bind-count {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

/* 重复SN码输入框高亮提示 */
:deep(.sn-duplicate .el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--el-color-danger) inset;
}
</style>

