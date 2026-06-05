"""在线用户数统计定时任务。

定时统计并广播当前在线用户数量到所有WebSocket客户端。
用于解决以下问题：
- 客户端页面刷新后可快速同步最新在线人数
- 减少服务端主动推送频率，降低资源消耗
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings

from apps.websocket.session_registry import get_user_session_registry

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler = None


def broadcast_online_user_count():
    """定时统计在线用户数并广播。"""
    registry = get_user_session_registry()
    online_count = registry.get_online_user_count()
    session_count = registry.get_total_session_count()

    logger.debug(f"定时统计：在线用户数={online_count}, 总会话数={session_count}")

    # 广播在线用户数量（需要配合WebSocket实现）
    try:
        from apps.websocket.consumers import broadcast_to_topic
        broadcast_to_topic('/topic/online-count', online_count)
    except ImportError:
        pass


def start_online_user_count_job():
    """启动在线用户数统计定时任务。"""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler()
    # 每3分钟执行一次
    _scheduler.add_job(
        broadcast_online_user_count,
        'cron',
        minute='*/3',
        id='online_user_count_job'
    )
    _scheduler.start()
    logger.info("在线用户数统计定时任务已启动")


def stop_online_user_count_job():
    """停止在线用户数统计定时任务。"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("在线用户数统计定时任务已停止")
