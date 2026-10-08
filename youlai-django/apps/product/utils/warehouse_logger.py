"""
库存操作日志工具模块

提供统一的日志记录功能，确保：
1. 1次操作即使造成多条数据库修改，也只生成1条日志记录
2. 日志中记录对数据的所有操作详情（JSON格式）
3. 记录操作来源模块，便于溯源
4. 记录操作人（当前登录用户的昵称）
"""

import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def get_operator_info(request) -> Dict[str, Any]:
    """
    从请求中获取当前操作人的信息
    
    解析优先级（与 operation_logs.get_request_operator 保持一致，避免两套逻辑漂移）：
      1. 纯 JWT fallback（不依赖 Redis，对 function-based view 最稳）
      2. request.user（DRF @api_view / Django AuthenticationMiddleware 场景）
      3. JWTAuthentication.get_validated_token 兜底（旧链路，保留兼容）
    """
    result = {
        'operator_id': None,
        'operator_name': '系统',
    }
    
    if request is None:
        return result

    # --- 0. 优先复用 JwtRequiredMiddleware 已验签的 payload（写操作必经鉴权，必为有效 token） ---
    payload = (getattr(request, "META", None) or {}).get("_JWT_PAYLOAD")
    if payload and payload.get("user_id"):
        display_name = (payload.get("nickname") or payload.get("user_name") or "").strip()
        if display_name:
            return {
                'operator_id': payload.get("user_id"),
                'operator_name': display_name,
            }
        # 旧 token payload 无姓名声明 → 落到下方查库路径，按 user_id 查昵称

    # --- 1. 纯 JWT fallback（复用 operation_logs 已验证过的稳定路径） ---
    try:
        from apps.system.operation_logs.request_user import _extract_bearer_token, _jwt_fallback_resolve
        operator = _jwt_fallback_resolve(_extract_bearer_token(request))
        if operator:
            uid, uname = operator
            result['operator_id'] = uid
            result['operator_name'] = uname
            return result
    except Exception:
        pass
    
    # --- 2. request.user ---
    if hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False):
        user = request.user
        result['operator_id'] = user.id
        nickname = getattr(user, 'nickname', None)
        if nickname:
            result['operator_name'] = nickname
        elif hasattr(user, 'username'):
            result['operator_name'] = user.username
        return result
    
    # --- 3. 兜底：手动 JWT 解析（不依赖 Redis 的纯签名校验） ---
    jwt_decode_error = None
    try:
        from rest_framework_simplejwt.backends import TokenBackend
        from django.conf import settings

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            jwt_settings = getattr(settings, "SIMPLE_JWT", {})
            backend = TokenBackend(
                algorithm=jwt_settings.get("ALGORITHM", "HS256"),
                signing_key=jwt_settings.get("SIGNING_KEY", settings.SECRET_KEY),
            )
            token_data = backend.decode(token, verify=True)
            user_id = token_data.get('user_id')
            if user_id is not None:
                resolved_name = _resolve_user_display(user_id)
                result['operator_id'] = user_id
                result['operator_name'] = resolved_name or '系统'
    except Exception as exc:
        jwt_decode_error = f"{type(exc).__name__}: {exc}"

    # --- 诊断日志：所有解析路径都失败时记录原因，用于定位"系统"操作人问题 ---
    if result['operator_id'] is None:
        try:
            from django.conf import settings
            meta = getattr(request, 'META', {}) or {}
            auth_header = meta.get('HTTP_AUTHORIZATION', '') or ''
            has_bearer = auth_header.startswith('Bearer ')
            diag = {
                'path': getattr(request, 'path', ''),
                'method': getattr(request, 'method', ''),
                'has_bearer': has_bearer,
                'user_attr': str(getattr(request, 'user', None)),
                'jwt_error': jwt_decode_error,
            }
            if has_bearer:
                try:
                    # 不验签仅看 payload 的 exp，区分"过期"与"无 token"
                    import jwt as _pyjwt
                    unverified = _pyjwt.decode(
                        auth_header[7:],
                        options={'verify_signature': False, 'verify_exp': False},
                    )
                    import datetime
                    exp = unverified.get('exp')
                    diag['token_exp'] = datetime.datetime.fromtimestamp(exp).isoformat() if exp else None
                    diag['now'] = datetime.datetime.now().isoformat()
                    diag['token_user_id'] = unverified.get('user_id')
                    diag['has_name_claims'] = bool(unverified.get('user_name') or unverified.get('nickname'))
                except Exception as exc2:
                    diag['inspect_error'] = f"{type(exc2).__name__}: {exc2}"
            logger.warning("[库存日志-操作人解析失败] %s", diag)
        except Exception:
            pass

    return result


def _resolve_user_display(user_id) -> str:
    """根据 user_id 查询用户昵称或用户名，查不到时返回空串。"""
    if not user_id:
        return ''
    try:
        from apps.system.users.models import User
        user = User.objects.filter(id=user_id).only('username', 'nickname').first()
        if user is None:
            return ''
        return (user.nickname or '').strip() or (user.username or '').strip()
    except Exception:
        return ''


def create_warehouse_log(
    request,
    storage_status: int,
    name: str = '',
    sn_code: str = '',
    material_code: str = '',
    count: int = 1,
    description: str = '',
    user_description: str = '',
    module: str = '',
    action_type: str = '',
    operation_detail: Optional[List[Dict[str, Any]]] = None,
    **kwargs
) -> Optional['WarehouseLog']:
    """
    创建库存操作日志
    
    Args:
        request: Django HTTP 请求对象（用于获取操作人信息）
        storage_status: 操作类型（1-入库, 2-出库外销, 3-出库研发, 4-绑定, 5-解除绑定, 6-回退, 7-手动调整）
        name: 产品/物料名称
        sn_code: SN码
        material_code: 物料编码
        count: 数量
        description: 系统自动生成的操作描述
        user_description: 用户手动输入的补充描述
        module: 操作来源模块（如 finish_product, inventory 等）
        action_type: 具体操作类型（如 bind_joint, unbind_joint 等）
        operation_detail: 操作详情列表，每个元素是一个字典，描述对数据的具体操作
        **kwargs: 其他可选参数
    
    Returns:
        WarehouseLog 实例或 None
    """
    try:
        from apps.product.products.models import WarehouseLog
        
        # 获取操作人信息
        operator_info = get_operator_info(request)
        
        # 将操作详情转换为 JSON
        if operation_detail is not None:
            if isinstance(operation_detail, list):
                operation_detail_json = operation_detail
            else:
                operation_detail_json = [operation_detail]
        else:
            operation_detail_json = []
        
        log = WarehouseLog.objects.create(
            name=name,
            sn_code=sn_code,
            material_code=material_code,
            storage_status=storage_status,
            count=count,
            description=description,
            user_description=user_description,
            operator_id=operator_info['operator_id'],
            operator_name=operator_info['operator_name'],
            module=module,
            action_type=action_type,
            operation_detail=operation_detail_json,
        )
        
        logger.info(
            "[库存日志创建] id=%s, storage_status=%s, operator=%s, module=%s, action_type=%s",
            log.id, storage_status, operator_info['operator_name'], module, action_type
        )
        
        return log
        
    except Exception as e:
        logger.error(f"创建库存操作日志失败: {str(e)}", exc_info=True)
        return None


def log_inventory_operation(
    request,
    operation_type: str,
    products: List[Dict[str, Any]],
    module: str = '',
    description: str = '',
    extra_details: Optional[Dict[str, Any]] = None
) -> Optional['WarehouseLog']:
    """
    记录一次库存操作，支持多个产品的批量操作
    
    这个函数确保：
    - 1次操作即使涉及多个产品的修改，也只生成1条日志
    - 每个产品的操作详情都会被完整记录
    
    Args:
        request: Django HTTP 请求对象
        operation_type: 操作类型标识（如 'stock_in', 'stock_out', 'bind_joint', 'unbind_joint'）
        products: 操作的产品列表，每个产品是一个字典，包含：
                  - name: 产品名称
                  - sn_code: SN码
                  - material_code: 物料编码
                  - quantity_change: 数量变化（正数增加，负数减少）
                  - before_stock: 操作前库存
                  - after_stock: 操作后库存
                  - details: 额外的产品详情
        module: 操作来源模块
        description: 操作描述
        extra_details: 额外的操作详情
    
    Returns:
        WarehouseLog 实例或 None
    """
    try:
        from apps.product.products.models import WarehouseLog
        
        # 确定 storage_status
        storage_status_map = {
            'stock_in': WarehouseLog.STORAGE_IN,
            'stock_out_sale': WarehouseLog.STORAGE_OUT_SALE,
            'stock_out_randd': WarehouseLog.STORAGE_OUT_RANDD,
            'bind_joint': WarehouseLog.BIND,
            'unbind_joint': WarehouseLog.UNBIND,
            'rollback': WarehouseLog.ROLLBACK,
            'manual_adjust': WarehouseLog.MANUAL_ADJUST,
        }
        
        storage_status = storage_status_map.get(operation_type, WarehouseLog.MANUAL_ADJUST)
        
        # 获取操作人信息
        operator_info = get_operator_info(request)
        
        # 构建操作详情
        operation_detail = []
        for product in products:
            detail = {
                'product_name': product.get('name', ''),
                'sn_code': product.get('sn_code', ''),
                'material_code': product.get('material_code', ''),
                'quantity_change': product.get('quantity_change', 0),
                'before_stock': product.get('before_stock'),
                'after_stock': product.get('after_stock'),
            }
            if product.get('details'):
                detail['product_details'] = product['details']
            operation_detail.append(detail)
        
        if extra_details:
            operation_detail.append({
                'extra_info': extra_details
            })
        
        # 计算总数量变化
        total_count = sum(p.get('quantity_change', 1) for p in products)
        
        # 主名称取第一个产品
        main_name = products[0].get('name', '') if products else ''
        main_sn_code = products[0].get('sn_code', '') if products else ''
        main_material_code = products[0].get('material_code', '') if products else ''
        
        log = WarehouseLog.objects.create(
            name=main_name,
            sn_code=main_sn_code,
            material_code=main_material_code,
            storage_status=storage_status,
            count=abs(total_count) if total_count != 0 else 1,
            description=description or f"{operation_type}: 操作 {len(products)} 个产品",
            operator_id=operator_info['operator_id'],
            operator_name=operator_info['operator_name'],
            module=module,
            action_type=operation_type,
            operation_detail=operation_detail,
        )
        
        logger.info(
            "[库存操作日志] operation_type=%s, products_count=%d, operator=%s, module=%s",
            operation_type, len(products), operator_info['operator_name'], module
        )
        
        return log
        
    except Exception as e:
        logger.error(f"记录库存操作日志失败: {str(e)}", exc_info=True)
        return None


def create_single_product_log(
    request,
    storage_status: int,
    product: Dict[str, Any],
    module: str = '',
    description: str = '',
    operation_detail: Optional[Dict[str, Any]] = None
) -> Optional['WarehouseLog']:
    """
    为单个产品创建日志
    
    Args:
        request: Django HTTP 请求对象
        storage_status: 操作类型
        product: 产品信息字典
        module: 操作来源模块
        description: 操作描述
        operation_detail: 操作详情
    
    Returns:
        WarehouseLog 实例或 None
    """
    try:
        from apps.product.products.models import WarehouseLog
        
        operator_info = get_operator_info(request)
        
        if operation_detail is None:
            operation_detail = {
                'product_name': product.get('name', ''),
                'sn_code': product.get('sn_code', ''),
                'material_code': product.get('material_code', ''),
                'quantity_change': product.get('quantity_change', 1),
                'before_stock': product.get('before_stock'),
                'after_stock': product.get('after_stock'),
            }
        
        log = WarehouseLog.objects.create(
            name=product.get('name', ''),
            sn_code=product.get('sn_code', ''),
            material_code=product.get('material_code', ''),
            storage_status=storage_status,
            count=abs(product.get('quantity_change', 1)),
            description=description,
            operator_id=operator_info['operator_id'],
            operator_name=operator_info['operator_name'],
            module=module,
            operation_detail=[operation_detail] if isinstance(operation_detail, dict) else operation_detail,
        )
        
        return log
        
    except Exception as e:
        logger.error(f"创建单个产品日志失败: {str(e)}", exc_info=True)
        return None
