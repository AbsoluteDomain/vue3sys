"""系统管理-字典路由。

"""

from rest_framework.routers import SimpleRouter

from .views import DictItemViewSet, DictViewSet


router = SimpleRouter(trailing_slash=False)
router.register(r"", DictViewSet, basename="dicts")
router.register(r"(?P<dict_code>[^/.]+)/items", DictItemViewSet, basename="dict-items")

urlpatterns = router.urls
