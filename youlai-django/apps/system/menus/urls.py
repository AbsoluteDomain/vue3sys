"""系统管理-菜单路由。

"""

from rest_framework.routers import SimpleRouter

from .views import MenuViewSet


router = SimpleRouter(trailing_slash=False)
router.register(r"", MenuViewSet, basename="menus")

urlpatterns = router.urls
