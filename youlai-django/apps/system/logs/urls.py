"""系统管理-日志路由。

"""

from rest_framework.routers import SimpleRouter

from .views import LogViewSet


router = SimpleRouter(trailing_slash=False)
router.register(r"", LogViewSet, basename="logs")

urlpatterns = router.urls
