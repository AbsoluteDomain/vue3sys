"""系统管理-统计路由。

"""

from rest_framework.routers import SimpleRouter

from .views import VisitViewSet


router = SimpleRouter(trailing_slash=False)
router.register(r"", VisitViewSet, basename="statistics")

urlpatterns = router.urls
