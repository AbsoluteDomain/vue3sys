"""系统管理-通知公告路由。

"""

from rest_framework.routers import SimpleRouter

from .views import NoticeViewSet


router = SimpleRouter(trailing_slash=False)
router.register(r"", NoticeViewSet, basename="notices")

urlpatterns = router.urls
