"""系统管理-用户路由。

"""

from rest_framework.routers import SimpleRouter

from .views import UserViewSet


router = SimpleRouter(trailing_slash=False)
router.register(r"", UserViewSet, basename="users")

urlpatterns = router.urls
