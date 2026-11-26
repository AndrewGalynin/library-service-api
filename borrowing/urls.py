from django.urls import include, path
from rest_framework.routers import DefaultRouter

from borrowing.views import BorrowingViewSet

app_name = "borrowing"

router = DefaultRouter()
router.register("", BorrowingViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
