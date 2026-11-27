from django.urls import include, path
from rest_framework.routers import DefaultRouter

from payment.views import PaymentViewSet

app_name = "payment"

router = DefaultRouter()
router.register("", PaymentViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
