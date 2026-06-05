"""系统管理-系统配置路由。

"""

from rest_framework.routers import SimpleRouter

from .views import ConfigViewSet


router = SimpleRouter(trailing_slash=False)
router.register(r"", ConfigViewSet, basename="configs")

urlpatterns = router.urls
