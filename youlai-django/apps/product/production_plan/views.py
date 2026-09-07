import json
from datetime import datetime

from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.product.boms.models import AssemblyRecipe, BomList
from apps.product.boms.utils import build_bom_requirements
from apps.product.products.models import Product
from apps.product.products.constants import product_type_label

from .models import ProductionPlan


# 共享辅助函数 build_bom_requirements 已移至 apps.product.boms.utils
# 此处保留别名以兼容本模块内既有调用
_build_bom_requirements = build_bom_requirements


@csrf_exempt
@require_http_methods(["POST"])
def calculate_production_requirements(request):
    """计算生产计划物料需求（考虑前面日期的累计库存消耗）"""
    try:
        body = json.loads(request.body or "{}")
        if isinstance(body, list):
            plan_items = body
            plan_date = None
        else:
            plan_items = body.get("items", body.get("boms", []))
            plan_date = body.get("date")
        
        if not plan_items:
            return JsonResponse({"code": "400", "msg": "请提供生产计划项目"})

        # 收集本次计划涉及的 BOM ID
        plan_bom_ids = set()
        for item in plan_items:
            bom_id = item.get("bom_id") or item.get("id")
            if bom_id:
                try:
                    plan_bom_ids.add(int(bom_id))
                except (TypeError, ValueError):
                    continue

        # 预解析日期范围内的历史计划（用于累计库存消耗）
        previous_plans = []
        target_date = None
        if plan_date:
            try:
                target_date = datetime.strptime(plan_date, "%Y-%m-%d").date()
                today = datetime.now().date()
                previous_plans = list(
                    ProductionPlan.objects.filter(
                        plan_date__lt=target_date,
                        plan_date__gte=today,
                    ).order_by("plan_date")
                )
            except ValueError:
                pass

        # 合并本次计划和历史计划涉及的 BOM，统一构建需求映射（支持物料编码回退）
        all_bom_ids = set(plan_bom_ids)
        all_bom_ids.update(p.bom_id for p in previous_plans if p.bom_id)
        bom_requirements = _build_bom_requirements(all_bom_ids)

        # 收集所有有效产品 ID，批量加载库存
        all_product_ids = set()
        for req_map in bom_requirements.values():
            all_product_ids.update(req_map.keys())

        stock_map = {}
        for product in Product.objects.filter(id__in=all_product_ids, is_del=0):
            stock_map[product.id] = product.quantity if product.quantity is not None else 0

        # 历史计划：模拟消耗原料 + 增加成品库存
        if previous_plans:
            prev_bom_ids = {p.bom_id for p in previous_plans if p.bom_id}
            prev_bom_map = {
                b.id: b
                for b in BomList.objects.filter(id__in=prev_bom_ids, is_del=0)
            }
            for plan in previous_plans:
                bom = prev_bom_map.get(plan.bom_id)
                if not bom:
                    continue

                # 成品入库（通过 BomList.finished_product_id 直接关联）
                fp_id = bom.finished_product_id
                if not fp_id and bom.material_code:
                    # 过渡兜底：未回填 finished_product_id 时按 material_code 匹配
                    fp = Product.objects.filter(
                        material_code=bom.material_code, is_del=0
                    ).first()
                    if fp:
                        fp_id = fp.id
                if fp_id:
                    stock_map[fp_id] = (
                        stock_map.get(fp_id, 0) + plan.quantity
                    )

                # 原料消耗（使用有效产品 ID）
                reqs = bom_requirements.get(bom.id, {})
                for eff_id, unit_qty in reqs.items():
                    consumed = unit_qty * plan.quantity
                    stock_map[eff_id] = max(0, stock_map.get(eff_id, 0) - consumed)

        # 构建本次计划的需求明细
        requirements = {}
        for item in plan_items:
            bom_id = item.get("bom_id") or item.get("id")
            quantity = item.get("quantity", 1)
            if not bom_id or quantity < 1:
                continue

            try:
                bom_id_int = int(bom_id)
            except (TypeError, ValueError):
                continue

            reqs = bom_requirements.get(bom_id_int, {})
            for eff_id, unit_qty in reqs.items():
                total_required = unit_qty * quantity
                if eff_id not in requirements:
                    product_obj = Product.objects.filter(id=eff_id, is_del=0).first()
                    requirements[eff_id] = {
                        "product_id": eff_id,
                        "product_name": product_obj.name if product_obj else "",
                        "material_code": product_obj.material_code or "" if product_obj else "",
                        "total_required": 0,
                        "stock_before": stock_map.get(eff_id, 0),
                        "alert_quantity": float(product_obj.alert_quantity or 0) if product_obj else 0,
                        "procurement_cycle": float(product_obj.procurement_cycle or 0) if product_obj else 0,
                    }
                requirements[eff_id]["total_required"] += total_required

        # bom_requirements 直接复用为周期需求缓存（已使用有效产品 ID）
        bom_requirements_cache = bom_requirements
        
        # 计算每个产品的周期需求 (2倍采购周期内的未来计划需求)
        from datetime import date, timedelta
        today_date = date.today()
        cycle_demand_map = {}
        if plan_date:
            try:
                target_date = datetime.strptime(plan_date, "%Y-%m-%d").date()
            except ValueError:
                target_date = today_date
        else:
            target_date = today_date
        
        # 收集所有未来计划 (从target_date开始)
        future_plans_all = ProductionPlan.objects.filter(plan_date__gte=target_date)
        for req_pid, req_data in requirements.items():
            cycle = req_data.get("procurement_cycle", 0)
            if cycle > 0:
                cycle_end = target_date + timedelta(days=cycle * 2)
                cycle_demand = 0
                for plan in future_plans_all:
                    if plan.plan_date > cycle_end:
                        continue
                    bom_req = bom_requirements_cache.get(plan.bom_id, {})
                    if req_pid in bom_req:
                        cycle_demand += bom_req[req_pid] * plan.quantity
                cycle_demand_map[req_pid] = cycle_demand
        
        result = []
        for req in requirements.values():
            total_required = float(req["total_required"])
            current_stock = float(req["stock_before"])
            alert_quantity = float(req.get("alert_quantity", 0))
            procurement_cycle = float(req.get("procurement_cycle", 0))
            
            # 计算各种短缺类型
            shortage = 0
            shortage_type = ""
            
            # 1. 库存缺料: 当前库存 < 本次需求
            actual_shortage = max(0, total_required - current_stock)
            
            # 2. 计划缺料: 2倍采购周期内需求 > 当前库存
            plan_shortage = 0
            if procurement_cycle > 0:
                cycle_demand = cycle_demand_map.get(req["product_id"], 0)
                if cycle_demand > 0 and current_stock <= cycle_demand:
                    plan_shortage = max(0, cycle_demand - current_stock)
            
            # 3. 缺料警告: 当前库存 <= 预警数量
            alert_shortage = 0
            if alert_quantity > 0 and current_stock <= alert_quantity:
                alert_shortage = max(0, alert_quantity - current_stock)
            
            # 按优先级: actual > plan > alert
            if actual_shortage > 0:
                shortage = actual_shortage
                shortage_type = "actual"
            elif plan_shortage > 0:
                shortage = plan_shortage
                shortage_type = "plan"
            elif alert_shortage > 0:
                shortage = alert_shortage
                shortage_type = "alert"
            
            result.append({
                "product_id": req["product_id"],
                "product_name": req["product_name"],
                "material_code": req["material_code"],
                "total_required": total_required,
                "current_stock": current_stock,
                "stock_before": current_stock,
                "shortage": float(shortage),
                "shortage_type": shortage_type,
                "alert_quantity": alert_quantity,
                "procurement_cycle": procurement_cycle,
            })
        
        return JsonResponse({
            "code": "00000",
            "msg": "成功",
            "data": result,
        })
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"计算失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["GET"])
def get_production_plan(request):
    """获取指定日期的生产计划"""
    try:
        plan_date = request.GET.get("date")
        if not plan_date:
            return JsonResponse({"code": "400", "msg": "请提供日期"})
        
        try:
            date_obj = datetime.strptime(plan_date, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"code": "400", "msg": "日期格式无效，须为 YYYY-MM-DD"})
        
        plans = ProductionPlan.objects.filter(plan_date=date_obj)
        
        bom_ids = {p.bom_id for p in plans}
        bom_map = {}
        if bom_ids:
            for bom in BomList.objects.filter(id__in=bom_ids, is_del=0):
                bom_map[bom.id] = bom
        
        result = {
            "date": plan_date,
            "boms": [],
        }
        
        for plan in plans:
            bom = bom_map.get(plan.bom_id)
            if bom:
                result["boms"].append({
                    "id": bom.id,
                    "bom_model": bom.bom_model,
                    "bom_name": bom.bom_name or "",
                    "type": bom.type,
                    "type_name": bom.get_type_display(),
                    "quantity": plan.quantity,
                })
        
        return JsonResponse({
            "code": "00000",
            "msg": "成功",
            "data": result,
        })
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"获取失败: {str(e)}"})


@csrf_exempt
@require_http_methods(["POST"])
def save_production_plan(request):
    """保存生产计划"""
    try:
        body = json.loads(request.body or "{}")
        plan_date = body.get("date")
        boms = body.get("boms", [])
        # 预留库存倍率 (默认1.5)
        try:
            multiplier = float(body.get("multiplier", 1.5))
        except (ValueError, TypeError):
            multiplier = 1.5

        if not plan_date:
            return JsonResponse({"code": "400", "msg": "请提供日期"})

        try:
            date_obj = datetime.strptime(plan_date, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"code": "400", "msg": "日期格式无效，须为 YYYY-MM-DD"})

        ProductionPlan.objects.filter(plan_date=date_obj).delete()

        saved_bom_ids = []
        for item in boms:
            bom_id = item.get("bom_id") or item.get("id")
            quantity = item.get("quantity", 1)

            if not bom_id:
                continue
            if quantity < 1:
                continue

            try:
                bom_obj = BomList.objects.get(id=int(bom_id), is_del=0)
            except BomList.DoesNotExist:
                continue

            ProductionPlan.objects.create(
                plan_date=date_obj,
                bom_id=bom_obj.id,
                quantity=quantity,
            )
            saved_bom_ids.append({
                "id": bom_obj.id,
                "quantity": quantity,
            })

        # 计算当日计划的缺料情况，让前端可即时反馈
        has_shortage = False
        shortage_details = []
        shortage_bom_names = []
        if saved_bom_ids:
            bom_ids = [item["id"] for item in saved_bom_ids]
            bom_map = {}
            for bom in BomList.objects.filter(id__in=bom_ids, is_del=0):
                bom_map[bom.id] = bom
            # 数据库实际库存已经扣除了过去生产的实际消耗
            stock_map = _build_stock_map_for_boms(saved_bom_ids)
            # db_stock_map 保存 DB 原始库存 (用于 plan 类型判定)
            db_stock_map = dict(stock_map)

            # 如果保存的是未来日期, 需要先消耗今天到该日期之间的已存在计划
            from datetime import date as date_cls
            today_cls = date_cls.today()
            if date_obj > today_cls:
                in_range_plans = ProductionPlan.objects.filter(
                    plan_date__gte=today_cls,
                    plan_date__lt=date_obj
                )
                # 合并区间内计划的 BOM，统一构建需求映射（支持物料编码回退）
                in_range_bom_ids = {p.bom_id for p in in_range_plans if p.bom_id}
                in_range_bom_ids.update(bom_ids)
                in_range_requirements = _build_bom_requirements(in_range_bom_ids)

                for pp in in_range_plans:
                    reqs = in_range_requirements.get(pp.bom_id, {})
                    for eff_id, unit_qty in reqs.items():
                        stock_map[eff_id] = max(
                            0.0,
                            float(stock_map.get(eff_id, 0)) - unit_qty * float(pp.quantity)
                        )

            # 构建 bom_requirements 映射（使用有效产品 ID）
            bom_requirements = _build_bom_requirements(bom_ids)

            # 计算所有未来计划的计划缺料数据
            future_plans = ProductionPlan.objects.filter(plan_date__gte=date_obj)
            plan_shortage_map = _compute_plan_shortage_data(
                future_plans, bom_requirements, db_stock_map, multiplier
            )

            has_shortage, shortage_details, shortage_bom_names = _check_plan_shortage_with_stock(
                saved_bom_ids, bom_map, stock_map, plan_shortage_map, db_stock_map
            )

        return JsonResponse({
            "code": "00000",
            "msg": "保存成功",
            "data": {
                "date": plan_date,
                "has_shortage": has_shortage,
                "shortage_details": shortage_details,
                "shortage_bom_names": shortage_bom_names,
            },
        })
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"保存失败: {str(e)}"})


def _build_stock_map_for_boms(bom_items):
    """根据 BOM 列表构建当前库存快照（使用有效产品 ID，支持物料编码回退）"""
    bom_ids = [item.get("id") for item in bom_items if item.get("id")]
    bom_requirements = _build_bom_requirements(bom_ids)

    product_ids = set()
    for req_map in bom_requirements.values():
        product_ids.update(req_map.keys())

    stock_map = {}
    if product_ids:
        for product in Product.objects.filter(id__in=product_ids, is_del=0):
            stock_map[product.id] = float(product.quantity or 0)
    return stock_map


@csrf_exempt
@require_http_methods(["GET"])
def list_production_plan(request):
    """获取生产计划列表（含累计库存消耗计算，只统计今天及以后的计划）"""
    try:
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        # 预留库存倍率 (默认1.5)
        try:
            multiplier = float(request.GET.get("multiplier", 1.5))
        except (ValueError, TypeError):
            multiplier = 1.5
        
        today = datetime.now().date()
        
        # 解析日期参数
        start = None
        end = None
        if start_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                pass
        if end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        # 加载所有计划（包括过去的计划用于显示已过期）
        # 注意: 数据库实际库存已经扣除了过去生产的实际消耗
        # 因此 stock_map 直接用 DB 库存值作为起点, 不需要再扣除过去的计划
        
        # 过去日期的计划 (用于显示已过期状态, 不参与库存消耗计算)
        if start:
            past_plans = list(ProductionPlan.objects.filter(plan_date__lt=start).order_by("plan_date"))
        else:
            past_plans = list(ProductionPlan.objects.filter(plan_date__lt=today).order_by("plan_date"))
        
        # 当前日期范围内的计划 (今天 + 未来)
        qs = ProductionPlan.objects.all()
        if start:
            qs = qs.filter(plan_date__gte=start)
        else:
            qs = qs.filter(plan_date__gte=today)
        if end:
            qs = qs.filter(plan_date__lte=end)
        
        # 保存查询集引用用于计划缺料计算
        plans_qs = qs.order_by("plan_date")
        plans = list(plans_qs)
        all_range_plans = past_plans + plans
        
        bom_ids = {p.bom_id for p in all_range_plans}
        bom_map = {}
        if bom_ids:
            for bom in BomList.objects.filter(id__in=bom_ids, is_del=0):
                bom_map[bom.id] = bom

        # 预先批量计算每个BOM的需求 {bom_id: {product_id: required_qty}}
        # (提前到此处，供后续 all_product_ids / _consume_plan_stock 复用，避免 N+1 查询)
        # 使用有效产品 ID（产品删除重建后通过 material_code 回退）
        bom_requirements = _build_bom_requirements(bom_ids)

        all_product_ids = set()
        for req_pid in bom_requirements.values():
            all_product_ids.update(req_pid.keys())

        stock_map = {}
        product_cycles = {}
        for product in Product.objects.filter(id__in=all_product_ids, is_del=0):
            stock_map[product.id] = float(product.quantity or 0)
            product_cycles[product.id] = float(product.procurement_cycle or 0)

        # 保存数据库实际库存 (用于短缺判定)
        db_stock_map = dict(stock_map)

        # 预先批量计算每个BOM对应的成品（通过 finished_product_id 关联，避免 N+1）
        bom_product_map = {}
        if bom_ids:
            # 主路径：直接从 BomList.finished_product_id 取
            for bid, bom in bom_map.items():
                if bom.finished_product_id:
                    bom_product_map[bid] = bom.finished_product_id
            # 过渡兜底：未回填 finished_product_id 的 BOM，按 material_code 批量匹配
            missing_code_boms = {
                bid: bom.material_code
                for bid, bom in bom_map.items()
                if not bom.finished_product_id and bom.material_code
            }
            if missing_code_boms:
                finished_products = Product.objects.filter(
                    material_code__in=list(missing_code_boms.values()), is_del=0
                )
                code_to_pid = {p.material_code: p.id for p in finished_products}
                for bid, mcode in missing_code_boms.items():
                    if mcode in code_to_pid:
                        bom_product_map[bid] = code_to_pid[mcode]

        # 预计算所有未来计划的计划缺料数据
        future_plans_for_shortage = ProductionPlan.objects.filter(
            plan_date__gte=today
        ).order_by("plan_date")
        plan_shortage_map = _compute_plan_shortage_data(
            future_plans_for_shortage, bom_requirements, db_stock_map, multiplier
        )
        
        result = []
        current_date = None
        date_plan = None
        
        def _consume_plan_stock(plan_bom_id, plan_quantity):
            """消耗单个计划的原料库存并增加成品（使用预计算的 bom_requirements，避免 N+1）"""
            if not plan_bom_id or plan_quantity < 1:
                return
            reqs = bom_requirements.get(plan_bom_id)
            if reqs:
                for product_id, unit_qty in reqs.items():
                    stock_map[product_id] = max(0.0, float(stock_map.get(product_id, 0)) - unit_qty * float(plan_quantity))
            # 添加成品到库存
            finished_product_id = bom_product_map.get(plan_bom_id)
            if finished_product_id:
                stock_map[finished_product_id] = float(stock_map.get(finished_product_id, 0)) + float(plan_quantity)
        
        # 注意: 数据库实际库存已经扣除了过去生产的实际消耗
        # 因此 stock_map 直接从 DB 库存作为起点, 不再扣除 past_plans
        # past_plans 仅用于显示"已过期"状态
        
        # 处理当前日期范围内的计划
        for plan in plans:
            if plan.plan_date != current_date:
                if date_plan:
                    if current_date >= today:
                        # 检查当日短缺（使用实际DB库存和计划缺料数据）
                        date_plan["has_shortage"], date_plan["shortage_details"], date_plan["shortage_bom_names"] = _check_plan_shortage_with_stock(
                            date_plan["boms"], bom_map, stock_map, plan_shortage_map, db_stock_map
                        )
                        # 消耗所有原料并增加成品（无论是否短缺），更新 stock_map 供后续日期使用
                        for bom_item in date_plan["boms"]:
                            _consume_plan_stock(bom_item["id"], bom_item["quantity"])
                    else:
                        # 过期的计划：标记为已过期, 只消耗库存不检查短缺
                        date_plan["is_expired"] = True
                        for bom_item in date_plan["boms"]:
                            _consume_plan_stock(bom_item["id"], bom_item["quantity"])
                        date_plan["has_shortage"] = False
                        date_plan["shortage_details"] = []
                        date_plan["shortage_bom_names"] = []
                    result.append(date_plan)
                current_date = plan.plan_date
                date_plan = {
                    "date": current_date.isoformat(),
                    "boms": [],
                    "has_shortage": False,
                    "shortage_details": [],
                    "shortage_bom_names": [],
                    "is_expired": False,
                }
            
            bom = bom_map.get(plan.bom_id)
            if bom:
                date_plan["boms"].append({
                    "id": bom.id,
                    "bom_model": bom.bom_model,
                    "bom_name": bom.bom_name or "",
                    "type": bom.type,
                    "type_name": bom.get_type_display(),
                    "quantity": plan.quantity,
                })
        
        if date_plan:
            if current_date >= today:
                date_plan["has_shortage"], date_plan["shortage_details"], date_plan["shortage_bom_names"] = _check_plan_shortage_with_stock(
                    date_plan["boms"], bom_map, stock_map, plan_shortage_map, db_stock_map
                )
                for bom_item in date_plan["boms"]:
                    _consume_plan_stock(bom_item["id"], bom_item["quantity"])
            else:
                # 过期的计划
                date_plan["is_expired"] = True
                for bom_item in date_plan["boms"]:
                    _consume_plan_stock(bom_item["id"], bom_item["quantity"])
                date_plan["has_shortage"] = False
                date_plan["shortage_details"] = []
                date_plan["shortage_bom_names"] = []
            result.append(date_plan)

        # 添加过期的计划到结果中（只显示最近30天的过期计划）
        from datetime import timedelta
        expired_cutoff = today - timedelta(days=30)
        expired_dates = {}
        for past_plan in past_plans:
            if past_plan.plan_date >= expired_cutoff:
                date_str = past_plan.plan_date.isoformat()
                if date_str not in expired_dates:
                    expired_dates[date_str] = {
                        "date": date_str,
                        "boms": [],
                        "has_shortage": False,
                        "shortage_details": [],
                        "shortage_bom_names": [],
                        "is_expired": True,
                    }
                bom = bom_map.get(past_plan.bom_id)
                if bom:
                    expired_dates[date_str]["boms"].append({
                        "id": bom.id,
                        "bom_model": bom.bom_model,
                        "bom_name": bom.bom_name or "",
                        "type": bom.type,
                        "type_name": bom.get_type_display(),
                        "quantity": past_plan.quantity,
                    })
        
        # 合并过期计划到结果
        result_dates = {r["date"] for r in result}
        for date_str, expired_plan in expired_dates.items():
            if date_str not in result_dates:
                result.append(expired_plan)
        
        # 按日期排序
        result.sort(key=lambda x: x["date"])
        
        return JsonResponse({
            "code": "00000",
            "msg": "成功",
            "data": result,
        })
    except Exception as e:
        return JsonResponse({"code": "500", "msg": f"获取失败: {str(e)}"})


def _compute_plan_shortage_data(future_plans, bom_requirements, db_stock_map, multiplier=1.5):
    """预计算每个产品的计划缺料数据
    
    计划缺料逻辑:
    - 计算所有未来计划的总需求和涉及的天数
    - 平均日需求 = 总需求 / 计划天数
    - 所需库存 = 平均日需求 * 采购周期 * 预留库存倍率
    - 若当前库存 < 所需库存, 则提示计划缺料
    
    参数:
        multiplier: 预留库存倍率 (默认1.5, 即采购周期*1.5)
    """
    from datetime import timedelta
    
    # 计算每个产品的总需求和涉及的计划天数
    product_total_demand = {}
    product_plan_days = {}
    
    for plan in future_plans:
        bom_req = bom_requirements.get(plan.bom_id, {})
        for pid, unit_qty in bom_req.items():
            demand = float(unit_qty) * float(plan.quantity)
            product_total_demand[pid] = float(product_total_demand.get(pid, 0)) + demand
            # 记录该产品涉及的计划日期
            if pid not in product_plan_days:
                product_plan_days[pid] = set()
            product_plan_days[pid].add(plan.plan_date)
    
    # 获取产品的采购周期
    product_ids = set(product_total_demand.keys())
    product_cycles = {}
    if product_ids:
        for p in Product.objects.filter(id__in=product_ids, is_del=0):
            product_cycles[p.id] = float(p.procurement_cycle or 0)
    
    # 计算每个产品的所需库存
    plan_shortage_map = {}
    for pid, total_demand in product_total_demand.items():
        cycle = product_cycles.get(pid, 0)
        if cycle <= 0:
            continue
        
        distinct_days = len(product_plan_days.get(pid, set()))
        if distinct_days == 0:
            continue
        
        avg_daily = float(total_demand) / float(distinct_days)
        required_stock = float(avg_daily) * float(cycle) * float(multiplier)
        
        plan_shortage_map[pid] = {
            "total_demand": float(total_demand),
            "distinct_days": distinct_days,
            "avg_daily": float(avg_daily),
            "required_stock": float(required_stock),
            "multiplier": float(multiplier),
        }
    
    return plan_shortage_map


def _check_plan_shortage_with_stock(boms, bom_map, stock_map, plan_shortage_map=None, db_stock_map=None):
    """检查计划是否存在库存短缺
    
    短缺类型 (shortage_type):
    - actual: 库存缺料 (所有未来计划总需求 > 当前库存) - 红色
    - plan: 计划缺料 (当前库存 < 平均日需求 * 采购周期 * 2) - 橙色
    - alert: 缺料警告 (当前库存 <= 预警数量) - 黄色
    
    参数:
        boms: 计划中的BOM列表
        bom_map: BOM映射
        stock_map: 当前库存映射 (已消耗过去计划, 用于显示)
        plan_shortage_map: 每个产品的计划缺料数据 {product_id: {required_stock, avg_daily, total_demand, distinct_days}}
        db_stock_map: 数据库实际库存映射 (用于短缺判定)
    
    优先级: actual(3) > plan(2) > alert(1)
    """
    # 如果没有传 db_stock_map, 则使用 stock_map (兼容旧调用)
    if db_stock_map is None:
        db_stock_map = stock_map

    shortage_details = []
    has_shortage = False
    shortage_bom_names = set()

    # 收集本次计划涉及的所有 BOM 的 recipe，构建有效产品 ID 映射（支持物料编码回退）
    bom_ids_in_plan = [bom_item.get("id") for bom_item in boms if bom_item.get("id")]
    bom_requirements = _build_bom_requirements(bom_ids_in_plan)

    # 有效产品 ID 集合
    plan_product_ids = set()
    for req_map in bom_requirements.values():
        plan_product_ids.update(req_map.keys())

    # 批量获取产品信息（按有效 ID）
    products_info = {}
    for product in Product.objects.filter(id__in=plan_product_ids, is_del=0):
        products_info[product.id] = product

    for bom_item in boms:
        bom_id = bom_item.get("id")
        quantity = bom_item.get("quantity", 1)

        if not bom_id or quantity < 1:
            continue

        bom = bom_map.get(bom_id)
        if not bom:
            continue

        bom_name = bom.bom_model or bom.bom_name or ""
        bom_has_shortage = False

        # 使用预计算的 bom_requirements（已按有效产品 ID 聚合）
        reqs = bom_requirements.get(bom_id, {})
        for eff_id, unit_qty in reqs.items():
            total_required = float(unit_qty) * float(quantity)
            # 当天开始前的库存 (消耗过去计划后的模拟库存)
            stock_before_plan = float(stock_map.get(eff_id, 0))
            # 数据库实际库存 (用于 plan 类型的全局库存水平判定)
            actual_stock = float(db_stock_map.get(eff_id, 0))

            product = products_info.get(eff_id)
            product_name = product.name if product else "未知"
            material_code = product.material_code if product else ""
            alert_quantity = float(product.alert_quantity or 0) if product else 0
            procurement_cycle = float(product.procurement_cycle or 0) if product else 0

            # 判定短缺类型
            shortage = 0
            shortage_type = ""
            actual_shortage = 0
            plan_shortage = 0
            alert_shortage = 0

            # 1. 库存缺料: 计划后库存 < 0 (最严重)
            stock_after_plan = stock_before_plan - total_required
            if stock_after_plan < 0:
                actual_shortage = abs(stock_after_plan)

            # 2. 计划缺料: 当前库存 < 平均日需求 * 采购周期 * 2 (中等)
            if plan_shortage_map and eff_id in plan_shortage_map:
                ps_data = plan_shortage_map[eff_id]
                required_stock = float(ps_data["required_stock"])
                if required_stock > 0 and actual_stock < required_stock:
                    plan_shortage = required_stock - actual_stock

            # 3. 缺料警告: 计划后库存 <= 预警数量 (最轻)
            if alert_quantity > 0 and stock_after_plan <= alert_quantity:
                alert_shortage = max(0.0, alert_quantity - stock_after_plan)

            # 按严重程度排序: actual > plan > alert
            if actual_shortage > 0:
                shortage = actual_shortage
                shortage_type = "actual"
                bom_has_shortage = True
                has_shortage = True
            elif plan_shortage > 0:
                shortage = plan_shortage
                shortage_type = "plan"
                bom_has_shortage = True
                has_shortage = True
            elif alert_shortage > 0:
                shortage = alert_shortage
                shortage_type = "alert"
                bom_has_shortage = True
                has_shortage = True

            shortage_details.append({
                "product_id": eff_id,
                "product_name": product_name,
                "material_code": material_code,
                "required": total_required,
                "stock_before": stock_before_plan,
                "stock_after": max(0.0, stock_after_plan),
                "db_stock": actual_stock,
                "shortage": shortage,
                "shortage_type": shortage_type,
                "alert_quantity": alert_quantity,
                "procurement_cycle": procurement_cycle,
                "required_stock": plan_shortage_map.get(eff_id, {}).get("required_stock", 0) if plan_shortage_map else 0,
                "avg_daily": plan_shortage_map.get(eff_id, {}).get("avg_daily", 0) if plan_shortage_map else 0,
                "distinct_days": plan_shortage_map.get(eff_id, {}).get("distinct_days", 0) if plan_shortage_map else 0,
            })

        if bom_has_shortage and bom_name:
            shortage_bom_names.add(bom_name)

    return has_shortage, shortage_details, list(shortage_bom_names)
