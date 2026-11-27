from django_q.tasks import async_task
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from borrowing.models import Borrowing
from borrowing.serializers import (
    BorrowingCreateSerializer,
    BorrowingReturnSerializer,
    BorrowingSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="List borrowings",
        description=(
            "Retrieve a list of book borrowings. "
            "Regular users only see their own "
            "borrowings, while staff users see all records "
            "and can filter by user_id."
        ),
        parameters=[
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by active status "
                            "(true = not returned yet, "
                            "false = already returned).",
            ),
            OpenApiParameter(
                name="user_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter borrowings by specific user ID "
                            "(available for admin users only).",
            ),
        ],
    ),
    create=extend_schema(
        summary="Create a new borrowing",
        description=(
            "Borrow a book by providing book ID and expected_return_date. "
            "Atomically decreases book inventory by 1, "
            "creates a pending Stripe payment session, "
            "and sends a Telegram notification to administrators."
        ),
    ),
    retrieve=extend_schema(
        summary="Retrieve borrowing details",
        description="Get detailed information about a specific borrowing, "
                    "including linked Stripe payments.",
    ),
)
class BorrowingViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Borrowing.objects.select_related(
        "book",
        "user"
    ).prefetch_related("payments")
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        else:
            user_id = self.request.query_params.get("user_id")
            if user_id and user_id.isdigit():
                queryset = queryset.filter(user_id=int(user_id))

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() == "true":
                queryset = queryset.filter(actual_return_date__isnull=True)
            elif is_active.lower() == "false":
                queryset = queryset.filter(actual_return_date__isnull=False)

        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return BorrowingCreateSerializer
        if self.action == "return_book":
            return BorrowingReturnSerializer
        return BorrowingSerializer

    def perform_create(self, serializer):
        borrowing = serializer.save(user=self.request.user)
        message = (
            f"<b>New Borrowing Created!</b>\n"
            f"ID: #{borrowing.id}\n"
            f"Book: {borrowing.book.title} ({borrowing.book.author})\n"
            f"User: {borrowing.user.email}\n"
            f"Borrow date: {borrowing.borrow_date}\n"
            f"Expected return date: {borrowing.expected_return_date}"
        )
        async_task("notification.tasks.send_telegram_notification", message)

    @extend_schema(
        summary="Return a borrowed book",
        description=(
            "Sets actual_return_date to today and "
            "atomically increases the book's inventory by 1. "
            "If the book is returned after expected_return_date, "
            "automatically generates a Stripe "
            "Checkout Session for the overdue fine. "
            "No request body is required."
        ),
        request=None,
        responses={200: BorrowingSerializer},
    )
    @action(
        methods=["POST"],
        detail=True,
        url_path="return",
    )
    def return_book(self, request, pk=None):
        borrowing = self.get_object()
        serializer = self.get_serializer(borrowing, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
