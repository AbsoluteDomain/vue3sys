"""系统管理-角色路由。

"""

from rest_framework.routers import SimpleRouter

from .views import RoleViewSet


router = SimpleRouter(trailing_slash=False)
router.register(r"", RoleViewSet, basename="roles")

urlpatterns = router.urls
