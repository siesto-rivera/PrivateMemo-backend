from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, MemoViewSet


router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"memos", MemoViewSet, basename="memo")

urlpatterns = router.urls
