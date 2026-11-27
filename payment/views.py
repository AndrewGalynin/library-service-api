import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404
from django_q.tasks import async_task
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from payment.models import Payment
from payment.serializers import PaymentSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Payment.objects.select_related(
        "borrowing", "borrowing__book", "borrowing__user"
    )
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_staff:
            queryset = queryset.filter(borrowing__user=self.request.user)
        return queryset

    @extend_schema(
        summary="Confirm successful Stripe payment",
        description=(
            "Callback endpoint for Stripe Checkout success redirect. "
            "Verifies payment status "
            "via Stripe API using session_id, marks the Payment as PAID, "
            "and sends a Telegram notification."
        ),
        parameters=[
            OpenApiParameter(
                name="session_id",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Stripe Checkout Session ID returned in the redirect URL.",
            ),
        ],
        responses={200: PaymentSerializer},
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="success",
        permission_classes=(AllowAny,),
    )
    def success(self, request):
        session_id = request.query_params.get("session_id")
        if not session_id:
            return Response(
                {"detail": "session_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = get_object_or_404(Payment, session_id=session_id)

        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if session.payment_status == "paid":
            if payment.status != Payment.Status.PAID:
                payment.status = Payment.Status.PAID
                payment.save(update_fields=["status"])

                message = (
                    f"<b>Payment Successful!</b>\n"
                    f"Payment ID: #{payment.id}\n"
                    f"Type: {payment.type}\n"
                    f"Amount: ${payment.money_to_pay}\n"
                    f"Borrowing ID: #{payment.borrowing.id}\n"
                    f"Book: {payment.borrowing.book.title}\n"
                    f"User: {payment.borrowing.user.email}"
                )
                async_task(
                    "notification.tasks.send_telegram_notification",
                    message,
                )

            serializer = self.get_serializer(payment)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            {"detail": "Payment has not been completed yet."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @extend_schema(
        summary="Handle cancelled Stripe payment",
        description="Callback endpoint for Stripe Checkout cancel redirect. "
                    "Informs the user that payment is paused.",
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="cancel",
        permission_classes=(AllowAny,),
    )
    def cancel(self, request):
        return Response(
            {
                "detail": (
                    "Payment was cancelled or paused. "
                    "The payment session remains available for 24 hours."
                )
            },
            status=status.HTTP_200_OK,
        )
