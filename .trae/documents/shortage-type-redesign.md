# 缺料类型重新设计方案

## Context

当前系统有两个模块涉及缺料/预警显示，但它们的逻辑和术语不统一：
- **生产计划模块** (`productionPlan/index.vue`): 已部分实现 3 种缺料类型(actual/plan/alert)，但物料需求对话框表格尚未展示类型
- **库存预警模块** (`stockAlert/index.vue`): 仍使用旧的"静态/动态"分类，与生产计划模块不一致

用户要求统一为 3 种缺料类型，用不同颜色和文字区分：

| 类型 | 代号 | 含义 | 颜色 | Element Tag类型 |
|------|------|------|------|-----------------|
| 库存缺料 | `actual` | 进行生产计划后实际库存不足 | 🔴 红色 | danger |
| 计划缺料 | `plan` | 按采购周期2倍计算的未来需求超过库存 | 🟠 橙色 | warning |
| 缺料警告 | `alert` | 当前库存 ≤ 预警数量(alert_quantity) | 🟡 黄色 | success |

优先级：actual(3) > plan(2) > alert(1)，一个产品只显示最严重的类型。

---

## 修改文件清单

### 后端 (2 个文件)

#### 1. `youlai-django/apps/product/production_plan/views.py`

**`_check_plan_shortage_with_stock`** (已完成，上一轮修改)
- 已支持 `cycle_demand_map` 参数和 `shortage_type` 返回
- 逻辑：actual(total_required > current_stock) > plan(cycle_demand > current_stock) > alert(stock ≤ alert_quantity)

**`calculate_production_requirements`** (需修改 ~L100-L176)
- 当前返回：`product_id, product_name, material_code, total_required, current_stock, stock_before, shortage`
- 新增返回字段：`shortage_type`, `alert_quantity`, `procurement_cycle`
- 计算逻辑：
  - 查询产品的 `alert_quantity` 和 `procurement_cycle`
  - 计算 `cycle_demand`(2倍采购周期内未来计划需求)
  - 按优先级判定 `shortage_type`：actual > plan > alert

**`list_production_plan`** (已完成，上一轮修改)
- 已支持 `cycle_demand_map` 和 `_check_plan_shortage_with_stock` 调用

**`save_production_plan`** (已完成，上一轮修改)
- 已支持 `cycle_demand_map` 计算

#### 2. `youlai-django/apps/product/products/views.py`

**`stock_alert_list`** (需重写 ~L556-L698)

重写为统一的 3 类型系统：

```python
# 对每个产品计算 3 种缺料
# 1. actual: 所有未来计划总需求 > 当前库存
actual_shortage = max(0, total_future_demand - current_stock)

# 2. plan: 2倍采购周期内需求 > 当前库存 (仅有采购周期时)
if cycle_days > 0:
    cycle_demand = sum(计划在 2*cycle_days 内的需求)
    plan_shortage = max(0, cycle_demand - current_stock)

# 3. alert: 当前库存 ≤ 预警数量
alert_shortage = max(0, alert_quantity - current_stock) if alert_quantity > 0 and stock <= alert_quantity

# 按优先级取最严重类型
# actual(3) > plan(2) > alert(1)
```

返回结构变更：
- 移除 `alert_type`(旧"静态/动态"字符串)
- 新增 `shortage_type`(actual/plan/alert)
- 新增 `actual_shortage`, `plan_shortage`, `alert_shortage` 明细
- 保留 `is_alert`, `suggested_order`, `total_demand` 等字段

### 前端 (2 个文件)

#### 3. `vue3-element-admin/src/views/product/productionPlan/index.vue`

**日历颜色** (已完成)：3 种颜色 `has-shortage-actual/plan/alert`

**缺料汇总表** (已完成)：新增"缺料类型"列，带颜色标签

**物料需求对话框表格** (~L99-L143，需修改)：
- 新增"缺料类型"列，显示 `shortage_type` 对应的彩色标签
- "缺口"列按类型着色(actual=红, plan=橙, alert=黄)
- "状态"列从"不足/充足"改为显示具体类型标签

#### 4. `vue3-element-admin/src/views/product/stockAlert/index.vue`

**完整重写**：

汇总卡片：展示 3 种类型的计数
```
监控零件数 | 库存缺料(红) | 计划缺料(橙) | 缺料警告(黄) | 正常
```

表格列：
| 列 | 说明 |
|----|------|
| 零件名称 | |
| 物料编码 | |
| 当前库存 | 按类型着色 |
| 预警库存 | alert_quantity |
| 采购周期 | |
| 预警期需求量 | 2倍周期内需求 |
| 总需求量 | 所有未来计划需求 |
| 缺料类型 | 彩色标签：库存缺料(红)/计划缺料(橙)/缺料警告(黄) |
| 缺口数量 | 按类型着色 |
| 建议补货量 | |

---

## 实现步骤

### Step 1: 修改 `calculate_production_requirements` 后端
- 在 `production_plan/views.py` 的 `calculate_production_requirements` 中
- 为每个 requirement 项添加 `shortage_type`, `alert_quantity`, `procurement_cycle` 字段
- 计算 cycle_demand 并判定类型

### Step 2: 重写 `stock_alert_list` 后端
- 在 `products/views.py` 中重写 `stock_alert_list`
- 使用统一的 3 类型逻辑
- 返回 `shortage_type` 字段

### Step 3: 修改生产计划前端 - 物料需求对话框表格
- 在 `productionPlan/index.vue` 的物料需求表格中
- 新增"缺料类型"列
- 修改"缺口"和"状态"列的着色逻辑

### Step 4: 重写库存预警前端
- 在 `stockAlert/index.vue` 中
- 更新汇总卡片为 3 类型计数
- 更新表格列和标签颜色
- 添加 `getShortageTypeLabel`/`getTagType` 等辅助函数

---

## 验证方式

1. **后端验证**：用 Django shell 调用 `stock_alert_list` 和 `list_production_plan`，检查返回的 `shortage_type` 字段
2. **前端验证**：
   - 打开生产计划页面，查看日历颜色(红/橙/黄)和缺料汇总表
   - 点击日期打开对话框，查看物料需求表的缺料类型列
   - 打开库存预警页面，查看 3 类型标签和颜色
3. **场景测试**：
   - 库存缺料：库存为0或极少，制定生产计划 → 显示红色"库存缺料"
   - 计划缺料：库存充足但2倍采购周期内需求超过库存 → 显示橙色"计划缺料"
   - 缺料警告：库存低于alert_quantity但能满足当前计划 → 显示黄色"缺料警告"
