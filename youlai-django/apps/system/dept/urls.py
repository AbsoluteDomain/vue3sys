"""系统管理-部门路由。

"""

from rest_framework.routers import SimpleRouter

from .views import DeptViewSet


router = SimpleRouter(trailing_slash=False)
router.register(r"", DeptViewSet, basename="depts")

urlpatterns = router.urls
