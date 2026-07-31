# 修复计划

## 问题1：后端报错 - FinishProduct 没有 bom_type 属性

### 根因分析
`FinishProduct` 模型没有 `bom_type` 字段，`bom_type` 来自关联的 `BomList` 模型。之前添加的代码 `item.bom_type == 0` 无法工作。

### 修复方案
在 `update_finish_product` 函数中：
1. 先获取 BOM 记录，从中获取 `bom_type`
2. 使用获取到的 `bom_type` 进行验证判断

### 修改文件
- `c:\work\vue3sys\youlai-django\apps\product\finish_products\views.py`

### 具体步骤
1. 在获取 `item` 后，尝试获取关联的 BOM：
   ```python
   try:
       bom = BomList.objects.get(id=item.bom_id, is_del=0)
       bom_type = bom.type
   except BomList.DoesNotExist:
       bom_type = None
   ```

2. 将所有 `item.bom_type == 0` 替换为 `bom_type == 0`

## 问题2：库存看板合格率计算

### 需求
合格率 = 合格 / (合格 + 不良)，排除未测试和测试中。

### 修改文件
- `c:\work\vue3sys\vue3-element-admin\src\views\mainBoard\index.vue`

### 具体步骤
1. 修改 `newProductPassRateOptions`：
   - 移除"未统计"分类
   - 只显示"合格"和"不良"两个分类
   - `other = 0`

2. 修改 `repairProductPassRateOptions`：
   - 同上逻辑

## 风险评估
- 后端修改涉及核心保存逻辑，需测试确保正常流程不受影响
- 前端修改仅涉及展示，风险较低
